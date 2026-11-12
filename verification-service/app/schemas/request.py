from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class VerificationMode(str, Enum):
    """Execution mode for verification requests."""
    BLOCKING = "blocking"
    ASYNC = "async"


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
    mode: VerificationMode = Field(default=VerificationMode.BLOCKING, description="Execution mode: blocking or async")
    categories: Optional[List[str]] = Field(default=None, description="Optional category filters for verification")

    @model_validator(mode="before")
    @classmethod
    def reconcile_text_fields(cls, data: object) -> object:
        """Ensures either response_text or text is populated."""
        if isinstance(data, dict):
            if "response_text" not in data and "text" in data:
                data["response_text"] = data["text"]
            elif "text" not in data and "response_text" in data:
                data["text"] = data["response_text"]
        return data
