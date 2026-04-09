"""YouTube Music implementation of the StreamingAdapter interface.

Uses the YouTube Data API v3. Tracks are represented by bare YouTube video IDs
(e.g., "dQw4w9WgXcW"). Playlist URLs point to music.youtube.com so the UI sends
users to YouTube Music rather than regular YouTube.
"""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.streaming import PlaylistInfo, StreamingAdapter, TrackSearchResult
from app.models.search_cache import SearchCache
from app.models.streaming_connection import StreamingConnection
from app.utils.encryption import decrypt

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class YouTubeApiError(Exception):
    """Base exception for YouTube API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class YouTubeAuthError(YouTubeApiError):
    """Raised on 401/403 token issues."""

    pass


class YouTubeRateLimitError(YouTubeApiError):
    """Raised on 429 responses."""

    def __init__(self, message: str, retry_after: int = 1, status_code: int | None = 429):
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# YouTubeAdapter
# ---------------------------------------------------------------------------


class YouTubeAdapter(StreamingAdapter):
    """YouTube Data API v3 implementation of the StreamingAdapter interface."""

    YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
    MUSIC_PLAYLIST_URL = "https://music.youtube.com/playlist?list={playlist_id}"
    TOKEN_REFRESH_BUFFER = timedelta(minutes=5)
    SEARCH_CACHE_TTL = timedelta(days=7)
    REQUEST_TIMEOUT = 15.0

    def __init__(self, connection: StreamingConnection, db: AsyncSession | None = None):
        self._connection = connection
        self._db = db
        self._access_token = decrypt(connection.access_token_encrypted)
        self._external_user_id = connection.external_user_id

    # ------------------------------------------------------------------
    # Auth + request plumbing
    # ------------------------------------------------------------------

    async def _ensure_token_fresh(self) -> None:
        """Refresh the access token if it expires within TOKEN_REFRESH_BUFFER."""
        from app.services.streaming_service import refresh_youtube_token

        token_expires_at = self._connection.token_expires_at
        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now + self.TOKEN_REFRESH_BUFFER >= token_expires_at:
            if self._db is None:
                raise RuntimeError("YouTubeAdapter requires a db session for token refresh but none was provided.")
            new_access_token = await refresh_youtube_token(self._db, self._connection)
            self._access_token = new_access_token

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make an authenticated request to the YouTube API with auto-refresh."""
        await self._ensure_token_fresh()

        async with httpx.AsyncClient(
            base_url=self.YOUTUBE_API_BASE,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=self.REQUEST_TIMEOUT,
        ) as client:
            response = await client.request(method, path, **kwargs)

        if response.status_code in (401, 403):
            self._connection.status = "error"
            if self._db is not None:
                await self._db.flush()
            raise YouTubeAuthError(
                f"YouTube token expired or forbidden ({response.status_code})",
                status_code=response.status_code,
            )

        if response.status_code == 429:
            retry_after_str = response.headers.get("Retry-After", "1")
            try:
                retry_after = int(retry_after_str)
            except ValueError:
                retry_after = 1
            raise YouTubeRateLimitError(
                "YouTube rate limit exceeded",
                retry_after=retry_after,
                status_code=429,
            )

        if response.status_code >= 400:
            raise YouTubeApiError(
                f"YouTube API error: {response.status_code}",
                status_code=response.status_code,
            )

        return response

    # ------------------------------------------------------------------
    # search_tracks with 7-day cache
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_image(thumbnails: dict) -> str | None:
        for key in ("high", "medium", "default"):
            if key in thumbnails and thumbnails[key].get("url"):
                return thumbnails[key]["url"]
        return None

    def _parse_search_items(self, items: list[dict]) -> list[TrackSearchResult]:
        results: list[TrackSearchResult] = []
        for item in items:
            id_field = item.get("id") or {}
            video_id = id_field.get("videoId") if isinstance(id_field, dict) else None
            if not video_id:
                continue
            snippet = item.get("snippet") or {}
            thumbnails = snippet.get("thumbnails") or {}
            results.append(
                TrackSearchResult(
                    track_id=video_id,
                    title=snippet.get("title", ""),
                    artist=snippet.get("channelTitle", ""),
                    album=None,
                    image_url=self._pick_image(thumbnails),
                    duration_ms=None,
                )
            )
        return results

    async def _load_cache(self, query: str) -> list[TrackSearchResult] | None:
        if self._db is None:
            return None
        result = await self._db.execute(
            select(SearchCache).where(
                SearchCache.platform == "youtube",
                SearchCache.query == query,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created_at > self.SEARCH_CACHE_TTL:
            return None

        raw = row.results
        if isinstance(raw, dict):
            raw_items = raw.get("items", [])
        elif isinstance(raw, list):
            raw_items = raw
        else:
            return None
        return [TrackSearchResult(**item) for item in raw_items]

    async def _save_cache(self, query: str, results: list[TrackSearchResult]) -> None:
        if self._db is None:
            return
        payload = {"items": [asdict(r) for r in results]}

        existing = await self._db.execute(
            select(SearchCache).where(
                SearchCache.platform == "youtube",
                SearchCache.query == query,
            )
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            row.results = payload
            row.created_at = datetime.now(timezone.utc)
        else:
            self._db.add(
                SearchCache(
                    platform="youtube",
                    query=query,
                    results=payload,
                )
            )
        await self._db.flush()

    async def search_tracks(self, query: str, limit: int = 10) -> list[TrackSearchResult]:
        """Search YouTube Music for tracks matching the query, with 7-day cache."""
        cached = await self._load_cache(query)
        if cached is not None:
            return cached

        response = await self._request(
            "GET",
            "/search",
            params={
                "part": "snippet",
                "type": "video",
                "videoCategoryId": "10",
                "q": query,
                "maxResults": limit,
            },
        )
        items = response.json().get("items", [])
        results = self._parse_search_items(items)
        await self._save_cache(query, results)
        return results

    # ------------------------------------------------------------------
    # Playlist methods
    # ------------------------------------------------------------------

    async def create_playlist(self, name: str, description: str) -> PlaylistInfo:
        """Create a new YouTube playlist for the connected user."""
        response = await self._request(
            "POST",
            "/playlists",
            params={"part": "snippet,status"},
            json={
                "snippet": {"title": name, "description": description},
                "status": {"privacyStatus": "public"},
            },
        )
        data = response.json()
        playlist_id = data["id"]
        return PlaylistInfo(
            external_id=playlist_id,
            url=self.MUSIC_PLAYLIST_URL.format(playlist_id=playlist_id),
            name=data.get("snippet", {}).get("title", name),
        )

    async def _list_playlist_items_full(self, playlist_id: str) -> list[dict]:
        """Return the raw playlistItems (id + contentDetails) for a playlist."""
        response = await self._request(
            "GET",
            "/playlistItems",
            params={
                "part": "id,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            },
        )
        return response.json().get("items", [])

    async def get_playlist_tracks(self, playlist_id: str) -> list[str]:
        """Return the list of video IDs in a YouTube playlist."""
        response = await self._request(
            "GET",
            "/playlistItems",
            params={
                "part": "contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            },
        )
        items = response.json().get("items", [])
        return [item["contentDetails"]["videoId"] for item in items if item.get("contentDetails")]

    async def replace_playlist_tracks(self, playlist_id: str, track_ids: list[str]) -> None:
        """Replace all tracks in a YouTube playlist (diff-based to save quota)."""
        current_items = await self._list_playlist_items_full(playlist_id)
        current_video_ids = [item["contentDetails"]["videoId"] for item in current_items if item.get("contentDetails")]

        if list(current_video_ids) == list(track_ids):
            return

        # Delete existing items (using playlistItem ids, not video ids).
        for item in current_items:
            item_id = item.get("id")
            if not item_id:
                continue
            await self._request("DELETE", "/playlistItems", params={"id": item_id})

        # Insert new items in order.
        for video_id in track_ids:
            await self._request(
                "POST",
                "/playlistItems",
                params={"part": "snippet"},
                json={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    }
                },
            )

    async def get_playlist_url(self, playlist_id: str) -> str:
        """Return the YouTube Music URL for a playlist (no API call needed)."""
        return self.MUSIC_PLAYLIST_URL.format(playlist_id=playlist_id)

    async def validate_connection(self) -> bool:
        """Validate the YouTube connection by calling channels.list?mine=true."""
        try:
            response = await self._request(
                "GET",
                "/channels",
                params={"part": "id", "mine": "true"},
            )
        except YouTubeAuthError:
            return False
        items = response.json().get("items", [])
        return bool(items)

    async def update_playlist_details(self, playlist_id: str, name: str, description: str) -> None:
        """Update the name and description of an existing YouTube playlist."""
        await self._request(
            "PUT",
            "/playlists",
            params={"part": "snippet"},
            json={
                "id": playlist_id,
                "snippet": {
                    "title": name,
                    "description": description,
                },
            },
        )

    async def find_playlist_by_name(self, name: str) -> "PlaylistInfo | None":
        """Search the user's playlists (first 50) for one matching the given name."""
        response = await self._request(
            "GET",
            "/playlists",
            params={"part": "snippet", "mine": "true", "maxResults": 50},
        )
        items = response.json().get("items", [])
        for item in items:
            snippet = item.get("snippet") or {}
            if snippet.get("title") == name:
                playlist_id = item["id"]
                return PlaylistInfo(
                    external_id=playlist_id,
                    url=self.MUSIC_PLAYLIST_URL.format(playlist_id=playlist_id),
                    name=snippet.get("title", name),
                )
        return None
