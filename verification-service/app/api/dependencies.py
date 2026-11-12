import hmac
import logging
from typing import Optional

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.database import get_db_session
from app.services.verification_pipeline import VerificationPipeline
from app.utils.exceptions import AuthenticationError, ConfigurationError

_pipeline: Optional[VerificationPipeline] = None
_auth_logger = logging.getLogger("freshguard.auth")


def get_app_settings() -> Settings:
    """Dependency for providing cached app settings."""
    return get_settings()


def get_app_logger() -> logging.Logger:
    """Dependency for providing logger instance."""
    return logging.getLogger("freshguard")


def get_pipeline(settings: Settings = Depends(get_app_settings)) -> VerificationPipeline:
    """Dependency provider for shared VerificationPipeline orchestrator."""
    global _pipeline
    if _pipeline is None:
        _pipeline = VerificationPipeline(settings=settings)
    return _pipeline


def validate_auth_config(settings: Settings) -> None:
    """Validate authentication configuration at startup based on ENVIRONMENT.

    Call this during the application lifespan startup to catch misconfigurations
    before the service starts accepting traffic.

    Environment-specific rules:
    - Production (ENVIRONMENT in {"production", "prod"}):
        * API_AUTH_MODE must be "enforce". Starting with "disabled" or "warn"
          raises ConfigurationError.
        * VERIFICATION_SERVICE_API_KEY must be set and non-empty.
    - Staging (ENVIRONMENT in {"staging"}):
        * API_AUTH_MODE must be "warn" or "enforce". Starting with "disabled"
          raises ConfigurationError.
        * If API_AUTH_MODE is "enforce", VERIFICATION_SERVICE_API_KEY must be non-empty.
    - Development & Test (ENVIRONMENT in {"development", "dev", "test"}) or other environments:
        * API_AUTH_MODE may be "disabled", "warn", or "enforce".
        * If API_AUTH_MODE is "enforce", VERIFICATION_SERVICE_API_KEY must be non-empty.

    Raises:
        ConfigurationError: When the environment authentication rules are violated.
    """
    env = (settings.ENVIRONMENT or "development").lower().strip()
    mode = (settings.API_AUTH_MODE or "disabled").lower().strip()
    api_key = settings.VERIFICATION_SERVICE_API_KEY.strip() if settings.VERIFICATION_SERVICE_API_KEY else ""

    # Rule 1: Production strictly requires API_AUTH_MODE=enforce and non-empty key
    if env in ("production", "prod"):
        if mode == "disabled":
            raise ConfigurationError(
                "Production environment strictly forbids API_AUTH_MODE='disabled'. "
                "Production requires API_AUTH_MODE=enforce with a valid VERIFICATION_SERVICE_API_KEY. "
                "Service startup aborted."
            )
        if mode == "warn":
            raise ConfigurationError(
                "Production environment strictly forbids API_AUTH_MODE='warn'. "
                "Production requires API_AUTH_MODE=enforce with a valid VERIFICATION_SERVICE_API_KEY. "
                "Service startup aborted."
            )
        if mode != "enforce":
            raise ConfigurationError(
                f"Production environment requires API_AUTH_MODE=enforce (got '{settings.API_AUTH_MODE}'). "
                "Service startup aborted."
            )
        if not api_key:
            raise ConfigurationError(
                "Production environment requires VERIFICATION_SERVICE_API_KEY to be set and non-empty. "
                "Service startup aborted."
            )
        return

    # Rule 2: Staging permits warn or enforce, but never disabled
    if env in ("staging",):
        if mode == "disabled":
            raise ConfigurationError(
                "Staging environment strictly forbids API_AUTH_MODE='disabled'. "
                "Staging must use API_AUTH_MODE=warn or API_AUTH_MODE=enforce. "
                "Service startup aborted."
            )
        if mode == "enforce" and not api_key:
            raise ConfigurationError(
                "API_AUTH_MODE=enforce requires VERIFICATION_SERVICE_API_KEY to be set and non-empty. "
                "Service startup aborted."
            )
        return

    # Rule 3: Development, test, and all other environments
    if mode == "enforce" and not api_key:
        raise ConfigurationError(
            "API_AUTH_MODE=enforce requires VERIFICATION_SERVICE_API_KEY to be set and non-empty. "
            "Set the key via the environment variable, or use API_AUTH_MODE=warn or API_AUTH_MODE=disabled "
            "for local development/testing. Service startup aborted."
        )


async def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_app_settings),
) -> None:
    """FastAPI dependency enforcing X-API-Key authentication on protected routes.

    Behaviour is controlled by ``settings.API_AUTH_MODE``:

    - ``disabled``: All requests pass through unconditionally. Intended for
      local development only.
    - ``warn``: Requests with a missing or invalid key are allowed, but a
      WARNING is emitted. Never logs the key value itself.
    - ``enforce``: Missing or invalid keys raise :class:`AuthenticationError`
      (HTTP 401) with a generic message that does not reveal whether the key
      was absent or wrong.

    Uses ``hmac.compare_digest`` for constant-time comparison to prevent
    timing-based secret inference.

    The key value is never logged under any authentication mode.
    """
    mode = settings.API_AUTH_MODE  # already normalised to lowercase by validator

    if mode == "disabled":
        return

    expected_key = settings.VERIFICATION_SERVICE_API_KEY

    # Determine whether the supplied key matches using constant-time comparison.
    # We only call compare_digest when both sides are non-empty; a missing or
    # empty key on either side is an immediate failure.
    key_valid: bool = (
        bool(x_api_key)
        and bool(expected_key)
        and hmac.compare_digest(
            x_api_key.encode("utf-8"),
            expected_key.encode("utf-8"),
        )
    )

    if key_valid:
        return  # Authentication passed

    if mode == "enforce":
        # Generic message: do not reveal whether key was absent or wrong.
        raise AuthenticationError()

    # warn mode: allow the request but emit a warning (never log the key).
    _auth_logger.warning(
        "Request to '%s' has a missing or invalid X-API-Key "
        "(API_AUTH_MODE=warn — request allowed).",
        request.url.path,
    )
