"""Correlates every request's log lines and produces one structured access
log entry per request.

core/logging.py already wires a `structlog.contextvars.merge_contextvars`
processor into every logger — without something binding to it per request,
that processor has nothing to merge. This middleware is what actually does
that: it binds `request_id` (from `X-Request-ID`, or a fresh one), `method`,
and `path` for the life of the request, so every log line emitted anywhere
during that request — including from deep inside chunking/embedding
helpers, not just the route handler — carries them automatically.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id, method=request.method, path=request.url.path
        )
        start = time.monotonic()
        try:
            response = await call_next(request)
            duration_ms = round((time.monotonic() - start) * 1000, 2)
            logger.info("http.request", status_code=response.status_code, duration_ms=duration_ms)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.monotonic() - start) * 1000, 2)
            logger.exception("http.request", status_code=500, duration_ms=duration_ms)
            raise
        finally:
            # Cleared only after logging above, on both paths — clearing
            # first would strip request_id/method/path from the very log
            # line this middleware exists to produce.
            structlog.contextvars.clear_contextvars()
