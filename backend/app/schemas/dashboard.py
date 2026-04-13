"""Pydantic schemas for dashboard and plans endpoints."""

from pydantic import BaseModel

from app.schemas.streaming import StreamingConnectionStatus


class PlanSongWithMatch(BaseModel):
    pco_song_id: str
    title: str
    matched: bool


class PlanPlaylist(BaseModel):
    platform: str
    status: str
    url: str | None = None
    last_synced_at: str | None = None
    error_message: str | None = None


class PlanWithSongs(BaseModel):
    pco_plan_id: str
    date: str  # ISO date string
    title: str
    songs: list[PlanSongWithMatch]
    playlists: list[PlanPlaylist]
    unmatched_count: int


class PlansResponse(BaseModel):
    plans: list[PlanWithSongs]


class SyncLogEntry(BaseModel):
    id: str
    sync_trigger: str
    status: str
    songs_total: int
    songs_matched: int
    songs_unmatched: int
    started_at: str  # ISO datetime string
    completed_at: str | None = None


class DashboardResponse(BaseModel):
    church_name: str
    pco_connected: bool
    service_type_selected: bool
    streaming_connections: list[StreamingConnectionStatus]
    upcoming_plans: list[PlanWithSongs]
    unmatched_song_count: int
    recent_syncs: list[SyncLogEntry]
