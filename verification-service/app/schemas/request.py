from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.claims import ClaimCategory


class VerificationMode(str, Enum):
    """Execution mode for verification requests."""
    BLOCKING = "blocking"


class VerificationRequest(BaseModel):
    """
    Verification request payload accepted by FreshGuard.
    Fully compatible with Bifrost Gateway Go plugin and REST callers.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    request_id: str = Field(..., min_length=1, max_length=128, description="Correlation identifier for tracing")
    response_text: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        alias="text",
        description="LLM response text or content to verify",
    )
    model: Optional[str] = Field(default=None, max_length=128, description="Source LLM model identifier")
    source: Optional[str] = Field(default="bifrost", max_length=64, description="Originating gateway or client")
    mode: VerificationMode = Field(default=VerificationMode.BLOCKING, description="Execution mode: blocking only")
    categories: Optional[List[str]] = Field(default=None, description="Optional category filters for verification")

    @field_validator("response_text", mode="before")
    @classmethod
    def reject_blank_text(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Text must contain at least one non-whitespace character.")
        return value.strip()

    @field_validator("mode", mode="before")
    @classmethod
    def require_supported_mode(cls, value: object) -> VerificationMode:
        return VerificationMode(value)

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return values
        allowed = {category.value for category in ClaimCategory}
        normalized = [value.strip().lower() for value in values]
        unknown = sorted(set(normalized) - allowed)
        if unknown:
            raise ValueError(
                f"Unknown categories: {', '.join(unknown)}. Allowed categories: {', '.join(sorted(allowed))}."
            )
        return normalized
