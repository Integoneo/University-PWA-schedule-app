from collections.abc import AsyncIterator
import redis.asyncio as aioredis
from app.db.config import settings
from typing import Any


redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)

cache_keys = {
    "configs": "pwa:system:config",  # Ключ для системых конфигов PWA приложения
    "institutes": "pwa:users:institutes",  # Ключ для институтов и соотвествующих им группам
    "group": lambda id: (
        f"pwa:lessons:group_{id}"
    ),  # Ключ для расписания конкретной группы
}


class CacheKeys:
    # Статические ключи (можно добавить тайп-хинтинг для надежности)
    configs: str = "pwa:system:config"
    institutes: str = "pwa:users:institutes"

    # Динамический ключ
    @staticmethod
    def group(group_id: Any) -> str:

        try:
            group_id = int(group_id)
        except Exception as e:
            group_id = -1
        """Ключ для расписания конкретной группы"""
        return f"pwa:lessons:group_{group_id}"


# cache_key = "pwa:system:config"
# cached_institutes_key = "pwa:users:institutes"
# cache_key = f"pwa:lessons:group_{group_id}"


async def get_redis_session() -> AsyncIterator[aioredis.Redis]:
    """
    Функция для асинхронного подключения к Redis
    """
    redis_session = aioredis.Redis(connection_pool=redis_pool)

    try:
        yield redis_session
    finally:
        await redis_session.close()
