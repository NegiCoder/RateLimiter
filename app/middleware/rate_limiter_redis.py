from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.services.token_bucket_redis import allow_request_redis
from app.core.config import RATE_LIMIT_CAPACITY, RATE_LIMIT_REFILL_RATE
from app.utils.client import get_client_id

EXCLUDED_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/health", "/favicon.ico"}

class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (
            request.url.path in EXCLUDED_PATHS
            or request.url.path.startswith("/debug")
            or request.url.path.startswith("/assets")
        ):
            return await call_next(request)

        client_id = get_client_id(request)

        try:
            allowed, tokens = allow_request_redis(
                client_id=client_id,
                capacity=RATE_LIMIT_CAPACITY,
                refill_rate=RATE_LIMIT_REFILL_RATE
            )
        except Exception:
            # Fail open: if Redis is unavailable, keep the API reachable.
            allowed = True
            tokens = RATE_LIMIT_CAPACITY

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
            response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_CAPACITY)
            response.headers["X-RateLimit-Remaining"] = str(max(0, int(tokens)))
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_CAPACITY)
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(tokens)))
        return response