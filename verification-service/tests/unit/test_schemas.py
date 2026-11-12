from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas.claims import (
    ClaimCategory,
    ClaimVerdict,
    ClaimVerdictResult,
    ExtractedClaim,
)
from app.schemas.evidence import EvidenceItem, EvidenceMinimal, EvidenceSourceType
from app.schemas.request import VerificationMode, VerificationRequest
from app.schemas.response import (
    APIErrorDetail,
    FreshnessStatus,
    LifecycleStatus,
    VerificationResponse,
    VerificationStatus,
)


# ==============================================================================
# Request Schema Tests
# ==============================================================================

def test_valid_verification_request():
    """Test creating a valid VerificationRequest using standard fields."""
    req = VerificationRequest(
        request_id="req_123",
        response_text="Python 3.12 is the latest stable version.",
        model="gpt-4o",
        source="bifrost",
        mode=VerificationMode.BLOCKING,
    )
    assert req.request_id == "req_123"
    assert req.response_text == "Python 3.12 is the latest stable version."
    assert req.model == "gpt-4o"
    assert req.source == "bifrost"
    assert req.mode == VerificationMode.BLOCKING


def test_verification_request_alias_compatibility():
    """Test that Go client payload with 'text' alias is accepted."""
    req = VerificationRequest(
        request_id="req_456",
        text="Stripe fee is 2.9% + 30c per transaction.",
        categories=["pricing"],
    )
    assert req.request_id == "req_456"
    assert req.response_text == "Stripe fee is 2.9% + 30c per transaction."
    assert req.categories == ["pricing"]


def test_missing_required_request_fields():
    """Test ValidationError when required fields are missing."""
    with pytest.raises(ValidationError):
        VerificationRequest()  # missing both request_id and response_text

    with pytest.raises(ValidationError):
        VerificationRequest(request_id="req_123")  # missing text/response_text


def test_invalid_empty_request_strings():
    """Test that empty strings fail validation for request."""
    with pytest.raises(ValidationError):
        VerificationRequest(request_id="", response_text="Valid text")

    with pytest.raises(ValidationError):
        VerificationRequest(request_id="req_123", response_text="")


# ==============================================================================
# Extracted Claim Tests
# ==============================================================================

def test_valid_extracted_claim():
    """Test valid ExtractedClaim instance."""
    claim = ExtractedClaim(
        claim_id="claim_001",
        text="Python 3.12 is the latest stable release",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
        time_sensitive=True,
    )
    assert claim.claim_id == "claim_001"
    assert claim.entity == "Python"
    assert claim.category == ClaimCategory.SOFTWARE_VERSION
    assert claim.time_sensitive is True


def test_extracted_claim_string_category_normalization():
    """Test that category string is normalized to enum member."""
    claim = ExtractedClaim(
        claim_id="claim_002",
        text="OpenAI CEO is Sam Altman",
        category="leadership",
        entity="OpenAI",
        attribute="ceo",
    )
    assert claim.category == ClaimCategory.LEADERSHIP


def test_invalid_extracted_claim():
    """Test missing entity and empty claim text raise ValidationError."""
    with pytest.raises(ValidationError):
        ExtractedClaim(
            claim_id="claim_003",
            text="",  # Empty text
            entity="Python",
            attribute="version",
        )

    with pytest.raises(ValidationError):
        ExtractedClaim(
            claim_id="claim_003",
            text="Some statement",
            attribute="version",
            # missing entity
        )


# ==============================================================================
# Evidence Schema Tests
# ==============================================================================

def test_valid_evidence_item():
    """Test valid EvidenceItem with URL and timestamps."""
    ev = EvidenceItem(
        evidence_id="ev_001",
        title="Python Releases",
        url="https://www.python.org/downloads/",
        content="Python 3.13.0 is the latest stable release.",
        relevance_score=0.98,
        source_type=EvidenceSourceType.OFFICIAL_DOCS,
    )
    assert ev.evidence_id == "ev_001"
    assert str(ev.url) == "https://www.python.org/downloads/"
    assert ev.relevance_score == 0.98
    assert ev.retrieved_at.tzinfo == timezone.utc


def test_evidence_item_alias_support():
    """Test alias support matching Go contract (source_url, source_title, snippet)."""
    ev = EvidenceItem(
        source_title="Go Release History",
        source_url="https://go.dev/doc/devel/release",
        snippet="Go 1.22 is released.",
    )
    assert ev.title == "Go Release History"
    assert str(ev.url) == "https://go.dev/doc/devel/release"
    assert ev.content == "Go 1.22 is released."


def test_invalid_url_evidence():
    """Test invalid URL fails validation."""
    with pytest.raises(ValidationError):
        EvidenceItem(
            title="Invalid URL Example",
            url="not_a_valid_url",
            content="Content",
        )


def test_evidence_minimal_url_validation():
    """Test EvidenceMinimal URL prefix validation."""
    valid_min = EvidenceMinimal(title="Test", url="https://example.com")
    assert valid_min.url == "https://example.com"

    with pytest.raises(ValidationError):
        EvidenceMinimal(title="Test", url="ftp://example.com")


