import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set
import httpx
from pydantic import HttpUrl, ValidationError

from app.config import Settings, get_settings
from app.schemas.claims import ExtractedClaim
from app.schemas.evidence import EvidenceItem, EvidenceSourceType, ensure_utc_datetime
from app.services.search_query import SearchQueryGenerator
from app.utils.exceptions import ConfigurationError, TavilyAPIError

logger = logging.getLogger("freshguard.tavily")


class TavilyService:
    """
    Asynchronous Tavily service for retrieving real-time web evidence.
    Includes rate-limit handling, bounded concurrency, deduplication, and domain ranking.
    """

    TAVILY_SEARCH_URL: str = "https://api.tavily.com/search"
    DEFAULT_MAX_CONCURRENCY: int = 5

    def __init__(
        self,
        api_key: Optional[str] = None,
        settings: Optional[Settings] = None,
        client: Optional[httpx.AsyncClient] = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ):
        self.settings = settings or get_settings()
        self.api_key = api_key or self.settings.TAVILY_API_KEY
        self.timeout = self.settings.TAVILY_TIMEOUT_SECONDS
        self.max_retries = self.settings.TAVILY_MAX_RETRIES
        self.max_results = self.settings.TAVILY_MAX_RESULTS
        self.search_depth = self.settings.TAVILY_SEARCH_DEPTH
        self._external_client = client
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=self.timeout)

    def _parse_published_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Safely parses published_date into timezone-aware UTC datetime."""
        if not date_str or not isinstance(date_str, str):
            return None
        try:
            # Handle ISO format strings like "2026-10-15T12:00:00Z" or "2026-10-15"
            cleaned = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return ensure_utc_datetime(dt)
        except Exception:
            return None

    def _is_authoritative(self, url_str: str, entity: str) -> bool:
        """Determines if the URL belongs to an authoritative domain for the entity."""
        auth_domains = SearchQueryGenerator.get_authoritative_domains(entity)
        lower_url = url_str.lower()
        return any(domain.lower() in lower_url for domain in auth_domains)

    async def search(self, query: str, claim: Optional[ExtractedClaim] = None) -> List[EvidenceItem]:
        """
        Executes a single search query against Tavily and normalizes results into EvidenceItem objects.
        """
        if not self.api_key:
            raise ConfigurationError(
                "TAVILY_API_KEY is not configured.",
                details={"service": "tavily"},
            )

        payload: Dict[str, Any] = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": self.search_depth,
            "include_answer": False,
            "max_results": self.max_results,
        }

        entity = claim.entity if claim else ""
        claim_id = claim.claim_id if claim else "claim_000"

        client_provided = self._external_client is not None
        client = self._external_client or httpx.AsyncClient(timeout=self.timeout)

        try:
            attempt = 0
            base_delay = 0.5
            response_json: Optional[Dict[str, Any]] = None

            while attempt <= self.max_retries:
                attempt += 1
                try:
                    async with self.semaphore:
                        response = await client.post(
                            self.TAVILY_SEARCH_URL,
                            json=payload,
                            headers={"Content-Type": "application/json"},
                        )

                    # Do NOT retry 401, 400, or 403 permanent errors
                    if response.status_code in (401, 403):
                        raise TavilyAPIError(
                            message=f"Tavily authentication failed with HTTP {response.status_code}.",
                            details={"status_code": response.status_code, "query": query},
                        )

                    if response.status_code == 400:
                        raise TavilyAPIError(
                            message=f"Tavily rejected query with HTTP 400: {response.text}",
                            details={"status_code": 400, "query": query},
                        )

                    # Transient retryable errors (429 Rate Limit, 5xx Server Errors)
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt > self.max_retries:
                            raise TavilyAPIError(
                                message=f"Tavily search failed after {self.max_retries} retries with status {response.status_code}.",
                                details={"status_code": response.status_code, "query": query},
                            )
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Tavily transient HTTP %d on attempt %d. Backing off for %.2fs.",
                            response.status_code,
                            attempt,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    try:
                        response_json = response.json()
                    except Exception as e:
                        raise TavilyAPIError(
                            message=f"Tavily returned invalid JSON: {str(e)}",
                            details={"query": query},
                        )
                    break

                except httpx.TimeoutException as e:
                    if attempt > self.max_retries:
                        raise TavilyAPIError(
                            message=f"Tavily request timed out after {self.timeout}s.",
                            details={"timeout": self.timeout, "query": query},
                        )
                    await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
                except httpx.RequestError as e:
                    if attempt > self.max_retries:
                        raise TavilyAPIError(
                            message=f"Tavily network communication error: {str(e)}",
                            details={"query": query, "error_type": type(e).__name__},
                        )
                    await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

            if not isinstance(response_json, dict) or "results" not in response_json:
                raise TavilyAPIError(
                    message="Tavily response missing 'results' field.",
                    details={"raw_response": response_json},
                )

            raw_results = response_json.get("results", [])
            if not isinstance(raw_results, list):
                raise TavilyAPIError(
                    message="Tavily 'results' field is not a list.",
                    details={"results_type": type(raw_results).__name__},
                )

            # Normalize and deduplicate evidence items by URL
            seen_urls: Set[str] = set()
            normalized_evidence: List[EvidenceItem] = []

            for idx, item in enumerate(raw_results, start=1):
                raw_url = item.get("url")
                if not raw_url or not isinstance(raw_url, str):
                    continue

                clean_url = raw_url.strip()
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                title = item.get("title", "") or "Untitled Evidence"
                content = item.get("content", "") or ""
                raw_score = item.get("score", 1.0)

                # Clamp relevance score safely between 0.0 and 1.0
                try:
                    relevance_score = max(0.0, min(1.0, float(raw_score)))
                except (ValueError, TypeError):
                    relevance_score = 0.5

                # Detect if domain is authoritative
                is_auth = self._is_authoritative(clean_url, entity)
                if is_auth:
                    source_type = EvidenceSourceType.OFFICIAL_DOCS
                    # Boost relevance score for authoritative domains
                    relevance_score = min(1.0, relevance_score + 0.1)
                else:
                    source_type = EvidenceSourceType.WEBSITE

                published_at = self._parse_published_date(item.get("published_date"))

                try:
                    evidence_item = EvidenceItem(
                        evidence_id=f"ev_{claim_id}_{idx:02d}",
                        title=title[:500],
                        url=clean_url,
                        content=content[:10000],
                        relevance_score=round(relevance_score, 2),
                        retrieved_at=datetime.now(timezone.utc),
                        published_at=published_at,
                        source_type=source_type,
                    )
                    normalized_evidence.append(evidence_item)
                except ValidationError as e:
                    logger.warning("Skipping invalid evidence item from URL %s: %s", clean_url, e)
                    continue

            # Sort authoritative sources to the top, then by relevance score
            normalized_evidence.sort(
                key=lambda x: (x.source_type == EvidenceSourceType.OFFICIAL_DOCS, x.relevance_score),
                reverse=True,
            )

            logger.info(
                "Retrieved and normalized %d evidence items for query: '%s'",
                len(normalized_evidence),
                query,
            )
            return normalized_evidence

        finally:
            if not client_provided:
                await client.aclose()

    async def retrieve_evidence_for_claim(self, claim: ExtractedClaim) -> List[EvidenceItem]:
        """Generates query and retrieves evidence for an individual claim."""
        query = SearchQueryGenerator.generate_query(claim)
        return await self.search(query=query, claim=claim)

    async def retrieve_evidence_for_claims(
        self,
        claims: List[ExtractedClaim],
    ) -> Dict[str, List[EvidenceItem]]:
        """
        Retrieves evidence for multiple claims concurrently with bounded concurrency.
        """
        if not claims:
            return {}

        async def _fetch(claim: ExtractedClaim):
            evidence = await self.retrieve_evidence_for_claim(claim)
            return claim.claim_id, evidence

        results = await asyncio.gather(*[_fetch(c) for c in claims])
        return {claim_id: evidence for claim_id, evidence in results}
