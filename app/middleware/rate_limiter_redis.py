from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.services.token_bucket_redis import allow_request_redis
from app.core.config import RATE_LIMIT_CAPACITY, RATE_LIMIT_REFILL_RATE

EXCLUDED_PATHS = {"/docs", "/openapi.json", "/redoc"}

class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXCLUDED_PATHS or request.url.path.startswith("/debug"):
            return await call_next(request)

        xff = request.headers.get("x-forwarded-for")
        client_id = xff.split(",")[0].strip() if xff else request.client.host

        # When deployed behind a proxy, request.client.host returns the proxy’s IP, so we use X-Forwarded-For to extract the actual client IP for accurate rate limiting.

        try:
            allowed, tokens = allow_request_redis(
                client_id=client_id,
                capacity=RATE_LIMIT_CAPACITY,
                refill_rate=RATE_LIMIT_REFILL_RATE
            )
        except Exception:
            # Redis failure fallback
            allowed = True # fail open
            tokens = RATE_LIMIT_CAPACITY
            # If Redis fails: 
              # rate limiter is skipped
              # every request is allowed

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
            response.headers["X-RateLimit-Limit"] = "10"
            response.headers["X-RateLimit-Remaining"] = str(max(0, int(tokens)))
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(tokens)))
        return response