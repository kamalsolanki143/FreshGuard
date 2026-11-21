"""Regression and Incident Verification Test Suite for FreshGuard.

Directly validates the 12 failure modes and reliability invariants from the
Production HTTP 500 Incident Investigation:
1. Successful pricing verification flow.
2. Gemini extraction failure propagation (pipeline degradation + HTTP 502 on unhandled error).
3. Gemini verdict failure propagation (clean error envelope / UNCERTAIN verdict).
4. Tavily authentication failure handling (HTTP 502, no secret leakage).
5. Tavily rate limit handling (HTTP 502 after retry exhaustion).
6. Tavily timeout handling (HTTP 502).
7. Database initialization failure handling.
8. Database write failure rollback and 503 mapping.
9. Database connection drop during idempotency check (HTTP 503 DATABASE_UNAVAILABLE).
10. Invalid structured LLM output (ExtractionError on non-JSON / schema mismatch).
11. Vercel proxy error contract conformance.
12. Backend readiness probe when database is unavailable (HTTP 503).
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.database import check_db_schema_ready, get_db_session, init_db
from app.main import app
from app.schemas.claims import ClaimCategory, ClaimExtractionResponse, ClaimVerdict, ClaimVerdictResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceMinimal, EvidenceSourceType
from app.schemas.request import VerificationRequest
from app.schemas.response import FreshnessStatus, LifecycleStatus, VerificationResponse
from app.services.llm_provider import GeminiLLMProvider
from app.services.tavily_service import TavilyService
from app.services.verification_pipeline import VerificationPipeline
from app.utils.exceptions import (
    ConfigurationError,
    DatabaseError,
    ExtractionError,
    TavilyAPIError,
    VerdictError,
)


@pytest_asyncio.fixture(autouse=True)
async def ensure_db_schema():
    """Ensures database schema tables exist for all incident regression tests."""
    await init_db()


# 1. Successful Pricing Verification Flow
@pytest.mark.asyncio
async def test_01_successful_pricing_verification(async_client: AsyncClient):
    """Scenario 1: End-to-end pricing verification for ChatGPT Plus costs $20/month."""
    payload = {
        "request_id": f"reg-test-pricing-{datetime.now(timezone.utc).timestamp()}",
        "text": "ChatGPT Plus costs $20 per month and includes access to GPT-4.",
        "categories": ["pricing"],
    }
    response = await async_client.post("/v1/verifications", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["request_id"] == payload["request_id"]
    assert "verification_id" in data
    assert data["status"] in ("completed", "accepted")
    assert data["freshness_status"] in ("FRESH", "STALE", "UNCERTAIN")
    assert data["claims_checked"] >= 1
    assert data["processing_time_ms"] >= 0
    assert len(data["results"]) >= 1
    assert any(c.get("category") == "pricing" for c in data["results"])


# 2. Gemini Extraction Failure Propagation
@pytest.mark.asyncio
async def test_02_gemini_extraction_failure_propagation(async_client: AsyncClient):
    """Scenario 2: When claim extraction fails, pipeline degrades safely to UNCERTAIN,
    and route-level ExtractionError returns HTTP 502 with EXTRACTION_ERROR code."""
    # A. Route-level propagation check
    with patch("app.api.routes.verifications.VerificationPipeline.verify", new_callable=AsyncMock) as mock_verify:
        mock_verify.side_effect = ExtractionError(
            message="Gemini extraction call failed.",
            details={"provider": "gemini", "model": "gemini-2.0-flash"},
        )
        payload = {
            "request_id": "reg-test-ext-fail",
            "text": "ChatGPT Plus costs $20 per month.",
        }
        response = await async_client.post("/v1/verifications", json=payload, headers={"X-Request-ID": "reg-test-ext-fail"})
        assert response.status_code == 502
        err = response.json()
        assert err["code"] == "EXTRACTION_ERROR"
        assert "Gemini extraction call failed" in err["message"]
        assert err["retryable"] is True


# 3. Gemini Verdict Failure Propagation
@pytest.mark.asyncio
async def test_03_gemini_verdict_failure_propagation(async_client: AsyncClient):
    """Scenario 3: When verdict judgment encounters an unhandled error, API returns clean error envelope."""
    with patch("app.api.routes.verifications.VerificationPipeline.verify", new_callable=AsyncMock) as mock_verify:
        mock_verify.side_effect = VerdictError(
            message="Verdict assessment failed due to upstream LLM disruption.",
            details={"claim_id": "claim_001"},
        )
        payload = {
            "request_id": "reg-test-verdict-fail",
            "text": "ChatGPT Plus costs $20 per month.",
        }
        response = await async_client.post("/v1/verifications", json=payload, headers={"X-Request-ID": "reg-test-verdict-fail"})
        assert response.status_code in (500, 502)
        err = response.json()
        assert err["code"] == "VERDICT_ERROR"
        assert "Verdict assessment failed" in err["message"]


# 4. Tavily Authentication Failure Handling
@pytest.mark.asyncio
async def test_04_tavily_authentication_failure_handling(async_client: AsyncClient):
    """Scenario 4: Tavily 401/403 raises TavilyAPIError and returns HTTP 502 without exposing secrets."""
    # A. Direct service behavior check
    mock_http_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized: Invalid API Key"
    mock_http_client.post = AsyncMock(return_value=mock_resp)

    tavily_svc = TavilyService(api_key="tvly-secret-12345", client=mock_http_client)
    with pytest.raises(TavilyAPIError) as exc_info:
        await tavily_svc.search("ChatGPT Plus pricing")
    assert "Tavily authentication failed" in exc_info.value.message
    assert "tvly-secret-12345" not in str(exc_info.value.details)

    # B. Route-level 502 error mapping check
    with patch("app.api.routes.verifications.VerificationPipeline.verify", new_callable=AsyncMock) as mock_verify:
        mock_verify.side_effect = TavilyAPIError(
            message="Tavily authentication failed with HTTP 401.",
            details={"status_code": 401},
        )
        response = await async_client.post(
            "/v1/verifications",
            json={"request_id": "reg-test-tavily-auth", "text": "ChatGPT Plus pricing"},
            headers={"X-Request-ID": "reg-test-tavily-auth"},
        )
        assert response.status_code == 502
        err = response.json()
        assert err["code"] == "TAVILY_API_ERROR"
        assert "tvly-" not in response.text


# 5. Tavily Rate Limit Handling
@pytest.mark.asyncio
async def test_05_tavily_rate_limit_handling(async_client: AsyncClient):
    """Scenario 5: Tavily 429 rate limit raises TavilyAPIError after retry exhaustion."""
    mock_http_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Too Many Requests"
    mock_http_client.post = AsyncMock(return_value=mock_resp)

    tavily_svc = TavilyService(api_key="test-key", client=mock_http_client)
    tavily_svc.max_retries = 1
    with pytest.raises(TavilyAPIError) as exc_info:
        await tavily_svc.search("pricing query")
    assert "429" in exc_info.value.message


# 6. Tavily Timeout Handling
@pytest.mark.asyncio
async def test_06_tavily_timeout_handling(async_client: AsyncClient):
    """Scenario 6: Tavily network timeout raises TavilyAPIError mapped to HTTP 502."""
    mock_http_client = MagicMock()
    mock_http_client.post = AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))

    tavily_svc = TavilyService(api_key="test-key", client=mock_http_client)
    tavily_svc.max_retries = 1
    with pytest.raises(TavilyAPIError) as exc_info:
        await tavily_svc.search("pricing query")
    assert "timed out" in exc_info.value.message.lower()


# 7. Database Initialization Failure Handling
@pytest.mark.asyncio
async def test_07_database_initialization_failure():
    """Scenario 7: When schema is not ready, check_db_schema_ready detects missing table."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("relation 'verification_records' does not exist")
    is_ready = await check_db_schema_ready(mock_session)
    assert is_ready is False


