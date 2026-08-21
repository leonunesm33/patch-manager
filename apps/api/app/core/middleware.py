"""
Request-scoped middleware.

RequestIDMiddleware:
  - Reads X-Request-ID header from the client (useful for tracing) or generates a new UUID.
  - Binds the request_id to structlog's contextvars so every log line within
    the same request automatically includes it.
  - Forwards the request_id back in the response header X-Request-ID.
"""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Clear any previous contextvars from a reused worker and bind the new id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
