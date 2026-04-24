"""Pure-ASGI request-context middleware.

This MUST remain a pure-ASGI class (``__call__(scope, receive, send)``) and
MUST NOT be rewritten on top of starlette's higher-level base-http-middleware
abstraction. Per RESEARCH.md § P1 / research callout #4: that abstraction runs
the downstream app in a separate ``anyio`` task and copies the contextvar
state, which means any ``structlog.contextvars.bind_contextvars(...)`` done
inside the middleware is invisible to the request handler. The pure-ASGI form
below sets the contextvar in the SAME task that runs the handler, so
``merge_contextvars`` in the structlog processor chain sees ``request_id``
in every log line emitted during the request.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from app.util.ids import new_uuid7

_log = structlog.get_logger("app.http")


class RequestContextMiddleware:
    """Bind ``request_id`` contextvar, echo header, emit one access log.

    Flow per request:
        1. Read ``X-Request-ID`` header (lowercased via ASGI convention).
        2. If absent, generate a UUIDv7 (lex-sortable) as the request_id.
        3. ``clear_contextvars()`` then ``bind_contextvars(request_id=...)``.
        4. Wrap ``send`` to append ``x-request-id`` to the response headers
           and capture the final status code.
        5. In ``finally``, emit a single ``"request"`` log event with
           method / path / status / duration_ms, then clear contextvars so
           the next request starts clean (contextvars are task-local; this
           defends against any server runtime that reuses tasks).
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            # Pass through lifespan, websocket, etc. untouched.
            await self.app(scope, receive, send)
            return

        hdrs = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        rid = hdrs.get("x-request-id") or str(new_uuid7())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid)

        start = time.perf_counter()
        status_holder: dict[str, int] = {"status": 0}

        async def send_wrapper(msg: dict) -> None:
            if msg["type"] == "http.response.start":
                status_holder["status"] = msg.get("status", 0)
                headers = list(msg.get("headers", []))
                headers.append((b"x-request-id", rid.encode()))
                msg["headers"] = headers
            await send(msg)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            _log.info(
                "request",
                method=scope.get("method"),
                path=scope.get("path"),
                status=status_holder["status"],
                duration_ms=duration_ms,
            )
            structlog.contextvars.clear_contextvars()
