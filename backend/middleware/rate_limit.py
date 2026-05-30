"""Rate limiting middleware — per-IP request throttling."""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.

    Default: 100 requests per minute per IP.
    Configurable via RATE_LIMIT env var (requests per minute).
    """

    def __init__(self, app, rate_per_minute: int = 100):
        super().__init__(app)
        self.rate_per_minute = rate_per_minute
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = now - 60  # 1-minute sliding window

        # Clean old entries
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if ts > window
        ]

        if len(self.requests[client_ip]) >= self.rate_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Too many requests. Limit: {self.rate_per_minute}/minute.",
                },
                headers={"Retry-After": "60"},
            )

        self.requests[client_ip].append(now)
        return await call_next(request)
