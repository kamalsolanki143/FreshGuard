from abc import ABC, abstractmethod
import asyncio
import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.utils.exceptions import ConfigurationError, ExtractionError
from app.utils.retry import retry_async

logger = logging.getLogger("freshguard.llm_provider")

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract base adapter for LLM providers."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_text: str,
        response_model: Type[T],
    ) -> T:
        """Generates structured output validated against a Pydantic model."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider for deterministic unit and integration testing.
    Can be configured with custom canned outputs, simulated exceptions, or simulated delays.
    """

    def __init__(
        self,
        canned_response: Optional[Dict[str, Any]] = None,
        raw_text_override: Optional[str] = None,
        simulate_timeout: bool = False,
        simulate_error: Optional[Exception] = None,
        delay_seconds: float = 0.0,
    ):
        self.canned_response = canned_response
        self.raw_text_override = raw_text_override
        self.simulate_timeout = simulate_timeout
        self.simulate_error = simulate_error
        self.delay_seconds = delay_seconds

    async def generate_structured(
        self,
        system_prompt: str,
        user_text: str,
        response_model: Type[T],
    ) -> T:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.simulate_timeout:
            raise ExtractionError(
                message="LLM extraction timed out.",
                details={"provider": "mock", "timeout": True},
            )

        if self.simulate_error:
            raise self.simulate_error

        # If raw text override provided (useful for testing malformed JSON)
        if self.raw_text_override is not None:
            try:
                parsed = json.loads(self.raw_text_override)
            except Exception as e:
                raise ExtractionError(
                    message=f"LLM produced malformed JSON: {str(e)}",
                    details={"raw_output": self.raw_text_override},
                )
            try:
                return response_model.model_validate(parsed)
            except ValidationError as e:
                raise ExtractionError(
                    message="LLM output failed Pydantic schema validation.",
                    details={"validation_errors": e.errors()},
                )

        # If canned response dict provided
        if self.canned_response is not None:
            try:
                return response_model.model_validate(self.canned_response)
            except ValidationError as e:
                raise ExtractionError(
                    message="Mock canned response failed Pydantic validation.",
                    details={"validation_errors": e.errors()},
                )

        # Default heuristic mock behavior when no canned response is passed
        # Provides reasonable default claims for common test strings
        clean_text = user_text.lower()
        mock_claims = []

        if "python 3.12" in clean_text or "python" in clean_text:
            mock_claims.append({
                "claim_id": "claim_001",
                "text": "Python 3.12 is the latest stable version",
                "category": "software_version",
                "entity": "Python",
                "attribute": "latest_version",
                "time_sensitive": True,
            })

        if "$20" in clean_text or "chatgpt plus" in clean_text or "cost" in clean_text:
            mock_claims.append({
                "claim_id": f"claim_00{len(mock_claims) + 1}",
                "text": "ChatGPT Plus costs $20 per month",
                "category": "pricing",
                "entity": "ChatGPT Plus",
                "attribute": "monthly_price",
                "time_sensitive": True,
            })

        if "sundar pichai" in clean_text or "ceo" in clean_text:
            mock_claims.append({
                "claim_id": f"claim_00{len(mock_claims) + 1}",
                "text": "Sundar Pichai is the CEO of Google",
                "category": "leadership",
                "entity": "Google",
                "attribute": "ceo",
                "time_sensitive": True,
            })

        # Check if response_model is for verdict assessment
        if "verdict" in response_model.model_fields:
            lower_user = user_text.lower()
            evidence_part = lower_user
            if "retrieved web evidence" in lower_user:
                evidence_part = lower_user.split("retrieved web evidence", 1)[1]

            if "contradicts" in evidence_part or "superseded" in evidence_part or "python 3.13" in evidence_part:
                return response_model.model_validate({
                    "verdict": "CONTRADICTED",
                    "confidence": 0.95,
                    "reason": "Evidence indicates a newer version or contradictory fact.",
                    "supporting_evidence_ids": [],
                    "contradicting_evidence_ids": ["ev_01", "ev_c1", "ev_02"],
                    "corrected_value": "Python 3.13",
                })
            elif "conflicting" in evidence_part or "conflict" in evidence_part:
                return response_model.model_validate({
                    "verdict": "UNCLEAR",
                    "confidence": 0.40,
                    "reason": "Evidence contains conflicting statements from multiple sources.",
                    "supporting_evidence_ids": [],
                    "contradicting_evidence_ids": [],
                    "corrected_value": None,
                })
            elif "confirms" in evidence_part or "latest stable" in evidence_part or "2.9%" in evidence_part:
                return response_model.model_validate({
                    "verdict": "SUPPORTED",
                    "confidence": 0.92,
                    "reason": "Evidence directly confirms the claim.",
                    "supporting_evidence_ids": ["ev_01", "ev_c1", "ev_c2"],
                    "contradicting_evidence_ids": [],
                    "corrected_value": None,
                })
            else:
                return response_model.model_validate({
                    "verdict": "UNCLEAR",
                    "confidence": 0.50,
                    "reason": "Available evidence is insufficient or inconclusive.",
                    "supporting_evidence_ids": [],
                    "contradicting_evidence_ids": [],
                    "corrected_value": None,
                })


        return response_model.model_validate({"claims": mock_claims})



