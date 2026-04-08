from pydantic import BaseModel, Field


class PcoConnectRequest(BaseModel):
    application_id: str = Field(min_length=1)
    secret: str = Field(min_length=1)


class ServiceType(BaseModel):
    id: str
    name: str


class PcoConnectResponse(BaseModel):
    status: str
    service_types: list[ServiceType]


class PcoStatusResponse(BaseModel):
    connected: bool
    auth_method: str | None
    status: str | None
    last_successful_call_at: str | None  # ISO 8601 string or None
    service_type_id: str | None = None
    service_type_name: str | None = None


class SelectServiceTypeRequest(BaseModel):
    service_type_id: str = Field(min_length=1)


class SelectServiceTypeResponse(BaseModel):
    service_type_id: str
    service_type_name: str


class Plan(BaseModel):
    id: str
    title: str
    sort_date: str  # ISO date string
    series_title: str | None = None


class PlanSong(BaseModel):
    pco_song_id: str
    title: str
    artist: str | None = None
