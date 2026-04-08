from pydantic import BaseModel


class PlatformSyncResult(BaseModel):
    platform: str
    sync_status: str  # "synced", "pending", "error"
    playlist_url: str | None = None
    error_message: str | None = None


class SyncResult(BaseModel):
    sync_status: str  # "synced", "partial", "pending", "error"
    songs_total: int
    songs_matched: int
    songs_unmatched: int
    platforms: list[PlatformSyncResult]
