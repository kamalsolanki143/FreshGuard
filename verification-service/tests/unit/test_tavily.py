import asyncio
import json
import pytest
import httpx

from app.schemas.claims import ClaimCategory, ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceSourceType
from app.services.search_query import SearchQueryGenerator
from app.services.tavily_service import TavilyService
from app.utils.exceptions import TavilyAPIError


# ==============================================================================
# Helper Mock Transports
# ==============================================================================

def create_mock_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


# ==============================================================================
# Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_successful_search():
    """Test successful search with authoritative domain identification."""
    mock_response = {
        "query": "Python latest stable version release notes official",
        "results": [
            {
                "title": "Python 3.13.0 Release Notes",
                "url": "https://www.python.org/downloads/release/python-3130/",
                "content": "Python 3.13.0 is the latest stable release.",
                "score": 0.95,
                "published_date": "2026-10-07T12:00:00Z",
            },
            {
                "title": "Python News and Tutorials",
                "url": "https://example-tech-blog.com/python-313",
                "content": "A blog review of Python 3.13 features.",
                "score": 0.80,
                "published_date": "2026-10-08",
            },
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response)

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        claim = ExtractedClaim(
            claim_id="claim_001",
            text="Python 3.12 is the latest stable version",
            category=ClaimCategory.SOFTWARE_VERSION,
            entity="Python",
            attribute="latest_version",
        )

        evidence = await service.retrieve_evidence_for_claim(claim)

        assert len(evidence) == 2
        # Authoritative domain (python.org) should be prioritized and boosted
        assert evidence[0].source_type == EvidenceSourceType.OFFICIAL_DOCS
        assert "python.org" in str(evidence[0].url)
        assert evidence[0].relevance_score > 0.95
        assert evidence[0].published_at is not None
        assert evidence[1].source_type == EvidenceSourceType.WEBSITE


@pytest.mark.asyncio
async def test_duplicate_url_removal():
    """Test that search results with identical URLs are deduplicated."""
    mock_response = {
        "results": [
            {
                "title": "Python Downloads",
                "url": "https://www.python.org/downloads/",
                "content": "Download page snippet 1",
                "score": 0.90,
            },
            {
                "title": "Duplicate Python Downloads",
                "url": "https://www.python.org/downloads/",
                "content": "Download page snippet 2",
                "score": 0.95,
            },
            {
                "title": "Different URL",
                "url": "https://docs.python.org/3/",
                "content": "Official docs",
                "score": 0.85,
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response)

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        evidence = await service.search("Python downloads")

        assert len(evidence) == 2
        urls = [str(e.url) for e in evidence]
        assert len(set(urls)) == 2


@pytest.mark.asyncio
async def test_empty_search_results():
    """Test that zero search results cleanly return an empty list without fabricating evidence."""
    mock_response = {"results": []}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response)

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        evidence = await service.search("Unknown query with zero results")
        assert evidence == []


@pytest.mark.asyncio
async def test_invalid_response_structure():
    """Test that malformed Tavily response raises TavilyAPIError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Invalid structure missing results"})

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        with pytest.raises(TavilyAPIError) as exc_info:
            await service.search("test query")
        assert "missing 'results' field" in exc_info.value.message


@pytest.mark.asyncio
async def test_http_401_unauthorized():
    """Test HTTP 401 is not retried and raises TavilyAPIError immediately."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, json={"detail": "Unauthorized invalid key"})

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-invalid-key", client=client)
        with pytest.raises(TavilyAPIError) as exc_info:
            await service.search("test query")

        assert call_count == 1  # No retries on 401
        assert "authentication failed" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_http_429_rate_limit_backoff():
    """Test HTTP 429 triggers exponential backoff and succeeds on subsequent attempt."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, json={"error": "Rate limit exceeded"})
        return httpx.Response(200, json={"results": [{"title": "Success", "url": "https://example.com", "score": 0.9}]})

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        evidence = await service.search("test rate limit")

        assert attempts == 2
        assert len(evidence) == 1
        assert str(evidence[0].url) == "https://example.com/"


@pytest.mark.asyncio
async def test_http_500_server_error_exhaustion():
    """Test HTTP 500 across all retries raises TavilyAPIError."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, json={"error": "Internal server error"})

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        with pytest.raises(TavilyAPIError) as exc_info:
            await service.search("test server error")

        assert attempts > 1
        assert "failed after" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout during search raises TavilyAPIError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out")

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        with pytest.raises(TavilyAPIError) as exc_info:
            await service.search("timeout query")

        assert "timed out" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_network_failure_handling():
    """Test network connection error raises TavilyAPIError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network is unreachable")

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        with pytest.raises(TavilyAPIError) as exc_info:
            await service.search("network error query")

        assert "network communication error" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_retrieve_evidence_for_multiple_claims():
    """Test concurrent evidence retrieval for multiple claims."""
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        query = body.get("query", "")
        if "Python" in query:
            return httpx.Response(200, json={"results": [{"title": "Python Releases", "url": "https://python.org", "score": 0.95}]})
        elif "Stripe" in query:
            return httpx.Response(200, json={"results": [{"title": "Stripe Pricing", "url": "https://stripe.com/pricing", "score": 0.92}]})
        return httpx.Response(200, json={"results": []})

    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client)
        claim1 = ExtractedClaim(claim_id="c1", text="Python 3.12 is latest", category=ClaimCategory.SOFTWARE_VERSION, entity="Python", attribute="version")
        claim2 = ExtractedClaim(claim_id="c2", text="Stripe fee is 2.9%", category=ClaimCategory.PRICING, entity="Stripe", attribute="fee")

        results = await service.retrieve_evidence_for_claims([claim1, claim2])

        assert "c1" in results
        assert "c2" in results
        assert len(results["c1"]) == 1
        assert str(results["c1"][0].url) == "https://python.org/"
        assert len(results["c2"]) == 1
        assert str(results["c2"][0].url) == "https://stripe.com/pricing"


@pytest.mark.asyncio
async def test_bounded_concurrency():
    """Test that max_concurrency semaphore limits concurrent requests."""
    active_requests = 0
    max_observed_concurrency = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active_requests, max_observed_concurrency
        active_requests += 1
        if active_requests > max_observed_concurrency:
            max_observed_concurrency = active_requests
        active_requests -= 1
        return httpx.Response(200, json={"results": []})

    concurrency_limit = 2
    async with create_mock_client(handler) as client:
        service = TavilyService(api_key="tvly-mock-key", client=client, max_concurrency=concurrency_limit)
        claims = [
            ExtractedClaim(claim_id=f"c{i}", text=f"Claim {i}", category=ClaimCategory.OTHER, entity=f"Entity {i}", attribute="attr")
            for i in range(10)
        ]

        await service.retrieve_evidence_for_claims(claims)
        assert max_observed_concurrency <= concurrency_limit


def test_search_query_generation_across_categories():
    """Test precision query generation across all supported categories."""
    claim_ver = ExtractedClaim(claim_id="1", text="v", category=ClaimCategory.SOFTWARE_VERSION, entity="Node.js", attribute="latest_version")
    assert "Node.js latest stable version release notes official" == SearchQueryGenerator.generate_query(claim_ver)

    claim_price = ExtractedClaim(claim_id="2", text="p", category=ClaimCategory.PRICING, entity="OpenAI", attribute="api_pricing")
    assert "OpenAI api pricing price cost pricing official" == SearchQueryGenerator.generate_query(claim_price)

    claim_lead = ExtractedClaim(claim_id="3", text="l", category=ClaimCategory.LEADERSHIP, entity="Google", attribute="ceo")
    assert "Google current ceo official leadership" == SearchQueryGenerator.generate_query(claim_lead)

    claim_avail = ExtractedClaim(claim_id="4", text="a", category=ClaimCategory.PRODUCT_AVAILABILITY, entity="RTX 5090", attribute="availability")
    assert "RTX 5090 stock availability buy now official" == SearchQueryGenerator.generate_query(claim_avail)

    claim_news = ExtractedClaim(claim_id="5", text="n", category=ClaimCategory.RECENT_EVENTS, entity="Apple", attribute="m4_launch")
    assert "Apple m4 launch announcement latest news" == SearchQueryGenerator.generate_query(claim_news)
