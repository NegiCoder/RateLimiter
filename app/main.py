from fastapi import FastAPI

from app.core.database import SessionLocal
from app.models.rate_limiter import RateLimiter
from datetime import datetime, timezone

from app.middleware.rate_limiter_redis import RateLimiterMiddleware

from app.core.redis import redis_client

app = FastAPI(title="Rate Limiter Service")

# Middleware (REAL LOGIC)
app.add_middleware(RateLimiterMiddleware)

# Actual test endpoint (goes through middleware)
@app.get("/test")
def test():
    return {"message": "Request allowed"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug/redis-ping")
def redis_ping():
    return {"ping": redis_client.ping()}

@app.get("/debug/redis-bucket/{client_id}")
def get_redis_bucket(client_id: str):
    key = f"rate_limiter:{client_id}"
    bucket = redis_client.hgetall(key)
    ttl = redis_client.ttl(key)

    if not bucket:
        return {"message": "Bucket not found"}

    return {
        "client_id": client_id,
        "bucket": bucket,
        "ttl": ttl
    }