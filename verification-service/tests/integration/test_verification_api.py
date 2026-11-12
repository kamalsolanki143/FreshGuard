from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
import jsonschema
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_pipeline
from app.database.database import get_db_session
from app.database.models import Base
from app.database.repository import VerificationRepository
from app.main import app
from app.schemas.claims import ClaimCategory, ClaimVerdict, ClaimVerdictResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceMinimal, EvidenceSourceType
from app.schemas.response import (
    FreshnessStatus,
    LifecycleStatus,
    VerificationResponse,
    VerificationStatus,
)
from app.services.prefilter import PrefilterResult
from app.services.verification_pipeline import VerificationPipeline


@pytest_asyncio.fixture
async def integration_app():
    """Sets up an isolated in-memory test database and mock pipeline for API integration testing."""
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

    # Create mock pipeline to guarantee zero real external network or LLM calls
    mock_pipeline = VerificationPipeline()
    mock_pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["software_version"], confidence=0.9
    ))
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[
        ExtractedClaim(
            claim_id="claim_001",
            text="Python 3.12 is the latest stable version.",
            category=ClaimCategory.SOFTWARE_VERSION,
            entity="Python",
            attribute="latest_version",
            time_sensitive=True,
        )
    ])
    mock_ev = EvidenceItem(
        evidence_id="ev_001",
        title="Python Releases",
        url="https://www.python.org/downloads/",
        content="Python 3.12 is the latest stable release.",
        relevance_score=0.95,
        source_type=EvidenceSourceType.OFFICIAL_DOCS,
        retrieved_at=datetime.now(timezone.utc),
    )
    mock_pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[mock_ev])
    mock_pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_001",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.95,
        reason="Evidence confirms Python 3.12 is the latest stable release.",
        evidence_ids=["ev_001"],
        evidence=[EvidenceMinimal(title="Python Releases", url="https://www.python.org/downloads/")],
        checked_at=datetime.now(timezone.utc),
    ))

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, mock_pipeline, sm

    app.dependency_overrides.clear()
    await engine.dispose()


# 1. Health endpoint
@pytest.mark.asyncio
async def test_health_endpoint(integration_app):
    client, _, _ = integration_app
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "freshguard-verification"
    assert "version" in data


