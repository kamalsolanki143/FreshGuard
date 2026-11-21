from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
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
    """Validate critical configuration and database schema before accepting traffic."""
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info(
        "Starting %s (v%s) in %s mode",
        settings.SERVICE_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )

    try:
        validate_auth_config(settings)
    except Exception:
        logger.critical("Authentication configuration check failed; startup aborted.", exc_info=True)
        raise

    # A service without initialized tables cannot safely accept verification traffic.
    # Fail startup rather than serving requests that later fail with opaque SQL errors.
    try:
        await init_db()
    except Exception:
        logger.exception("Database initialization failed; refusing to start verification service.")
        raise

    try:
        yield
    finally:
        try:
            await get_engine().dispose()
        except Exception:
            logger.warning("Database engine disposal failed during shutdown.", exc_info=True)
        logger.info("Shutting down %s", settings.SERVICE_NAME)


def create_app() -> FastAPI:
    """Creates and configures the application."""
    settings = get_settings()

    app = FastAPI(
        title="FreshGuard Verification Service",
        description="Real-time freshness verification and semantic cache protection layer for LLMs.",
        version=settings.VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        RequestBodySizeLimitMiddleware,
        max_bytes=settings.MAX_REQUEST_BODY_SIZE,
    )

    @app.exception_handler(FreshGuardException)
    async def freshguard_exception_handler(request: Request, exc: FreshGuardException) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID") or "unknown"
        logger.warning(
            "FreshGuardException request_id=%s code=%s path=%s details=%s",
            request_id,
            exc.code,
            request.url.path,
            exc.details,
        )
        response_headers = {"Retry-After": "60"} if exc.status_code == 429 else None
        return JSONResponse(
            status_code=exc.status_code,
            headers=response_headers,
            content={
                "code": exc.code,
                "message": exc.message,
                "error": exc.message,
                "request_id": request_id,
                "retryable": exc.status_code in (429, 502, 503, 504),
                "details": exc.details or {},
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID") or "unknown"
        message = str(exc.detail) if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": "HTTP_ERROR",
                "message": message,
                "request_id": request_id,
                "retryable": exc.status_code in (429, 502, 503, 504),
                "details": {},
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID") or "unknown"
        logger.warning(
            "Validation error request_id=%s path=%s errors=%s",
            request_id,
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "error": "Request validation failed.",
                "request_id": request_id,
                "retryable": False,
                "details": {"validation_errors": jsonable_encoder(exc.errors())},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID") or "unknown"
        logger.error(
            "Unhandled exception request_id=%s path=%s type=%s",
            request_id,
            request.url.path,
            type(exc).__name__,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "error": "An internal server error occurred.",
                "request_id": request_id,
                "retryable": False,
                "details": {},
            },
        )

    @app.middleware("http")
    async def enforce_verification_content_type(request: Request, call_next):
        if request.method == "POST" and request.url.path.rstrip("/") == "/v1/verifications":
            content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                request_id = request.headers.get("X-Request-ID") or "unknown"
                return JSONResponse(
                    status_code=415,
                    content={
                        "code": "UNSUPPORTED_MEDIA_TYPE",
                        "message": "Content-Type must be application/json.",
                        "request_id": request_id,
                        "retryable": False,
                        "details": {"received_content_type": content_type or None},
                    },
                )
        return await call_next(request)

    app.include_router(health.router)
    app.include_router(verifications.router)
    return app


app = create_app()
