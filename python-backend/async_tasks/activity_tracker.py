from hashlib import md5
import json
from asyncio import sleep
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm.util import _is_mapped_annotation
from sqlmodel import select


from app.db.cache import CacheKeys
from app.db.engine import async_session_maker
from app.models.schedule import PWAInstalls
from app.utils import get_logger, redis_client, send_tg_alert
from redis import asyncio as aioredis
from sqlalchemy import update

logger = get_logger("Tracker scheduler")


default_unknown_hash = md5("Unknown".encode()).hexdigest()[:16]


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
    ids_set = set()
    for device_id_bytes, payload_bytes in raw_updates.items():
        device_id = device_id_bytes.decode()  # type: ignore
        payload = json.loads(payload_bytes.decode())  # type: ignore

        # Беру из хэша все device_id которые являются UUID
        try:
            device_id = UUID(device_id)
            ids_set.add(device_id)
        except Exception:  # Pyright: ignore
            # Если пришел не UUID - скип
            continue

        ip_hash = payload.get("ip_hash", default_unknown_hash)
        update_data.append(
            {
                "device_id": device_id,
                "last_activity": datetime.fromisoformat(payload["last_activity"]),
                "ip_hash": ip_hash,
            }
        )

    # Если нет валидных, просто удаляем мусор и дропаем функцию
    if not update_data or not ids_set:
        await redis_client.delete(CacheKeys.activity_tasks_processed)
        return

    # 3. Безопасное открытие сессии для фоновой таски
    async with async_session_maker() as session:
        # Беру из базы данных все id которые есть в очереди таски
        stmt = select(PWAInstalls.device_id).where(PWAInstalls.device_id.in_(ids_set))
        # Выполняю этот запрос и сразу получаю UUID
        existing_ids = set((await session.scalars(stmt)).all())

        # Если нет валидных, просто удаляем мусор и дропаем функцию
        if not existing_ids:
            await redis_client.delete(CacheKeys.activity_tasks_processed)
            return

        trusted_data = []
        # Забираю обьекты которые подходят для базы
        for id_item in update_data:
            if id_item["device_id"] in existing_ids:
                trusted_data.append(id_item)

        stmt = update(PWAInstalls)
        await session.execute(stmt, trusted_data)
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
