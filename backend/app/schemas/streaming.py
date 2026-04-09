"""Pydantic models for streaming API request/response."""

from pydantic import BaseModel


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
