from datetime import datetime, timedelta, timezone
import pytest

from app.schemas.claims import ClaimCategory, ClaimVerdict
from app.schemas.response import VerificationStatus
from app.services.freshness_policy import FreshnessEvaluation, FreshnessPolicyEngine


@pytest.fixture
def policy_engine():
    return FreshnessPolicyEngine()


def test_category_specific_ttls(policy_engine: FreshnessPolicyEngine):
    """Test default TTL configurations across all defined categories."""
    assert policy_engine.get_ttl(ClaimCategory.SOFTWARE_VERSION) == 86400  # 24 hours
    assert policy_engine.get_ttl(ClaimCategory.PRICING) == 21600           # 6 hours
    assert policy_engine.get_ttl(ClaimCategory.LEADERSHIP) == 86400        # 24 hours
    assert policy_engine.get_ttl(ClaimCategory.PRODUCT_AVAILABILITY) == 3600  # 1 hour
    assert policy_engine.get_ttl(ClaimCategory.RECENT_EVENTS) == 21600     # 6 hours
    assert policy_engine.get_ttl(ClaimCategory.CURRENT_STATISTICS) == 86400 # 24 hours
    assert policy_engine.get_ttl(ClaimCategory.GENERAL_KNOWLEDGE) == 2592000 # 30 days
    assert policy_engine.get_ttl(ClaimCategory.OTHER) == 43200             # 12 hours


def test_fresh_record(policy_engine: FreshnessPolicyEngine):
    """Test that verification checked 1 hour ago with 24h TTL evaluates as FRESH."""
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    eval_result: FreshnessEvaluation = policy_engine.evaluate_freshness(
        checked_at=one_hour_ago,
        category=ClaimCategory.SOFTWARE_VERSION,
        verdict=ClaimVerdict.SUPPORTED,
        reference_time=now,
    )

    assert eval_result.is_fresh is True
    assert eval_result.status == VerificationStatus.FRESH
    assert eval_result.ttl_seconds == 86400
    assert eval_result.expires_at > now
    assert eval_result.age_seconds == pytest.approx(3600, abs=5)


def test_expired_record(policy_engine: FreshnessPolicyEngine):
    """Test that verification checked 7 hours ago with 6h pricing TTL evaluates as STALE."""
    now = datetime.now(timezone.utc)
    seven_hours_ago = now - timedelta(hours=7)

    eval_result: FreshnessEvaluation = policy_engine.evaluate_freshness(
        checked_at=seven_hours_ago,
        category=ClaimCategory.PRICING,
        verdict=ClaimVerdict.SUPPORTED,
        reference_time=now,
    )

    assert eval_result.is_fresh is False
    assert eval_result.status == VerificationStatus.STALE
    assert eval_result.ttl_seconds == 21600
    assert eval_result.expires_at < now


def test_missing_timestamp_handling(policy_engine: FreshnessPolicyEngine):
    """Test that missing checked_at timestamp is conservatively treated as STALE."""
    eval_result = policy_engine.evaluate_freshness(
        checked_at=None,
        category=ClaimCategory.SOFTWARE_VERSION,
        verdict=ClaimVerdict.SUPPORTED,
    )

    assert eval_result.is_fresh is False
    assert eval_result.status == VerificationStatus.STALE
    assert "missing" in eval_result.reason.lower()


def test_inconclusive_verdict_cannot_be_fresh(policy_engine: FreshnessPolicyEngine):
    """Test that UNCLEAR verdict cannot be certified as FRESH even if checked 1 second ago."""
    now = datetime.now(timezone.utc)
    just_now = now - timedelta(seconds=1)

    eval_result = policy_engine.evaluate_freshness(
        checked_at=just_now,
        category=ClaimCategory.SOFTWARE_VERSION,
        verdict=ClaimVerdict.UNCLEAR,
        reference_time=now,
    )

    assert eval_result.is_fresh is False
    assert eval_result.status == VerificationStatus.UNCERTAIN
    assert "inconclusive" in eval_result.reason.lower()


def test_future_timestamp_safety(policy_engine: FreshnessPolicyEngine):
    """Test that far-future timestamps are safely clamped rather than granting infinite TTL."""
    now = datetime.now(timezone.utc)
    far_future = now + timedelta(days=10)

    eval_result = policy_engine.evaluate_freshness(
        checked_at=far_future,
        category=ClaimCategory.SOFTWARE_VERSION,
        verdict=ClaimVerdict.SUPPORTED,
        reference_time=now,
    )

    # Future timestamps are clamped to now, expiring within normal TTL
    assert eval_result.is_fresh is True
    assert eval_result.expires_at <= now + timedelta(seconds=86400)


def test_dynamic_policy_override(policy_engine: FreshnessPolicyEngine):
    """Test registering runtime policy overrides without code modifications."""
    policy_engine.register_policy("crypto_pricing", 300)  # 5 minutes
    assert policy_engine.get_ttl("crypto_pricing") == 300

    now = datetime.now(timezone.utc)
    ten_mins_ago = now - timedelta(minutes=10)
    assert policy_engine.is_fresh(ten_mins_ago, "crypto_pricing", reference_time=now) is False

    two_mins_ago = now - timedelta(minutes=2)
    assert policy_engine.is_fresh(two_mins_ago, "crypto_pricing", reference_time=now) is True