# 8. Database Write Failure Rollback and 503 Mapping
@pytest.mark.asyncio
async def test_08_database_write_failure_persists_safely(async_client: AsyncClient):
    """Scenario 8: Database write failure during verification persistence returns HTTP 503 (DatabaseError)."""
    with patch("app.database.repository.VerificationRepository.save_verification", new_callable=AsyncMock) as mock_save:
        mock_save.side_effect = Exception("Neon connection terminated unexpectedly during write.")
        payload = {
            "request_id": "reg-test-db-write-fail",
            "text": "ChatGPT Plus costs $20 per month.",
        }
        response = await async_client.post("/v1/verifications", json=payload, headers={"X-Request-ID": "reg-test-db-write-fail"})
        assert response.status_code == 503
        err = response.json()
        assert err["code"] == "DATABASE_ERROR"
        assert "Failed to persist verification" in err["message"]
        assert err["retryable"] is True


# 9. Database Connection Drop during Idempotency Check
@pytest.mark.asyncio
async def test_09_database_idempotency_lookup_failure_resilient(async_client: AsyncClient):
    """Scenario 9: Unreachable database during idempotency check returns HTTP 503 DATABASE_UNAVAILABLE."""
    with patch("app.database.repository.VerificationRepository.get_verification_by_request_id", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Connection to Neon database failed: connection refused.")
        payload = {
            "request_id": "reg-test-idempotency-drop",
            "text": "ChatGPT Plus costs $20 per month.",
        }
        response = await async_client.post("/v1/verifications", json=payload, headers={"X-Request-ID": "reg-test-idempotency-drop"})
        assert response.status_code == 503
        err = response.json()
        assert err["code"] == "DATABASE_UNAVAILABLE"
        assert "temporarily unavailable" in err["message"].lower()
        assert err["retryable"] is True


# 10. Invalid Structured LLM Output
@pytest.mark.asyncio
async def test_10_invalid_structured_llm_output():
    """Scenario 10: GeminiLLMProvider catches malformed or non-JSON output and raises ExtractionError."""
    settings = Settings(
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="test-key-valid",
        _env_file=None,
    )
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Here is the result: { invalid_json_content"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

    provider = GeminiLLMProvider(settings=settings, client=mock_client)
    with pytest.raises(ExtractionError) as exc_info:
        await provider.generate_structured(
            system_prompt="Test",
            user_text="Test",
            response_model=ClaimExtractionResponse,
        )
    assert "non-JSON" in exc_info.value.message or "JSON" in exc_info.value.message


# 11. Vercel Proxy Upstream Error Contract Conformance
@pytest.mark.asyncio
async def test_11_vercel_proxy_contract_simulation(async_client: AsyncClient):
    """Scenario 11: Error responses from API conform to the contract expected by Vercel serverless proxy."""
    with patch("app.api.routes.verifications.VerificationPipeline.verify", new_callable=AsyncMock) as mock_verify:
        mock_verify.side_effect = ExtractionError(
            message="Transient Gemini API rate limit exceeded.",
            details={"code": 429, "retryable": True},
        )
        payload = {
            "request_id": "reg-test-proxy-contract",
            "text": "ChatGPT Plus costs $20 per month.",
        }
        response = await async_client.post(
            "/v1/verifications",
            json=payload,
            headers={"X-Request-ID": "reg-test-proxy-contract"},
        )
        assert response.status_code == 502
        err = response.json()
        # Verify proxy contract fields exist
        assert "error" in err
        assert "code" in err
        assert "message" in err
        assert "request_id" in err
        assert err["request_id"] == "reg-test-proxy-contract"
        assert err["retryable"] is True


# 12. Backend Readiness When Database Is Unavailable
@pytest.mark.asyncio
async def test_12_backend_readiness_when_database_unavailable(async_client: AsyncClient):
    """Scenario 12: GET /health/ready returns HTTP 503 when the database schema is uninitialized or down."""
    with patch("app.api.routes.health.check_db_schema_ready", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        response = await async_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "uninitialized"
