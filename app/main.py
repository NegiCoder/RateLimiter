from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.middleware.rate_limiter_redis import RateLimiterMiddleware
from app.core.redis import redis_client
from app.core.config import RATE_LIMIT_CAPACITY, RATE_LIMIT_REFILL_RATE
from app.utils.client import get_client_id

app = FastAPI(title="Rate Limiter Service")
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Middleware (REAL LOGIC)
app.add_middleware(RateLimiterMiddleware)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")

# Actual test endpoint (goes through middleware)
@app.get("/test")
def test():
    return {"message": "Request allowed"}

@app.get("/health")
def health():
    try:
        redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": redis_ok,
        "capacity": RATE_LIMIT_CAPACITY,
        "refill_rate": RATE_LIMIT_REFILL_RATE,
    }

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


@app.get("/debug/me")
def get_my_bucket(request: Request):
    client_id = get_client_id(request)
    key = f"rate_limiter:{client_id}"
    return {
        "client_id": client_id,
        "bucket": redis_client.hgetall(key),
        "ttl": redis_client.ttl(key),
    }


@app.post("/debug/reset")
def reset_my_bucket(request: Request):
    client_id = get_client_id(request)
    deleted = redis_client.delete(f"rate_limiter:{client_id}")
    return {"client_id": client_id, "deleted": bool(deleted)}