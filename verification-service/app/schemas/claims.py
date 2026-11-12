from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer
from app.schemas.evidence import EvidenceItem, EvidenceMinimal, ensure_utc_datetime


class ClaimCategory(str, Enum):
    """Categories of claims verified by FreshGuard."""
    SOFTWARE_VERSION = "software_version"
    PRICING = "pricing"
    LEADERSHIP = "leadership"
    PRODUCT_AVAILABILITY = "product_availability"
    RECENT_EVENTS = "recent_events"
    TECHNOLOGY_RELEASES = "technology_releases"
    CURRENT_STATISTICS = "current_statistics"
    GENERAL_KNOWLEDGE = "general_knowledge"
    OTHER = "other"


class ClaimVerdict(str, Enum):
    """Verification verdict for an individual factual claim.

    Values are lowercase to match the Go client constants (VerdictSupported, VerdictContradicted,
    VerdictUnclear) and the shared/schemas/verification_api.json enum definition.
    """
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNCLEAR = "unclear"

    @classmethod
    def _missing_(cls, value: object):
        """Allow case-insensitive resolution (e.g. 'SUPPORTED' -> SUPPORTED)."""
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper():
                    return member
        return None


class ExtractedClaim(BaseModel):
    """Represents a discrete, structured factual claim extracted from an LLM response."""
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    claim_id: str = Field(..., min_length=1, max_length=128, description="Deterministic identifier for the claim")
    text: str = Field(..., min_length=1, max_length=2000, alias="original_text", description="Verbatim or summarized statement")
    category: ClaimCategory = Field(default=ClaimCategory.OTHER, description="Category classification")
    entity: str = Field(..., min_length=1, max_length=256, description="Subject entity (e.g., Python, Stripe, OpenAI)")
    attribute: str = Field(..., min_length=1, max_length=256, description="Attribute of subject (e.g., latest_version, pro_price, ceo)")
    time_sensitive: bool = Field(default=True, description="Whether this claim is subject to change over time")

    @field_validator("category", mode="before")
    @classmethod
    def parse_category(cls, v: Union[str, ClaimCategory]) -> ClaimCategory:
        if isinstance(v, ClaimCategory):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower().replace(" ", "_").replace("-", "_")
            for member in ClaimCategory:
                if member.value == normalized:
                    return member
        return ClaimCategory.OTHER


class ClaimExtractionRequest(BaseModel):
    """Input payload to trigger structured claim extraction."""
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    text: str = Field(..., min_length=1, max_length=50000, alias="response_text", description="LLM text to extract claims from")


class ClaimExtractionResponse(BaseModel):
    """Output payload from structured claim extraction."""
    model_config = ConfigDict(populate_by_name=True)

    claims: List[ExtractedClaim] = Field(default_factory=list, description="List of extracted factual claims")


class ClaimVerdictResult(BaseModel):
    """Verification judgment on an individual extracted claim.

    Includes optional ExtractedClaim metadata fields (category, entity, attribute, original_text)
    to satisfy the shared/schemas/verification_api.json Claim object requirements when serialized.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    claim_id: str = Field(..., min_length=1, max_length=128, description="Identifier of the claim verified")
    verdict: ClaimVerdict = Field(..., description="Verdict outcome: supported, contradicted, or unclear")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score calibrated between 0.0 and 1.0")
    reason: str = Field(..., min_length=1, max_length=2000, description="Justification grounded strictly in evidence")
    evidence_ids: List[str] = Field(default_factory=list, description="List of evidence IDs grounding this verdict")
    evidence: List[Union[EvidenceItem, EvidenceMinimal]] = Field(default_factory=list, description="Evidence items attached to this claim")
    corrected_value: Optional[str] = Field(default=None, description="Correct value if claim was contradicted")
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Verification check timestamp in UTC",
    )
    # Claim metadata — populated at the API boundary from ExtractedClaim.
    # Optional for backward compatibility with internal pipeline code.
    category: Optional[str] = Field(default=None, description="Claim category (e.g. software_version, pricing)")
    entity: Optional[str] = Field(default=None, description="Subject entity of the claim")
    attribute: Optional[str] = Field(default=None, description="Attribute of the subject entity")
    original_text: Optional[str] = Field(default=None, alias="text", description="Verbatim claim text from the LLM response")

    @field_validator("checked_at", mode="after")
    @classmethod
    def validate_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc_datetime(v)

    @field_validator("verdict", mode="before")
    @classmethod
    def parse_verdict(cls, v: Union[str, ClaimVerdict]) -> ClaimVerdict:
        if isinstance(v, ClaimVerdict):
            return v
        if isinstance(v, str):
            res = ClaimVerdict._missing_(v)
            if res is not None:
                return res
        raise ValueError(f"Invalid verdict: {v}. Must be supported, contradicted, or unclear.")

    @model_serializer(mode="wrap")
    def _serialize_verdict_result(self, handler):
        d = handler(self)
        if isinstance(d, dict):
            # Ensure text and original_text are synchronized for TS/Go/Python compatibility
            if d.get("original_text") is not None:
                d.setdefault("text", d["original_text"])
            elif d.get("text") is not None:
                d.setdefault("original_text", d["text"])
        return d

    def model_dump(self, *args, **kwargs):
        d = super().model_dump(*args, **kwargs)
        if "original_text" in d and d["original_text"] is not None:
            d.setdefault("text", d["original_text"])
        elif "text" in d and d["text"] is not None:
            d.setdefault("original_text", d["text"])
        return d
