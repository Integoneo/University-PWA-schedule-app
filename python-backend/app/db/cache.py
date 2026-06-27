from collections.abc import AsyncIterator
import redis.asyncio as aioredis
from app.db.config import settings


redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis_session() -> AsyncIterator[aioredis.Redis]:
    """
    Функция для асинхронного подключения к Redis
    """
    redis_session = aioredis.Redis(connection_pool=redis_pool)

    try:
        yield redis_session
    finally:
        await redis_session.close()
