import pytest
from app.services.prefilter import PrefilterEngine, PrefilterResult


@pytest.fixture
def prefilter():
    return PrefilterEngine()


def test_software_version_detection(prefilter: PrefilterEngine):
    """Test detection of software version claims."""
    text = "Python 3.12 is the latest stable version."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "software_version" in result.categories
    assert result.confidence >= 0.85


def test_pricing_detection(prefilter: PrefilterEngine):
    """Test detection of pricing and subscription claims."""
    text = "ChatGPT Plus costs $20 per month for individual users."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "pricing" in result.categories
    assert result.confidence >= 0.85


def test_leadership_detection(prefilter: PrefilterEngine):
    """Test detection of corporate leadership claims."""
    text = "Sundar Pichai is the current CEO of Google."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "leadership" in result.categories
    assert result.confidence >= 0.85


def test_product_availability_detection(prefilter: PrefilterEngine):
    """Test detection of product stock / availability claims."""
    text = "The Nvidia RTX 5090 is currently out of stock at major retailers."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "product_availability" in result.categories
    assert result.confidence >= 0.85


def test_recent_events_detection(prefilter: PrefilterEngine):
    """Test detection of claims referencing recent temporal anchors."""
    text = "Yesterday, OpenAI just announced their next generation model."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "recent_events" in result.categories
    assert result.confidence >= 0.85


def test_statistics_detection(prefilter: PrefilterEngine):
    """Test detection of fluctuating statistical claims."""
    text = "The US inflation rate is currently at 3.2% according to latest reports."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "statistics" in result.categories
    assert result.confidence >= 0.85


def test_general_knowledge_reduction(prefilter: PrefilterEngine):
    """Test that timeless scientific or historical facts do not trigger verification."""
    text = "Photosynthesis is the process by which green plants use sunlight to synthesize nutrients."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is False
    assert result.confidence < 0.60
    assert "general_knowledge" in result.categories or not result.categories


def test_historical_fact_reduction(prefilter: PrefilterEngine):
    """Test that historical facts without current claims are not flagged."""
    text = "Python was created in 1991 by Guido van Rossum."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is False


def test_multiple_categories_detection(prefilter: PrefilterEngine):
    """Test response containing both software version and pricing claims."""
    text = "Python 3.12 is the latest stable release and Github Copilot costs $10 per month."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "software_version" in result.categories
    assert "pricing" in result.categories
    assert len(result.categories) >= 2


def test_empty_and_whitespace_input(prefilter: PrefilterEngine):
    """Test that empty or whitespace inputs are handled safely."""
    assert prefilter.evaluate("").requires_verification is False
    assert prefilter.evaluate("   ").requires_verification is False
    assert prefilter.evaluate(None).requires_verification is False


def test_irrelevant_text_no_false_positive(prefilter: PrefilterEngine):
    """Test conversational or general text does not trigger verification."""
    text = "Here is a recipe for chocolate chip cookies. Mix flour, sugar, and butter."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is False
    assert result.confidence == 0.0


def test_case_insensitive_matching(prefilter: PrefilterEngine):
    """Test uppercase and lowercase variations trigger correctly."""
    text = "NODE.JS VERSION 22 IS THE LATEST STABLE RELEASE."
    result: PrefilterResult = prefilter.evaluate(text)

    assert result.requires_verification is True
    assert "software_version" in result.categories
