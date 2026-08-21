"""
Rate limiter singleton using slowapi (wraps the `limits` library).

Usage in route handlers:

    from app.core.limiter import limiter

    @router.post("/login")
    @limiter.limit("5/minute")
    def login(request: Request, payload: LoginRequest, ...):
        ...

The `request: Request` parameter must be present in the handler signature
for slowapi to identify the client IP correctly.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
