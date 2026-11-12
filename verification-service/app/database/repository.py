from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    ClaimRecord,
    EvidenceRecord,
    FreshnessPolicyRecord,
    VerificationRecord,
)
from app.schemas.claims import ClaimCategory, ClaimVerdict, ClaimVerdictResult, ExtractedClaim
from app.schemas.evidence import EvidenceItem, ensure_utc_datetime
from app.schemas.response import (
    FreshnessStatus,
    LifecycleStatus,
    VerificationResponse,
    VerificationStatus,
)
from app.utils.exceptions import DatabaseError

if TYPE_CHECKING:
    from app.services.freshness_policy import FreshnessPolicyEngine

logger = logging.getLogger("freshguard.repository")


def generate_claim_fingerprint(entity: str, attribute: str, category: str, text: str) -> str:
    """
    Computes a deterministic, normalized SHA-256 fingerprint for a claim.
    Combines entity, attribute, category, and canonical core keywords to prevent false cache collisions.
    """
    clean_entity = entity.strip().lower()
    clean_attr = attribute.strip().lower().replace("_", "")
    clean_cat = category.strip().lower()
    clean_text = " ".join(text.strip().lower().split())

    raw_key = f"{clean_entity}|{clean_attr}|{clean_cat}|{clean_text}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class VerificationRepository:
    """
    Asynchronous persistence and cache lookup repository.
    """

    @staticmethod
    async def save_verification(
        session: AsyncSession,
        resp: VerificationResponse,
        claims: Optional[List[ExtractedClaim]] = None,
        evidence_map: Optional[Dict[str, List[EvidenceItem]]] = None,
        policy_engine: Optional[FreshnessPolicyEngine] = None,
    ) -> VerificationRecord:
        """
        Persists a completed verification session, associated claims, and grounded evidence.
        """
        now = datetime.now(timezone.utc)
        if policy_engine is not None:
            engine = policy_engine
        else:
            from app.services.freshness_policy import FreshnessPolicyEngine
            engine = FreshnessPolicyEngine()
        verif_id = resp.verification_id or f"verif_{resp.request_id}_{int(now.timestamp())}"

        # Determine lifecycle and freshness statuses
        lifecycle_str = resp.status.value if hasattr(resp.status, "value") else str(resp.status)
        freshness_str = (
            resp.freshness_status.value
            if hasattr(resp.freshness_status, "value")
            else (str(resp.freshness_status) if resp.freshness_status is not None else None)
        )
        if lifecycle_str in ("FRESH", "STALE", "UNCERTAIN", "NOT_REQUIRED"):
            if not freshness_str:
                freshness_str = lifecycle_str
            lifecycle_str = "completed"

        # 1. Create top-level verification record
        verif_record = VerificationRecord(
            verification_id=verif_id,
            request_id=resp.request_id,
            status=lifecycle_str,
            freshness_status=freshness_str,
            requires_refresh=resp.requires_refresh,
            claims_checked=resp.claims_checked,
            processing_time_ms=resp.processing_time_ms,
            checked_at=ensure_utc_datetime(resp.checked_at) or now,
            created_at=now,
        )
        session.add(verif_record)

        # Map claims by claim_id for structured access
        claim_meta_map: Dict[str, ExtractedClaim] = {c.claim_id: c for c in (claims or [])}
        ev_map = evidence_map or {}

        # 2. Persist claims and attached evidence
        for result in resp.results:
            meta = claim_meta_map.get(result.claim_id)
            entity = meta.entity if meta else "unknown"
            attribute = meta.attribute if meta else "unknown"
            category_str = meta.category.value if meta else "other"
            original_text = meta.text if meta else result.reason

            # Calculate deterministic fingerprint and policy expiration
            fingerprint = generate_claim_fingerprint(entity, attribute, category_str, original_text)
            checked_time = ensure_utc_datetime(result.checked_at) or now
            expires_time = engine.calculate_expiration(checked_time, category_str)

            # Safety rule: Inconclusive or failed verifications are not cached as reusable facts
            is_cacheable = (
                result.verdict in (ClaimVerdict.SUPPORTED, ClaimVerdict.CONTRADICTED)
                and lifecycle_str not in ("failed", "FAILED")
                and len(result.evidence) > 0
            )

            claim_record = ClaimRecord(
                verification_id=verif_id,
                claim_id=result.claim_id,
                claim_fingerprint=fingerprint,
                category=category_str,
                entity=entity,
                attribute=attribute,
                original_text=original_text,
                verdict=result.verdict.value,
                confidence=result.confidence,
                reason=result.reason,
                corrected_value=result.corrected_value,
                checked_at=checked_time,
                expires_at=expires_time,
                is_cached_fact=is_cacheable,
            )
            session.add(claim_record)
            await session.flush()  # Populates claim_record.id for foreign key

            # Persist full evidence records if provided in evidence_map
            raw_evidence = ev_map.get(result.claim_id, [])
            for ev in raw_evidence:
                ev_record = EvidenceRecord(
                    claim_db_id=claim_record.id,
                    evidence_id=ev.evidence_id or f"ev_{claim_record.id}_{int(now.timestamp())}",
                    title=ev.title,
                    url=str(ev.url),
                    content=ev.content or "",
                    relevance_score=ev.relevance_score,
                    source_type=ev.source_type.value,
                    retrieved_at=ensure_utc_datetime(ev.retrieved_at) or now,
                    published_at=ensure_utc_datetime(ev.published_at),
                )
                session.add(ev_record)

        await session.flush()
        logger.info("Persisted verification %s with %d claims.", verif_id, len(resp.results))
        return verif_record

    @staticmethod
    async def get_verification_by_id(
        session: AsyncSession,
        verification_id: str,
    ) -> Optional[VerificationRecord]:
        """Retrieves a verification record along with its claims and evidence."""
        stmt = (
            select(VerificationRecord)
            .where(VerificationRecord.verification_id == verification_id)
            .options(
                selectinload(VerificationRecord.claims).selectinload(ClaimRecord.evidence)
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_verification_by_request_id(
        session: AsyncSession,
        request_id: str,
    ) -> Optional[VerificationRecord]:
        """Retrieves the latest verification record matching request_id for idempotency."""
        stmt = (
            select(VerificationRecord)
            .where(VerificationRecord.request_id == request_id)
            .options(
                selectinload(VerificationRecord.claims).selectinload(ClaimRecord.evidence)
            )
            .order_by(desc(VerificationRecord.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_fresh_cached_claim(
        session: AsyncSession,
        entity: str,
        attribute: str,
        category: str,
        text: str,
        reference_time: Optional[datetime] = None,
    ) -> Optional[ClaimRecord]:
        """
        Finds an unexpired, verified claim matching the normalized fingerprint.
        Enforces that the record is marked cacheable and is strictly within its TTL window.
        """
        now = ensure_utc_datetime(reference_time) or datetime.now(timezone.utc)
        fingerprint = generate_claim_fingerprint(entity, attribute, category, text)

        stmt = (
            select(ClaimRecord)
            .where(
                ClaimRecord.claim_fingerprint == fingerprint,
                ClaimRecord.is_cached_fact.is_(True),
                ClaimRecord.expires_at > now,
            )
            .options(selectinload(ClaimRecord.evidence))
            .order_by(desc(ClaimRecord.checked_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            exp_utc = ensure_utc_datetime(record.expires_at)
            secs_left = int((exp_utc - now).total_seconds()) if exp_utc else 0
            logger.info("Cache hit for claim fingerprint: %s (expires in %ds)", fingerprint, secs_left)
        return record

    @staticmethod
    async def list_verification_history(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[VerificationRecord]:
        """Lists historical verification records ordered by creation date descending."""
        stmt = (
            select(VerificationRecord)
            .options(selectinload(VerificationRecord.claims))
            .order_by(desc(VerificationRecord.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def save_or_update_policy(
        session: AsyncSession,
        category: str,
        ttl_seconds: int,
        description: Optional[str] = None,
    ) -> FreshnessPolicyRecord:
        """Creates or updates a persistent category freshness policy."""
        now = datetime.now(timezone.utc)
        stmt = select(FreshnessPolicyRecord).where(FreshnessPolicyRecord.category == category)
        result = await session.execute(stmt)
        policy = result.scalar_one_or_none()

        if policy:
            policy.ttl_seconds = ttl_seconds
            policy.description = description or policy.description
            policy.updated_at = now
        else:
            policy = FreshnessPolicyRecord(
                category=category,
                ttl_seconds=ttl_seconds,
                description=description,
                updated_at=now,
            )
            session.add(policy)

        await session.flush()
        return policy

    @staticmethod
    async def get_policy(
        session: AsyncSession,
        category: str,
    ) -> Optional[FreshnessPolicyRecord]:
        """Retrieves persistent policy record by category."""
        stmt = select(FreshnessPolicyRecord).where(FreshnessPolicyRecord.category == category)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_policies(
        session: AsyncSession,
    ) -> List[FreshnessPolicyRecord]:
        """Lists all persisted policy records."""
        stmt = select(FreshnessPolicyRecord).order_by(FreshnessPolicyRecord.category)
        result = await session.execute(stmt)
        return list(result.scalars().all())
