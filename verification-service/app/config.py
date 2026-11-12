from functools import lru_cache
import json
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application Settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SERVICE_NAME: str = "freshguard-verification"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

    # CORS Settings
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from comma-separated strings or JSON arrays.

        Accepted formats (via environment variable):
            CORS_ORIGINS=https://example.com,http://localhost:3000
            CORS_ORIGINS=["https://example.com","http://localhost:3000"]

        Rules:
        - An already-constructed list passes through unchanged.
        - A string beginning with '[' is parsed as JSON. If parsing fails, a
          ValueError is raised — misconfiguration is never silently swallowed.
        - A plain comma-separated string is split and stripped.
        - An empty string results in a ValueError (not a silent wildcard fallback).

        The only way to allow all origins is to supply the literal value ['*']
        or the string '*' explicitly.
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                # JSON-array format
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"CORS_ORIGINS looks like a JSON array but could not be parsed: {exc}"
                    ) from exc
                if not isinstance(parsed, list):
                    raise ValueError(
                        "CORS_ORIGINS JSON must be an array of strings, got: "
                        f"{type(parsed).__name__}"
                    )
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
            if not stripped:
                raise ValueError(
                    "CORS_ORIGINS is set to an empty string. "
                    "Supply explicit origins or '*' to allow all."
                )
            # Comma-separated format
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        raise ValueError(f"CORS_ORIGINS must be a string or list, got: {type(v).__name__}")

    # Request body protection
    MAX_REQUEST_BODY_SIZE: int = Field(
        default=1_048_576,  # 1 MiB
        description="Maximum HTTP request body size in bytes. Requests exceeding this are rejected with 413.",
    )

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./freshguard.db"

    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "mock", "openai", "gemini"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TIMEOUT_SECONDS: float = 15.0
    LLM_MAX_RETRIES: int = 2

    # Authentication Settings
    # API_AUTH_MODE controls how the X-API-Key header is enforced:
    #   "disabled" - No authentication required (local development only).
    #   "warn"     - Missing/invalid key is logged but request is allowed.
    #   "enforce"  - Valid X-API-Key is required; invalid requests return HTTP 401.
    # Production deployments MUST use "enforce".
    API_AUTH_MODE: str = Field(default="disabled", validation_alias="API_AUTH_MODE")
    # VERIFICATION_SERVICE_API_KEY - the shared secret sent as X-API-Key by callers.
    # Required when API_AUTH_MODE=enforce. Never hardcode or log this value.
    VERIFICATION_SERVICE_API_KEY: str = Field(
        default="", validation_alias="VERIFICATION_SERVICE_API_KEY"
    )

    @field_validator("API_AUTH_MODE", mode="before")
    @classmethod
    def validate_auth_mode(cls, v: str) -> str:
        """Normalise and validate API_AUTH_MODE at construction time."""
        allowed = {"disabled", "warn", "enforce"}
        normalised = str(v).lower().strip()
        if normalised not in allowed:
            raise ValueError(
                f"API_AUTH_MODE must be one of: {', '.join(sorted(allowed))}. "
                f"Got: '{v}'"
            )
        return normalised

    # Gemini Developer API Settings
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")

    # Tavily API Settings
    TAVILY_API_KEY: str = Field(default="", validation_alias="TAVILY_API_KEY")
    TAVILY_TIMEOUT_SECONDS: float = Field(default=10.0, validation_alias="TAVILY_TIMEOUT")
    TAVILY_MAX_RETRIES: int = 2
    TAVILY_SEARCH_DEPTH: str = Field(default="advanced", validation_alias="TAVILY_SEARCH_DEPTH")
    TAVILY_MAX_RESULTS: int = Field(default=5, validation_alias="TAVILY_MAX_RESULTS")

    # Freshness Policy Default TTLs (in seconds)
    TTL_SOFTWARE_VERSION: int = Field(default=86400, description="Software version TTL (24 hours)")
    TTL_PRICING: int = Field(default=21600, description="Pricing TTL (6 hours)")
    TTL_LEADERSHIP: int = Field(default=86400, description="Leadership TTL (24 hours)")
    TTL_PRODUCT_AVAILABILITY: int = Field(default=3600, description="Product availability TTL (1 hour)")
    TTL_RECENT_EVENTS: int = Field(default=21600, description="Recent events TTL (6 hours)")
    TTL_STATISTICS: int = Field(default=86400, description="Statistics TTL (24 hours)")
    TTL_GENERAL_KNOWLEDGE: int = Field(default=2592000, description="General knowledge TTL (30 days)")
    TTL_GENERAL: int = Field(default=43200, description="Fallback general TTL (12 hours)")



@lru_cache
def get_settings() -> Settings:
    """Returns cached application settings instance."""
    return Settings()
