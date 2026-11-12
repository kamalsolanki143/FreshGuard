from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_app_settings
from app.config import Settings
from app.database.database import get_db_session

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
async def health_check(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """
    Returns the health status, service identifier, and version of FreshGuard.

    This is a **liveness** probe: it confirms the process is alive and the
    configuration is loaded. It does NOT verify database connectivity.
    """
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
    )


@router.get(
    "/health/ready",
    summary="Service Readiness Check",
    responses={
        200: {"description": "Service is ready to handle requests"},
        503: {"description": "Service is not ready — database is unreachable"},
    },
)
async def readiness_check(
    settings: Settings = Depends(get_app_settings),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Verifies that the service is fully ready to handle requests by confirming
    database connectivity via a lightweight ``SELECT 1`` query.

    This is a **readiness** probe suitable for container orchestrators (Kubernetes,
    Cloud Run, Render). It returns HTTP 200 when ready and HTTP 503 when the
    database is unreachable, allowing the platform to route traffic away from
    unhealthy instances.

    The existing ``GET /health`` liveness contract is not affected.
    """
    try:
        await session.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "service": settings.SERVICE_NAME,
                "database": "ok",
            },
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.SERVICE_NAME,
                "database": "unreachable",
            },
        )
