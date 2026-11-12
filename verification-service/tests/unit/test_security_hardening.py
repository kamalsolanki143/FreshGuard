"""Security hardening tests — Stage 11 Phase 4.

Covers four independent security fixes:

1. Database URL credential masking — verifies that _mask_db_url redacts passwords
   before they appear in log output.
2. CORS origin parsing — verifies both comma-separated and JSON-array formats,
   and confirms that invalid JSON arrays raise ValueError rather than silently
   falling back to ['*'].
3. Request body size limiting — verifies that requests within the limit are
   accepted and that oversized requests (detected via Content-Length header or
   actual body size) are rejected with HTTP 413 and a conforming APIError body.
4. Readiness endpoint — verifies GET /health/ready returns HTTP 200 with
   database connectivity confirmed, and that the original GET /health contract
   is unaffected.

All tests run against the real FastAPI application via async_client (the global
conftest fixture), which uses the existing freshguard.db initialized at startup.
Tests are independent and do not share state.
"""

import logging

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch

from app.database.database import _mask_db_url
from app.config import Settings
from app.middleware.body_limit import RequestBodySizeLimitMiddleware


# ---------------------------------------------------------------------------
# 1. Database URL credential masking
# ---------------------------------------------------------------------------


class TestMaskDbUrl:
    """Unit tests for _mask_db_url credential redaction."""

    def test_sqlite_url_is_unchanged(self):
        """SQLite URLs have no credentials and must pass through unmodified."""
        url = "sqlite+aiosqlite:///./freshguard.db"
        assert _mask_db_url(url) == url

    def test_postgres_password_is_masked(self):
        """PostgreSQL passwords must be replaced with '***'."""
        url = "postgresql+asyncpg://admin:supersecret@db.example.com:5432/freshguard"
        masked = _mask_db_url(url)
        assert "supersecret" not in masked, "Plain password appeared in masked URL"
        assert "***" in masked
        # Useful context must be preserved
        assert "admin" in masked
        assert "db.example.com" in masked
        assert "freshguard" in masked

    def test_url_without_password_is_unchanged(self):
        """A URL with a username but no password must not be altered."""
        url = "postgresql+asyncpg://admin@db.example.com/freshguard"
        assert _mask_db_url(url) == url

    def test_simple_password_masking(self):
        """Shorter credential-bearing URL is correctly masked."""
        url = "postgresql+asyncpg://user:secret@localhost/testdb"
        masked = _mask_db_url(url)
        assert "secret" not in masked
        assert "***" in masked
        assert "user" in masked
        assert "localhost" in masked
        assert "testdb" in masked

    def test_credentials_not_logged(self, caplog):
        """Calling get_engine must never write a plain-text password to log output.

        We mock create_async_engine to avoid actually connecting to a database,
        then inspect the captured log records.
        """
        password_bearing_url = "postgresql+asyncpg://user:topsecret@host/db"

        # Reset the singleton so our custom URL is accepted by get_engine
        import app.database.database as db_module
        original_engine = db_module._engine
        original_sessionmaker = db_module._sessionmaker
        db_module._engine = None
        db_module._sessionmaker = None

        try:
            with patch("app.database.database.create_async_engine") as mock_engine_factory:
                mock_engine_obj = MagicMock()
                mock_engine_factory.return_value = mock_engine_obj
                with caplog.at_level(logging.INFO, logger="freshguard.database"):
                    db_module.get_engine(database_url=password_bearing_url)

            for record in caplog.records:
                assert "topsecret" not in record.getMessage(), (
                    f"Database password appeared in log: {record.getMessage()!r}"
                )
        finally:
            # Always restore the original singleton, even on test failure
            db_module._engine = original_engine
            db_module._sessionmaker = original_sessionmaker


# ---------------------------------------------------------------------------
# 2. CORS origin parsing
# ---------------------------------------------------------------------------


