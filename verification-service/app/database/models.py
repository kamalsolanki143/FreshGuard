from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


class VerificationRecord(Base):
    """Stored history of a verification request."""
    __tablename__ = "verification_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    freshness_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    requires_refresh: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    claims_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    claims: Mapped[List["ClaimRecord"]] = relationship(
        "ClaimRecord",
        back_populates="verification",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_verif_req_created", "request_id", "created_at"),
    )


class ClaimRecord(Base):
    """Discrete factual claim verified and stored for cache / freshness lookup."""
    __tablename__ = "claim_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("verification_records.verification_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    claim_id: Mapped[str] = mapped_column(String(128), nullable=False)
    claim_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    attribute: Mapped[str] = mapped_column(String(256), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_value: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    is_cached_fact: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    verification: Mapped["VerificationRecord"] = relationship(
        "VerificationRecord",
        back_populates="claims",
    )
    evidence: Mapped[List["EvidenceRecord"]] = relationship(
        "EvidenceRecord",
        back_populates="claim",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_claim_fingerprint_expires", "claim_fingerprint", "expires_at"),
    )


class EvidenceRecord(Base):
    """Supporting or refuting web evidence grounding a claim verdict."""
    __tablename__ = "evidence_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_db_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("claim_records.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), default="website", nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    claim: Mapped["ClaimRecord"] = relationship(
        "ClaimRecord",
        back_populates="evidence",
    )


class FreshnessPolicyRecord(Base):
    """Persisted category freshness policy TTLs."""
    __tablename__ = "freshness_policy_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
