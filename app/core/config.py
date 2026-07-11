import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

RATE_LIMIT_CAPACITY = int(os.getenv("RATE_LIMIT_CAPACITY", 10))
RATE_LIMIT_REFILL_RATE = float(os.getenv("RATE_LIMIT_REFILL_RATE", 1))

