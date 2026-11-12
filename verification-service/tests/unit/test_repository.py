from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base
from app.database.repository import VerificationRepository, generate_claim_fingerprint
from app.schemas.claims import ClaimCategory, ClaimVerdict, ClaimVerdictResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceMinimal, EvidenceSourceType
from app.schemas.response import (
    FreshnessStatus,
    LifecycleStatus,
    VerificationResponse,
    VerificationStatus,
)
from app.services.freshness_policy import FreshnessPolicyEngine


@pytest_asyncio.fixture
async def test_db_session():
    """Provides an isolated in-memory SQLite database session for unit testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
def sample_verification():
    claim_meta = ExtractedClaim(
        claim_id="claim_001",
        text="Python 3.12 is the latest stable version.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
    )
    verdict_res = ClaimVerdictResult(
        claim_id="claim_001",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.96,
        reason="Official release notes confirm 3.12.",
        evidence_ids=["ev_01"],
        evidence=[EvidenceMinimal(title="Python Releases", url="https://python.org")],
    )
    resp = VerificationResponse(
        request_id="req_100",
        verification_id="verif_100",
        status=LifecycleStatus.COMPLETED,
        freshness_status=FreshnessStatus.FRESH,
        requires_refresh=False,
        claims_checked=1,
        results=[verdict_res],
        processing_time_ms=150,
    )
    ev_item = EvidenceItem(
        evidence_id="ev_01",
        title="Python Releases",
        url="https://python.org",
        content="Python 3.12 is the latest stable version.",
        relevance_score=0.98,
        source_type=EvidenceSourceType.OFFICIAL_DOCS,
    )
    return resp, [claim_meta], {"claim_001": [ev_item]}


@pytest.mark.asyncio
async def test_save_and_retrieve_verification(test_db_session: AsyncSession, sample_verification):
    """Test persisting a verification session and retrieving it by verification_id."""
    resp, claims, ev_map = sample_verification

    saved = await VerificationRepository.save_verification(
        test_db_session,
        resp,
        claims=claims,
        evidence_map=ev_map,
    )
    await test_db_session.commit()

    assert saved.verification_id == "verif_100"
    assert saved.request_id == "req_100"

    retrieved = await VerificationRepository.get_verification_by_id(test_db_session, "verif_100")
    assert retrieved is not None
    assert retrieved.verification_id == "verif_100"
    assert retrieved.status == "completed"
    assert retrieved.freshness_status == "FRESH"
    assert len(retrieved.claims) == 1
    assert retrieved.claims[0].claim_id == "claim_001"
    assert retrieved.claims[0].verdict == ClaimVerdict.SUPPORTED.value
    assert len(retrieved.claims[0].evidence) == 1
    assert "python.org" in retrieved.claims[0].evidence[0].url


@pytest.mark.asyncio
async def test_claim_fingerprint_generation():
    """Test deterministic fingerprint generation and normalization."""
    fp1 = generate_claim_fingerprint("Python", "latest_version", "software_version", "Python 3.12 is latest")
    fp2 = generate_claim_fingerprint("  python  ", "latestversion", "software_version", "python 3.12 is   latest")
    assert fp1 == fp2  # Normalized equivalence


@pytest.mark.asyncio
async def test_find_fresh_cached_claim_hit(test_db_session: AsyncSession, sample_verification):
    """Test looking up an existing verified claim while still within its fresh window."""
    resp, claims, ev_map = sample_verification
    await VerificationRepository.save_verification(test_db_session, resp, claims=claims, evidence_map=ev_map)
    await test_db_session.commit()

    # Search for matching claim
    cached = await VerificationRepository.find_fresh_cached_claim(
        test_db_session,
        entity="Python",
        attribute="latest_version",
        category="software_version",
        text="Python 3.12 is the latest stable version.",
    )

    assert cached is not None
    assert cached.claim_id == "claim_001"
    assert cached.verdict == ClaimVerdict.SUPPORTED.value
    assert cached.is_cached_fact is True
    assert len(cached.evidence) == 1


@pytest.mark.asyncio
async def test_cache_miss_after_expiration(test_db_session: AsyncSession, sample_verification):
    """Test that an expired verification is excluded from cache lookup."""
    resp, claims, ev_map = sample_verification
    await VerificationRepository.save_verification(test_db_session, resp, claims=claims, evidence_map=ev_map)
    await test_db_session.commit()

    # Query with a reference time in the future beyond the 24h TTL (e.g. 26 hours later)
    future_time = datetime.now(timezone.utc) + timedelta(hours=26)
    cached = await VerificationRepository.find_fresh_cached_claim(
        test_db_session,
        entity="Python",
        attribute="latest_version",
        category="software_version",
        text="Python 3.12 is the latest stable version.",
        reference_time=future_time,
    )

    assert cached is None  # Cache miss due to expiration


@pytest.mark.asyncio
async def test_inconclusive_claims_not_cached_as_facts(test_db_session: AsyncSession):
    """Test that UNCLEAR claims are marked is_cached_fact=False and not reused."""
    claim_meta = ExtractedClaim(claim_id="c_unclear", text="Unclear claim", category=ClaimCategory.OTHER, entity="E", attribute="a")
    verdict_res = ClaimVerdictResult(claim_id="c_unclear", verdict=ClaimVerdict.UNCLEAR, confidence=0.3, reason="Insufficient evidence")
    resp = VerificationResponse(
        request_id="req_unc",
        verification_id="verif_unc",
        status=VerificationStatus.UNCERTAIN,
        requires_refresh=True,
        claims_checked=1,
        results=[verdict_res],
    )

    await VerificationRepository.save_verification(test_db_session, resp, claims=[claim_meta])
    await test_db_session.commit()

    cached = await VerificationRepository.find_fresh_cached_claim(test_db_session, "E", "a", "other", "Unclear claim")
    assert cached is None


@pytest.mark.asyncio
async def test_missing_verification_returns_none(test_db_session: AsyncSession):
    """Test querying non-existent verification ID returns None cleanly."""
    result = await VerificationRepository.get_verification_by_id(test_db_session, "non_existent_id")
    assert result is None


@pytest.mark.asyncio
async def test_save_and_retrieve_freshness_policies(test_db_session: AsyncSession):
    """Test creating, updating, and querying persistent freshness policies."""
    # Create policy
    policy = await VerificationRepository.save_or_update_policy(
        test_db_session,
        category="pricing",
        ttl_seconds=1800,  # 30 mins
        description="Dynamic pricing TTL",
    )
    await test_db_session.commit()
    assert policy.category == "pricing"
    assert policy.ttl_seconds == 1800

    # Query policy
    fetched = await VerificationRepository.get_policy(test_db_session, "pricing")
    assert fetched is not None
    assert fetched.ttl_seconds == 1800

    # Update policy
    updated = await VerificationRepository.save_or_update_policy(
        test_db_session,
        category="pricing",
        ttl_seconds=3600,
    )
    await test_db_session.commit()
    assert updated.ttl_seconds == 3600

    # List policies
    policies = await VerificationRepository.list_policies(test_db_session)
    assert len(policies) == 1
    assert policies[0].category == "pricing"


@pytest.mark.asyncio
async def test_transaction_rollback(test_db_session: AsyncSession, sample_verification):
    """Test that uncommitted or rolled back transactions do not persist records."""
    resp, claims, _ = sample_verification
    await VerificationRepository.save_verification(test_db_session, resp, claims=claims)
    await test_db_session.rollback()

    retrieved = await VerificationRepository.get_verification_by_id(test_db_session, "verif_100")
    assert retrieved is None
