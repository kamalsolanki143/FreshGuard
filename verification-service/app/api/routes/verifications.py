from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_pipeline, require_api_key
from app.database.database import get_db_session
from app.database.models import VerificationRecord
from app.database.repository import VerificationRepository
from app.schemas.claims import ClaimVerdict, ClaimVerdictResult
from app.schemas.evidence import EvidenceItem, ensure_utc_datetime
from app.schemas.request import VerificationMode, VerificationRequest
from app.schemas.response import (
    FreshnessStatus,
    LifecycleStatus,
    VerificationResponse,
    VerificationStatus,
)
from app.services.verification_pipeline import VerificationPipeline
from app.utils.exceptions import FreshGuardException, NotFoundError

logger = logging.getLogger("freshguard.api.verifications")

# require_api_key is applied at the router level so that every current and
# future endpoint in this router is automatically protected.
# Health routes (/health, /health/ready) live in a separate router and are
# intentionally excluded from this dependency.
router = APIRouter(
    prefix="/v1/verifications",
    tags=["verifications"],
    dependencies=[Depends(require_api_key)],
)


def record_to_response(record: VerificationRecord) -> VerificationResponse:
    """Converts a persisted VerificationRecord ORM instance into a VerificationResponse.

    Populates claim metadata fields (category, entity, attribute, original_text) from
    ClaimRecord so that GET responses are schema-compliant with the Go client Claim type.
    Separates lifecycle status ("completed") from freshness status (e.g. "FRESH").
    """
    results: List[ClaimVerdictResult] = []
    for c in record.claims:
        ev_items = [
            EvidenceItem(
                evidence_id=ev.evidence_id,
                title=ev.title,
                url=ev.url,
                content=ev.content,
                relevance_score=ev.relevance_score,
                source_type=ev.source_type,
                retrieved_at=ensure_utc_datetime(ev.retrieved_at),
                published_at=ensure_utc_datetime(ev.published_at),
            )
            for ev in c.evidence
        ]
        ev_ids = [ev.evidence_id for ev in c.evidence]
        results.append(
            ClaimVerdictResult(
                claim_id=c.claim_id,
                verdict=ClaimVerdict(c.verdict),
                confidence=c.confidence,
                reason=c.reason,
                evidence_ids=ev_ids,
                evidence=ev_items,
                corrected_value=c.corrected_value,
                checked_at=ensure_utc_datetime(c.checked_at),
                # Claim metadata for shared schema compliance
                category=c.category,
                entity=c.entity,
                attribute=c.attribute,
                original_text=c.original_text,
            )
        )

    # Determine freshness_status and lifecycle status from stored value.
    _freshness_values = {"FRESH", "STALE", "UNCERTAIN", "NOT_REQUIRED"}
    _lifecycle_values = {"accepted", "completed", "failed"}

    stored_status = record.status or "completed"
    if stored_status in _freshness_values:
        freshness_status = FreshnessStatus(stored_status)
        lifecycle_status = LifecycleStatus.COMPLETED
    elif stored_status in _lifecycle_values:
        lifecycle_status = LifecycleStatus(stored_status)
        freshness_raw = getattr(record, "freshness_status", None)
        freshness_status = FreshnessStatus(freshness_raw) if freshness_raw in _freshness_values else None
    else:
        lifecycle_status = LifecycleStatus.COMPLETED
        freshness_status = None

    return VerificationResponse(
        request_id=record.request_id,
        verification_id=record.verification_id,
        status=lifecycle_status,
        freshness_status=freshness_status,
        requires_refresh=record.requires_refresh,
        claims_checked=record.claims_checked,
        results=results,
        claims=results,
        processing_time_ms=record.processing_time_ms,
        checked_at=ensure_utc_datetime(record.checked_at),
    )


@router.post(
    "",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit LLM response text for freshness and factual verification",
)
@router.post(
    "/",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def create_verification(
    request: VerificationRequest,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    pipeline: VerificationPipeline = Depends(get_pipeline),
    session: AsyncSession = Depends(get_db_session),
) -> VerificationResponse:
    """
    Evaluates response text against factual claims, real-time web evidence,
    and category-specific freshness policies.
    Provides idempotent deduplication when the same request_id is resubmitted.

    Execution mode note:
    Verifications execute synchronously in blocking mode. Asynchronous 202 Accepted
    background task delegation requires a durable background worker queue and is not
    yet implemented; mode="async" executes synchronously and returns HTTP 200 with
    completed lifecycle status.
    """
    if x_request_id and not request.request_id:
        request.request_id = x_request_id

    # Check for idempotency: existing verification for identical request_id
    existing_record = await VerificationRepository.get_verification_by_request_id(session, request.request_id)
    if existing_record is not None:
        logger.info("Idempotent hit: returning existing verification %s for request_id %s", existing_record.verification_id, request.request_id)
        return record_to_response(existing_record)

    try:
        logger.info("Starting verification for request %s (mode: %s)", request.request_id, request.mode)
        response = await pipeline.verify(request, session=session)
        return response
    except FreshGuardException:
        raise
    except Exception as exc:
        logger.error("Internal error during verification %s: %s", request.request_id, exc, exc_info=True)
        raise FreshGuardException(
            message="An internal server error occurred during verification.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            details={},
        )



@router.get(
    "/{verification_id}",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a stored verification result by its unique verification ID",
)
async def get_verification(
    verification_id: str,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    session: AsyncSession = Depends(get_db_session),
) -> VerificationResponse:
    """
    Retrieves a historical verification record by verification ID.
    Returns HTTP 404 with standard APIError envelope if not found.
    """
    record = await VerificationRepository.get_verification_by_id(session, verification_id)
    if not record:
        logger.warning("Verification with ID '%s' not found (request_id=%s)", verification_id, x_request_id)
        raise NotFoundError(
            message=f"Verification with ID '{verification_id}' was not found.",
            details={"verification_id": verification_id, "request_id": x_request_id},
        )

    return record_to_response(record)
