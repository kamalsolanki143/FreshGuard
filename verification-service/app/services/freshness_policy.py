from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, get_settings
from app.schemas.claims import ClaimCategory, ClaimVerdict
from app.schemas.evidence import ensure_utc_datetime
from app.schemas.response import FreshnessStatus, VerificationStatus

logger = logging.getLogger("freshguard.freshness_policy")


class FreshnessEvaluation(BaseModel):
    """Evaluation result detailing the freshness state of a cached claim or verification."""
    model_config = ConfigDict(extra="ignore")

    is_fresh: bool = Field(..., description="Whether the record is within its valid TTL window")
    status: FreshnessStatus = Field(..., description="FRESH, STALE, or UNCERTAIN")
    category: str = Field(..., description="Claim category evaluated")
    ttl_seconds: int = Field(..., description="Policy TTL applied in seconds")
    checked_at: Optional[datetime] = Field(default=None, description="Original verification timestamp (UTC)")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration deadline timestamp (UTC)")
    age_seconds: Optional[float] = Field(default=None, description="Elapsed time since verification in seconds")
    reason: str = Field(..., description="Explanation of freshness determination")


class FreshnessPolicyEngine:
    """
    Configurable freshness policy engine managing TTLs and expiration calculations
    per claim category.
    """

    CLOCK_DRIFT_TOLERANCE_SECONDS: float = 5.0

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._custom_policies: Dict[str, int] = {}

    def get_ttl(self, category: Union[str, ClaimCategory]) -> int:
        """Returns the configured TTL in seconds for a given category."""
        clean_cat = category.value if isinstance(category, ClaimCategory) else str(category).lower().strip()

        # Check runtime registered policies first
        if clean_cat in self._custom_policies:
            return self._custom_policies[clean_cat]

        # Check settings
        if clean_cat == ClaimCategory.SOFTWARE_VERSION.value:
            return self.settings.TTL_SOFTWARE_VERSION
        elif clean_cat == ClaimCategory.PRICING.value:
            return self.settings.TTL_PRICING
        elif clean_cat == ClaimCategory.LEADERSHIP.value:
            return self.settings.TTL_LEADERSHIP
        elif clean_cat == ClaimCategory.PRODUCT_AVAILABILITY.value:
            return self.settings.TTL_PRODUCT_AVAILABILITY
        elif clean_cat == ClaimCategory.RECENT_EVENTS.value:
            return self.settings.TTL_RECENT_EVENTS
        elif clean_cat in (ClaimCategory.CURRENT_STATISTICS.value, "statistics"):
            return self.settings.TTL_STATISTICS
        elif clean_cat == ClaimCategory.GENERAL_KNOWLEDGE.value:
            return self.settings.TTL_GENERAL_KNOWLEDGE
        else:
            return self.settings.TTL_GENERAL

    def register_policy(self, category: Union[str, ClaimCategory], ttl_seconds: int) -> None:
        """Registers or overrides a category TTL at runtime."""
        if ttl_seconds <= 0:
            raise ValueError(f"TTL must be positive integer, got {ttl_seconds}")
        clean_cat = category.value if isinstance(category, ClaimCategory) else str(category).lower().strip()
        self._custom_policies[clean_cat] = ttl_seconds
        logger.info("Registered freshness policy for category '%s': %ds", clean_cat, ttl_seconds)

    def calculate_expiration(
        self,
        checked_at: datetime,
        category: Union[str, ClaimCategory],
    ) -> datetime:
        """Calculates the UTC expiration timestamp given verification time and category."""
        utc_checked = ensure_utc_datetime(checked_at)
        ttl = self.get_ttl(category)
        return utc_checked + timedelta(seconds=ttl)

    def evaluate_freshness(
        self,
        checked_at: Optional[datetime],
        category: Union[str, ClaimCategory],
        verdict: Optional[Union[str, ClaimVerdict]] = None,
        reference_time: Optional[datetime] = None,
    ) -> FreshnessEvaluation:
        """
        Imparts conservative evaluation of record freshness.
        """
        now = ensure_utc_datetime(reference_time) if reference_time else datetime.now(timezone.utc)
        cat_str = category.value if isinstance(category, ClaimCategory) else str(category).lower().strip()
        ttl = self.get_ttl(category)

        # 1. Missing timestamp check
        if checked_at is None:
            return FreshnessEvaluation(
                is_fresh=False,
                status=FreshnessStatus.STALE,
                category=cat_str,
                ttl_seconds=ttl,
                checked_at=None,
                expires_at=None,
                age_seconds=None,
                reason="Verification timestamp is missing; record cannot be certified as fresh.",
            )

        utc_checked = ensure_utc_datetime(checked_at)

        # 2. Incomplete or inconclusive verdict check
        if verdict is not None:
            if isinstance(verdict, ClaimVerdict):
                is_conclusive = verdict in (ClaimVerdict.SUPPORTED, ClaimVerdict.CONTRADICTED)
                verdict_str = verdict.value
            else:
                verdict_str = str(verdict).lower()
                is_conclusive = verdict_str in ("supported", "contradicted")

            if not is_conclusive:
                return FreshnessEvaluation(
                    is_fresh=False,
                    status=FreshnessStatus.UNCERTAIN,
                    category=cat_str,
                    ttl_seconds=ttl,
                    checked_at=utc_checked,
                    expires_at=utc_checked + timedelta(seconds=ttl),
                    age_seconds=max(0.0, (now - utc_checked).total_seconds()),
                    reason=f"Previous verification concluded with inconclusive verdict '{verdict_str}'; not eligible for fresh cache.",
                )

        # 3. Future timestamp check (safeguard against clock drift or invalid data)
        age_seconds = (now - utc_checked).total_seconds()
        if age_seconds < -self.CLOCK_DRIFT_TOLERANCE_SECONDS:
            logger.warning("Record checked_at is in the future by %.2fs. Clamping to current time.", -age_seconds)
            utc_checked = now
            age_seconds = 0.0

        expires_at = utc_checked + timedelta(seconds=ttl)
        is_fresh = now < expires_at

        if is_fresh:
            return FreshnessEvaluation(
                is_fresh=True,
                status=FreshnessStatus.FRESH,
                category=cat_str,
                ttl_seconds=ttl,
                checked_at=utc_checked,
                expires_at=expires_at,
                age_seconds=round(max(0.0, age_seconds), 2),
                reason=f"Record is fresh (age: {int(age_seconds)}s / TTL: {ttl}s).",
            )
        else:
            return FreshnessEvaluation(
                is_fresh=False,
                status=FreshnessStatus.STALE,
                category=cat_str,
                ttl_seconds=ttl,
                checked_at=utc_checked,
                expires_at=expires_at,
                age_seconds=round(age_seconds, 2),
                reason=f"Record has expired (age: {int(age_seconds)}s / TTL: {ttl}s).",
            )

    def is_fresh(
        self,
        checked_at: Optional[datetime],
        category: Union[str, ClaimCategory],
        verdict: Optional[Union[str, ClaimVerdict]] = None,
        reference_time: Optional[datetime] = None,
    ) -> bool:
        """Helper returning boolean freshness flag."""
        return self.evaluate_freshness(checked_at, category, verdict, reference_time).is_fresh
