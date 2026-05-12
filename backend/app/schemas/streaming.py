"""Pydantic models for streaming API request/response."""

from pydantic import BaseModel, Field


class SpotifyAuthorizeResponse(BaseModel):
    authorization_url: str


class YouTubeAuthorizeResponse(BaseModel):
    authorization_url: str


class StreamingConnectionStatus(BaseModel):
    platform: str
    connected: bool
    status: str
    external_user_id: str


class StreamingStatusResponse(BaseModel):
    connections: list[StreamingConnectionStatus]


class StreamingSettingsResponse(BaseModel):
    platform: str
    playlist_mode: str
    playlist_name_template: str
    playlist_description_template: str


class StreamingSettingsUpdate(BaseModel):
    playlist_mode: str | None = Field(default=None, pattern="^(shared|per_plan)$")
    playlist_name_template: str | None = Field(default=None, min_length=1, max_length=500)
    playlist_description_template: str | None = Field(default=None, max_length=1000)
