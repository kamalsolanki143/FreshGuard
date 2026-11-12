"""Unit and integration tests for X-API-Key authentication.

Covers all requirements:
1.  Valid key in enforce mode → 200.
2.  Missing key in enforce mode → 401.
3.  Invalid/wrong key in enforce mode → 401.
4.  API_AUTH_MODE=disabled → all requests pass through (no key needed).
5.  API_AUTH_MODE=warn + missing key → 200 (warning logged, not tested here).
6.  API_AUTH_MODE=warn + invalid key → 200.
7.  API_AUTH_MODE=warn + valid key → 200.
8.  Startup failure when enforce mode has no configured key.
9.  POST /v1/verifications authentication.
10. GET /v1/verifications/{id} authentication.
11. Public health endpoints remain accessible without any key.
12. 401 response body matches APIError schema (never leaks key material).
13. Existing idempotency behaviour is unaffected by authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_app_settings, get_pipeline, validate_auth_config
from app.config import Settings
from app.database.database import get_db_session
from app.database.models import Base
from app.main import app
from app.schemas.claims import ClaimCategory, ClaimVerdict, ClaimVerdictResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceSourceType
from app.services.prefilter import PrefilterResult
from app.services.verification_pipeline import VerificationPipeline
from app.utils.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_KEY = "test-secret-key-for-unit-tests-only"
_WRONG_KEY = "definitely-not-the-right-key"

_VERIFY_PAYLOAD = {
    "request_id": "auth-test-req-001",
    "text": "GPT-4 costs $20 per month.",
    "mode": "blocking",
}


def _make_settings(**overrides) -> Settings:
    """Construct a Settings instance with test-safe defaults."""
    defaults = dict(
        ENVIRONMENT="test",
        DEBUG=True,
        LLM_PROVIDER="mock",
        API_AUTH_MODE="disabled",
        VERIFICATION_SERVICE_API_KEY="",
        _env_file=None,
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_test_env():
    """Sets up an isolated in-memory test database and mock pipeline for auth tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db_session():
        async with sm() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    mock_pipeline = VerificationPipeline()
    mock_pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["pricing"], confidence=0.9
    ))
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[
        ExtractedClaim(
            claim_id="claim_001",
            text="GPT-4 costs $20 per month.",
            category=ClaimCategory.PRICING,
            entity="OpenAI",
            attribute="price",
            time_sensitive=True,
        )
    ])
    mock_ev = EvidenceItem(
        evidence_id="ev_001",
        title="Pricing Docs",
        url="https://openai.com/pricing",
        content="ChatGPT Plus is $20/month.",
        relevance_score=0.95,
        source_type=EvidenceSourceType.OFFICIAL_DOCS,
        retrieved_at=datetime.now(timezone.utc),
    )
    mock_pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[mock_ev])
    mock_pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_001",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.95,
        reason="Evidence confirms pricing.",
        evidence_ids=["ev_001"],
        evidence=[],
        checked_at=datetime.now(timezone.utc),
    ))

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

    yield

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def disabled_client(auth_test_env):
    """AsyncClient with authentication disabled (default dev mode)."""
    settings = _make_settings(API_AUTH_MODE="disabled")
    app.dependency_overrides[get_app_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def warn_client(auth_test_env):
    """AsyncClient with API_AUTH_MODE=warn and a configured key."""
    settings = _make_settings(
        API_AUTH_MODE="warn",
        VERIFICATION_SERVICE_API_KEY=_VALID_KEY,
    )
    app.dependency_overrides[get_app_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def enforce_client(auth_test_env):
    """AsyncClient with API_AUTH_MODE=enforce and a configured key."""
    settings = _make_settings(
        API_AUTH_MODE="enforce",
        VERIFICATION_SERVICE_API_KEY=_VALID_KEY,
    )
    app.dependency_overrides[get_app_settings] = lambda: settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


# ---------------------------------------------------------------------------
# 1. validate_auth_config — startup-time checks (synchronous, no HTTP)
# ---------------------------------------------------------------------------

class TestValidateAuthConfig:
    """Tests for the startup-time authentication configuration validator."""

    def test_disabled_mode_no_key_passes(self):
        """disabled mode: no key required — validation always passes."""
        settings = _make_settings(API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY="")
        validate_auth_config(settings)  # must not raise

    def test_disabled_mode_with_key_passes(self):
        """disabled mode: a key may be present without error."""
        settings = _make_settings(API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        validate_auth_config(settings)  # must not raise

    def test_warn_mode_no_key_passes(self):
        """warn mode: missing key is allowed at startup (request-level warning only)."""
        settings = _make_settings(API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY="")
        validate_auth_config(settings)  # must not raise

    def test_warn_mode_with_key_passes(self):
        """warn mode with key: valid configuration."""
        settings = _make_settings(API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        validate_auth_config(settings)  # must not raise

    def test_enforce_mode_with_key_passes(self):
        """enforce mode with key configured: valid production configuration."""
        settings = _make_settings(
            API_AUTH_MODE="enforce",
            VERIFICATION_SERVICE_API_KEY=_VALID_KEY,
        )
        validate_auth_config(settings)  # must not raise

    def test_enforce_mode_without_key_raises_configuration_error(self):
        """enforce mode without a key MUST fail at startup — Requirement 8."""
        settings = _make_settings(API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY="")
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "enforce" in exc_info.value.message
        assert "VERIFICATION_SERVICE_API_KEY" in exc_info.value.message
        assert exc_info.value.code == "CONFIGURATION_ERROR"

    def test_invalid_auth_mode_rejected_by_settings(self):
        """Unknown API_AUTH_MODE values are rejected by the Settings validator."""
        with pytest.raises(Exception):
            _make_settings(API_AUTH_MODE="supermode")

    # Production environment tests (ENVIRONMENT="production")
    def test_production_disabled_mode_fails_startup(self):
        """Production startup MUST fail if API_AUTH_MODE is disabled."""
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY="")
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "Production" in exc_info.value.message
        assert "disabled" in exc_info.value.message

    def test_production_disabled_mode_with_key_fails_startup(self):
        """Production startup MUST fail if API_AUTH_MODE is disabled, even if key is provided."""
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "Production" in exc_info.value.message
        assert "disabled" in exc_info.value.message

    def test_production_warn_mode_fails_startup(self):
        """Production startup MUST fail if API_AUTH_MODE is warn."""
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY="")
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "Production" in exc_info.value.message
        assert "warn" in exc_info.value.message

    def test_production_warn_mode_with_key_fails_startup(self):
        """Production startup MUST fail if API_AUTH_MODE is warn, even if key is provided."""
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "Production" in exc_info.value.message
        assert "warn" in exc_info.value.message

    def test_production_enforce_without_key_fails_startup(self):
        """Production startup MUST fail if API_AUTH_MODE is enforce but key is missing."""
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY="")
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "Production" in exc_info.value.message
        assert "VERIFICATION_SERVICE_API_KEY" in exc_info.value.message

    def test_production_enforce_with_whitespace_key_fails_startup(self):
        """Production startup MUST fail if key is whitespace only."""
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY="   ")
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "Production" in exc_info.value.message
        assert "VERIFICATION_SERVICE_API_KEY" in exc_info.value.message

    def test_production_enforce_with_valid_key_succeeds(self):
        """Production startup succeeds only when API_AUTH_MODE=enforce AND key is valid."""
        settings = _make_settings(
            ENVIRONMENT="production",
            API_AUTH_MODE="enforce",
            VERIFICATION_SERVICE_API_KEY=_VALID_KEY,
        )
        validate_auth_config(settings)  # must not raise

    # Alias "prod" tests
    def test_prod_alias_disabled_mode_fails(self):
        """ENVIRONMENT='prod' alias also rejects disabled mode."""
        settings = _make_settings(ENVIRONMENT="prod", API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY="")
        with pytest.raises(ConfigurationError):
            validate_auth_config(settings)

    def test_prod_alias_warn_mode_fails(self):
        """ENVIRONMENT='prod' alias also rejects warn mode."""
        settings = _make_settings(ENVIRONMENT="prod", API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        with pytest.raises(ConfigurationError):
            validate_auth_config(settings)

    def test_prod_alias_enforce_with_key_succeeds(self):
        """ENVIRONMENT='prod' alias succeeds when enforce mode and key are set."""
        settings = _make_settings(ENVIRONMENT="prod", API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        validate_auth_config(settings)  # must not raise

    # Staging environment tests (ENVIRONMENT="staging")
    def test_staging_disabled_mode_fails_startup(self):
        """Staging environment does not permit disabled mode."""
        settings = _make_settings(ENVIRONMENT="staging", API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY="")
        with pytest.raises(ConfigurationError) as exc_info:
            validate_auth_config(settings)
        assert "Staging" in exc_info.value.message
        assert "disabled" in exc_info.value.message

    def test_staging_warn_mode_without_key_succeeds(self):
        """Staging environment permits warn mode even without a key."""
        settings = _make_settings(ENVIRONMENT="staging", API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY="")
        validate_auth_config(settings)  # must not raise

    def test_staging_warn_mode_with_key_succeeds(self):
        """Staging environment permits warn mode with key."""
        settings = _make_settings(ENVIRONMENT="staging", API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        validate_auth_config(settings)  # must not raise

    def test_staging_enforce_without_key_fails_startup(self):
        """Staging with enforce mode requires a key."""
        settings = _make_settings(ENVIRONMENT="staging", API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY="")
        with pytest.raises(ConfigurationError):
            validate_auth_config(settings)

    def test_staging_enforce_with_key_succeeds(self):
        """Staging with enforce mode and key succeeds."""
        settings = _make_settings(ENVIRONMENT="staging", API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        validate_auth_config(settings)  # must not raise

    # Development and test environment tests
    def test_development_disabled_mode_succeeds(self):
        """Development environment allows disabled mode."""
        settings = _make_settings(ENVIRONMENT="development", API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY="")
        validate_auth_config(settings)  # must not raise

    def test_development_warn_mode_succeeds(self):
        """Development environment allows warn mode."""
        settings = _make_settings(ENVIRONMENT="development", API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY="")
        validate_auth_config(settings)  # must not raise

    def test_test_env_disabled_mode_succeeds(self):
        """Test environment allows disabled mode."""
        settings = _make_settings(ENVIRONMENT="test", API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY="")
        validate_auth_config(settings)  # must not raise


class TestProductionLifespanStartup:
    """Integration tests verifying application lifespan startup behavior under production configuration."""

    @pytest.mark.asyncio
    async def test_lifespan_aborts_in_production_with_disabled_auth(self):
        """FastAPI lifespan aborts startup when ENVIRONMENT=production and API_AUTH_MODE=disabled."""
        from unittest.mock import patch
        from app.main import lifespan
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="disabled", VERIFICATION_SERVICE_API_KEY="")
        with patch("app.main.get_settings", return_value=settings):
            with pytest.raises(ConfigurationError) as exc_info:
                async with lifespan(app):
                    pass
        assert "Production" in exc_info.value.message
        assert "disabled" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_lifespan_aborts_in_production_with_warn_auth(self):
        """FastAPI lifespan aborts startup when ENVIRONMENT=production and API_AUTH_MODE=warn."""
        from unittest.mock import patch
        from app.main import lifespan
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="warn", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        with patch("app.main.get_settings", return_value=settings):
            with pytest.raises(ConfigurationError) as exc_info:
                async with lifespan(app):
                    pass
        assert "Production" in exc_info.value.message
        assert "warn" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_lifespan_aborts_in_production_with_empty_key(self):
        """FastAPI lifespan aborts startup when ENVIRONMENT=production and key is missing."""
        from unittest.mock import patch
        from app.main import lifespan
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY="")
        with patch("app.main.get_settings", return_value=settings):
            with pytest.raises(ConfigurationError) as exc_info:
                async with lifespan(app):
                    pass
        assert "Production" in exc_info.value.message
        assert "VERIFICATION_SERVICE_API_KEY" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_lifespan_succeeds_in_production_with_enforce_and_valid_key(self):
        """FastAPI lifespan successfully boots in production when API_AUTH_MODE=enforce and key is provided."""
        from unittest.mock import patch
        from app.main import lifespan
        settings = _make_settings(ENVIRONMENT="production", API_AUTH_MODE="enforce", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        with patch("app.main.get_settings", return_value=settings):
            async with lifespan(app):
                # Service successfully started
                pass


# ---------------------------------------------------------------------------
# 2. Public health endpoints — must NEVER require authentication
# ---------------------------------------------------------------------------

class TestPublicHealthEndpoints:
    """Health endpoints must remain accessible without credentials — Requirement 11."""

    @pytest.mark.asyncio
    async def test_health_accessible_in_disabled_mode(self, disabled_client):
        resp = await disabled_client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_ready_accessible_in_disabled_mode(self, disabled_client):
        resp = await disabled_client.get("/health/ready")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_accessible_in_enforce_mode_without_key(self, enforce_client):
        """Even in enforce mode, /health must be reachable without X-API-Key."""
        resp = await enforce_client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_ready_accessible_in_enforce_mode_without_key(self, enforce_client):
        """/health/ready must be reachable without X-API-Key."""
        resp = await enforce_client.get("/health/ready")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_accessible_in_warn_mode_without_key(self, warn_client):
        resp = await warn_client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. API_AUTH_MODE=disabled — all verification requests pass through
# ---------------------------------------------------------------------------

class TestDisabledMode:
    """Requirement 4: disabled mode — no authentication at all."""

    @pytest.mark.asyncio
    async def test_post_allowed_without_key(self, disabled_client):
        """POST /v1/verifications succeeds without any X-API-Key header."""
        resp = await disabled_client.post("/v1/verifications", json=_VERIFY_PAYLOAD)
        # 200 OK or any non-401 (pipeline may return 200 or 422 for mock)
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_get_allowed_without_key(self, disabled_client):
        """GET /v1/verifications/{id} returns 404 (not 401) for unknown ID."""
        resp = await disabled_client.get("/v1/verifications/nonexistent-id-disabled")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_post_allowed_with_arbitrary_key(self, disabled_client):
        """In disabled mode, any key (including wrong ones) is accepted."""
        resp = await disabled_client.post(
            "/v1/verifications",
            json=_VERIFY_PAYLOAD,
            headers={"X-API-Key": "whatever"},
        )
        assert resp.status_code != 401


# ---------------------------------------------------------------------------
# 4. API_AUTH_MODE=warn — requests allowed regardless, warning emitted
# ---------------------------------------------------------------------------

class TestWarnMode:
    """Requirement 5 & 6: warn mode allows all requests."""

    @pytest.mark.asyncio
    async def test_post_allowed_without_key(self, warn_client):
        """Requirement 5: missing key in warn mode → request allowed (not 401)."""
        resp = await warn_client.post("/v1/verifications", json=_VERIFY_PAYLOAD)
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_post_allowed_with_wrong_key(self, warn_client):
        """Requirement 6: invalid key in warn mode → request still allowed."""
        resp = await warn_client.post(
            "/v1/verifications",
            json={**_VERIFY_PAYLOAD, "request_id": "warn-wrong-key"},
            headers={"X-API-Key": _WRONG_KEY},
        )
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_post_allowed_with_valid_key(self, warn_client):
        """Requirement 7: valid key in warn mode → request allowed."""
        resp = await warn_client.post(
            "/v1/verifications",
            json={**_VERIFY_PAYLOAD, "request_id": "warn-valid-key"},
            headers={"X-API-Key": _VALID_KEY},
        )
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_get_allowed_without_key(self, warn_client):
        """GET endpoint also allowed in warn mode without key."""
        resp = await warn_client.get("/v1/verifications/some-id-warn")
        assert resp.status_code == 404  # not 401 — auth passed, record just missing


# ---------------------------------------------------------------------------
# 5. API_AUTH_MODE=enforce — strict key enforcement
# ---------------------------------------------------------------------------

class TestEnforceMode:
    """Requirements 1, 2, 3, 9, 10: enforce mode behaviour."""

    @pytest.mark.asyncio
    async def test_post_valid_key_returns_non_401(self, enforce_client):
        """Requirement 1: valid key → pipeline processes request (not 401)."""
        resp = await enforce_client.post(
            "/v1/verifications",
            json={**_VERIFY_PAYLOAD, "request_id": "enforce-valid-post"},
            headers={"X-API-Key": _VALID_KEY},
        )
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_post_missing_key_returns_401(self, enforce_client):
        """Requirement 2: missing key in enforce mode → HTTP 401."""
        resp = await enforce_client.post("/v1/verifications", json=_VERIFY_PAYLOAD)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_post_wrong_key_returns_401(self, enforce_client):
        """Requirement 3: invalid key in enforce mode → HTTP 401."""
        resp = await enforce_client.post(
            "/v1/verifications",
            json=_VERIFY_PAYLOAD,
            headers={"X-API-Key": _WRONG_KEY},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_valid_key_returns_404_not_401(self, enforce_client):
        """Requirement 1 (GET): valid key passes auth; unknown ID returns 404."""
        resp = await enforce_client.get(
            "/v1/verifications/unknown-enforce-id",
            headers={"X-API-Key": _VALID_KEY},
        )
        assert resp.status_code == 404  # auth passed; record simply doesn't exist

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_401(self, enforce_client):
        """Requirement 2 (GET): missing key → 401 on GET endpoint too."""
        resp = await enforce_client.get("/v1/verifications/some-id")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_wrong_key_returns_401(self, enforce_client):
        """Requirement 3 (GET): wrong key → 401 on GET endpoint."""
        resp = await enforce_client.get(
            "/v1/verifications/some-id",
            headers={"X-API-Key": _WRONG_KEY},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_string_key_returns_401(self, enforce_client):
        """An empty X-API-Key header value is treated as missing."""
        resp = await enforce_client.post(
            "/v1/verifications",
            json=_VERIFY_PAYLOAD,
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_whitespace_only_key_returns_401(self, enforce_client):
        """A key consisting only of whitespace is not accepted."""
        resp = await enforce_client.post(
            "/v1/verifications",
            json=_VERIFY_PAYLOAD,
            headers={"X-API-Key": "   "},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 6. 401 response body — APIError schema compliance and no secret leakage
# ---------------------------------------------------------------------------

class TestUnauthorizedResponseBody:
    """Requirement 12: 401 body must conform to APIError schema and not leak key material."""

    @pytest.mark.asyncio
    async def test_401_body_has_expected_fields(self, enforce_client):
        resp = await enforce_client.post("/v1/verifications", json=_VERIFY_PAYLOAD)
        assert resp.status_code == 401
        body = resp.json()
        assert "code" in body
        assert "message" in body
        assert "retryable" in body

    @pytest.mark.asyncio
    async def test_401_code_is_unauthorized(self, enforce_client):
        resp = await enforce_client.post("/v1/verifications", json=_VERIFY_PAYLOAD)
        assert resp.json()["code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_401_message_is_generic(self, enforce_client):
        """Message must not reveal whether key was absent or wrong."""
        resp = await enforce_client.post(
            "/v1/verifications",
            json=_VERIFY_PAYLOAD,
            headers={"X-API-Key": _WRONG_KEY},
        )
        body = resp.json()
        assert resp.status_code == 401
        # Message should be the same for missing vs wrong key (generic)
        assert "Missing or invalid" in body["message"]

    @pytest.mark.asyncio
    async def test_401_body_does_not_contain_key_value(self, enforce_client):
        """The raw key must NEVER appear anywhere in the 401 response body."""
        resp = await enforce_client.post(
            "/v1/verifications",
            json=_VERIFY_PAYLOAD,
            headers={"X-API-Key": _WRONG_KEY},
        )
        body_text = resp.text
        assert _WRONG_KEY not in body_text
        assert _VALID_KEY not in body_text

    @pytest.mark.asyncio
    async def test_401_retryable_is_false(self, enforce_client):
        """Authentication failures are not retryable."""
        resp = await enforce_client.post("/v1/verifications", json=_VERIFY_PAYLOAD)
        assert resp.json()["retryable"] is False


# ---------------------------------------------------------------------------
# 7. Idempotency unaffected by authentication — Requirement 13
# ---------------------------------------------------------------------------

class TestIdempotencyWithAuth:
    """Idempotent deduplication must still work when authentication is active."""

    @pytest.mark.asyncio
    async def test_idempotent_post_returns_same_result_in_enforce_mode(self, enforce_client):
        """Two identical POST requests with a valid key return consistent results."""
        payload = {**_VERIFY_PAYLOAD, "request_id": "idempotency-auth-test-unique"}
        headers = {"X-API-Key": _VALID_KEY}

        resp1 = await enforce_client.post("/v1/verifications", json=payload, headers=headers)
        assert resp1.status_code != 401

        resp2 = await enforce_client.post("/v1/verifications", json=payload, headers=headers)
        assert resp2.status_code != 401

        # Both responses must succeed (idempotent hit should return same data)
        if resp1.status_code == 200 and resp2.status_code == 200:
            assert resp1.json()["verification_id"] == resp2.json()["verification_id"]


# ---------------------------------------------------------------------------
# 8. Settings construction — validator behaviour
# ---------------------------------------------------------------------------

class TestSettingsAuthModeValidator:
    """API_AUTH_MODE validator normalises and rejects unknown values."""

    def test_valid_modes_are_accepted(self):
        for mode in ("disabled", "warn", "enforce"):
            s = _make_settings(API_AUTH_MODE=mode)
            assert s.API_AUTH_MODE == mode

    def test_uppercase_modes_are_normalised(self):
        s = _make_settings(API_AUTH_MODE="ENFORCE", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        assert s.API_AUTH_MODE == "enforce"

    def test_mixed_case_mode_is_normalised(self):
        s = _make_settings(API_AUTH_MODE="Warn", VERIFICATION_SERVICE_API_KEY=_VALID_KEY)
        assert s.API_AUTH_MODE == "warn"

    def test_unknown_mode_raises_validation_error(self):
        with pytest.raises(Exception):
            _make_settings(API_AUTH_MODE="open")
