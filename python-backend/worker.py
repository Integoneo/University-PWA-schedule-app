import asyncio
import json
from xxhash import xxh64
from pydantic import ValidationError
import redis.asyncio as aioredis

from app.db.engine import get_async_session
from app.db.config import settings

# Импортируем наш модуль
from app.worker_modules.group_lessons.schemas import SchedulePayloadSchema
from app.worker_modules.group_lessons.processor import process_schedule


REDIS = settings.REDIS_URL


async def main_worker_loop():
    print("🎧 Нативный Async Worker запущен и ждет расписания...")
    r = aioredis.from_url(REDIS)
    STREAM_NAME, GROUP_NAME, CONSUMER_NAME = (
        "ready_schedules",
        "python",
        "python-worker",
    )

    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError:
        pass

    try:
        while True:
            try:
                response = await r.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=2000
                )
                if not response:
                    continue

                _, messages = response[0]
                msg_id, data = messages[0]

                try:
                    payload_bytes = data.get(b"payload")
                    raw_dict = json.loads(payload_bytes)

                    check_hash = xxh64(payload_bytes).hexdigest()

                    validated_schedule = SchedulePayloadSchema(**raw_dict)

                    async for session in get_async_session():
                        await process_schedule(session, validated_schedule, check_hash)

                    print(f"[{msg_id.decode()}] Успех: {validated_schedule.group}")

                except ValidationError as e:
                    print(
                        f"[{msg_id.decode()}] Ошибка формата JSON. Валидация провалена:"
                    )
                    print(e.json())

                await r.xack(STREAM_NAME, GROUP_NAME, msg_id)
                await r.xdel(STREAM_NAME, msg_id)

            except aioredis.ConnectionError:
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Непредвиденная ошибка воркера: {e}")
                await asyncio.sleep(5)

    except asyncio.CancelledError:
        print("🛑 Завершение работы воркера...")
    finally:
        await r.close()
