"""Schemas for church settings endpoints."""

from pydantic import BaseModel, Field


class ChurchSettingsResponse(BaseModel):
    playlist_mode: str
    playlist_name_template: str
    playlist_description_template: str


class ChurchSettingsUpdate(BaseModel):
    playlist_mode: str | None = Field(default=None, pattern="^(shared|per_plan)$")
    playlist_name_template: str | None = Field(default=None, min_length=1, max_length=500)
    playlist_description_template: str | None = Field(default=None, max_length=1000)
