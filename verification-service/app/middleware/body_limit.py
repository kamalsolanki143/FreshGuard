"""Request body size limit middleware.

Rejects HTTP requests whose body size exceeds a configurable maximum before the
body is fully read, protecting the service from memory-exhaustion attacks caused
by oversized payloads.

Design notes:
- Checks ``Content-Length`` header first (cheapest path, no body buffering).
- For requests without Content-Length, streams the body and counts bytes.
- Returns a standard FreshGuard APIError JSON envelope with HTTP 413.
- Implemented as a pure ASGI middleware so it runs before any FastAPI routing
  or Pydantic parsing overhead.
"""

import json
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

_413_BODY = json.dumps(
    {
        "code": "REQUEST_TOO_LARGE",
        "message": "Request body exceeds the maximum allowed size.",
        "error": "Request body exceeds the maximum allowed size.",
        "request_id": "unknown",
        "retryable": False,
        "details": {},
    }
).encode("utf-8")

_413_HEADERS = [
    (b"content-type", b"application/json"),
    (b"content-length", str(len(_413_BODY)).encode("ascii")),
]


class RequestBodySizeLimitMiddleware:
    """ASGI middleware enforcing a maximum HTTP request body size.

    Args:
        app: The inner ASGI application.
        max_bytes: Maximum permitted body size in bytes (inclusive).
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Pass through WebSocket and lifespan scopes unchanged
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Fast path: reject based on Content-Length header alone
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = 0
            if declared_size > self.max_bytes:
                await self._send_413(send)
                return

        # Slow path: stream and count for requests without Content-Length
        total_bytes = 0
        body_chunks: list[bytes] = []
        body_too_large = False

        async def limited_receive() -> dict:
            nonlocal total_bytes, body_too_large
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                total_bytes += len(chunk)
                if total_bytes > self.max_bytes:
                    body_too_large = True
                    # Return an empty body-complete message so inner app doesn't hang
                    return {"type": "http.request", "body": b"", "more_body": False}
                body_chunks.append(chunk)
            return message

        # Let the inner application run; it will read the body via limited_receive
        # We wrap send to intercept responses only if we detect oversized body
        response_started = False

        async def intercepting_send(message: dict) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        # We cannot defer body-too-large detection cleanly without buffering in
        # the streaming path, so we eagerly check by pre-reading with a sentinel.
        # For the streaming slow path, inject our limited receive and check after.
        if content_length is None:
            # Pre-drain the body ourselves to check the limit before routing
            async def _drain() -> bytes:
                nonlocal total_bytes
                body = b""
                async for chunk in request.stream():
                    body += chunk
                    total_bytes += len(chunk)
                    if total_bytes > self.max_bytes:
                        return b""  # oversized sentinel
                return body

            full_body = await _drain()
            if total_bytes > self.max_bytes:
                await self._send_413(send)
                return

            # Reconstruct a synthetic receive that replays the already-read body
            body_sent = False

            async def replay_receive() -> dict:
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": full_body, "more_body": False}
                return {"type": "http.disconnect"}

            await self.app(scope, replay_receive, send)
        else:
            await self.app(scope, receive, send)

    @staticmethod
    async def _send_413(send: Send) -> None:
        """Sends a minimal HTTP 413 response with a JSON APIError body."""
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": _413_HEADERS,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": _413_BODY,
                "more_body": False,
            }
        )
