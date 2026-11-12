import pytest
from packaging.version import Version

from app.schemas.claims import ClaimCategory, ClaimVerdict, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceSourceType
from app.services.version_validator import VersionValidator


@pytest.fixture
def validator():
    return VersionValidator()


def test_standard_and_multidigit_version_comparison():
    """Verify non-lexical packaging.version.Version mathematical ordering."""
    v3_10 = Version("3.10.0")
    v3_9 = Version("3.9.0")
    v2_0 = Version("2.0.0")
    v1_99 = Version("1.99.9")

    assert v3_10 > v3_9
    assert v2_0 > v1_99


def test_prerelease_distinction():
    """Verify that prereleases are identified as prereleases and not stable."""
    v_rc = Version("1.0.0rc1")
    v_beta = Version("2.0.0b2")
    v_stable = Version("1.0.0")

    assert v_rc.is_prerelease is True
    assert v_beta.is_prerelease is True
    assert v_stable.is_prerelease is False
    assert v_stable > v_rc


def test_safe_parse_invalid_version_strings(validator: VersionValidator):
    """Test that invalid version strings return None and do not crash."""
    assert validator.safe_parse_version("invalid_ver_string") is None
    assert validator.safe_parse_version("") is None
    assert validator.safe_parse_version("...") is None
    assert validator.safe_parse_version("3.12.0") == Version("3.12.0")
    assert validator.safe_parse_version("v1.5") == Version("1.5")


def test_latest_stable_version_contradicted_by_newer(validator: VersionValidator):
    """Test claim that Python 3.12 is latest is contradicted when evidence reports Python 3.13."""
    claim = ExtractedClaim(
        claim_id="claim_001",
        text="Python 3.12 is the latest stable version.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_01",
            title="Python Release News",
            url="https://www.python.org/downloads/",
            content="Python 3.13.0 is the latest stable release for all platforms.",
            relevance_score=0.98,
            source_type=EvidenceSourceType.OFFICIAL_DOCS,
        )
    ]

    result = validator.validate_claim(claim, evidence)

    assert result.verdict == ClaimVerdict.CONTRADICTED
    assert result.confidence >= 0.90
    assert "3.13" in result.reason
    assert result.corrected_value == "3.13.0"


def test_latest_stable_version_supported(validator: VersionValidator):
    """Test claim that Python 3.12 is latest is supported when evidence confirms 3.12."""
    claim = ExtractedClaim(
        claim_id="claim_002",
        text="Python 3.12 is the latest stable release.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_02",
            title="Python Release News",
            url="https://www.python.org/downloads/",
            content="Python 3.12.0 is the latest stable version.",
            relevance_score=0.98,
            source_type=EvidenceSourceType.OFFICIAL_DOCS,
        )
    ]

    result = validator.validate_claim(claim, evidence)

    assert result.verdict == ClaimVerdict.SUPPORTED
    assert result.confidence >= 0.90
    assert "confirms" in result.reason.lower()


def test_prerelease_in_evidence_not_treated_as_latest_stable(validator: VersionValidator):
    """Test that evidence mentioning a prerelease (3.13rc1) does not invalidate current stable (3.12)."""
    claim = ExtractedClaim(
        claim_id="claim_003",
        text="Python 3.12 is the latest stable version.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_03",
            title="Python Preview",
            url="https://www.python.org/downloads/",
            content="Python 3.12.0 is the latest stable release. Python 3.13rc1 is in testing.",
            relevance_score=0.98,
        )
    ]

    result = validator.validate_claim(claim, evidence)

    # Since 3.12 is stable and 3.13rc1 is a prerelease, claim is SUPPORTED
    assert result.verdict == ClaimVerdict.SUPPORTED


def test_missing_version_evidence(validator: VersionValidator):
    """Test that zero evidence yields UNCLEAR."""
    claim = ExtractedClaim(
        claim_id="claim_004",
        text="Go 1.22 is the latest stable version.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Go",
        attribute="latest_version",
    )

    result = validator.validate_claim(claim, [])

    assert result.verdict == ClaimVerdict.UNCLEAR
    assert result.confidence == 0.0
    assert "Missing evidence" in result.reason


