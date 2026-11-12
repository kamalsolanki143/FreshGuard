"""Unit tests for GeminiLLMProvider and factory routing.

Validates:
1. Missing API key handling (raises ConfigurationError).
2. Successful structured generation with ClaimExtractionResponse.
3. Successful structured generation with LLMVerdictAssessment.
4. Markdown code fence stripping (```json ... ```).
5. Malformed non-JSON output handling (raises ExtractionError).
6. Pydantic schema validation failure handling (raises ExtractionError).
7. Rate limit (HTTP 429) backoff retry and clean ExtractionError mapping.
8. Service error (HTTP 503) backoff retry and clean ExtractionError mapping.
9. Generic client error (HTTP 400) handling.
10. Request timeout (asyncio.TimeoutError) handling.
11. Factory routing (get_llm_provider) for gemini, openai, and mock.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import BaseModel

from app.config import Settings
from app.schemas.claims import ClaimCategory, ClaimExtractionResponse, ClaimVerdict, ExtractedClaim
from app.services.llm_provider import (
    GeminiLLMProvider,
    MockLLMProvider,
    OpenAILLMProvider,
    get_llm_provider,
)
from app.services.verdict_engine import LLMVerdictAssessment
from app.utils.exceptions import ConfigurationError, ExtractionError
from google.genai import errors


class MockGeminiResponse:
    """Mock Gemini API response object."""
    def __init__(self, text: str):
        self.text = text


class TestGeminiLLMProviderInit:
    """Tests initialization and configuration validation."""

    def test_missing_api_key_raises_configuration_error(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="",
            LLM_API_KEY="",
            _env_file=None,
        )
        with pytest.raises(ConfigurationError) as exc_info:
            GeminiLLMProvider(settings=settings)
        assert "GEMINI_API_KEY" in exc_info.value.message

    def test_fallback_to_llm_api_key_if_gemini_api_key_unset(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="",
            LLM_API_KEY="fallback-key-123",
            _env_file=None,
        )
        mock_client = MagicMock()
        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        assert provider.api_key == "fallback-key-123"
        assert provider.model == "gemini-2.5-flash"

    def test_custom_model_configuration(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            GEMINI_MODEL="gemini-2.5-flash-lite",
            _env_file=None,
        )
        mock_client = MagicMock()
        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        assert provider.model == "gemini-2.5-flash-lite"


class TestGeminiStructuredGeneration:
    """Tests structured output generation across schemas and error states."""

    @pytest.mark.asyncio
    async def test_successful_claim_extraction_response(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            _env_file=None,
        )
        json_output = (
            '{"claims": [{"claim_id": "c1", "text": "Python 3.12 is released", '
            '"category": "software_version", "entity": "Python", "attribute": "version", "time_sensitive": true}]}'
        )
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MockGeminiResponse(text=json_output)
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        result = await provider.generate_structured(
            system_prompt="Extract claims",
            user_text="Python 3.12 is released",
            response_model=ClaimExtractionResponse,
        )

        assert isinstance(result, ClaimExtractionResponse)
        assert len(result.claims) == 1
        assert result.claims[0].claim_id == "c1"
        assert result.claims[0].category == ClaimCategory.SOFTWARE_VERSION
        assert result.claims[0].entity == "Python"

    @pytest.mark.asyncio
    async def test_successful_verdict_assessment_response(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            _env_file=None,
        )
        json_output = (
            '{"verdict": "supported", "confidence": 0.95, "reason": "Confirmed by docs", '
            '"supporting_evidence_ids": ["ev_1"], "contradicting_evidence_ids": [], "corrected_value": null}'
        )
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MockGeminiResponse(text=json_output)
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        result = await provider.generate_structured(
            system_prompt="Judge claim",
            user_text="Claim and evidence text",
            response_model=LLMVerdictAssessment,
        )

        assert isinstance(result, LLMVerdictAssessment)
        assert result.verdict == ClaimVerdict.SUPPORTED
        assert result.confidence == 0.95
        assert result.supporting_evidence_ids == ["ev_1"]

    @pytest.mark.asyncio
    async def test_markdown_code_fences_stripped(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            _env_file=None,
        )
        wrapped_json = "```json\n" + '{"claims": []}' + "\n```"
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MockGeminiResponse(text=wrapped_json)
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        result = await provider.generate_structured(
            system_prompt="Extract claims",
            user_text="No facts here",
            response_model=ClaimExtractionResponse,
        )

        assert isinstance(result, ClaimExtractionResponse)
        assert result.claims == []

    @pytest.mark.asyncio
    async def test_malformed_non_json_raises_extraction_error(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            _env_file=None,
        )
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MockGeminiResponse(text="Sorry, I cannot process this.")
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        with pytest.raises(ExtractionError) as exc_info:
            await provider.generate_structured(
                system_prompt="Extract claims",
                user_text="Invalid input",
                response_model=ClaimExtractionResponse,
            )
        assert "non-JSON content" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_schema_mismatch_raises_extraction_error(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            _env_file=None,
        )
        # Missing required 'confidence' and 'reason' fields
        invalid_schema_json = '{"verdict": "unknown_verdict"}'
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MockGeminiResponse(text=invalid_schema_json)
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        with pytest.raises(ExtractionError) as exc_info:
            await provider.generate_structured(
                system_prompt="Judge claim",
                user_text="Text",
                response_model=LLMVerdictAssessment,
            )
        assert "schema validation" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_rate_limit_429_exhaustion_raises_retryable_extraction_error(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            LLM_MAX_RETRIES=1,
            _env_file=None,
        )
        mock_client = MagicMock()
        # Mock APIError with status 429
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=errors.APIError(429, {"error": {"message": "Resource exhausted"}})
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        with pytest.raises(ExtractionError) as exc_info:
            await provider.generate_structured(
                system_prompt="Extract",
                user_text="Text",
                response_model=ClaimExtractionResponse,
            )
        assert "rate limit exceeded" in exc_info.value.message
        assert exc_info.value.details.get("retryable") is True
        assert exc_info.value.details.get("status_code") == 429

    @pytest.mark.asyncio
    async def test_service_error_503_raises_retryable_extraction_error(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            LLM_MAX_RETRIES=1,
            _env_file=None,
        )
        mock_client = MagicMock()
        # Mock APIError with status 503
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=errors.APIError(503, {"error": {"message": "Service unavailable"}})
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        with pytest.raises(ExtractionError) as exc_info:
            await provider.generate_structured(
                system_prompt="Extract",
                user_text="Text",
                response_model=ClaimExtractionResponse,
            )
        assert "temporarily unavailable" in exc_info.value.message
        assert exc_info.value.details.get("retryable") is True
        assert exc_info.value.details.get("status_code") == 503

    @pytest.mark.asyncio
    async def test_client_error_400_raises_non_retryable_extraction_error(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            LLM_MAX_RETRIES=1,
            _env_file=None,
        )
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=errors.APIError(400, {"error": {"message": "Bad request"}})
        )

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        with pytest.raises(ExtractionError) as exc_info:
            await provider.generate_structured(
                system_prompt="Extract",
                user_text="Text",
                response_model=ClaimExtractionResponse,
            )
        assert "HTTP 400" in exc_info.value.message
        assert exc_info.value.details.get("retryable") is not True

    @pytest.mark.asyncio
    async def test_timeout_raises_extraction_error(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            LLM_TIMEOUT_SECONDS=0.01,
            _env_file=None,
        )

        async def slow_call(*args, **kwargs):
            await asyncio.sleep(0.1)
            return MockGeminiResponse(text='{"claims": []}')

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(side_effect=slow_call)

        provider = GeminiLLMProvider(settings=settings, client=mock_client)
        with pytest.raises(ExtractionError) as exc_info:
            await provider.generate_structured(
                system_prompt="Extract",
                user_text="Text",
                response_model=ClaimExtractionResponse,
            )
        assert "timed out" in exc_info.value.message
        assert exc_info.value.details.get("timeout") == 0.01


class TestLLMProviderFactoryRouting:
    """Verifies factory routing for mock, openai, and gemini providers."""

    def test_mock_provider_routing(self):
        settings = Settings(LLM_PROVIDER="mock", _env_file=None)
        provider = get_llm_provider(settings=settings)
        assert isinstance(provider, MockLLMProvider)

    def test_openai_provider_routing(self):
        settings = Settings(
            LLM_PROVIDER="openai",
            LLM_API_KEY="sk-fake-test",
            _env_file=None,
        )
        provider = get_llm_provider(settings=settings)
        assert isinstance(provider, OpenAILLMProvider)

    def test_gemini_provider_routing(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="AIzaFakeTestKey",
            _env_file=None,
        )
        with patch("google.genai.Client"):
            provider = get_llm_provider(settings=settings)
        assert isinstance(provider, GeminiLLMProvider)

    def test_unrecognized_provider_defaults_to_mock(self):
        settings = Settings(LLM_PROVIDER="unknown-provider", _env_file=None)
        provider = get_llm_provider(settings=settings)
        assert isinstance(provider, MockLLMProvider)