class TestCorsOriginParsing:
    """Unit tests for Settings.assemble_cors_origins validator."""

    def test_comma_separated_string(self):
        """Comma-separated origin string must be split and stripped correctly."""
        s = Settings(
            CORS_ORIGINS="https://freshguard.vercel.app, http://localhost:3000",
        )
        assert s.CORS_ORIGINS == ["https://freshguard.vercel.app", "http://localhost:3000"]

    def test_json_array_string(self):
        """A JSON-array string must be parsed via json.loads."""
        s = Settings(
            CORS_ORIGINS='["https://freshguard.vercel.app","http://localhost:3000"]',
        )
        assert s.CORS_ORIGINS == ["https://freshguard.vercel.app", "http://localhost:3000"]

    def test_list_passthrough(self):
        """A Python list value must pass through unchanged."""
        origins = ["https://a.example.com", "https://b.example.com"]
        s = Settings(CORS_ORIGINS=origins)
        assert s.CORS_ORIGINS == origins

    def test_wildcard_string_accepted(self):
        """The literal string '*' must be accepted as ['*']."""
        s = Settings(CORS_ORIGINS="*")
        assert s.CORS_ORIGINS == ["*"]

    def test_single_origin_string(self):
        """A single-origin comma-separated value must produce a one-element list."""
        s = Settings(CORS_ORIGINS="https://freshguard.vercel.app")
        assert s.CORS_ORIGINS == ["https://freshguard.vercel.app"]

    def test_invalid_json_array_raises_validation_error(self):
        """A malformed JSON-array string must raise ValidationError, not silently become ['*']."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(CORS_ORIGINS='["https://example.com"')  # unterminated JSON
        # The error must reference our CORS field — not silently fail
        raw_errors = str(exc_info.value)
        assert "cors" in raw_errors.lower() or "json" in raw_errors.lower() or "cors_origins" in raw_errors.lower()

    def test_empty_string_raises_validation_error(self):
        """An empty CORS_ORIGINS string must raise ValidationError, not silently become ['*']."""
        with pytest.raises(ValidationError):
            Settings(CORS_ORIGINS="   ")

    def test_json_array_does_not_silently_fallback(self):
        """The fixed parser must NOT return ['*'] when given a JSON array.

        Regression guard: the old code fell back to ['*'] for any string starting
        with '[' that it couldn't handle. The new code must parse it correctly.
        """
        s = Settings(CORS_ORIGINS='["https://only-this.com"]')
        assert s.CORS_ORIGINS == ["https://only-this.com"]
        assert "*" not in s.CORS_ORIGINS


# ---------------------------------------------------------------------------
# 3. Request body size limiting
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def tiny_limit_client():
    """AsyncClient wired to a minimal FastAPI app with a 100-byte body limit.

    This isolated app is used to test the middleware behaviour with a deliberately
    small limit without depending on production app configuration.
    """
    mini_app = FastAPI()
    mini_app.add_middleware(RequestBodySizeLimitMiddleware, max_bytes=100)

    @mini_app.post("/probe")
    async def _probe():
        return {"ok": True}

    transport = ASGITransport(app=mini_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


class TestRequestBodySizeLimit:
    """Integration tests for the RequestBodySizeLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_body_within_limit_accepted(self, tiny_limit_client):
        """A request body within the configured limit must succeed (not 413)."""
        small_body = b'{"key": "value"}'  # 16 bytes, well within 100-byte limit
        response = await tiny_limit_client.post(
            "/probe",
            content=small_body,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    @pytest.mark.asyncio
    async def test_oversized_body_via_content_length_rejected(self, tiny_limit_client):
        """Content-Length exceeding limit must be rejected with HTTP 413 (fast path)."""
        response = await tiny_limit_client.post(
            "/probe",
            content=b"x" * 10,  # small actual body
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": "101",  # declares over limit
            },
        )
        assert response.status_code == 413, (
            f"Expected 413 for oversized Content-Length, got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_oversized_actual_body_rejected(self, tiny_limit_client):
        """Actual body exceeding the limit must be rejected with 413 (streaming slow path).

        Content-Length header is intentionally omitted to exercise the streaming path.
        """
        big_body = b"x" * 101  # 101 bytes, 1 byte over the 100-byte limit
        response = await tiny_limit_client.post(
            "/probe",
            content=big_body,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 413, (
            f"Expected 413 for oversized body (streaming), got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_413_response_is_valid_api_error_envelope(self, tiny_limit_client):
        """The 413 response body must be a conforming APIError JSON envelope."""
        response = await tiny_limit_client.post(
            "/probe",
            content=b"x" * 101,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 413
        body = response.json()
        assert body.get("code") == "REQUEST_TOO_LARGE"
        assert "message" in body
        assert "retryable" in body
        assert body["retryable"] is False

    @pytest.mark.asyncio
    async def test_body_at_exact_limit_accepted(self, tiny_limit_client):
        """A request body at the exact limit boundary (100 bytes) must be accepted."""
        exact_body = b"x" * 100  # exactly the limit
        response = await tiny_limit_client.post(
            "/probe",
            content=exact_body,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_production_app_middleware_via_content_length_header(self):
        """Production app rejects oversized Content-Length without touching the DB.

        The body-size middleware runs before any routing or DB session creation.
        A 10 MiB Content-Length header triggers the fast-path reject immediately.
        """
        from app.main import app as production_app
        transport = ASGITransport(app=production_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/v1/verifications",
                content=b'{"request_id":"x","text":"tiny"}',
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": str(10 * 1024 * 1024),  # 10 MiB declared
                },
            )
        assert response.status_code == 413, (
            f"Expected 413 for oversized Content-Length in production app, "
            f"got {response.status_code}"
        )
        body = response.json()
        assert body.get("code") == "REQUEST_TOO_LARGE"


# ---------------------------------------------------------------------------
# 4. Readiness endpoint
# ---------------------------------------------------------------------------


class TestReadinessEndpoint:
    """Integration tests for GET /health/ready."""

    @pytest.mark.asyncio
    async def test_readiness_returns_200_when_database_ok(self, async_client):
        """GET /health/ready must return 200 when database is reachable."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["database"] == "ok"

    @pytest.mark.asyncio
    async def test_readiness_contains_service_name(self, async_client):
        """Readiness response must include the service name for operator clarity."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body.get("service") == "freshguard-verification"

    @pytest.mark.asyncio
    async def test_readiness_503_when_db_execute_raises(self):
        """GET /health/ready must return 503 when the database execute call raises.

        Uses a fresh ASGI client scoped to this test so the patch is isolated.
        """
        from app.main import app as production_app

        with patch(
            "app.api.routes.health.AsyncSession.execute",
            new_callable=AsyncMock,
            side_effect=Exception("simulated DB failure"),
        ):
            transport = ASGITransport(app=production_app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.get("/health/ready")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert body["database"] == "unreachable"

    @pytest.mark.asyncio
    async def test_liveness_unaffected_by_readiness(self, async_client):
        """GET /health must still return 200 and preserve its original contract.

        Verifies that adding /health/ready did not break the existing /health endpoint.
        """
        response = await async_client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "service" in body
        assert "version" in body
        # Confirm original fields are intact and no readiness fields leaked in
        assert "database" not in body
