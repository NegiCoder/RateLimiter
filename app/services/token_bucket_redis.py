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
        ttl
    )
    print(f"Client: {client_id}, Allowed: {allowed}, Tokens left: {tokens}")
    return bool(allowed), tokens

# concurrency-unsafe (causes race conditions) implementation of a token bucket rate limiter using Redis to store the bucket state.
# import time #to get current timestamp
# from app.core.redis import redis_client #your Redis connection (used to store bucket data)

# def allow_request_redis(client_id: str, capacity: int, refill_rate: float) -> bool:
#     key = f"rate_limiter:{client_id}" #Unique Redis key per user
#     now = time.time() #current timestamp in seconds

#     bucket = redis_client.hgetall(key) #Get bucket data (all fields) from Redis (returns dict or empty if not exists) 
#     if not bucket:
#         redis_client.hset(key, mapping={
#             "tokens": capacity - 1, 
#             "last_refill_ts": now,
#             "capacity": capacity,
#             "refill_rate": refill_rate
#         })
#         redis_client.expire(key, 600)
# #The values of capacity and refill_rate are whatever you pass as arguments to the allow_request_redis function for that user/request. 
#         return True #First request, create bucket with capacity-1 tokens and return True

#     tokens = float(bucket["tokens"])
#     last_refill_ts = float(bucket["last_refill_ts"])
#     stored_capacity = float(bucket["capacity"])
#     stored_refill_rate = float(bucket["refill_rate"])

#     elapsed = now - last_refill_ts
#     refill = elapsed * stored_refill_rate
#     tokens = min(stored_capacity, tokens + refill)

#     if tokens < 1:
#         redis_client.hset(key, mapping={
#             "tokens": tokens,
#             "last_refill_ts": now
#         })
#         redis_client.expire(key, 600)
#         return False

#     tokens -= 1

#     redis_client.hset(key, mapping={
#         "tokens": tokens,
#         "last_refill_ts": now
#     })
#     redis_client.expire(key, 600)

#     return True