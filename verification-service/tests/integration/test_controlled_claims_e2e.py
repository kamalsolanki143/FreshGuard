import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.schemas.claims import ClaimCategory, ClaimVerdict
from app.schemas.response import FreshnessStatus, LifecycleStatus


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    # ASGITransport does not automatically trigger FastAPI lifespan.
    # Start it explicitly so schema initialization and shutdown match production.
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Content-Type": "application/json"},
        ) as c:
            yield c


@pytest.mark.asyncio
async def test_scenario_1_current_software_version(client):
    """Scenario 1: A known current software version assertion."""
    payload = {
        "request_id": "e2e-scen-1",
        "text": "Python 3.12 is the latest stable version.",
        "categories": ["software_version"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "e2e-scen-1"
    assert data["status"] == LifecycleStatus.COMPLETED.value
    assert data["claims_checked"] >= 1
    assert any(c["category"] == "software_version" for c in data["claims"])


@pytest.mark.asyncio
async def test_scenario_2_outdated_software_version(client):
    """Scenario 2: A deliberately outdated software version assertion."""
    payload = {
        "request_id": "e2e-scen-2",
        "text": "Python 3.8 is the latest stable version.",
        "categories": ["software_version"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == LifecycleStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_scenario_3_pricing_claim_official_evidence(client):
    """Scenario 3: A pricing claim with official evidence."""
    payload = {
        "request_id": "e2e-scen-3",
        "text": "ChatGPT Plus costs $20 per month.",
        "categories": ["pricing"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["claims_checked"] >= 1
    pricing_claims = [c for c in data["claims"] if c["category"] == "pricing"]
    assert len(pricing_claims) >= 1
    # Check persistence
    verif_id = data["verification_id"]
    get_resp = await client.get(f"/v1/verifications/{verif_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["verification_id"] == verif_id


@pytest.mark.asyncio
async def test_scenario_4_contradicted_pricing_claim(client):
    """Scenario 4: A contradicted pricing claim (e.g. Free API hallucination)."""
    payload = {
        "request_id": "e2e-scen-4",
        "text": "Contradicted claim text",
        "categories": ["pricing"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == LifecycleStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_scenario_5_leadership_claim_official_evidence(client):
    """Scenario 5: A leadership claim with official evidence."""
    payload = {
        "request_id": "e2e-scen-5",
        "text": "Sundar Pichai is the CEO of Google.",
        "categories": ["leadership"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["claims_checked"] >= 1
    assert any(c["category"] == "leadership" for c in data["claims"])


@pytest.mark.asyncio
async def test_scenario_6_claim_with_no_reliable_evidence(client):
    """Scenario 6: A claim with no reliable evidence returns UNCLEAR."""
    payload = {
        "request_id": "e2e-scen-6",
        "text": "Ambiguous unverified claim with mysterious entity.",
        "categories": ["other"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == LifecycleStatus.COMPLETED.value
    # Never converts missing or ambiguous evidence into false SUPPORTED
    if data["claims_checked"] > 0:
        for c in data["claims"]:
            assert c["verdict"] in ["unclear", "contradicted"]


@pytest.mark.asyncio
async def test_scenario_7_multiple_categories_response(client):
    """Scenario 7: A response containing multiple categories in one passage."""
    payload = {
        "request_id": "e2e-scen-7",
        "text": (
            "Python 3.12 is the latest version. "
            "ChatGPT Plus costs $20 per month. "
            "Sundar Pichai is the CEO of Google."
        ),
        "categories": ["software_version", "pricing", "leadership"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["claims_checked"] == 3
    found_categories = {c["category"] for c in data["claims"]}
    assert "software_version" in found_categories
    assert "pricing" in found_categories
    assert "leadership" in found_categories


@pytest.mark.asyncio
async def test_scenario_8_no_time_sensitive_claims(client):
    """Scenario 8: A response with no time-sensitive claims."""
    payload = {
        "request_id": "e2e-scen-8",
        "text": "Photosynthesis is the biological process by which green plants synthesize nutrients from water and carbon dioxide using sunlight.",
        "categories": ["pricing", "software_version", "leadership"]
    }
    resp = await client.post("/v1/verifications", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["claims_checked"] == 0
    assert data["freshness_status"] == FreshnessStatus.NOT_REQUIRED.value
    assert data["requires_refresh"] is False
    assert len(data["claims"]) == 0
