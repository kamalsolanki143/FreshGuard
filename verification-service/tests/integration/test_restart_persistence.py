from datetime import datetime, timezone
import os
from pathlib import Path
import pytest

from app.database.database import get_engine, get_sessionmaker, init_db, _engine, _sessionmaker
import app.database.database as db_module
from app.database.repository import VerificationRepository
from app.schemas.claims import ClaimCategory, ClaimVerdict, ClaimVerdictResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceSourceType
from app.schemas.response import FreshnessStatus, LifecycleStatus, VerificationResponse
from app.services.freshness_policy import FreshnessPolicyEngine


@pytest.mark.asyncio
async def test_verification_persistence_across_backend_restart(tmp_path: Path):
    """
    Verifies that when persistent database storage is configured, verification records,
    claims, and evidence survive a complete backend/database engine restart.
    """
    db_file = tmp_path / "persistent_history.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

    # Phase 1: First backend process lifecycle - Initialize DB and store record
    db_module._engine = None
    db_module._sessionmaker = None
    engine1 = get_engine(db_url)
    await init_db(engine1)
    sm1 = get_sessionmaker(engine1)

    now = datetime.now(timezone.utc)
    req_id = "restart-test-req-001"
    verif_id = "verif_restart_test_999"

    verdict_results = [
        ClaimVerdictResult(
            claim_id="claim_restart_01",
            verdict=ClaimVerdict.SUPPORTED,
            confidence=0.98,
            reason="Verified against official release documentation.",
            evidence_ids=["ev_restart_01"],
            checked_at=now,
        )
    ]

    v_response = VerificationResponse(
        request_id=req_id,
        verification_id=verif_id,
        status=LifecycleStatus.COMPLETED,
        freshness_status=FreshnessStatus.FRESH,
        requires_refresh=False,
        claims_checked=1,
        results=verdict_results,
        claims=verdict_results,
        processing_time_ms=120,
    )

    claims = [
        ExtractedClaim(
            claim_id="claim_restart_01",
            text="Python 3.12 is the latest stable release.",
            category=ClaimCategory.SOFTWARE_VERSION,
            entity="Python",
            attribute="latest_version",
            time_sensitive=True,
        )
    ]

    evidence_map = {
        "claim_restart_01": [
            EvidenceItem(
                evidence_id="ev_restart_01",
                source_title="Python 3.12 Release Notes",
                source_url="https://docs.python.org/3.12/",
                content="Python 3.12.0 is the latest stable version.",
                relevance_score=0.98,
                source_type=EvidenceSourceType.OFFICIAL_DOCS,
            )
        ]
    }

    policy = FreshnessPolicyEngine()

    async with sm1() as session1:
        await VerificationRepository.save_verification(
            session=session1,
            resp=v_response,
            claims=claims,
            evidence_map=evidence_map,
            policy_engine=policy,
        )
        await session1.commit()

    # Phase 2: Complete Backend Shutdown / Process Teardown
    await engine1.dispose()
    db_module._engine = None
    db_module._sessionmaker = None

    # Verify that the DB file actually exists on disk with positive byte size
    assert db_file.exists()
    assert db_file.stat().st_size > 0

    # Phase 3: Second backend process lifecycle - Reconnect from scratch to persistent file
    engine2 = get_engine(db_url)
    sm2 = get_sessionmaker(engine2)

    async with sm2() as session2:
        # 1. Fetch by verification_id
        record = await VerificationRepository.get_verification_by_id(session2, verif_id)
        assert record is not None, "Record must persist across backend restarts"
        assert record.verification_id == verif_id
        assert record.request_id == req_id
        assert record.claims_checked == 1
        assert len(record.claims) == 1

        persisted_claim = record.claims[0]
        assert persisted_claim.claim_id == "claim_restart_01"
        assert persisted_claim.entity == "Python"
        assert len(persisted_claim.evidence) == 1

        persisted_ev = persisted_claim.evidence[0]
        assert persisted_ev.evidence_id == "ev_restart_01"
        assert "docs.python.org" in str(persisted_ev.url)

        # 2. Fetch by request_id (idempotency lookup after restart)
        record_by_req = await VerificationRepository.get_verification_by_request_id(session2, req_id)
        assert record_by_req is not None
        assert record_by_req.verification_id == verif_id

    await engine2.dispose()
    db_module._engine = None
    db_module._sessionmaker = None
