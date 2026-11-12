import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Dict, List, Optional, Set, Tuple, Union
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.database.models import ClaimRecord
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
    ensure_utc_datetime,
)
from app.schemas.request import VerificationRequest
from app.schemas.response import (
    APIErrorDetail,
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
from app.services.version_validator import VersionValidator
from app.utils.exceptions import (
    DatabaseError,
    ExtractionError,
    FreshGuardException,
    TavilyAPIError,
)

logger = logging.getLogger("freshguard.pipeline")


class VerificationPipeline:
    """
    Central verification pipeline orchestrator for FreshGuard.
    Coordinates prefiltering, claim extraction, semantic cache lookup,
    Tavily evidence retrieval, deterministic version validation, LLM verdict judgment,
    freshness policy enforcement, and database persistence.
    """

    def __init__(
        self,
        prefilter: Optional[PrefilterEngine] = None,
        extraction_engine: Optional[ClaimExtractionEngine] = None,
        tavily_service: Optional[TavilyService] = None,
        verdict_engine: Optional[VerdictEngine] = None,
        version_validator: Optional[VersionValidator] = None,
        policy_engine: Optional[FreshnessPolicyEngine] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.prefilter = prefilter or PrefilterEngine()
        self.extraction_engine = extraction_engine or ClaimExtractionEngine()
        self.tavily_service = tavily_service or TavilyService(settings=self.settings)
        self.verdict_engine = verdict_engine or VerdictEngine()
        self.version_validator = version_validator or VersionValidator()
        self.policy_engine = policy_engine or FreshnessPolicyEngine(settings=self.settings)
        self.session_factory = session_factory

    @staticmethod
    def is_version_claim(claim: ExtractedClaim) -> bool:
        """Determines if a claim is a software version assertion suitable for deterministic validation."""
        return (
            claim.category == ClaimCategory.SOFTWARE_VERSION
            or "version" in claim.attribute.lower()
        )

    @staticmethod
    def _freshness_to_lifecycle(
        freshness: Union[FreshnessStatus, VerificationStatus, str],
    ) -> tuple[LifecycleStatus, FreshnessStatus]:
        """
        Maps an internal freshness status to the two-field API contract.

        Returns (lifecycle_status, freshness_status):
        - lifecycle_status: LifecycleStatus.COMPLETED
        - freshness_status: FreshnessStatus enum (FRESH, STALE, UNCERTAIN, NOT_REQUIRED)
        """
        if isinstance(freshness, FreshnessStatus):
            return LifecycleStatus.COMPLETED, freshness
        raw = freshness.value if hasattr(freshness, "value") else str(freshness)
        freshness_val = FreshnessStatus._missing_(raw)
        if freshness_val is None:
            freshness_val = FreshnessStatus.FRESH
        return LifecycleStatus.COMPLETED, freshness_val

    async def verify(
        self,
        request: VerificationRequest,
        session: Optional[AsyncSession] = None,
    ) -> VerificationResponse:
        """
        Executes the full end-to-end verification pipeline.
        Manages scoped database sessions if session_factory is present and session is omitted.
        """
        start_time = time.perf_counter()
        verification_id = f"verif_{request.request_id}_{uuid.uuid4().hex[:8]}"

        # 1. Guard against empty text
        if not request.response_text or not request.response_text.strip():
            logger.debug("Verification skipped for empty text in request %s", request.request_id)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            _lifecycle, _freshness = self._freshness_to_lifecycle(FreshnessStatus.NOT_REQUIRED)
            return VerificationResponse(
                request_id=request.request_id,
                verification_id=verification_id,
                status=_lifecycle,
                freshness_status=_freshness,
                requires_refresh=False,
                claims_checked=0,
                results=[],
                claims=[],
                processing_time_ms=elapsed_ms,
                checked_at=datetime.now(timezone.utc),
            )

        # 2. Run rules-based prefilter
        prefilter_result: PrefilterResult = self.prefilter.evaluate(request.response_text)
        if not prefilter_result.requires_verification:
            logger.info("Prefilter bypassed verification for request %s (signals: %s)", request.request_id, prefilter_result.matched_signals)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            _lifecycle, _freshness = self._freshness_to_lifecycle(FreshnessStatus.NOT_REQUIRED)
            return VerificationResponse(
                request_id=request.request_id,
                verification_id=verification_id,
                status=_lifecycle,
                freshness_status=_freshness,
                requires_refresh=False,
                claims_checked=0,
                results=[],
                claims=[],
                processing_time_ms=elapsed_ms,
                checked_at=datetime.now(timezone.utc),
            )

        # 3. Extract factual claims
        try:
            extracted_claims: List[ExtractedClaim] = await self.extraction_engine.extract_claims(
                request.response_text
            )
        except ExtractionError as e:
            logger.warning("Claim extraction failed for request %s: %s", request.request_id, e.message)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            _lifecycle, _freshness = self._freshness_to_lifecycle(FreshnessStatus.UNCERTAIN)
            return VerificationResponse(
                request_id=request.request_id,
                verification_id=verification_id,
                status=_lifecycle,
                freshness_status=_freshness,
                requires_refresh=False,
                claims_checked=0,
                results=[],
                claims=[],
                processing_time_ms=elapsed_ms,
                checked_at=datetime.now(timezone.utc),
                error=APIErrorDetail(
                    code="EXTRACTION_FAILURE",
                    message=e.message,
                    request_id=request.request_id,
                    retryable=False,
                    details=e.details,
                ),
            )

        # Apply category filter if requested by caller
        if request.categories:
            allowed_cats = {c.strip().lower() for c in request.categories}
            extracted_claims = [
                c for c in extracted_claims
                if c.category.value in allowed_cats or c.category in allowed_cats
            ]

        # 4. Handle zero extracted claims safely
        if not extracted_claims:
            logger.info("No time-sensitive claims extracted from text for request %s", request.request_id)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            _lifecycle, _freshness = self._freshness_to_lifecycle(FreshnessStatus.FRESH)
            resp = VerificationResponse(
                request_id=request.request_id,
                verification_id=verification_id,
                status=_lifecycle,
                freshness_status=_freshness,
                requires_refresh=False,
                claims_checked=0,
                results=[],
                claims=[],
                processing_time_ms=elapsed_ms,
                checked_at=datetime.now(timezone.utc),
            )
            await self._persist_verification(resp, [], {}, session)
            return resp

        # 5. Process claims with session management
        if session is not None:
            return await self._process_claims(
                request=request,
                verification_id=verification_id,
                extracted_claims=extracted_claims,
                session=session,
                start_time=start_time,
            )
        elif self.session_factory is not None:
            async with self.session_factory() as managed_session:
                return await self._process_claims(
                    request=request,
                    verification_id=verification_id,
                    extracted_claims=extracted_claims,
                    session=managed_session,
                    start_time=start_time,
                )
        else:
            return await self._process_claims(
                request=request,
                verification_id=verification_id,
                extracted_claims=extracted_claims,
                session=None,
                start_time=start_time,
            )

    async def _process_claims(
        self,
        request: VerificationRequest,
        verification_id: str,
        extracted_claims: List[ExtractedClaim],
        session: Optional[AsyncSession],
        start_time: float,
    ) -> VerificationResponse:
        """Internal processing pipeline coordinating cache, search, validation, and evaluation."""
        now = datetime.now(timezone.utc)
        resolved_verdicts: Dict[str, ClaimVerdictResult] = {}
        combined_evidence_map: Dict[str, List[EvidenceItem]] = {}
        uncached_claims: List[ExtractedClaim] = []

        # Step A: Cache Lookup for each claim
        for claim in extracted_claims:
            cached_result = None
            if session is not None:
                try:
                    cached_record: Optional[ClaimRecord] = await VerificationRepository.find_fresh_cached_claim(
                        session=session,
                        entity=claim.entity,
                        attribute=claim.attribute,
                        category=claim.category.value,
                        text=claim.text,
                        reference_time=now,
                    )
                    if cached_record and cached_record.is_cached_fact and cached_record.verdict != ClaimVerdict.UNCLEAR.value:
                        cached_result = self._convert_cached_record_to_result(claim, cached_record)
                        # Extract full evidence items from record
                        combined_evidence_map[claim.claim_id] = self._convert_evidence_records(cached_record)
                except Exception as e:
                    logger.warning("Cache lookup error for claim %s: %s", claim.claim_id, e)
                    cached_result = None

            if cached_result is not None:
                logger.info("Reusing fresh cached fact for claim %s (verdict: %s)", claim.claim_id, cached_result.verdict)
                resolved_verdicts[claim.claim_id] = cached_result
            else:
                uncached_claims.append(claim)

        # Step B: Retrieve evidence for uncached claims via Tavily
        retrieval_errors: Dict[str, str] = {}
        if uncached_claims:
            # Deduplicate Tavily search queries for identical claims within the same request
            unique_query_map: Dict[str, List[ExtractedClaim]] = {}
            for claim in uncached_claims:
                fingerprint = generate_claim_fingerprint(
                    claim.entity, claim.attribute, claim.category.value, claim.text
                )
                unique_query_map.setdefault(fingerprint, []).append(claim)

            async def _fetch_for_claim_group(group: List[ExtractedClaim]):
                rep_claim = group[0]
                try:
                    ev_items = await self.tavily_service.retrieve_evidence_for_claim(rep_claim)
                    for c in group:
                        combined_evidence_map[c.claim_id] = ev_items
                except Exception as ex:
                    logger.warning("Tavily retrieval failed for claim %s: %s", rep_claim.claim_id, str(ex))
                    for c in group:
                        combined_evidence_map[c.claim_id] = []
                        retrieval_errors[c.claim_id] = str(ex)

            await asyncio.gather(*[_fetch_for_claim_group(group) for group in unique_query_map.values()])

        # Step C: Evaluate each uncached claim (Version Validator vs Verdict Engine)
        for claim in uncached_claims:
            ev_list = combined_evidence_map.get(claim.claim_id, [])

            # Check if evidence retrieval failed
            if claim.claim_id in retrieval_errors:
                err_msg = retrieval_errors[claim.claim_id]
                resolved_verdicts[claim.claim_id] = ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.UNCLEAR,
                    confidence=0.0,
                    reason=f"Evidence retrieval failed: {err_msg}",
                    evidence_ids=[],
                    evidence=[],
                    checked_at=now,
                )
                continue

            # Check if evidence list is empty
            if not ev_list:
                resolved_verdicts[claim.claim_id] = ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.UNCLEAR,
                    confidence=0.0,
                    reason="No supporting or refuting web evidence was retrieved.",
                    evidence_ids=[],
                    evidence=[],
                    checked_at=now,
                )
                continue

            # Deterministic Version Validation path
            if self.is_version_claim(claim):
                version_result = self.version_validator.validate_claim(claim, ev_list)
                if version_result.verdict in (ClaimVerdict.SUPPORTED, ClaimVerdict.CONTRADICTED):
                    resolved_verdicts[claim.claim_id] = version_result
                    continue
                # If VersionValidator returned UNCLEAR, fall back to LLM verdict engine
                logger.debug(
                    "Deterministic version validation returned UNCLEAR for %s; falling back to VerdictEngine.",
                    claim.claim_id,
                )

            # Standard semantic verdict evaluation
            try:
                verdict_res = await self.verdict_engine.evaluate_claim(claim, ev_list)
                resolved_verdicts[claim.claim_id] = verdict_res
            except Exception as ve_err:
                logger.error("Verdict engine failed for claim %s: %s", claim.claim_id, ve_err, exc_info=True)
                resolved_verdicts[claim.claim_id] = ClaimVerdictResult(
                    claim_id=claim.claim_id,
                    verdict=ClaimVerdict.UNCLEAR,
                    confidence=0.20,
                    reason=f"Verdict evaluation failed due to internal error: {str(ve_err)}",
                    evidence_ids=[e.evidence_id for e in ev_list if e.evidence_id],
                    evidence=[EvidenceMinimal(title=e.title, url=str(e.url)) for e in ev_list[:2]],
                    checked_at=now,
                )

        # Step D: Assemble and order final results, injecting ExtractedClaim metadata
        claim_meta_lookup = {c.claim_id: c for c in extracted_claims}
        final_results: List[ClaimVerdictResult] = []
        for c in extracted_claims:
            if c.claim_id not in resolved_verdicts:
                continue
            verdict_result = resolved_verdicts[c.claim_id]
            meta = claim_meta_lookup.get(c.claim_id)
            if meta is not None:
                # Inject claim metadata fields for schema compliance (copy to avoid mutation)
                enriched = verdict_result.model_copy(update={
                    "category": meta.category.value if meta.category else None,
                    "entity": meta.entity,
                    "attribute": meta.attribute,
                    "original_text": meta.text,
                })
                final_results.append(enriched)
            else:
                final_results.append(verdict_result)

        # Step E: Determine overall response status and refresh flag
        freshness_status, requires_refresh = self._aggregate_overall_status(extracted_claims, final_results)
        lifecycle_status, freshness_str = self._freshness_to_lifecycle(freshness_status)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        response = VerificationResponse(
            request_id=request.request_id,
            verification_id=verification_id,
            status=lifecycle_status,
            freshness_status=freshness_str,
            requires_refresh=requires_refresh,
            claims_checked=len(final_results),
            results=final_results,
            claims=final_results,
            processing_time_ms=elapsed_ms,
            checked_at=now,
        )

        # Step F: Persist to database
        await self._persist_verification(
            resp=response,
            claims=extracted_claims,
            evidence_map=combined_evidence_map,
            session=session,
        )

        return response

    def _aggregate_overall_status(
        self,
        claims: List[ExtractedClaim],
        results: List[ClaimVerdictResult],
    ) -> Tuple[FreshnessStatus, bool]:
        """
        Aggregates claim-level verdicts and category freshness policies into the overall status.
        Safety invariant: Incomplete or unclear verifications can NEVER be labeled FRESH.
        """
        if not results:
            return FreshnessStatus.FRESH, False

        claim_map = {c.claim_id: c for c in claims}

        # 1. Any contradicted claim invalidates freshness -> STALE
        if any(r.verdict == ClaimVerdict.CONTRADICTED for r in results):
            return FreshnessStatus.STALE, True

        # 2. Any unclear / failed claim implies uncertainty -> UNCERTAIN (never FRESH)
        if any(r.verdict == ClaimVerdict.UNCLEAR for r in results):
            return FreshnessStatus.UNCERTAIN, False

        # 3. All claims are SUPPORTED -> Check freshness policy TTLs
        all_fresh = True
        for result in results:
            meta = claim_map.get(result.claim_id)
            cat = meta.category if meta else ClaimCategory.OTHER
            eval_res = self.policy_engine.evaluate_freshness(
                checked_at=result.checked_at,
                category=cat,
                verdict=result.verdict,
            )
            if not eval_res.is_fresh:
                all_fresh = False
                break

        if all_fresh:
            return FreshnessStatus.FRESH, False
        else:
            return FreshnessStatus.STALE, True

    def _convert_cached_record_to_result(
        self,
        claim: ExtractedClaim,
        record: ClaimRecord,
    ) -> ClaimVerdictResult:
        """Converts a persisted ClaimRecord into a ClaimVerdictResult."""
        verdict = ClaimVerdict(record.verdict)
        ev_minimal = [
            EvidenceMinimal(title=ev.title, url=str(ev.url))
            for ev in record.evidence
        ]
        ev_ids = [ev.evidence_id for ev in record.evidence]

        return ClaimVerdictResult(
            claim_id=claim.claim_id,
            verdict=verdict,
            confidence=record.confidence,
            reason=f"[CACHED FACT] {record.reason}",
            evidence_ids=ev_ids,
            evidence=ev_minimal,
            corrected_value=record.corrected_value,
            checked_at=ensure_utc_datetime(record.checked_at),
        )

    def _convert_evidence_records(self, record: ClaimRecord) -> List[EvidenceItem]:
        """Converts EvidenceRecord ORM models to EvidenceItem Pydantic schemas."""
        items: List[EvidenceItem] = []
        for ev in record.evidence:
            source_type = (
                EvidenceSourceType(ev.source_type)
                if ev.source_type in [e.value for e in EvidenceSourceType]
                else EvidenceSourceType.WEBSITE
            )
            items.append(
                EvidenceItem(
                    evidence_id=ev.evidence_id,
                    title=ev.title,
                    url=ev.url,
                    content=ev.content or "",
                    relevance_score=ev.relevance_score,
                    source_type=source_type,
                    retrieved_at=ensure_utc_datetime(ev.retrieved_at) or ensure_utc_datetime(record.checked_at),
                    published_at=ensure_utc_datetime(ev.published_at),
                )
            )
        return items

    async def _persist_verification(
        self,
        resp: VerificationResponse,
        claims: List[ExtractedClaim],
        evidence_map: Dict[str, List[EvidenceItem]],
        session: Optional[AsyncSession],
    ) -> None:
        """
        Persists completed verification records and associated claims/evidence to the database.
        Database failures are rolled back and re-raised as DatabaseError.
        """
        if session is None:
            return

        try:
            await VerificationRepository.save_verification(
                session=session,
                resp=resp,
                claims=claims,
                evidence_map=evidence_map,
                policy_engine=self.policy_engine,
            )
            await session.commit()
            logger.info("Successfully persisted verification %s", resp.verification_id)
        except Exception as err:
            logger.error("Database persistence failed for verification %s: %s", resp.verification_id, err, exc_info=True)
            await session.rollback()
            raise DatabaseError(
                message=f"Failed to persist verification: {str(err)}",
                details={"verification_id": resp.verification_id, "original_error": type(err).__name__},
            )
