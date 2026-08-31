import json
from asyncio import sleep
from datetime import datetime
from uuid import UUID

from app.db.cache import CacheKeys
from app.db.engine import async_session_maker
from app.models.schedule import PWAInstalls
from app.utils import get_logger, redis_client, send_tg_alert
from redis import asyncio as aioredis
from sqlalchemy import update

logger = get_logger("Tracker scheduler")


async def flush_activity_to_db():
    # 1. Проверяем, не остался ли зависший хэш с прошлого раза (если БД падала)
    raw_updates = await redis_client.hgetall(CacheKeys.activity_tasks_processed)

    # 2. Если зависшего хэша нет, берем новую порцию данных
    if not raw_updates:
        try:
            await redis_client.rename(
                CacheKeys.activity_tasks, CacheKeys.activity_tasks_processed
            )
            # Сразу вычитываем только что переименованные данные
            raw_updates = await redis_client.hgetall(CacheKeys.activity_tasks_processed)
        except aioredis.ResponseError:
            return  # Новой активности пока нет, просто выходим

    if not raw_updates:
        return

    update_data = []
    for device_id_bytes, payload_bytes in raw_updates.items():
        device_id = device_id_bytes.decode()  # type: ignore
        payload = json.loads(payload_bytes.decode())  # type: ignore

        update_data.append(
            {
                "device_id": UUID(device_id),
                "last_activity": datetime.fromisoformat(payload["last_activity"]),
                "ip_hash": payload.get("ip_hash", "Unknown"),
            }
        )

    if not update_data:
        return

    # 3. Безопасное открытие сессии для фоновой таски
    async with async_session_maker() as session:
        # SQLAlchemy 2.0 executemany (одна транзакция)
        stmt = update(PWAInstalls)
        await session.execute(stmt, update_data)
        await session.commit()

    await redis_client.delete(CacheKeys.activity_tasks_processed)


async def tracker_main_loop():
    logger.info("Запуск Tracker scheduler...")
    while True:
        try:
            await flush_activity_to_db()
        except Exception as e:
            logger.error(f"Ошибка в Tracker scheduler: {e!s}")
            await send_tg_alert(
                "Tracker scheduler",
                "ERROR",
                "Сбой при записи активности",
                e.__class__.__name__,
            )
        # 180 секунд — отличный тайминг для батчинга аналитики
        await sleep(180)
