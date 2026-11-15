import pytest
from starlette.requests import Request

from app.api.dependencies import _rate_limit_buckets, enforce_rate_limit
from app.config import Settings
from app.utils.exceptions import FreshGuardException


def make_request(client_ip: str) -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/v1/verifications",
        "headers": [],
        "client": (client_ip, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    })


@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_configured_window_quota():
    client_ip = "198.51.100.77"
    _rate_limit_buckets.pop(client_ip, None)
    settings = Settings(RATE_LIMIT_ENABLED=True, RATE_LIMIT_REQUESTS_PER_MINUTE=2)

    await enforce_rate_limit(make_request(client_ip), settings)
    await enforce_rate_limit(make_request(client_ip), settings)

    with pytest.raises(FreshGuardException) as error:
        await enforce_rate_limit(make_request(client_ip), settings)

    assert error.value.status_code == 429
    assert error.value.code == "RATE_LIMITED"
    _rate_limit_buckets.pop(client_ip, None)


@pytest.mark.asyncio
async def test_rate_limit_can_be_disabled_for_local_tests():
    settings = Settings(RATE_LIMIT_ENABLED=False)
    await enforce_rate_limit(make_request("198.51.100.78"), settings)
