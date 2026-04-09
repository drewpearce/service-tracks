"""StreamingAdapter abstract base class, dataclasses, and factory."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.streaming_connection import StreamingConnection


@dataclass
class TrackSearchResult:
    track_id: str
    title: str
    artist: str
    album: str | None
    image_url: str | None
    duration_ms: int | None


@dataclass
class PlaylistInfo:
    external_id: str
    url: str
    name: str


class StreamingAdapter(ABC):
    """Interface for streaming platform integrations."""

    @abstractmethod
    async def search_tracks(self, query: str, limit: int = 10) -> list[TrackSearchResult]: ...

    @abstractmethod
    async def create_playlist(self, name: str, description: str) -> PlaylistInfo: ...

    @abstractmethod
    async def get_playlist_tracks(self, playlist_id: str) -> list[str]: ...

    @abstractmethod
    async def replace_playlist_tracks(self, playlist_id: str, track_ids: list[str]) -> None: ...

    @abstractmethod
    async def get_playlist_url(self, playlist_id: str) -> str: ...

    @abstractmethod
    async def validate_connection(self) -> bool: ...

    async def update_playlist_details(self, playlist_id: str, name: str, description: str) -> None:
        """Update the name and description of an existing playlist.

        Default no-op — adapters that support this should override it.
        """
        return

    async def find_playlist_by_name(self, name: str) -> "PlaylistInfo | None":
        """Search the user's playlists for one matching the given name.

        Default returns None — adapters that support this should override it.
        Used in shared mode to connect to an existing playlist rather than
        creating a duplicate.
        """
        return None


def get_streaming_adapter(
    platform: str, connection: StreamingConnection, db: AsyncSession | None = None
) -> StreamingAdapter:
    """Factory: return the appropriate adapter for the given platform."""
    if platform == "spotify":
        from app.adapters.spotify_adapter import SpotifyAdapter

        return SpotifyAdapter(connection, db=db)
    raise NotImplementedError(f"Unsupported streaming platform: {platform}")
