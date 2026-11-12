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
from app.schemas.response import FreshnessStatus, LifecycleStatus, VerificationResponse
from app.services.prefilter import PrefilterResult
from app.services.verification_pipeline import VerificationPipeline
from app.utils.exceptions import ExtractionError, TavilyAPIError


@pytest_asyncio.fixture
async def system_test_env():
    """
    Sets up an isolated in-memory SQLite database and configurable mock pipeline
    for end-to-end HTTP integration testing across all 13 Stage 11 scenarios.
    Guarantees zero network or external API access.
    """
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

    # Default mock pipeline behaviors
    mock_pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["software_version"], confidence=0.92
    ))
    mock_claim = ExtractedClaim(
        claim_id="claim_sys_001",
        text="Python 3.12 is the latest stable release.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
        time_sensitive=True,
    )
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[mock_claim])

    mock_ev = EvidenceItem(
        evidence_id="ev_sys_001",
        title="Python Documentation",
        url="https://www.python.org/downloads/",
        content="Python 3.12 is the current stable release.",
        relevance_score=0.96,
        source_type=EvidenceSourceType.OFFICIAL_DOCS,
        retrieved_at=datetime.now(timezone.utc),
    )
    mock_pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[mock_ev])
    mock_pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_sys_001",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.96,
        reason="Official release documentation confirms Python 3.12.",
        evidence_ids=["ev_sys_001"],
        evidence=[EvidenceMinimal(title="Python Documentation", url="https://www.python.org/downloads/")],
        checked_at=datetime.now(timezone.utc),
    ))

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_pipeline] = lambda: mock_pipeline

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, mock_pipeline, sm

    app.dependency_overrides.clear()
    await engine.dispose()


# ==============================================================================
# Scenario 1: Python service health endpoint
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_01_health_endpoint(system_test_env):
    """Scenario 1: Verifies the health check endpoint returns 200 with service metadata."""
    client, _, _ = system_test_env
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "freshguard-verification"
    assert "version" in data


# ==============================================================================
# Scenario 2: Valid blocking verification request
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_02_valid_blocking_verification(system_test_env):
    """Scenario 2: Verifies a standard blocking verification request returns HTTP 200 with completed status."""
    client, _, _ = system_test_env
    payload = {
        "request_id": "req_scenario_02",
        "text": "Python 3.12 is the latest stable release.",
        "mode": "blocking",
        "categories": ["software_version"],
    }
    resp = await client.post("/v1/verifications", json=payload, headers={"X-Request-ID": "req_scenario_02"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "req_scenario_02"
    assert data["status"] == "completed"
    assert data["freshness_status"] == "FRESH"
    assert data["requires_refresh"] is False
    assert data["claims_checked"] == 1
    assert len(data["claims"]) == 1
    assert data["claims"][0]["verdict"] == "supported"


# ==============================================================================
# Scenario 3: Invalid request and schema validation
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_03_invalid_request_validation(system_test_env):
    """Scenario 3: Verifies malformed or missing fields produce HTTP 422 with structured APIError."""
    client, _, _ = system_test_env

    # Submitting empty payload
    resp = await client.post("/v1/verifications", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert data["retryable"] is False
    assert "validation_errors" in data["details"]

    # Submitting invalid enum mode
    bad_payload = {"request_id": "req_bad_mode", "text": "Some statement", "mode": "invalid_mode_value"}
    resp_bad = await client.post("/v1/verifications", json=bad_payload)
    assert resp_bad.status_code == 422
    assert resp_bad.json()["code"] == "VALIDATION_ERROR"


# ==============================================================================
# Scenario 4: Empty or irrelevant claims
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_04_empty_or_irrelevant_claims(system_test_env):
    """Scenario 4: Verifies timeless facts or un-extractable claims bypass claim verification cleanly."""
    client, mock_pipeline, _ = system_test_env

    # 4A. Prefilter deems verification unnecessary (timeless fact)
    mock_pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=False, categories=[], confidence=0.0, matched_signals=["timeless_fact"]
    ))
    mock_pipeline.extraction_engine.extract_claims = AsyncMock()

    timeless_payload = {
        "request_id": "req_timeless_04",
        "text": "Water boils at 100 degrees Celsius under standard atmospheric pressure.",
        "mode": "blocking",
    }
    resp_timeless = await client.post("/v1/verifications", json=timeless_payload)
    assert resp_timeless.status_code == 200
    data_timeless = resp_timeless.json()
    assert data_timeless["status"] == "completed"
    assert data_timeless["freshness_status"] == "NOT_REQUIRED"
    assert data_timeless["claims_checked"] == 0
    # Extraction engine was never invoked
    mock_pipeline.extraction_engine.extract_claims.assert_not_called()

    # 4B. Text with zero extracted time-sensitive claims
    mock_pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["general"], confidence=0.5
    ))
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[])

    general_payload = {
        "request_id": "req_no_claims_04",
        "text": "Thank you for reaching out, have a great day!",
        "mode": "blocking",
    }
    resp_general = await client.post("/v1/verifications", json=general_payload)
    assert resp_general.status_code == 200
    data_general = resp_general.json()
    assert data_general["status"] == "completed"
    assert data_general["freshness_status"] == "FRESH"
    assert data_general["claims_checked"] == 0
    assert len(data_general["claims"]) == 0


