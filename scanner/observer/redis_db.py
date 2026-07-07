import redis.asyncio as aioredis

REDIS_URL = "redis://localhost:6379/0"

redis_pool = aioredis.Redis.from_url(REDIS_URL, decode_responses=True)