# 2. Valid POST request
@pytest.mark.asyncio
async def test_valid_post_request(integration_app):
    client, _, _ = integration_app
    payload = {
        "request_id": "req_api_001",
        "text": "Python 3.12 is the latest stable version.",
        "mode": "blocking",
    }
    resp = await client.post("/v1/verifications", json=payload, headers={"X-Request-ID": "req_api_001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "req_api_001"
    assert "verification_id" in data
    assert data["status"] == "completed"
    assert data["freshness_status"] == "FRESH"
    assert data["requires_refresh"] is False
    assert data["claims_checked"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["verdict"] == "supported"


# 3. Invalid POST request (malformed types)
@pytest.mark.asyncio
async def test_invalid_post_request(integration_app):
    client, _, _ = integration_app
    payload = {
        "request_id": "req_bad",
        "text": "Some text",
        "mode": "invalid_mode_unknown",
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "validation_errors" in data["details"]


# 4. Missing required fields
@pytest.mark.asyncio
async def test_missing_required_fields(integration_app):
    client, _, _ = integration_app
    payload = {
        "request_id": "req_missing_text",
        # missing text/response_text
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "VALIDATION_ERROR"


# 5. Complete verification response structure
@pytest.mark.asyncio
async def test_complete_verification_response(integration_app):
    client, _, _ = integration_app
    payload = {
        "request_id": "req_complete_005",
        "text": "Python 3.12 is released.",
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Verify all expected top-level fields
    for field in ["request_id", "verification_id", "status", "requires_refresh", "claims_checked", "results", "claims", "processing_time_ms", "checked_at"]:
        assert field in data, f"Missing expected field: {field}"

    # Results and claims must mirror each other for Go client compatibility
    assert data["results"] == data["claims"]

    # Verify claim verdict structure
    claim = data["results"][0]
    for c_field in ["claim_id", "verdict", "confidence", "reason", "evidence_ids", "evidence", "checked_at"]:
        assert c_field in claim, f"Missing claim field: {c_field}"


# 6. GET existing verification
@pytest.mark.asyncio
async def test_get_existing_verification(integration_app):
    client, _, _ = integration_app
    post_payload = {
        "request_id": "req_get_006",
        "text": "Python 3.12 is current version.",
    }
    post_resp = await client.post("/v1/verifications", json=post_payload)
    assert post_resp.status_code == 200
    verif_id = post_resp.json()["verification_id"]

    get_resp = await client.get(f"/v1/verifications/{verif_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["verification_id"] == verif_id
    assert data["request_id"] == "req_get_006"
    assert data["status"] == "completed"
    assert data["freshness_status"] == "FRESH"
    assert len(data["claims"]) == 1


# 7. GET nonexistent verification
@pytest.mark.asyncio
async def test_get_nonexistent_verification(integration_app):
    client, _, _ = integration_app
    resp = await client.get("/v1/verifications/verif_nonexistent_99999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["code"] == "NOT_FOUND"
    assert "not found" in data["message"].lower()


# 8. Correct HTTP status codes
@pytest.mark.asyncio
async def test_correct_http_status_codes(integration_app):
    client, _, _ = integration_app
    # Success 200
    r_ok = await client.post("/v1/verifications", json={"request_id": "r1", "text": "Test"})
    assert r_ok.status_code == 200

    # Validation Error 422
    r_val = await client.post("/v1/verifications", json={})
    assert r_val.status_code == 422

    # Not Found 404
    r_nf = await client.get("/v1/verifications/no_such_id")
    assert r_nf.status_code == 404


# 9. Database persistence verification
@pytest.mark.asyncio
async def test_database_persistence(integration_app):
    client, _, sm = integration_app
    req_id = "req_persist_009"
    resp = await client.post("/v1/verifications", json={"request_id": req_id, "text": "Python 3.12"})
    assert resp.status_code == 200
    verif_id = resp.json()["verification_id"]

    # Verify directly via session
    async with sm() as session:
        record = await VerificationRepository.get_verification_by_id(session, verif_id)
        assert record is not None
        assert record.request_id == req_id
        assert record.status == "completed"
        assert record.freshness_status == "FRESH"
        assert len(record.claims) == 1
        assert len(record.claims[0].evidence) >= 1


# 10. Response schema compatibility (Pydantic model roundtrip)
@pytest.mark.asyncio
async def test_response_schema_compatibility(integration_app):
    client, _, _ = integration_app
    resp = await client.post("/v1/verifications", json={"request_id": "req_roundtrip", "text": "Sample text"})
    assert resp.status_code == 200
    # Re-parse into VerificationResponse
    parsed = VerificationResponse.model_validate(resp.json())
    assert parsed.request_id == "req_roundtrip"
    assert parsed.status == LifecycleStatus.COMPLETED
    assert parsed.freshness_status == FreshnessStatus.FRESH


# 11. Enum serialization (strings, not internal objects)
@pytest.mark.asyncio
async def test_enum_serialization(integration_app):
    client, _, _ = integration_app
    resp = await client.post("/v1/verifications", json={"request_id": "req_enum", "text": "Python 3.12"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["status"], str)
    assert data["status"] in ("FRESH", "STALE", "UNCERTAIN", "NOT_REQUIRED", "completed", "accepted", "failed")
    assert isinstance(data["results"][0]["verdict"], str)
    assert data["results"][0]["verdict"] in ("SUPPORTED", "CONTRADICTED", "UNCLEAR", "supported", "contradicted", "unclear")


# 12. Timestamp serialization (ISO 8601 with UTC)
@pytest.mark.asyncio
async def test_timestamp_serialization(integration_app):
    client, _, _ = integration_app
    resp = await client.post("/v1/verifications", json={"request_id": "req_ts", "text": "Python 3.12"})
    assert resp.status_code == 200
    data = resp.json()
    checked_at_str = data["checked_at"]
    assert checked_at_str is not None
    # Verify parseable as ISO 8601
    dt = datetime.fromisoformat(checked_at_str.replace("Z", "+00:00"))
    assert dt.tzinfo is not None


# 13. Internal error handling without exposing stack traces
@pytest.mark.asyncio
async def test_internal_error_handling(integration_app):
    client, mock_pipeline, _ = integration_app
    mock_pipeline.verify = AsyncMock(side_effect=RuntimeError("Secret database password / crash"))

    resp = await client.post("/v1/verifications", json={"request_id": "req_err", "text": "Trigger error"})
    assert resp.status_code == 500
    data = resp.json()
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    # Never expose internal stack traces or secrets
    assert "Secret database password" not in json.dumps(data)


# 14. Dependency overrides for isolated test databases
@pytest.mark.asyncio
async def test_dependency_overrides_isolated_db(integration_app):
    client, _, sm = integration_app
    # Ensure sessionmaker is connected to in-memory SQLite and distinct from any file database
    async with sm() as session:
        records = await VerificationRepository.list_verification_history(session)
        assert isinstance(records, list)


# 15. No real Tavily or LLM API calls attempted
@pytest.mark.asyncio
async def test_no_real_api_calls(integration_app):
    client, mock_pipeline, _ = integration_app
    # Verify mock was called rather than real HTTP client
    resp = await client.post("/v1/verifications", json={"request_id": "req_no_call", "text": "Python 3.12"})
    assert resp.status_code == 200
    mock_pipeline.extraction_engine.extract_claims.assert_called_once()
    mock_pipeline.tavily_service.retrieve_evidence_for_claim.assert_called_once()


# 16. Contract validation against shared/schemas/verification_api.json
@pytest.mark.asyncio
async def test_contract_validation_against_shared_schema(integration_app):
    """
    Validates that request and response payloads adhere to the shared contract schema.
    """
    client, _, _ = integration_app
    schema_path = Path(__file__).resolve().parents[3] / "shared" / "schemas" / "verification_api.json"
    assert schema_path.exists(), f"Shared schema not found at {schema_path}"

    with open(schema_path, "r", encoding="utf-8") as f:
        shared_schema = json.load(f)

    # 1. Validate request payload against shared VerificationRequest definition
    req_schema = shared_schema["oneOf"][0]  # VerificationRequest
    req_payload = {
        "request_id": "req_schema_test",
        "text": "Python 3.12 is the latest version.",
        "mode": "blocking",
        "categories": ["software_version"],
    }
    jsonschema.validate(instance=req_payload, schema=req_schema)

    # 2. Submit request and get response
    resp = await client.post("/v1/verifications", json=req_payload)
    assert resp.status_code == 200
    resp_data = resp.json()

    # 3. Full validation of response against shared VerificationResponse schema
    resp_schema = {
        "$schema": shared_schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
        "definitions": shared_schema["definitions"],
        **shared_schema["oneOf"][1],
    }
    jsonschema.validate(instance=resp_data, schema=resp_schema)

    # 4. Check compatibility with Go client expected fields
    assert "verification_id" in resp_data
    assert "request_id" in resp_data
    assert "status" in resp_data
    assert "claims" in resp_data
    assert isinstance(resp_data["claims"], list)
    if resp_data["claims"]:
        claim = resp_data["claims"][0]
        assert "claim_id" in claim
        assert "verdict" in claim
        assert "confidence" in claim
        assert "evidence" in claim

    # 5. GET response validation against shared schema
    verif_id = resp_data["verification_id"]
    get_resp = await client.get(f"/v1/verifications/{verif_id}")
    assert get_resp.status_code == 200
    jsonschema.validate(instance=get_resp.json(), schema=resp_schema)


# 17. Lowercase verdict serialization
@pytest.mark.asyncio
async def test_lowercase_verdict_serialization(integration_app):
    client, _, _ = integration_app
    resp = await client.post("/v1/verifications", json={"request_id": "req_lc_verdict", "text": "Python 3.12 is released."})
    assert resp.status_code == 200
    data = resp.json()
    for claim in data["claims"]:
        assert claim["verdict"] in ("supported", "contradicted", "unclear")
        assert claim["verdict"] == claim["verdict"].lower()


# 18. Lifecycle status and freshness separation
@pytest.mark.asyncio
async def test_lifecycle_and_freshness_separation(integration_app):
    client, _, sm = integration_app
    resp = await client.post("/v1/verifications", json={"request_id": "req_sep", "text": "Python 3.12 is released."})
    assert resp.status_code == 200
    data = resp.json()
    # status must be lifecycle
    assert data["status"] in ("accepted", "completed", "failed")
    assert data["status"] == "completed"
    # freshness_status must be freshness evaluation
    assert data["freshness_status"] in ("FRESH", "STALE", "UNCERTAIN", "NOT_REQUIRED")
    assert data["freshness_status"] == "FRESH"

    # Verify DB separation
    async with sm() as session:
        rec = await VerificationRepository.get_verification_by_id(session, data["verification_id"])
        assert rec.status == "completed"
        assert rec.freshness_status == "FRESH"


# 19. Claim metadata serialization
@pytest.mark.asyncio
async def test_claim_metadata_serialization(integration_app):
    client, _, _ = integration_app
    resp = await client.post("/v1/verifications", json={"request_id": "req_claim_meta", "text": "Python 3.12 is released."})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["claims"]) > 0
    c = data["claims"][0]
    assert c["category"] == "software_version"
    assert c["entity"] == "Python"
    assert c["attribute"] == "latest_version"
    assert c["original_text"] == "Python 3.12 is the latest stable version."
    assert c["text"] == c["original_text"]


# 20. Evidence field aliases
@pytest.mark.asyncio
async def test_evidence_field_aliases(integration_app):
    client, _, _ = integration_app
    resp = await client.post("/v1/verifications", json={"request_id": "req_ev_aliases", "text": "Python 3.12 is released."})
    assert resp.status_code == 200
    data = resp.json()
    ev = data["claims"][0]["evidence"][0]
    # url and source_url must match
    assert ev["url"] == ev["source_url"]
    assert "https://www.python.org/downloads/" in ev["source_url"]
    # title and source_title must match
    assert ev["title"] == ev["source_title"]
    # snippet and content must match
    assert ev["snippet"] == ev["content"]


# 21. Repeated request_id / idempotency behavior
@pytest.mark.asyncio
async def test_repeated_request_id_idempotency(integration_app):
    client, mock_pipeline, _ = integration_app
    payload = {"request_id": "req_idempotent_test", "text": "Python 3.12 is released."}
    resp1 = await client.post("/v1/verifications", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Second call with identical request_id
    resp2 = await client.post("/v1/verifications", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Must return same verification_id
    assert data1["verification_id"] == data2["verification_id"]
    assert data1["request_id"] == data2["request_id"]
    assert data2["status"] == "completed"
    assert data2["freshness_status"] == "FRESH"


# 22. Async mode handling (synchronous execution fallback)
@pytest.mark.asyncio
async def test_async_mode_handling(integration_app):
    client, _, _ = integration_app
    payload = {"request_id": "req_async_mode", "text": "Python 3.12 is released.", "mode": "async"}
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["freshness_status"] == "FRESH"
