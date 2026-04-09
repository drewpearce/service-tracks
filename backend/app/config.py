import json

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Core
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # Database — accepts postgres:// or postgresql:// and normalises to postgresql+asyncpg://
    DATABASE_URL: str = "postgresql+asyncpg://worship_flow:worship_flow@localhost:5432/service_tracks"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalise_database_url(cls, v: object) -> object:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            # asyncpg uses ?ssl=require, not ?sslmode=require
            v = v.replace("sslmode=", "ssl=")
        return v

    # Encryption
    ENCRYPTION_KEY: str = ""  # Fernet key, required in production

    # Spotify OAuth
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    SPOTIFY_REDIRECT_URI: str = "http://127.0.0.1:8000/api/streaming/spotify/callback"

    # YouTube OAuth
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/streaming/youtube/callback"

    # Email (Resend)
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "noreply@localhost"

    # Monitoring
    SENTRY_DSN: str = ""

    # PCO
    PCO_WEBHOOK_SECRET: str = ""

    # CORS — accepts a JSON array string or a comma-separated string from env
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # CSRF
    CSRF_SECRET: str = "dev-csrf-secret-change-in-production"

    # Frontend URL (used in email verification and password reset links)
    FRONTEND_URL: str = "http://localhost:5173"

    # Session cookie security (False for local dev over HTTP, True in production)
    SESSION_COOKIE_SECURE: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