def test_confidence_and_relevance_boundaries():
    """Test that relevance score must be within [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        EvidenceItem(
            title="Test",
            url="https://example.com",
            relevance_score=1.5,  # Exceeds 1.0
        )

    with pytest.raises(ValidationError):
        EvidenceItem(
            title="Test",
            url="https://example.com",
            relevance_score=-0.1,  # Sub-zero
        )


# ==============================================================================
# Verdict Schema Tests
# ==============================================================================

def test_valid_claim_verdict():
    """Test valid ClaimVerdictResult creation."""
    result = ClaimVerdictResult(
        claim_id="claim_001",
        verdict=ClaimVerdict.SUPPORTED,
        confidence=0.95,
        reason="Official release notes confirm the version.",
        evidence_ids=["ev_001"],
    )
    assert result.verdict == ClaimVerdict.SUPPORTED
    assert result.confidence == 0.95
    assert result.checked_at.tzinfo == timezone.utc


def test_claim_verdict_case_insensitive_parsing():
    """Test case-insensitive verdict normalization (e.g. 'contradicted' -> CONTRADICTED)."""
    result = ClaimVerdictResult(
        claim_id="claim_002",
        verdict="contradicted",
        confidence=0.90,
        reason="Evidence indicates newer release.",
    )
    assert result.verdict == ClaimVerdict.CONTRADICTED


def test_invalid_verdict():
    """Test that invalid verdict values fail validation."""
    with pytest.raises(ValidationError):
        ClaimVerdictResult(
            claim_id="claim_003",
            verdict="INVALID_VERDICT",
            confidence=0.5,
            reason="Unknown verdict",
        )


def test_verdict_confidence_boundaries():
    """Test that confidence score must be strictly between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        ClaimVerdictResult(
            claim_id="claim_004",
            verdict=ClaimVerdict.UNCLEAR,
            confidence=1.1,
            reason="Confidence too high",
        )

    with pytest.raises(ValidationError):
        ClaimVerdictResult(
            claim_id="claim_004",
            verdict=ClaimVerdict.UNCLEAR,
            confidence=-0.05,
            reason="Confidence too low",
        )


# ==============================================================================
# Response Schema & Serialization Tests
# ==============================================================================

def test_valid_verification_response():
    """Test VerificationResponse creation and results/claims syncing."""
    claim_res = ClaimVerdictResult(
        claim_id="claim_001",
        verdict=ClaimVerdict.CONTRADICTED,
        confidence=0.95,
        reason="A newer stable version is available.",
        evidence=[
            EvidenceMinimal(title="Official Python Releases", url="https://www.python.org/downloads/")
        ],
    )

    resp = VerificationResponse(
        request_id="req_001",
        status=LifecycleStatus.COMPLETED,
        freshness_status=FreshnessStatus.STALE,
        requires_refresh=True,
        claims_checked=1,
        results=[claim_res],
        processing_time_ms=1200,
    )

    assert resp.request_id == "req_001"
    assert resp.status == LifecycleStatus.COMPLETED
    assert resp.freshness_status == FreshnessStatus.STALE
    assert resp.requires_refresh is True
    assert resp.claims_checked == 1
    assert len(resp.results) == 1
    assert len(resp.claims) == 1  # Synced for Go compatibility
    assert resp.results[0].verdict == ClaimVerdict.CONTRADICTED


def test_response_json_serialization():
    """Test that model_dump(mode='json') outputs clean JSON types matching Go/TS contracts."""
    resp = VerificationResponse(
        request_id="req_001",
        status=LifecycleStatus.COMPLETED,
        freshness_status=FreshnessStatus.STALE,
        requires_refresh=True,
        claims_checked=1,
        results=[
            ClaimVerdictResult(
                claim_id="claim_001",
                verdict=ClaimVerdict.CONTRADICTED,
                confidence=0.95,
                reason="Python 3.13 is now available.",
                evidence=[
                    EvidenceItem(
                        title="Python Downloads",
                        url="https://www.python.org/downloads/",
                        content="Python 3.13.0 is the latest stable release.",
                    )
                ],
            )
        ],
        processing_time_ms=1200,
    )

    dumped = resp.model_dump(mode="json")
    assert dumped["request_id"] == "req_001"
    assert dumped["status"] == "completed"
    assert dumped["freshness_status"] == "STALE"
    assert dumped["requires_refresh"] is True
    assert dumped["processing_time_ms"] == 1200
    assert isinstance(dumped["results"][0]["evidence"][0]["url"], str)
    assert dumped["results"][0]["evidence"][0]["url"] == "https://www.python.org/downloads/"
    assert dumped["results"][0]["evidence"][0]["source_url"] == "https://www.python.org/downloads/"
    assert dumped["results"][0]["evidence"][0]["source_title"] == "Python Downloads"
    assert dumped["results"][0]["evidence"][0]["snippet"] == "Python 3.13.0 is the latest stable release."
    assert "checked_at" in dumped


def test_timezone_aware_datetime_handling():
    """Test that naive datetimes are automatically assigned UTC timezone."""
    naive_dt = datetime(2026, 11, 8, 12, 0, 0)
    ev = EvidenceItem(
        title="Title",
        url="https://example.com",
        retrieved_at=naive_dt,
    )
    assert ev.retrieved_at.tzinfo == timezone.utc
    assert ev.retrieved_at.hour == 12


def test_api_error_detail_schema():
    """Test APIErrorDetail schema matching shared contract."""
    err = APIErrorDetail(
        code="RATE_LIMIT_EXCEEDED",
        message="Upstream search API rate limit exceeded.",
        request_id="req_999",
        retryable=True,
        details={"retry_after_seconds": 5},
    )
    assert err.code == "RATE_LIMIT_EXCEEDED"
    assert err.retryable is True
    assert err.details["retry_after_seconds"] == 5
