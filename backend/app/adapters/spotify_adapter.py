"""Spotify implementation of the StreamingAdapter interface."""

from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.streaming import PlaylistInfo, StreamingAdapter, TrackSearchResult
from app.models.streaming_connection import StreamingConnection
from app.utils.encryption import decrypt

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SpotifyApiError(Exception):
    """Base exception for Spotify API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SpotifyAuthError(SpotifyApiError):
    """Raised on 401 responses (token expired/revoked)."""

    pass


class SpotifyRateLimitError(SpotifyApiError):
    """Raised on 429 responses."""

    def __init__(self, message: str, retry_after: int = 1, status_code: int | None = 429):
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


class SpotifyForbiddenError(SpotifyApiError):
    """Raised on 403 responses (insufficient scope)."""

    pass


# ---------------------------------------------------------------------------
# SpotifyAdapter
# ---------------------------------------------------------------------------


class SpotifyAdapter(StreamingAdapter):
    """Spotify implementation of the StreamingAdapter interface."""

    SPOTIFY_API_BASE = "https://api.spotify.com/v1"
    TOKEN_REFRESH_BUFFER = timedelta(minutes=5)
    REQUEST_TIMEOUT = 15.0

    def __init__(self, connection: StreamingConnection, db: AsyncSession | None = None):
        self._connection = connection
        self._db = db
        self._access_token = decrypt(connection.access_token_encrypted)
        self._external_user_id = connection.external_user_id

    async def _ensure_token_fresh(self) -> None:
        """Refresh the access token if it expires within TOKEN_REFRESH_BUFFER."""
        from app.services.streaming_service import refresh_spotify_token

        token_expires_at = self._connection.token_expires_at
        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now + self.TOKEN_REFRESH_BUFFER >= token_expires_at:
            if self._db is None:
                raise RuntimeError(
                    "SpotifyAdapter requires a db session for token refresh but none was provided."
                )
            new_access_token = await refresh_spotify_token(self._db, self._connection)
            self._access_token = new_access_token

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make an authenticated request to the Spotify API with auto-refresh."""
        await self._ensure_token_fresh()

        async with httpx.AsyncClient(
            base_url=self.SPOTIFY_API_BASE,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=self.REQUEST_TIMEOUT,
        ) as client:
            response = await client.request(method, path, **kwargs)

        if response.status_code == 401:
            self._connection.status = "error"
            if self._db is not None:
                await self._db.flush()
            raise SpotifyAuthError("Spotify token expired or revoked", status_code=401)

        if response.status_code == 429:
            retry_after_str = response.headers.get("Retry-After", "1")
            try:
                retry_after = int(retry_after_str)
            except ValueError:
                retry_after = 1
            raise SpotifyRateLimitError(
                "Spotify rate limit exceeded",
                retry_after=retry_after,
                status_code=429,
            )

        if response.status_code == 403:
            raise SpotifyForbiddenError(
                "Spotify request forbidden (insufficient scope?)",
                status_code=403,
            )

        if response.status_code >= 400:
            raise SpotifyApiError(
                f"Spotify API error: {response.status_code}",
                status_code=response.status_code,
            )

        return response

    async def search_tracks(self, query: str, limit: int = 10) -> list[TrackSearchResult]:
        """Search Spotify for tracks matching the query."""
        response = await self._request(
            "GET",
            "/search",
            params={"type": "track", "q": query, "limit": limit},
        )
        items = response.json()["tracks"]["items"]
        results = []
        for item in items:
            images = item["album"].get("images", [])
            image_url = images[0]["url"] if images else None
            results.append(
                TrackSearchResult(
                    track_id=item["uri"],
                    title=item["name"],
                    artist=", ".join(a["name"] for a in item["artists"]),
                    album=item["album"]["name"],
                    image_url=image_url,
                    duration_ms=item["duration_ms"],
                )
            )
        return results

    async def create_playlist(self, name: str, description: str) -> PlaylistInfo:
        """Create a new Spotify playlist for the connected user."""
        response = await self._request(
            "POST",
            f"/users/{self._external_user_id}/playlists",
            json={"name": name, "description": description, "public": True},
        )
        data = response.json()
        return PlaylistInfo(
            external_id=data["id"],
            url=data["external_urls"]["spotify"],
            name=data["name"],
        )

    async def get_playlist_tracks(self, playlist_id: str) -> list[str]:
        """Return the list of track URIs in a Spotify playlist."""
        response = await self._request(
            "GET",
            f"/playlists/{playlist_id}/tracks",
            params={"fields": "items(track(uri))"},
        )
        data = response.json()
        return [
            item["track"]["uri"]
            for item in data["items"]
            if item.get("track")
        ]

    async def replace_playlist_tracks(self, playlist_id: str, track_ids: list[str]) -> None:
        """Replace all tracks in a Spotify playlist."""
        await self._request(
            "PUT",
            f"/playlists/{playlist_id}/tracks",
            json={"uris": track_ids},
        )

    async def get_playlist_url(self, playlist_id: str) -> str:
        """Return the Spotify web URL for a playlist (no API call needed)."""
        return f"https://open.spotify.com/playlist/{playlist_id}"

    async def validate_connection(self) -> bool:
        """Validate the Spotify connection by calling /me."""
        try:
            await self._request("GET", "/me")
            return True
        except SpotifyAuthError:
            return False

    async def update_playlist_details(self, playlist_id: str, name: str, description: str) -> None:
        """Update the name and description of an existing Spotify playlist."""
        await self._request(
            "PUT",
            f"/playlists/{playlist_id}",
            json={"name": name, "description": description},
        )

    async def find_playlist_by_name(self, name: str) -> "PlaylistInfo | None":
        """Search the current user's playlists for one matching the given name.

        Checks the first 50 playlists (one API call). Returns the first match
        or None if no playlist with that name is found.
        """
        from app.adapters.streaming import PlaylistInfo

        response = await self._request("GET", "/me/playlists", params={"limit": 50})
        items = response.json().get("items", [])
        for item in items:
            if item.get("name") == name:
                return PlaylistInfo(
                    external_id=item["id"],
                    url=item["external_urls"]["spotify"],
                    name=item["name"],
                )
        return None
