from typing import Any, Dict, Optional


class FreshGuardException(Exception):
    """Base exception class for all FreshGuard verification errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class ConfigurationError(FreshGuardException):
    """Raised when configuration is missing or invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            code="CONFIGURATION_ERROR",
            details=details,
        )


class AuthenticationError(FreshGuardException):
    """Raised when a request fails API-key authentication.

    Returns HTTP 401 with a generic message that deliberately avoids revealing
    whether the key was absent, incorrect, or the service is misconfigured.
    The actual key value is never logged or included in ``details``.
    """

    def __init__(
        self,
        message: str = "Missing or invalid API key.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            code="UNAUTHORIZED",
            details=details,
        )


class PrefilterError(FreshGuardException):
    """Raised when rule-based prefiltering fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            code="PREFILTER_ERROR",
            details=details,
        )


class ExtractionError(FreshGuardException):
    """Raised when LLM-powered claim extraction fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=502,
            code="EXTRACTION_ERROR",
            details=details,
        )


class TavilyAPIError(FreshGuardException):
    """Raised when Tavily search API fails or times out."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=502,
            code="TAVILY_API_ERROR",
            details=details,
        )


class VerdictError(FreshGuardException):
    """Raised when verdict evaluation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            code="VERDICT_ERROR",
            details=details,
        )


class VersionValidationError(FreshGuardException):
    """Raised when version comparison encounters invalid inputs."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            code="VERSION_VALIDATION_ERROR",
            details=details,
        )


class PolicyNotFoundError(FreshGuardException):
    """Raised when a requested freshness policy category does not exist."""

    def __init__(self, category: str):
        super().__init__(
            message=f"Freshness policy for category '{category}' was not found.",
            status_code=404,
            code="POLICY_NOT_FOUND",
            details={"category": category},
        )


class DatabaseError(FreshGuardException):
    """Raised when persistence or query fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            code="DATABASE_ERROR",
            details=details,
        )


class NotFoundError(FreshGuardException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=404,
            code="NOT_FOUND",
            details=details,
        )
