from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_serializer


class EvidenceSourceType(str, Enum):
    """Source classification for retrieved web evidence."""
    OFFICIAL_DOCS = "official_docs"
    NEWS = "news"
    WEBSITE = "website"
    OTHER = "other"


def ensure_utc_datetime(v: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware and set to UTC."""
    if v is None:
        return None
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)


class EvidenceItem(BaseModel):
    """Normalized evidence item attached to claim verdicts."""
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    evidence_id: Optional[str] = Field(default=None, description="Unique identifier for the evidence snippet")
    title: str = Field(..., min_length=1, max_length=500, alias="source_title", description="Title of the source webpage")
    url: HttpUrl = Field(..., alias="source_url", description="Verified source URL")
    content: Optional[str] = Field(default="", max_length=10000, alias="snippet", description="Extracted textual content or snippet")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence/relevance score between 0.0 and 1.0")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time the evidence was retrieved in UTC",
    )
    published_at: Optional[datetime] = Field(default=None, description="Original publication timestamp if available")
    source_type: EvidenceSourceType = Field(default=EvidenceSourceType.WEBSITE, description="Type of evidence source")

    @field_validator("retrieved_at", "published_at", mode="after")
    @classmethod
    def validate_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc_datetime(v)

    @model_serializer(mode="wrap")
    def _serialize_evidence(self, handler):
        d = handler(self)
        if isinstance(d, dict):
            # Guarantee evidence_id is not empty
            if not d.get("evidence_id"):
                d["evidence_id"] = f"ev_{abs(hash(str(d.get('url') or d.get('source_url') or 'ev'))) % 1000000:06d}"
            # Synchronize url and source_url
            if d.get("url") is not None:
                u_str = str(d["url"])
                d["url"] = u_str
                d.setdefault("source_url", u_str)
            elif d.get("source_url") is not None:
                u_str = str(d["source_url"])
                d["source_url"] = u_str
                d.setdefault("url", u_str)
            # Synchronize title and source_title
            if d.get("title") is not None:
                d.setdefault("source_title", d["title"])
            elif d.get("source_title") is not None:
                d.setdefault("title", d["source_title"])
            # Synchronize content and snippet
            if d.get("content") is not None:
                d.setdefault("snippet", d["content"])
            elif d.get("snippet") is not None:
                d.setdefault("content", d["snippet"])
            else:
                d.setdefault("snippet", "")
                d.setdefault("content", "")
        return d

    def model_dump(self, *args, **kwargs):
        """Custom dump ensuring HttpUrl is serialized to string and aliases populated."""
        d = super().model_dump(*args, **kwargs)
        if not d.get("evidence_id"):
            d["evidence_id"] = f"ev_{abs(hash(str(d.get('url') or d.get('source_url') or 'ev'))) % 1000000:06d}"
        if "url" in d and d["url"] is not None:
            u_str = str(d["url"])
            d["url"] = u_str
            d.setdefault("source_url", u_str)
        if "source_url" in d and d["source_url"] is not None:
            u_str = str(d["source_url"])
            d["source_url"] = u_str
            d.setdefault("url", u_str)
        if "title" in d:
            d.setdefault("source_title", d["title"])
        if "source_title" in d:
            d.setdefault("title", d["source_title"])
        if "content" in d:
            d.setdefault("snippet", d["content"] or "")
        if "snippet" in d:
            d.setdefault("content", d["snippet"] or "")
        return d


class EvidenceMinimal(BaseModel):
    """Minimal evidence format for concise API responses with contract alias support."""
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, extra="ignore")

    evidence_id: Optional[str] = Field(default=None, description="Unique evidence ID")
    title: str = Field(..., min_length=1, max_length=500, alias="source_title")
    url: str = Field(..., alias="source_url")
    content: Optional[str] = Field(default="", max_length=10000, alias="snippet")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time evidence was retrieved in UTC",
    )
    published_at: Optional[datetime] = Field(default=None)
    source_type: EvidenceSourceType = Field(default=EvidenceSourceType.WEBSITE)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        # Validate that string starts with http:// or https://
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("retrieved_at", "published_at", mode="after")
    @classmethod
    def validate_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        return ensure_utc_datetime(v)

    @model_serializer(mode="wrap")
    def _serialize_minimal(self, handler):
        d = handler(self)
        if isinstance(d, dict):
            if not d.get("evidence_id"):
                d["evidence_id"] = f"ev_{abs(hash(str(d.get('url') or d.get('source_url') or 'ev'))) % 1000000:06d}"
            if d.get("url") is not None:
                d.setdefault("source_url", str(d["url"]))
            elif d.get("source_url") is not None:
                d.setdefault("url", str(d["source_url"]))
            if d.get("title") is not None:
                d.setdefault("source_title", d["title"])
            elif d.get("source_title") is not None:
                d.setdefault("title", d["source_title"])
            if d.get("content") is not None:
                d.setdefault("snippet", d["content"])
            elif d.get("snippet") is not None:
                d.setdefault("content", d["snippet"])
            else:
                d.setdefault("snippet", "")
                d.setdefault("content", "")
        return d

    def model_dump(self, *args, **kwargs):
        d = super().model_dump(*args, **kwargs)
        if not d.get("evidence_id"):
            d["evidence_id"] = f"ev_{abs(hash(str(d.get('url') or d.get('source_url') or 'ev'))) % 1000000:06d}"
        if "url" in d:
            d.setdefault("source_url", str(d["url"]))
        if "source_url" in d:
            d.setdefault("url", str(d["source_url"]))
        if "title" in d:
            d.setdefault("source_title", d["title"])
        if "source_title" in d:
            d.setdefault("title", d["source_title"])
        if "content" in d:
            d.setdefault("snippet", d["content"] or "")
        if "snippet" in d:
            d.setdefault("content", d["snippet"] or "")
        return d
