from pydantic import BaseModel, Field

# --- Per-platform mapping state ---


class PlatformMappingState(BaseModel):
    matched: bool
    mapping_id: str | None = None
    track_id: str | None = None
    track_title: str | None = None
    track_artist: str | None = None


class SongWithPlatforms(BaseModel):
    pco_song_id: str
    title: str
    artist: str | None = None
    last_used_date: str | None = None
    platforms: dict[str, PlatformMappingState]


# --- Unmatched songs ---


class UnmatchedSongsResponse(BaseModel):
    unmatched_songs: list[SongWithPlatforms]


# --- Search ---


class TrackSearchResultSchema(BaseModel):
    track_id: str
    title: str
    artist: str
    album: str | None = None
    image_url: str | None = None
    duration_ms: int | None = None
    preview_url: str | None = None
    external_url: str | None = None


class SearchResponse(BaseModel):
    results: list[TrackSearchResultSchema]


# --- Match ---


class MatchRequest(BaseModel):
    pco_song_id: str = Field(min_length=1)
    pco_song_title: str = Field(min_length=1)
    pco_song_artist: str | None = None
    platform: str = Field(min_length=1)
    track_id: str = Field(min_length=1)
    track_title: str = Field(min_length=1)
    track_artist: str | None = None


class MatchResponse(BaseModel):
    mapping_id: str
    pco_song_title: str
    pco_song_artist: str | None
    track_title: str
    track_artist: str | None
    platform: str


# --- Mappings ---


class MappingsResponse(BaseModel):
    songs: list[SongWithPlatforms]
