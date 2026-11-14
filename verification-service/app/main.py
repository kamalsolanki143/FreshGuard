from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import validate_auth_config
from app.api.routes import health, verifications
from app.config import get_settings
from app.database.database import get_engine, init_db
from app.middleware.body_limit import RequestBodySizeLimitMiddleware
from app.utils.exceptions import FreshGuardException
from app.utils.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info(
        "Starting %s (v%s) in %s mode",
        settings.SERVICE_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )

    # Validate authentication configuration before accepting traffic.
    # Raises ConfigurationError (aborting startup) when API_AUTH_MODE=enforce
    # but VERIFICATION_SERVICE_API_KEY is not configured.
    try:
        validate_auth_config(settings)
    except Exception as auth_cfg_err:
        logger.critical(
            "Authentication configuration check failed: %s — startup aborted.",
            str(auth_cfg_err),
        )
        raise

    # Initialize database tables on application startup
    try:
        await init_db()
    except Exception as db_init_err:
        logger.warning("Database auto-init on startup encountered: %s", db_init_err)

    yield

    # Clean up database connection pool on shutdown
    try:
        engine = get_engine()
        await engine.dispose()
    except Exception as db_disp_err:
        logger.warning("Database disposal on shutdown encountered: %s", db_disp_err)

    logger.info("Shutting down %s", settings.SERVICE_NAME)


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="FreshGuard Verification Service",
        description="Real-time freshness verification and semantic cache protection layer for LLMs.",
        version=settings.VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"^https://.*\.pages\.dev$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Reject HTTP requests whose body exceeds the configured maximum size.
    # This middleware runs before any FastAPI routing or Pydantic parsing,
    # protecting against memory-exhaustion via oversized payloads.
    app.add_middleware(
        RequestBodySizeLimitMiddleware,
        max_bytes=settings.MAX_REQUEST_BODY_SIZE,
    )

    # Centralized Exception Handlers complying with APIError and shared schemas
    @app.exception_handler(FreshGuardException)
    async def freshguard_exception_handler(request: Request, exc: FreshGuardException) -> JSONResponse:
        logger.warning(
            "FreshGuardException: %s [%s] Path: %s Details: %s",
            exc.message,
            exc.code,
            request.url.path,
            exc.details,
        )
        req_id = request.headers.get("X-Request-ID") or "unknown"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "error": exc.message,
                "request_id": req_id,
                "retryable": exc.status_code in (429, 502, 503, 504),
                "details": exc.details or {},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("Validation error on path %s: %s", request.url.path, exc.errors())
        req_id = request.headers.get("X-Request-ID") or "unknown"
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "error": "Request validation failed.",
                "request_id": req_id,
                "retryable": False,
                "details": {"validation_errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception on %s: %s",
            request.url.path,
            str(exc),
            exc_info=True,
        )
        req_id = request.headers.get("X-Request-ID") or "unknown"
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "error": "An internal server error occurred.",
                "request_id": req_id,
                "retryable": False,
                "details": {},
            },
        )

    # Register Routers
    app.include_router(health.router)
    app.include_router(verifications.router)

    return app


app = create_app()
