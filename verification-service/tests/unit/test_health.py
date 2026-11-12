import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test that the /health endpoint returns 200 and matches the required contract."""
    response = await async_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "freshguard-verification"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_not_found_endpoint(async_client: AsyncClient):
    """Test 404 behavior for unknown paths."""
    response = await async_client.get("/non-existent")
    assert response.status_code == 404
