import logging

import redis

from app.core.config import REDIS_URL

logger = logging.getLogger(__name__)


def _build_client(url: str):
    """Create Redis client; return None if URL is missing or invalid."""
    if not url or not url.startswith(("redis://", "rediss://", "unix://")):
        logger.warning("Invalid or missing REDIS_URL — rate limiter will fail open")
        return None
    try:
        return redis.from_url(url, decode_responses=True)
    except Exception as exc:
        logger.warning("Could not connect to Redis: %s", exc)
        return None


# ponytail: module-level client; None when REDIS_URL is wrong — middleware fail-opens
redis_client = _build_client(REDIS_URL)
