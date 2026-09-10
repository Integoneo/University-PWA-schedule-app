from collections.abc import AsyncIterator
import redis.asyncio as aioredis
from app.db.config import settings


redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


class CacheKeys:
    # Статические ключи (можно добавить тайп-хинтинг для надежности)
    configs: str = "pwa:system:config"
    institutes: str = "pwa:users:institutes"
    teachers: str = "pwa:users:teachers"
    install_rate_limit: str = "pwa:system:ip_stats"
    activity_tasks: str = "pwa:system:pwa_updates"
    activity_tasks_processed: str = "pwa:system:pwa_updates_process"

    # Динамический ключ
    @staticmethod
    def group(group_id: int) -> str:
        """Ключ для расписания конкретной группы"""
        return f"pwa:lessons:group_{group_id}"

    @staticmethod
    def one_teacher(teacher_id: int) -> str:
        return f"pwa:teachers:teacher_{teacher_id}"


async def get_redis_session() -> AsyncIterator[aioredis.Redis]:
    """
    Функция для асинхронного подключения к Redis
    """
    redis_session = aioredis.Redis(connection_pool=redis_pool)

    try:
        yield redis_session
    finally:
        await redis_session.close()