class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI-compatible LLM provider using async HTTPX with structured output.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        if not self.settings.LLM_API_KEY:
            raise ConfigurationError(
                "LLM_API_KEY is required when using OpenAILLMProvider.",
                details={"provider": self.settings.LLM_PROVIDER},
            )

        self.api_key = self.settings.LLM_API_KEY
        self.base_url = (self.settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.model = self.settings.LLM_MODEL or "gpt-4o-mini"
        self.timeout = self.settings.LLM_TIMEOUT_SECONDS
        self.max_retries = self.settings.LLM_MAX_RETRIES

    @retry_async(exceptions=(httpx.RequestError, httpx.HTTPStatusError), max_retries=2, base_delay=0.5)
    async def _post_chat_completion(self, client: httpx.AsyncClient, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    async def generate_structured(
        self,
        system_prompt: str,
        user_text: str,
        response_model: Type[T],
    ) -> T:
        schema = response_model.model_json_schema()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text to extract claims from:\n\n{user_text}"},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": schema,
                },
            },
            "temperature": 0.0,
        }

        try:
            async with httpx.AsyncClient() as client:
                data = await self._post_chat_completion(client, payload)

            choice = data.get("choices", [{}])[0]
            raw_content = choice.get("message", {}).get("content", "{}")

            try:
                parsed_json = json.loads(raw_content)
            except json.JSONDecodeError as e:
                raise ExtractionError(
                    message=f"LLM produced non-JSON content: {str(e)}",
                    details={"raw_content": raw_content},
                )

            try:
                return response_model.model_validate(parsed_json)
            except ValidationError as e:
                raise ExtractionError(
                    message="LLM output failed Pydantic schema validation.",
                    details={"validation_errors": e.errors(), "parsed_json": parsed_json},
                )

        except httpx.TimeoutException as e:
            raise ExtractionError(
                message=f"LLM request timed out after {self.timeout}s: {str(e)}",
                details={"model": self.model, "timeout": self.timeout},
            )
        except httpx.HTTPStatusError as e:
            raise ExtractionError(
                message=f"LLM API returned HTTP {e.response.status_code}: {e.response.text}",
                details={"status_code": e.response.status_code},
            )
        except httpx.RequestError as e:
            raise ExtractionError(
                message=f"LLM network communication failed: {str(e)}",
                details={"error_type": type(e).__name__},
            )


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini Developer API provider using the official google-genai Python SDK.
    Supports asynchronous structured outputs validated against Pydantic models.
    """

    def __init__(self, settings: Optional[Settings] = None, client: Optional[Any] = None):
        self.settings = settings or get_settings()
        api_key = self.settings.GEMINI_API_KEY or self.settings.LLM_API_KEY
        if not api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY (or LLM_API_KEY) is required when using GeminiLLMProvider.",
                details={"provider": self.settings.LLM_PROVIDER},
            )

        self.api_key = api_key
        self.model = self.settings.GEMINI_MODEL or self.settings.LLM_MODEL or "gemini-2.5-flash"
        self.timeout = self.settings.LLM_TIMEOUT_SECONDS
        self.max_retries = self.settings.LLM_MAX_RETRIES

        if client is not None:
            self.client = client
        else:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)

    async def generate_structured(
        self,
        system_prompt: str,
        user_text: str,
        response_model: Type[T],
    ) -> T:
        from google.genai import errors, types

        schema = response_model.model_json_schema()
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.0,
        )

        attempt = 0
        raw_content = ""
        while True:
            try:
                response = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=self.model,
                        contents=f"Text to analyze:\n\n{user_text}",
                        config=config,
                    ),
                    timeout=self.timeout,
                )
                raw_content = getattr(response, "text", "") or ""
                break
            except errors.APIError as exc:
                status_code = getattr(exc, "code", None)
                if status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    attempt += 1
                    delay = 0.5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient Gemini API error (HTTP %s) on attempt %d/%d. Retrying in %.2fs: %s",
                        status_code,
                        attempt,
                        self.max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                    continue

                if status_code == 429:
                    raise ExtractionError(
                        message=f"Gemini API rate limit exceeded (HTTP 429): {str(exc)}",
                        details={"status_code": 429, "retryable": True, "model": self.model},
                    ) from exc
                elif status_code == 503:
                    raise ExtractionError(
                        message=f"Gemini API service temporarily unavailable (HTTP 503): {str(exc)}",
                        details={"status_code": 503, "retryable": True, "model": self.model},
                    ) from exc
                else:
                    raise ExtractionError(
                        message=f"Gemini API returned error (HTTP {status_code}): {str(exc)}",
                        details={"status_code": status_code, "model": self.model},
                    ) from exc
            except asyncio.TimeoutError as exc:
                raise ExtractionError(
                    message=f"Gemini request timed out after {self.timeout}s: {str(exc)}",
                    details={"model": self.model, "timeout": self.timeout},
                ) from exc
            except Exception as exc:
                if isinstance(exc, ExtractionError):
                    raise
                raise ExtractionError(
                    message=f"Gemini LLM call failed: {str(exc)}",
                    details={"error_type": type(exc).__name__, "model": self.model},
                ) from exc

        # Strip markdown code fences if model wrapped the JSON
        text_to_parse = raw_content.strip()
        if text_to_parse.startswith("```"):
            lines = text_to_parse.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text_to_parse = "\n".join(lines).strip()

        try:
            parsed_json = json.loads(text_to_parse)
        except json.JSONDecodeError as exc:
            raise ExtractionError(
                message=f"Gemini produced non-JSON content: {str(exc)}",
                details={"raw_content": raw_content},
            ) from exc

        try:
            return response_model.model_validate(parsed_json)
        except ValidationError as exc:
            raise ExtractionError(
                message="Gemini output failed Pydantic schema validation.",
                details={"validation_errors": exc.errors(), "parsed_json": parsed_json},
            ) from exc


def get_llm_provider(settings: Optional[Settings] = None) -> BaseLLMProvider:
    """Factory creating the configured LLM provider adapter."""
    s = settings or get_settings()
    provider_name = (s.LLM_PROVIDER or "mock").lower().strip()

    if provider_name == "openai":
        return OpenAILLMProvider(settings=s)
    elif provider_name == "gemini":
        return GeminiLLMProvider(settings=s)
    elif provider_name == "mock":
        return MockLLMProvider()
    else:
        logger.warning("Unrecognized LLM_PROVIDER '%s'. Defaulting to MockLLMProvider.", provider_name)
        return MockLLMProvider()
