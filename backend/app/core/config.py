"""Central application configuration.

All environment access goes through ``Settings``. Nothing else in the backend
should read ``os.environ``. Validation errors name the offending variable but
never echo its value, because values may contain credentials.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Fragments that only appear in unedited template values.
_PLACEHOLDER_MARKERS = ("YOUR_", "USER:PASSWORD", "HOST:PORT", "CHANGE_ME")


class ConfigurationError(RuntimeError):
    """Raised at startup when required configuration is missing or invalid."""


def _is_placeholder(value: str) -> bool:
    upper = value.upper()
    return any(marker in upper for marker in _PLACEHOLDER_MARKERS)


class Settings(BaseSettings):
    # The env file is anchored to backend/ so startup does not depend on the
    # working directory. Real environment variables take precedence.
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "PlotPlanner"
    api_prefix: str = "/api/v1"

    database_url: str
    supabase_url: str
    supabase_jwt_audience: str = "authenticated"
    frontend_url: str = "http://localhost:5173"

    # Optional integrations: the features that need them report themselves as
    # unconfigured instead of preventing startup.
    llm_provider: str = "groq"
    llm_api_key: str | None = None
    llm_model: str = "openai/gpt-oss-120b"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    youtube_api_key: str | None = None
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    adzuna_country: str = "us"

    max_upload_size_mb: int = 10
    ai_requests_per_minute: int = 12
    mcp_enabled: bool = True

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        if not self.api_prefix.startswith("/") or self.api_prefix.endswith("/"):
            raise ValueError("API_PREFIX must start with '/' and must not end with '/'")

        if _is_placeholder(self.database_url):
            raise ValueError("DATABASE_URL still contains template placeholder text")
        # The Supabase dashboard copies a libpq URI (postgresql://). SQLAlchemy needs the driver named.
        for libpq_scheme in ("postgresql://", "postgres://"):
            if self.database_url.startswith(libpq_scheme):
                self.database_url = "postgresql+psycopg://" + self.database_url[len(libpq_scheme) :]
                break
        if not self.database_url.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must be a postgresql:// connection string")

        if _is_placeholder(self.supabase_url):
            raise ValueError("SUPABASE_URL still contains template placeholder text")
        if not self.supabase_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ValueError("SUPABASE_URL must be an https:// URL")
        if self.supabase_url.endswith("/"):
            raise ValueError("SUPABASE_URL must not end with '/'")

        if not self.frontend_url.startswith(("http://", "https://")) or self.frontend_url.endswith("/"):
            raise ValueError("FRONTEND_URL must be an http(s) origin without a trailing '/'")

        for name in ("llm_api_key", "youtube_api_key", "adzuna_app_id", "adzuna_app_key"):
            value = getattr(self, name)
            if value is not None:
                value = value.strip()
                setattr(self, name, None if not value or _is_placeholder(value) else value)
        if not 1 <= self.max_upload_size_mb <= 50:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be between 1 and 50")
        return self

    @property
    def supabase_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"


def load_settings(**overrides) -> Settings:
    """Build settings, converting validation errors into value-free messages.

    ``overrides`` exist for tests (e.g. ``_env_file=None``); the app passes none.
    """
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        problems = []
        for error in exc.errors(include_input=False, include_url=False):
            name = ".".join(str(part) for part in error["loc"]).upper() or "settings"
            problems.append(f"{name}: {error['msg'].removeprefix('Value error, ')}")
        raise ConfigurationError("Invalid configuration:\n  " + "\n  ".join(problems)) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()
