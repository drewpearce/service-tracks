from pydantic import BaseModel

from app.schemas.sync import PlatformSyncResult


class SyncTriggerResponse(BaseModel):
    sync_status: str
    songs_total: int
    songs_matched: int
    songs_unmatched: int
    platforms: list[PlatformSyncResult]
