from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer, model_validator
from app.schemas.claims import ClaimVerdictResult
from app.schemas.evidence import ensure_utc_datetime


class LifecycleStatus(str, Enum):
    """Lifecycle state of a verification job matching the external API contract."""
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def _missing_(cls, value: object):
        """Allow case-insensitive lookup."""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None


class FreshnessStatus(str, Enum):
    """Semantic freshness state of verified factual information."""
    FRESH = "FRESH"
    STALE = "STALE"
    UNCERTAIN = "UNCERTAIN"
    NOT_REQUIRED = "NOT_REQUIRED"

    @classmethod
    def _missing_(cls, value: object):
        """Allow case-insensitive lookup."""
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper():
                    return member
        return None


class VerificationStatus(str, Enum):
    """Unified verification status enum maintained for backwards compatibility."""
    # Semantic Freshness Statuses
    FRESH = "FRESH"
    STALE = "STALE"
    UNCERTAIN = "UNCERTAIN"
    NOT_REQUIRED = "NOT_REQUIRED"

    # Gateway Lifecycle Statuses (Go contract compatibility)
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def _missing_(cls, value: object):
        """Allow case-insensitive lookup."""
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper() or member.value.lower() == value.lower():
                    return member
        return None


class APIErrorDetail(BaseModel):
    """Cross-service machine-readable error payload matching shared contracts."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable description of the error")
    request_id: str = Field(..., description="Correlation ID for the failed request")
    retryable: bool = Field(default=False, description="Whether caller may safely retry")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured debug context")


class VerificationResponse(BaseModel):
    """
    Standard verification response payload.

    Two-field status contract (matches Go client and shared/schemas/verification_api.json):
    - ``status``:           Lifecycle status — "completed", "accepted", or "failed".
    - ``freshness_status``: Freshness verdict — "FRESH", "STALE", "UNCERTAIN", or "NOT_REQUIRED".

    Compatible with Go Bifrost gateway adapter, Next.js frontend, and evaluation harnesses.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    request_id: str = Field(..., min_length=1, max_length=128, description="Correlation identifier matching request")
    verification_id: Optional[str] = Field(default=None, description="Unique verification job identifier")
    status: LifecycleStatus = Field(..., description="Lifecycle status: completed, accepted, or failed")
    freshness_status: Optional[FreshnessStatus] = Field(
        default=None,
        description="Freshness verdict: FRESH, STALE, UNCERTAIN, or NOT_REQUIRED",
    )
    requires_refresh: bool = Field(..., description="Whether cached response should be invalidated/refreshed")
    claims_checked: int = Field(default=0, ge=0, description="Count of time-sensitive claims evaluated")
    results: List[ClaimVerdictResult] = Field(default_factory=list, description="Detailed verification results per claim")
    claims: Optional[List[ClaimVerdictResult]] = Field(
        default=None,
        description="Alias for results matching shared/schemas/verification_api.json",
    )
    processing_time_ms: int = Field(default=0, ge=0, description="Verification latency in milliseconds")
    checked_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of completion in UTC",
    )
    result_url: Optional[str] = Field(default=None, description="Result retrieval URL for async workflows")
    error: Optional[APIErrorDetail] = Field(default=None, description="Error detail if status is failed")

    @field_validator("checked_at", mode="after")
    @classmethod
    def validate_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc_datetime(v)

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v: Any) -> LifecycleStatus:
        if isinstance(v, LifecycleStatus):
            return v
        if isinstance(v, str):
            res = LifecycleStatus._missing_(v)
            if res is not None:
                return res
            # Backwards compatibility: if a freshness status was passed to status, map to COMPLETED
            freshness_match = FreshnessStatus._missing_(v)
            if freshness_match is not None:
                return LifecycleStatus.COMPLETED
        if hasattr(v, "value"):
            return cls.parse_status(v.value)
        raise ValueError(f"Invalid status: {v}. Must be a valid LifecycleStatus enum value.")

    @field_validator("freshness_status", mode="before")
    @classmethod
    def parse_freshness(cls, v: Any) -> Optional[FreshnessStatus]:
        if v is None:
            return None
        if isinstance(v, FreshnessStatus):
            return v
        if isinstance(v, str):
            res = FreshnessStatus._missing_(v)
            if res is not None:
                return res
        if hasattr(v, "value"):
            return cls.parse_freshness(v.value)
        raise ValueError(f"Invalid freshness status: {v}. Must be FRESH, STALE, UNCERTAIN, or NOT_REQUIRED.")

    @model_validator(mode="before")
    @classmethod
    def reconcile_status_and_freshness(cls, data: Any) -> Any:
        """If legacy code passed a freshness value to status without freshness_status, populate both."""
        if isinstance(data, dict):
            status_val = data.get("status")
            freshness_val = data.get("freshness_status")
            if status_val is not None and freshness_val is None:
                raw_str = status_val.value if hasattr(status_val, "value") else str(status_val)
                freshness_match = FreshnessStatus._missing_(raw_str)
                if freshness_match is not None:
                    data["freshness_status"] = freshness_match
                    data["status"] = LifecycleStatus.COMPLETED
        return data

    @model_validator(mode="after")
    def sync_claims_and_results(self) -> "VerificationResponse":
        """Ensures results and claims mirror each other for full Go/TS compatibility."""
        if not self.claims and self.results:
            self.claims = self.results
        elif not self.results and self.claims:
            self.results = self.claims
            self.claims_checked = len(self.claims)
        return self

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        data = handler(self)
        if data.get("error") is None and "error" in data:
            del data["error"]
        return data
