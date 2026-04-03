"""
Sliding window rate limiter middleware.
Paper applied: arXiv API Gateway Governance 2025 — rate limiting as a unified API layer concern
- 100 requests per 60-second window per IP
- In-memory store (sufficient for single-instance; Redis would be used in production)
Assumption: Single-server deployment for this assessment.
"""
from fastapi import Request, HTTPException
from collections import defaultdict
from time import time

WINDOW_SECONDS = 60
MAX_REQUESTS   = 100

# ip -> list of request timestamps within the window
_request_log: dict[str, list[float]] = defaultdict(list)


async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    ip  = request.client.host if request.client else "unknown"
    now = time()

    # Evict timestamps outside the window
    _request_log[ip] = [t for t in _request_log[ip] if now - t < WINDOW_SECONDS]

    if len(_request_log[ip]) >= MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded — max {MAX_REQUESTS} requests per minute",
        )

    _request_log[ip].append(now)
    return await call_next(request)