# ==============================================================================
# Scenario 5: Tavily evidence retrieval using mocks
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_05_tavily_evidence_retrieval(system_test_env):
    """Scenario 5: Verifies Tavily evidence is retrieved, formatted, and exposed in response and database."""
    client, mock_pipeline, sm = system_test_env

    ev_doc = EvidenceItem(
        evidence_id="ev_stripe_doc",
        title="Stripe Official Pricing",
        url="https://stripe.com/pricing",
        content="Standard fee is 2.9% plus 30 cents per successful card charge.",
        relevance_score=0.98,
        source_type=EvidenceSourceType.OFFICIAL_DOCS,
        retrieved_at=datetime.now(timezone.utc),
    )
    mock_pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev_doc])
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[
        ExtractedClaim(
            claim_id="c_stripe",
            text="Stripe processing rate is 2.9% + 30c",
            category=ClaimCategory.PRICING,
            entity="Stripe",
            attribute="fee",
            time_sensitive=True,
        )
    ])
    mock_pipeline.verdict_engine.evaluate_claim = AsyncMock(return_value=ClaimVerdictResult(
        claim_id="c_stripe",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.98,
        reason="Stripe pricing confirmed.",
        evidence_ids=["ev_stripe_doc"],
        evidence=[EvidenceMinimal(title="Stripe Official Pricing", url="https://stripe.com/pricing")],
        checked_at=datetime.now(timezone.utc),
    ))

    resp = await client.post("/v1/verifications", json={"request_id": "req_tavily_05", "text": "Stripe rate is 2.9%"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["claims"]) == 1
    ev_list = data["claims"][0]["evidence"]
    assert len(ev_list) == 1
    assert ev_list[0]["source_url"] == "https://stripe.com/pricing"
    assert ev_list[0]["source_title"] == "Stripe Official Pricing"
    assert "evidence_id" in ev_list[0]

    # Verify persisted to SQLite
    verif_id = data["verification_id"]
    async with sm() as session:
        record = await VerificationRepository.get_verification_by_id(session, verif_id)
        assert record is not None
        assert len(record.claims[0].evidence) == 1
        assert record.claims[0].evidence[0].url == "https://stripe.com/pricing"


# ==============================================================================
# Scenario 6: Supported, contradicted, and unclear verdicts
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_06_claim_verdicts(system_test_env):
    """Scenario 6: Verifies lowercase claim verdict representation across supported, contradicted, and unclear."""
    client, mock_pipeline, _ = system_test_env

    # 6A. Contradicted claim -> STALE freshness
    c_false = ExtractedClaim(
        claim_id="c_false", text="Python 2.7 is latest", category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python", attribute="latest_version", time_sensitive=True,
    )
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[c_false])
    mock_pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="c_false", verdict=ClaimVerdict.CONTRADICTED, confidence=0.99,
        reason="Python 3.12 is newer than 2.7", evidence_ids=["ev1"],
        evidence=[EvidenceMinimal(title="Python", url="https://python.org")],
        checked_at=datetime.now(timezone.utc),
    ))

    resp_contra = await client.post("/v1/verifications", json={"request_id": "req_contra", "text": "Python 2.7 is latest"})
    data_contra = resp_contra.json()
    assert data_contra["claims"][0]["verdict"] == "contradicted"
    assert data_contra["freshness_status"] == "STALE"
    assert data_contra["requires_refresh"] is True
    assert data_contra["status"] == "completed"

    # 6B. Unclear claim -> UNCERTAIN freshness
    c_unclear = ExtractedClaim(
        claim_id="c_unclear", text="Unknown startup is worth $10B", category=ClaimCategory.CURRENT_STATISTICS,
        entity="Startup", attribute="valuation", time_sensitive=True,
    )
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[c_unclear])
    mock_pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[])  # No evidence

    resp_unclear = await client.post("/v1/verifications", json={"request_id": "req_unclear", "text": "Startup worth $10B"})
    data_unclear = resp_unclear.json()
    assert data_unclear["claims"][0]["verdict"] == "unclear"
    assert data_unclear["freshness_status"] == "UNCERTAIN"
    assert data_unclear["requires_refresh"] is False
    assert data_unclear["status"] == "completed"


