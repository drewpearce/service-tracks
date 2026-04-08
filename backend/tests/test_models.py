"""Lightweight tests that verify all models are registered with Base.metadata."""

import app.models  # noqa: F401 -- ensure all models are registered
from app.database import Base
from app.models import (
    Church,
    ChurchUser,
    PcoConnection,
    Playlist,
    SearchCache,
    SongMapping,
    StreamingConnection,
    SyncLog,
    UserSession,
    YouTubeQuotaUsage,
)

EXPECTED_TABLES = {
    "church",
    "church_user",
    "pco_connection",
    "streaming_connection",
    "song_mapping",
    "playlist",
    "sync_log",
    "youtube_quota_usage",
    "search_cache",
    "user_session",
}


def test_all_tables_registered():
    """All 10 expected tables are registered in Base.metadata."""
    registered = set(Base.metadata.tables.keys())
    assert EXPECTED_TABLES == registered, (
        f"Missing tables: {EXPECTED_TABLES - registered}; Unexpected tables: {registered - EXPECTED_TABLES}"
    )


def test_model_tablenames():
    """Each model class has the correct __tablename__."""
    expected = [
        (Church, "church"),
        (ChurchUser, "church_user"),
        (PcoConnection, "pco_connection"),
        (StreamingConnection, "streaming_connection"),
        (SongMapping, "song_mapping"),
        (Playlist, "playlist"),
        (SyncLog, "sync_log"),
        (YouTubeQuotaUsage, "youtube_quota_usage"),
        (SearchCache, "search_cache"),
        (UserSession, "user_session"),
    ]
    for model_cls, expected_name in expected:
        assert model_cls.__tablename__ == expected_name, (
            f"{model_cls.__name__}.__tablename__ is {model_cls.__tablename__!r}, expected {expected_name!r}"
        )
