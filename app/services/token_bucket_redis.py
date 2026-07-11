import time
from app.core.redis import redis_client

LUA_TOKEN_BUCKET = """
local key = KEYS[1] 

local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local bucket = redis.call("HGETALL", key)

local tokens
local last_refill_ts
local stored_capacity
local stored_refill_rate

if next(bucket) == nil then
    tokens = capacity
    last_refill_ts = now
    stored_capacity = capacity
    stored_refill_rate = refill_rate
else
    local data = {}
    for i = 1, #bucket, 2 do
        data[bucket[i]] = bucket[i + 1]
    end

    tokens = tonumber(data["tokens"])
    last_refill_ts = tonumber(data["last_refill_ts"])
    stored_capacity = tonumber(data["capacity"])
    stored_refill_rate = tonumber(data["refill_rate"])

    local elapsed = now - last_refill_ts
    local refill = elapsed * stored_refill_rate
    tokens = math.min(stored_capacity, tokens + refill)
end

local allowed = 0

if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
end

redis.call("HSET", key,
    "tokens", tokens,
    "last_refill_ts", now,
    "capacity", capacity,
    "refill_rate", refill_rate
)

redis.call("EXPIRE", key, ttl)

return {allowed,tokens}
"""

def allow_request_redis(client_id: str, capacity: int, refill_rate: float) -> tuple[bool, float]:
    key = f"rate_limiter:{client_id}"
    now = time.time()
    ttl = 600

    allowed, tokens = redis_client.eval(
        LUA_TOKEN_BUCKET,
        1,
        key,
        capacity,
        refill_rate,
        now,
        ttl,
    )
    # Redis may return Lua numbers as strings when decode_responses=True.
    return int(allowed) == 1, float(tokens)