# ==============================================================================
# Scenario 7: Lifecycle status and freshness status separation
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_07_status_separation(system_test_env):
    """Scenario 7: Verifies strict separation between lifecycle status and freshness status."""
    client, _, _ = system_test_env
    resp = await client.post("/v1/verifications", json={"request_id": "req_sep_07", "text": "Python 3.12 released."})
    assert resp.status_code == 200
    data = resp.json()

    # status is lifecycle only
    assert data["status"] in ("accepted", "completed", "failed")
    assert data["status"] == "completed"

    # freshness_status is domain freshness only
    assert data["freshness_status"] in ("FRESH", "STALE", "UNCERTAIN", "NOT_REQUIRED")
    assert data["freshness_status"] == "FRESH"


# ==============================================================================
# Scenario 8: Database persistence and GET retrieval
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_08_persistence_and_get_retrieval(system_test_env):
    """Scenario 8: Verifies verified facts persist and GET returns matching schema."""
    client, _, _ = system_test_env
    post_resp = await client.post("/v1/verifications", json={"request_id": "req_persist_08", "text": "Python 3.12 released."})
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    verif_id = post_data["verification_id"]

    # Retrieve through GET endpoint
    get_resp = await client.get(f"/v1/verifications/{verif_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()

    # Compare key fields
    assert get_data["verification_id"] == verif_id
    assert get_data["request_id"] == "req_persist_08"
    assert get_data["status"] == "completed"
    assert get_data["freshness_status"] == "FRESH"
    assert len(get_data["claims"]) == len(post_data["claims"])
    assert get_data["claims"][0]["verdict"] == post_data["claims"][0]["verdict"]
    assert get_data["claims"][0]["evidence"][0]["source_url"] == post_data["claims"][0]["evidence"][0]["source_url"]


# ==============================================================================
# Scenario 9: Duplicate request ID idempotency
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_09_request_id_idempotency(system_test_env):
    """Scenario 9: Verifies repeated submissions with identical request_id return the original result."""
    client, mock_pipeline, _ = system_test_env
    payload = {"request_id": "req_idempotent_09", "text": "Python 3.12 released."}

    # First submission
    resp1 = await client.post("/v1/verifications", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Reset mock call counts to verify pipeline is completely bypassed on second call
    mock_pipeline.extraction_engine.extract_claims.reset_mock()
    mock_pipeline.tavily_service.retrieve_evidence_for_claim.reset_mock()

    # Second submission
    resp2 = await client.post("/v1/verifications", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data1["verification_id"] == data2["verification_id"]
    assert data1["request_id"] == data2["request_id"]
    # Neither extraction nor Tavily retrieval must be invoked on idempotent hit
    mock_pipeline.extraction_engine.extract_claims.assert_not_called()
    mock_pipeline.tavily_service.retrieve_evidence_for_claim.assert_not_called()


# ==============================================================================
# Scenario 10: Tavily timeout and external service failure
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_10_tavily_timeout_failure(system_test_env):
    """Scenario 10: Verifies Tavily API timeouts fail gracefully to UNCLEAR without a 500 error."""
    client, mock_pipeline, _ = system_test_env

    mock_pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(
        side_effect=TavilyAPIError("Tavily request timed out after 10.0s")
    )
    mock_pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[
        ExtractedClaim(claim_id="c_timeout", text="Test claim", category=ClaimCategory.OTHER, entity="E", attribute="A")
    ])

    resp = await client.post("/v1/verifications", json={"request_id": "req_timeout_10", "text": "Test claim"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["freshness_status"] == "UNCERTAIN"
    assert data["claims"][0]["verdict"] == "unclear"
    assert "Evidence retrieval failed" in data["claims"][0]["reason"]


# ==============================================================================
# Scenario 11: Malformed LLM/extraction response
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_11_malformed_extraction_failure(system_test_env):
    """Scenario 11: Verifies extraction engine failure handles cleanly with UNCERTAIN freshness and error detail."""
    client, mock_pipeline, _ = system_test_env

    mock_pipeline.extraction_engine.extract_claims = AsyncMock(
        side_effect=ExtractionError("LLM response was not valid JSON")
    )

    resp = await client.post("/v1/verifications", json={"request_id": "req_extract_fail_11", "text": "Unparseable raw text"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["freshness_status"] == "UNCERTAIN"
    assert data["claims_checked"] == 0
    assert data["error"] is not None
    assert data["error"]["code"] == "EXTRACTION_FAILURE"


# ==============================================================================
# Scenario 12: Go client request payload compatibility
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_12_go_client_payload_compatibility(system_test_env):
    """
    Scenario 12: Simulates the exact HTTP request generated by Go Bifrost plugin client (client.go).
    Verifies full compatibility with Go client VerificationRequest & VerificationResponse structs.
    """
    client, _, _ = system_test_env

    # Exact JSON serialization produced by Go client:
    # type VerificationRequest struct { RequestID string, Text string, Mode string, Categories []string }
    go_payload = {
        "request_id": "req_bifrost_go_sim",
        "text": "Stripe processing fee is 2.9% plus 30 cents per transaction.",
        "mode": "blocking",
        "categories": ["pricing", "software_version", "leadership"],
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Request-ID": "req_bifrost_go_sim",
    }

    resp = await client.post("/v1/verifications", json=go_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Verify all fields in Go VerificationResponse struct:
    # VerificationID string, RequestID string, Status string, CheckedAt *time.Time, Claims []Claim
    assert "verification_id" in data and isinstance(data["verification_id"], str)
    assert data["request_id"] == "req_bifrost_go_sim"
    assert data["status"] == "completed"  # Matches client.StatusCompleted = "completed"
    assert "checked_at" in data
    assert isinstance(data["claims"], list)

    # Verify all fields in Go Claim struct:
    # ClaimID, Category, Entity, Attribute, OriginalText, Verdict, Confidence, CheckedAt, Evidence
    claim = data["claims"][0]
    assert "claim_id" in claim
    assert "category" in claim
    assert "entity" in claim
    assert "attribute" in claim
    assert "original_text" in claim
    assert claim["verdict"] in ("supported", "contradicted", "unclear")
    assert isinstance(claim["confidence"], float)
    assert "checked_at" in claim
    assert isinstance(claim["evidence"], list)

    # Verify all fields in Go Evidence struct:
    # EvidenceID, SourceURL, SourceTitle, Snippet, RetrievedAt, SourceType
    ev = claim["evidence"][0]
    assert "evidence_id" in ev
    assert "source_url" in ev
    assert "source_title" in ev
    assert "snippet" in ev
    assert "retrieved_at" in ev
    assert "source_type" in ev


# ==============================================================================
# Scenario 13: Response serialization compatibility with shared JSON schema
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_13_shared_json_schema_compliance(system_test_env):
    """
    Scenario 13: Strictly validates POST response, GET response, and error response
    against shared/schemas/verification_api.json.
    """
    client, _, _ = system_test_env
    schema_path = Path(__file__).resolve().parents[3] / "shared" / "schemas" / "verification_api.json"
    assert schema_path.exists(), f"Shared JSON schema missing at {schema_path}"

    with open(schema_path, "r", encoding="utf-8") as f:
        shared_schema = json.load(f)

    # Validate VerificationRequest schema against our test payload
    req_schema = shared_schema["oneOf"][0]
    test_req = {
        "request_id": "req_schema_strict",
        "text": "Python 3.12 is the latest stable release.",
        "mode": "blocking",
        "categories": ["software_version"],
    }
    jsonschema.validate(instance=test_req, schema=req_schema)

    # Submit and receive POST response
    post_resp = await client.post("/v1/verifications", json=test_req)
    assert post_resp.status_code == 200
    post_data = post_resp.json()

    # Validate POST response against VerificationResponse schema
    resp_schema = {
        "$schema": shared_schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
        "definitions": shared_schema["definitions"],
        **shared_schema["oneOf"][1],
    }
    jsonschema.validate(instance=post_data, schema=resp_schema)

    # Validate GET response against VerificationResponse schema
    verif_id = post_data["verification_id"]
    get_resp = await client.get(f"/v1/verifications/{verif_id}")
    assert get_resp.status_code == 200
    jsonschema.validate(instance=get_resp.json(), schema=resp_schema)

    # Validate 422 error response against APIError schema
    err_resp = await client.post("/v1/verifications", json={})
    assert err_resp.status_code == 422
    err_data = err_resp.json()
    err_schema = {
        "$schema": shared_schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
        "definitions": shared_schema["definitions"],
        **shared_schema["definitions"]["APIError"],
    }
    jsonschema.validate(instance=err_data, schema=err_schema)
