from pydantic import BaseModel, Field

# --- Unmatched songs ---


class UnmatchedSong(BaseModel):
    pco_song_id: str
    title: str
    artist: str | None = None
    last_used_date: str  # ISO date string from the plan's sort_date


class UnmatchedSongsResponse(BaseModel):
    unmatched_songs: list[UnmatchedSong]


# --- Search ---


class TrackSearchResultSchema(BaseModel):
    track_id: str
    title: str
    artist: str
    album: str | None = None
    image_url: str | None = None
    duration_ms: int | None = None


class SearchResponse(BaseModel):
    results: list[TrackSearchResultSchema]


# --- Match (Task 6.2) ---


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


# --- Mappings (Task 6.2) ---


class SongMappingSchema(BaseModel):
    id: str
    pco_song_id: str
    pco_song_title: str
    pco_song_artist: str | None
    platform: str
    track_id: str
    track_title: str
    track_artist: str | None


class MappingsResponse(BaseModel):
    mappings: list[SongMappingSchema]
