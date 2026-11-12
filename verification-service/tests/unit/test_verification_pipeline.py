import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base
from app.database.repository import VerificationRepository, generate_claim_fingerprint
from app.schemas.claims import (
    ClaimCategory,
    ClaimVerdict,
    ClaimVerdictResult,
    ExtractedClaim,
)
from app.schemas.evidence import (
    EvidenceItem,
    EvidenceMinimal,
    EvidenceSourceType,
)
from app.schemas.request import VerificationRequest
from app.schemas.response import (
    FreshnessStatus,
    LifecycleStatus,
    VerificationResponse,
    VerificationStatus,
)
from app.services.extraction import ClaimExtractionEngine
from app.services.freshness_policy import FreshnessPolicyEngine
from app.services.prefilter import PrefilterEngine, PrefilterResult
from app.services.tavily_service import TavilyService
from app.services.verdict_engine import VerdictEngine
from app.services.verification_pipeline import VerificationPipeline
from app.services.version_validator import VersionValidator
from app.utils.exceptions import (
    DatabaseError,
    ExtractionError,
    TavilyAPIError,
)


@pytest_asyncio.fixture
async def test_db_session():
    """Isolated in-memory SQLite async database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        yield session

    await engine.dispose()


def make_evidence_item(evidence_id: str = "ev_01", title: str = "Official Docs", url: str = "https://example.com/docs") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        title=title,
        url=url,
        content="Python 3.12 is the latest stable release.",
        relevance_score=0.95,
        source_type=EvidenceSourceType.OFFICIAL_DOCS,
        retrieved_at=datetime.now(timezone.utc),
    )


def make_claim(claim_id: str = "claim_001", entity: str = "Python", attribute: str = "latest_version", text: str = "Python 3.12 is the latest stable release.", category: ClaimCategory = ClaimCategory.SOFTWARE_VERSION) -> ExtractedClaim:
    return ExtractedClaim(
        claim_id=claim_id,
        text=text,
        category=category,
        entity=entity,
        attribute=attribute,
        time_sensitive=True,
    )


# 1. Complete verification flow
@pytest.mark.asyncio
async def test_complete_verification_flow(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["software_version"], confidence=0.9, matched_signals=["pricing"]
    ))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[
        make_claim(claim_id="claim_001")
    ])
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[
        make_evidence_item()
    ])
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_001",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.95,
        reason="Evidence confirms Python 3.12 is the latest stable release.",
        evidence_ids=["ev_01"],
        evidence=[EvidenceMinimal(title="Official Docs", url="https://example.com/docs")],
        checked_at=datetime.now(timezone.utc),
    ))

    req = VerificationRequest(request_id="req_001", text="Python 3.12 is the latest release.")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.request_id == "req_001"
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.FRESH
    assert resp.requires_refresh is False
    assert resp.claims_checked == 1
    assert len(resp.results) == 1
    assert resp.results[0].verdict == ClaimVerdict.SUPPORTED


# 2. Prefilter says verification unnecessary
@pytest.mark.asyncio
async def test_prefilter_says_verification_unnecessary(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=False, categories=[], confidence=0.0, matched_signals=["timeless_fact"]
    ))
    pipeline.extraction_engine.extract_claims = AsyncMock()

    req = VerificationRequest(request_id="req_002", text="Photosynthesis uses sunlight to synthesize nutrients.")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.NOT_REQUIRED
    assert resp.requires_refresh is False
    assert resp.claims_checked == 0
    assert len(resp.results) == 0
    pipeline.extraction_engine.extract_claims.assert_not_called()


# 3. Single extracted claim
@pytest.mark.asyncio
async def test_single_extracted_claim(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["pricing"], confidence=0.85
    ))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[
        make_claim(claim_id="c1", entity="Stripe", attribute="rate", text="Stripe fee is 2.9%", category=ClaimCategory.PRICING)
    ])
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[
        make_evidence_item(evidence_id="ev_stripe", title="Stripe Pricing", url="https://stripe.com/pricing")
    ])
    pipeline.verdict_engine.evaluate_claim = AsyncMock(return_value=ClaimVerdictResult(
        claim_id="c1",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.92,
        reason="Stripe fee is 2.9% + 30c.",
        evidence_ids=["ev_stripe"],
        evidence=[EvidenceMinimal(title="Stripe Pricing", url="https://stripe.com/pricing")],
        checked_at=datetime.now(timezone.utc),
    ))

    req = VerificationRequest(request_id="req_003", text="Stripe fee is 2.9%")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.claims_checked == 1
    assert resp.results[0].claim_id == "c1"
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.FRESH


# 4. Multiple extracted claims
@pytest.mark.asyncio
async def test_multiple_extracted_claims(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["leadership", "pricing"], confidence=0.88
    ))
    c1 = make_claim(claim_id="c1", entity="OpenAI", attribute="ceo", text="Sam Altman is CEO of OpenAI", category=ClaimCategory.LEADERSHIP)
    c2 = make_claim(claim_id="c2", entity="ChatGPT", attribute="pro_price", text="ChatGPT Plus is $20/month", category=ClaimCategory.PRICING)
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[c1, c2])

    ev1 = make_evidence_item("ev1", "OpenAI About", "https://openai.com/about")
    ev2 = make_evidence_item("ev2", "ChatGPT Pricing", "https://openai.com/pricing")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(side_effect=[[ev1], [ev2]])

    v1 = ClaimVerdictResult(claim_id="c1", verdict=ClaimVerdict.SUPPORTED, confidence=0.95, reason="Confirmed CEO", evidence_ids=["ev1"], evidence=[EvidenceMinimal(title="OpenAI About", url="https://openai.com/about")])
    v2 = ClaimVerdictResult(claim_id="c2", verdict=ClaimVerdict.SUPPORTED, confidence=0.95, reason="Confirmed $20", evidence_ids=["ev2"], evidence=[EvidenceMinimal(title="ChatGPT Pricing", url="https://openai.com/pricing")])
    pipeline.verdict_engine.evaluate_claim = AsyncMock(side_effect=[v1, v2])

    req = VerificationRequest(request_id="req_004", text="Sam Altman is CEO of OpenAI and ChatGPT Plus is $20/month")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.claims_checked == 2
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.FRESH
    assert resp.requires_refresh is False


# 5. Zero extracted claims
@pytest.mark.asyncio
async def test_zero_extracted_claims(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(
        requires_verification=True, categories=["pricing"], confidence=0.7
    ))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[])

    req = VerificationRequest(request_id="req_005", text="No claims were really here.")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.FRESH
    assert resp.requires_refresh is False
    assert resp.claims_checked == 0
    assert len(resp.results) == 0


# 6. Valid cache hit avoids Tavily
@pytest.mark.asyncio
async def test_valid_cache_hit_avoids_tavily(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_006", entity="FastAPI", attribute="latest_version", text="FastAPI 0.110 is released.", category=ClaimCategory.SOFTWARE_VERSION)

    # Pre-save verification into database so cache hit will find it
    prior_resp = VerificationResponse(
        request_id="prior_req",
        verification_id="prior_verif",
        status=VerificationStatus.FRESH,
        requires_refresh=False,
        claims_checked=1,
        results=[
            ClaimVerdictResult(
                claim_id="claim_006",
                verdict=ClaimVerdict.SUPPORTED,
                confidence=0.95,
                reason="FastAPI 0.110 confirmed released.",
                evidence_ids=["ev_prior"],
                evidence=[EvidenceMinimal(title="FastAPI Release", url="https://github.com/fastapi/releases")],
                checked_at=datetime.now(timezone.utc),
            )
        ]
    )
    ev_item = make_evidence_item("ev_prior", "FastAPI Release", "https://github.com/fastapi/releases")
    await VerificationRepository.save_verification(test_db_session, prior_resp, claims=[claim], evidence_map={"claim_006": [ev_item]})
    await test_db_session.commit()

    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock()

    req = VerificationRequest(request_id="req_006", text="FastAPI 0.110 is released.")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.claims_checked == 1
    assert resp.results[0].verdict == ClaimVerdict.SUPPORTED
    assert "[CACHED FACT]" in resp.results[0].reason
    pipeline.tavily_service.retrieve_evidence_for_claim.assert_not_called()


# 7. Expired cache triggers Tavily
@pytest.mark.asyncio
async def test_expired_cache_triggers_tavily(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_007", entity="Node.js", attribute="latest_version", text="Node.js 22 is out.", category=ClaimCategory.SOFTWARE_VERSION)

    # Pre-save with checked_at in the distant past (expired)
    past_time = datetime.now(timezone.utc) - timedelta(days=10)
    prior_resp = VerificationResponse(
        request_id="prior_req",
        verification_id="prior_verif_old",
        status=VerificationStatus.FRESH,
        requires_refresh=False,
        claims_checked=1,
        checked_at=past_time,
        results=[
            ClaimVerdictResult(
                claim_id="claim_007",
                verdict=ClaimVerdict.SUPPORTED,
                confidence=0.95,
                reason="Old verification",
                evidence_ids=["ev_old"],
                evidence=[EvidenceMinimal(title="Old Docs", url="https://nodejs.org")],
                checked_at=past_time,
            )
        ]
    )
    ev_item = make_evidence_item("ev_old", "Old Docs", "https://nodejs.org")
    await VerificationRepository.save_verification(test_db_session, prior_resp, claims=[claim], evidence_map={"claim_007": [ev_item]})
    await test_db_session.commit()

    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    fresh_ev = make_evidence_item("ev_fresh", "Node.js Current", "https://nodejs.org/current")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[fresh_ev])
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_007", verdict=ClaimVerdict.SUPPORTED, confidence=0.96, reason="Fresh validation", evidence_ids=["ev_fresh"], evidence=[EvidenceMinimal(title="Node.js Current", url="https://nodejs.org/current")]
    ))

    req = VerificationRequest(request_id="req_007", text="Node.js 22 is out.")
    resp = await pipeline.verify(req, session=test_db_session)

    pipeline.tavily_service.retrieve_evidence_for_claim.assert_called_once()
    assert "[CACHED FACT]" not in resp.results[0].reason
    assert resp.results[0].reason == "Fresh validation"


# 8. Cache miss triggers evidence retrieval
@pytest.mark.asyncio
async def test_cache_miss_triggers_evidence_retrieval(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_008", entity="Redis", attribute="latest_version", text="Redis 7.2 released.")
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    ev = make_evidence_item("ev_redis", "Redis Docs", "https://redis.io")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev])
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_008", verdict=ClaimVerdict.SUPPORTED, confidence=0.95, reason="Redis verified", evidence_ids=["ev_redis"], evidence=[EvidenceMinimal(title="Redis Docs", url="https://redis.io")]
    ))

    req = VerificationRequest(request_id="req_008", text="Redis 7.2 released.")
    resp = await pipeline.verify(req, session=test_db_session)

    pipeline.tavily_service.retrieve_evidence_for_claim.assert_called_once()
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.FRESH


# 9. Software-version deterministic path avoids LLM verdict engine
@pytest.mark.asyncio
async def test_software_version_deterministic_path(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_009", entity="Python", attribute="latest_version", text="Python 3.12 is the latest stable version.", category=ClaimCategory.SOFTWARE_VERSION)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    ev = make_evidence_item("ev_py", "Python Release", "https://python.org")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev])

    # VersionValidator returns deterministic SUPPORTED
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_009", verdict=ClaimVerdict.SUPPORTED, confidence=0.97, reason="Python 3.12 is greater than 3.11", evidence_ids=["ev_py"], evidence=[EvidenceMinimal(title="Python Release", url="https://python.org")]
    ))
    pipeline.verdict_engine.evaluate_claim = AsyncMock()

    req = VerificationRequest(request_id="req_009", text="Python 3.12 is latest")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.results[0].verdict == ClaimVerdict.SUPPORTED
    pipeline.verdict_engine.evaluate_claim.assert_not_called()


# 10. Version validator UNCLEAR falls back appropriately
@pytest.mark.asyncio
async def test_version_validator_unclear_falls_back_appropriately(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_010", entity="CustomLib", attribute="version", text="CustomLib v2 is available.", category=ClaimCategory.SOFTWARE_VERSION)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    ev = make_evidence_item("ev_cl", "CustomLib Blog", "https://customlib.org/blog")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev])

    # Deterministic validator returns UNCLEAR (e.g. non-standard version phrasing)
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_010", verdict=ClaimVerdict.UNCLEAR, confidence=0.3, reason="Deterministic validator unclear", evidence_ids=["ev_cl"], evidence=[]
    ))
    # Verdict engine resolves it semantically
    pipeline.verdict_engine.evaluate_claim = AsyncMock(return_value=ClaimVerdictResult(
        claim_id="claim_010", verdict=ClaimVerdict.SUPPORTED, confidence=0.88, reason="Blog confirms CustomLib v2 announcement.", evidence_ids=["ev_cl"], evidence=[EvidenceMinimal(title="CustomLib Blog", url="https://customlib.org/blog")]
    ))

    req = VerificationRequest(request_id="req_010", text="CustomLib v2 is available.")
    resp = await pipeline.verify(req, session=test_db_session)

    pipeline.verdict_engine.evaluate_claim.assert_called_once()
    assert resp.results[0].verdict == ClaimVerdict.SUPPORTED
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.FRESH


# 11. Non-version claims use verdict engine
@pytest.mark.asyncio
async def test_non_version_claims_use_verdict_engine(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_011", entity="Apple", attribute="ceo", text="Tim Cook is CEO of Apple.", category=ClaimCategory.LEADERSHIP)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["leadership"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    ev = make_evidence_item("ev_apple", "Apple Leadership", "https://apple.com/leadership")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev])

    pipeline.version_validator.validate_claim = MagicMock()
    pipeline.verdict_engine.evaluate_claim = AsyncMock(return_value=ClaimVerdictResult(
        claim_id="claim_011", verdict=ClaimVerdict.SUPPORTED, confidence=0.96, reason="Tim Cook confirmed as CEO.", evidence_ids=["ev_apple"], evidence=[EvidenceMinimal(title="Apple Leadership", url="https://apple.com/leadership")]
    ))

    req = VerificationRequest(request_id="req_011", text="Tim Cook is CEO of Apple.")
    resp = await pipeline.verify(req, session=test_db_session)

    pipeline.version_validator.validate_claim.assert_not_called()
    pipeline.verdict_engine.evaluate_claim.assert_called_once()
    assert resp.results[0].verdict == ClaimVerdict.SUPPORTED


# 12. Empty evidence produces UNCLEAR
@pytest.mark.asyncio
async def test_empty_evidence_produces_unclear(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_012", entity="ObscureApp", attribute="pricing", text="ObscureApp costs $50/yr.", category=ClaimCategory.PRICING)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["pricing"], confidence=0.85))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[])

    req = VerificationRequest(request_id="req_012", text="ObscureApp costs $50/yr.")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.results[0].verdict == ClaimVerdict.UNCLEAR
    assert "No supporting or refuting web evidence was retrieved." in resp.results[0].reason
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.UNCERTAIN


# 13. Tavily timeout
@pytest.mark.asyncio
async def test_tavily_timeout(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_013", entity="TestEntity", attribute="attr", text="Test claim", category=ClaimCategory.OTHER)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["other"], confidence=0.8))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(side_effect=TavilyAPIError("Tavily request timed out after 10.0s"))

    req = VerificationRequest(request_id="req_013", text="Test claim")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.results[0].verdict == ClaimVerdict.UNCLEAR
    assert "Evidence retrieval failed" in resp.results[0].reason
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.UNCERTAIN


# 14. Extraction failure
@pytest.mark.asyncio
async def test_extraction_failure(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(side_effect=ExtractionError("LLM response was not valid JSON"))

    req = VerificationRequest(request_id="req_014", text="Some raw text")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.UNCERTAIN
    assert resp.error is not None
    assert resp.error.code == "EXTRACTION_FAILURE"


# 15. Verdict engine failure
@pytest.mark.asyncio
async def test_verdict_engine_failure(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_015", entity="Company", attribute="revenue", text="Company revenue is $1B.", category=ClaimCategory.CURRENT_STATISTICS)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["statistics"], confidence=0.8))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    ev = make_evidence_item("ev_rev", "Company Report", "https://company.com/report")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev])
    pipeline.verdict_engine.evaluate_claim = AsyncMock(side_effect=RuntimeError("LLM inference failed"))

    req = VerificationRequest(request_id="req_015", text="Company revenue is $1B.")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.results[0].verdict == ClaimVerdict.UNCLEAR
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.UNCERTAIN


# 16. Database persistence
@pytest.mark.asyncio
async def test_database_persistence(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_016", entity="Postgres", attribute="latest_version", text="Postgres 16 is released.", category=ClaimCategory.SOFTWARE_VERSION)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    ev = make_evidence_item("ev_pg", "Postgres News", "https://postgresql.org")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev])
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_016", verdict=ClaimVerdict.SUPPORTED, confidence=0.95, reason="Postgres 16 is verified.", evidence_ids=["ev_pg"], evidence=[EvidenceMinimal(title="Postgres News", url="https://postgresql.org")]
    ))

    req = VerificationRequest(request_id="req_016", text="Postgres 16 is released.")
    resp = await pipeline.verify(req, session=test_db_session)

    # Verify persisted in database
    saved_verif = await VerificationRepository.get_verification_by_id(test_db_session, resp.verification_id)
    assert saved_verif is not None
    assert saved_verif.request_id == "req_016"
    assert saved_verif.claims_checked == 1
    assert len(saved_verif.claims) == 1
    assert saved_verif.claims[0].claim_id == "claim_016"


# 17. Database persistence failure
@pytest.mark.asyncio
async def test_database_persistence_failure(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    claim = make_claim(claim_id="claim_017")
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[claim])
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[make_evidence_item()])
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="claim_017", verdict=ClaimVerdict.SUPPORTED, confidence=0.95, reason="Supported", evidence_ids=["ev_01"], evidence=[]
    ))

    # Mock save_verification to raise an error
    with patch.object(VerificationRepository, "save_verification", side_effect=Exception("Disk full")):
        req = VerificationRequest(request_id="req_017", text="Some text")
        with pytest.raises(DatabaseError) as exc_info:
            await pipeline.verify(req, session=test_db_session)
        assert "Disk full" in exc_info.value.message


# 18. Independent claim failure
@pytest.mark.asyncio
async def test_independent_claim_failure(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    c1 = make_claim(claim_id="c_fail", entity="FailingService", attribute="status", text="Failing claim", category=ClaimCategory.OTHER)
    c2 = make_claim(claim_id="c_success", entity="Stripe", attribute="rate", text="Stripe fee is 2.9%", category=ClaimCategory.PRICING)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["pricing", "other"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[c1, c2])

    # c1 fails Tavily search; c2 succeeds
    async def _mock_retrieve(claim):
        if claim.claim_id == "c_fail":
            raise TavilyAPIError("Network timeout on c_fail")
        return [make_evidence_item("ev_stripe", "Stripe Pricing", "https://stripe.com/pricing")]

    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(side_effect=_mock_retrieve)
    pipeline.verdict_engine.evaluate_claim = AsyncMock(return_value=ClaimVerdictResult(
        claim_id="c_success", verdict=ClaimVerdict.SUPPORTED, confidence=0.94, reason="Verified Stripe", evidence_ids=["ev_stripe"], evidence=[]
    ))

    req = VerificationRequest(request_id="req_018", text="Failing and succeeding claims")
    resp = await pipeline.verify(req, session=test_db_session)

    assert resp.claims_checked == 2
    res_map = {r.claim_id: r for r in resp.results}
    assert res_map["c_fail"].verdict == ClaimVerdict.UNCLEAR
    assert res_map["c_success"].verdict == ClaimVerdict.SUPPORTED
    # One unclear claim means overall verification cannot be marked FRESH
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.UNCERTAIN


# 19. Mixed cached and uncached claims
@pytest.mark.asyncio
async def test_mixed_cached_and_uncached_claims(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    c_cached = make_claim(claim_id="c_cached", entity="Go", attribute="latest_version", text="Go 1.22 released.", category=ClaimCategory.SOFTWARE_VERSION)
    c_uncached = make_claim(claim_id="c_uncached", entity="Rust", attribute="latest_version", text="Rust 1.77 released.", category=ClaimCategory.SOFTWARE_VERSION)

    # Pre-populate c_cached
    prior_resp = VerificationResponse(
        request_id="prior_req",
        verification_id="prior_go",
        status=LifecycleStatus.COMPLETED,
        freshness_status=FreshnessStatus.FRESH,
        requires_refresh=False,
        claims_checked=1,
        results=[
            ClaimVerdictResult(
                claim_id="c_cached",
                verdict=ClaimVerdict.SUPPORTED,
                confidence=0.95,
                reason="Go 1.22 confirmed.",
                evidence_ids=["ev_go"],
                evidence=[EvidenceMinimal(title="Go Release", url="https://go.dev")],
                checked_at=datetime.now(timezone.utc),
            )
        ]
    )
    ev_go = make_evidence_item("ev_go", "Go Release", "https://go.dev")
    await VerificationRepository.save_verification(test_db_session, prior_resp, claims=[c_cached], evidence_map={"c_cached": [ev_go]})
    await test_db_session.commit()

    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["software_version"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[c_cached, c_uncached])

    ev_rust = make_evidence_item("ev_rust", "Rust Release", "https://rust-lang.org")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(return_value=[ev_rust])
    pipeline.version_validator.validate_claim = MagicMock(return_value=ClaimVerdictResult(
        claim_id="c_uncached", verdict=ClaimVerdict.SUPPORTED, confidence=0.95, reason="Rust 1.77 verified.", evidence_ids=["ev_rust"], evidence=[EvidenceMinimal(title="Rust Release", url="https://rust-lang.org")]
    ))

    req = VerificationRequest(request_id="req_019", text="Go 1.22 and Rust 1.77 released.")
    resp = await pipeline.verify(req, session=test_db_session)

    # Tavily should ONLY have been called for c_uncached!
    pipeline.tavily_service.retrieve_evidence_for_claim.assert_called_once()
    called_claim = pipeline.tavily_service.retrieve_evidence_for_claim.call_args[0][0]
    assert called_claim.claim_id == "c_uncached"

    res_map = {r.claim_id: r for r in resp.results}
    assert "[CACHED FACT]" in res_map["c_cached"].reason
    assert res_map["c_uncached"].reason == "Rust 1.77 verified."
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.FRESH


# 20. No incomplete result marked FRESH
@pytest.mark.asyncio
async def test_no_incomplete_result_marked_fresh(test_db_session: AsyncSession):
    pipeline = VerificationPipeline()
    c1 = make_claim(claim_id="c1", entity="Tech", attribute="info", text="Claim 1", category=ClaimCategory.OTHER)
    c2 = make_claim(claim_id="c2", entity="Tech", attribute="info", text="Claim 2", category=ClaimCategory.OTHER)
    pipeline.prefilter.evaluate = MagicMock(return_value=PrefilterResult(requires_verification=True, categories=["other"], confidence=0.9))
    pipeline.extraction_engine.extract_claims = AsyncMock(return_value=[c1, c2])

    ev1 = make_evidence_item("ev1", "Doc 1", "https://example.com/1")
    pipeline.tavily_service.retrieve_evidence_for_claim = AsyncMock(side_effect=[[ev1], []])

    # c1 is SUPPORTED; c2 has empty evidence -> UNCLEAR
    pipeline.verdict_engine.evaluate_claim = AsyncMock(return_value=ClaimVerdictResult(
        claim_id="c1", verdict=ClaimVerdict.SUPPORTED, confidence=0.95, reason="Supported", evidence_ids=["ev1"], evidence=[]
    ))

    req = VerificationRequest(request_id="req_020", text="Claim 1 and Claim 2")
    resp = await pipeline.verify(req, session=test_db_session)

    assert any(r.verdict == ClaimVerdict.UNCLEAR for r in resp.results)
    assert resp.freshness_status != FreshnessStatus.FRESH
    assert resp.freshness_status == FreshnessStatus.UNCERTAIN
    assert resp.status == LifecycleStatus.COMPLETED