def test_entity_mismatch_rejection(validator: VersionValidator):
    """Test that version comparison is rejected across different software entities."""
    claim = ExtractedClaim(
        claim_id="claim_005",
        text="Python 3.12 is latest.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_04",
            title="Node.js Release Notes",
            url="https://nodejs.org",
            content="Node.js version 22.0.0 is the latest stable release.",
            relevance_score=0.90,
        )
    ]

    result = validator.validate_claim(claim, evidence)

    assert result.verdict == ClaimVerdict.UNCLEAR
    assert "No retrieved evidence corresponds to software entity 'Python'" in result.reason


def test_version_requirement_specifier(validator: VersionValidator):
    """Test version requirement expressions such as >= 1.5."""
    claim = ExtractedClaim(
        claim_id="claim_006",
        text="FastAPI requires Pydantic version >= 2.0.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Pydantic",
        attribute="version_requirement",
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_05",
            title="Pydantic Release History",
            url="https://docs.pydantic.dev",
            content="Pydantic version 2.6.0 is available.",
            relevance_score=0.95,
        )
    ]

    result = validator.validate_claim(claim, evidence)

    assert result.verdict == ClaimVerdict.SUPPORTED
    assert "satisfies requirement" in result.reason


def test_version_release_order_comparison(validator: VersionValidator):
    """Test release order comparison claims like 'Version 4.0 was released after 3.9'."""
    claim_true = ExtractedClaim(
        claim_id="claim_007",
        text="Django 4.0 was released after Django 3.9.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Django",
        attribute="release_order",
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_06",
            title="Django",
            url="https://djangoproject.com",
            content="Django releases 4.0 and 3.9.",
            relevance_score=0.90,
        )
    ]

    result = validator.validate_claim(claim_true, evidence)
    assert result.verdict == ClaimVerdict.SUPPORTED
    assert "is deterministically greater than" in result.reason


def test_empty_and_malformed_inputs(validator: VersionValidator):
    """Test empty claims or claims without valid version numbers."""
    claim_no_ver = ExtractedClaim(
        claim_id="claim_008",
        text="Python is a fast and dynamic programming language.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="speed",
    )
    evidence = [
        EvidenceItem(
            evidence_id="ev_07",
            title="Python.org",
            url="https://python.org",
            content="Python is an interpreted language.",
        )
    ]

    result = validator.validate_claim(claim_no_ver, evidence)
    assert result.verdict == ClaimVerdict.UNCLEAR
    assert "No valid, parseable version number found" in result.reason


def test_independent_validation_multiple_claims(validator: VersionValidator):
    """Test validating multiple claims independently."""
    claim1 = ExtractedClaim(
        claim_id="c1",
        text="Python 3.12 is the latest stable version.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Python",
        attribute="latest_version",
    )
    claim2 = ExtractedClaim(
        claim_id="c2",
        text="Node.js 18 is the latest stable version.",
        category=ClaimCategory.SOFTWARE_VERSION,
        entity="Node.js",
        attribute="latest_version",
    )

    ev_map = {
        "c1": [
            EvidenceItem(
                evidence_id="e1",
                title="Python",
                url="https://python.org",
                content="Python 3.12 is the latest stable version.",
            )
        ],
        "c2": [
            EvidenceItem(
                evidence_id="e2",
                title="Node",
                url="https://nodejs.org",
                content="Node.js 22.0.0 is the latest stable version.",
            )
        ],
    }

    results = validator.validate_claims([claim1, claim2], ev_map)

    assert len(results) == 2
    assert results[0].claim_id == "c1"
    assert results[0].verdict == ClaimVerdict.SUPPORTED
    assert results[1].claim_id == "c2"
    assert results[1].verdict == ClaimVerdict.CONTRADICTED
    assert results[1].corrected_value == "22.0.0"
