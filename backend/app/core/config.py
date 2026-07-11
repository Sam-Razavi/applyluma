from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the project root regardless of where alembic/uvicorn is invoked from.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # backend/app/core -> backend/app -> backend -> project root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "ApplyLuma"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql://applyluma:applyluma@localhost:5432/applyluma"
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 100
    ANALYTICS_CACHE_TTL_HOURS: int = 1

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://applyluma.com",
        "https://applyluma.vercel.app",
    ]

    STORAGE_DIR: str = "/app/storage"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB

    OPENAI_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    ADZUNA_APP_ID: str = ""
    ADZUNA_API_KEY: str = ""
    ADZUNA_COUNTRY: str = "gb"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PREMIUM_PRICE_ID: str = ""
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "ApplyLuma <notifications@applyluma.com>"
    FRONTEND_URL: str = "https://applyluma.com"
    # Cloudflare Turnstile: default is the official test key that always passes.
    # Set a real key from https://dash.cloudflare.com in production.
    TURNSTILE_SECRET_KEY: str = "1x0000000000000000000000000000000AA"
    CONTACT_VERIFY_SECRET: str = ""
    # Override via CONTACT_RECIPIENT_EMAIL env var in production.
    CONTACT_RECIPIENT_EMAIL: str = "sam@samincodes.com"
    # Failed tailor + cover-letter jobs in the trailing hour that trigger a
    # health watchdog alert.
    WATCHDOG_FAILURE_SPIKE_THRESHOLD: int = 5


settings = Settings()
