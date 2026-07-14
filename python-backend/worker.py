import asyncio
import json
from xxhash import xxh64
from pydantic import ValidationError
import redis.asyncio as aioredis
from devtools import debug
import logging

from app.db.engine import get_async_session
from app.db.config import settings

# Импортируем наш модуль
from app.worker_modules.group_lessons.schemas import SchedulePayloadSchema
from app.worker_modules.group_lessons.processor import process_schedule


REDIS = settings.REDIS_URL
logging.basicConfig(
    level=logging.DEBUG,  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def main_worker_loop():
    logger.info("🎧 Нативный Async Worker запущен и ждет расписания...")
    r = aioredis.from_url(REDIS)
    STREAM_NAME, GROUP_NAME, CONSUMER_NAME = (
        "db:parsed_lessons",
        "python",
        "python-worker",
    )

    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError:
        pass

    try:
        log_waiting_flag = (
            True  # Переменная для того что бы вывести надпись об ожидании 1 раз
        )
        while True:
            raw_dict = {}
            try:
                response = await r.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=2000
                )

                has_response = bool(response)

                if not has_response:
                    if log_waiting_flag:
                        logger.info("Нахожусь в режиме ожидания")
                        log_waiting_flag = False

                    continue

                log_waiting_flag = True

                _, messages = response[0]
                msg_id, data = messages[0]
                try:
                    payload_bytes = data.get(b"payload")
                    raw_dict = json.loads(payload_bytes)

                    check_hash = xxh64(payload_bytes).hexdigest()

                    validated_schedule = SchedulePayloadSchema(**raw_dict)

                    async for session in get_async_session():
                        # 👇 ЛОВИМ КОРТЕЖ ИЗ ФУНКЦИИ
                        group_id, should_notify = await process_schedule(
                            session, validated_schedule, check_hash
                        )

                        print(f"[{msg_id.decode()}] Успех: {validated_schedule.group}")

                        # 👇ЗАГЛУШКА ДЛЯ PUSH УВЕДОМЛЕНИЙ СТУДЕНТАМ
                        if should_notify:
                            print(
                                f"🔔 [PUSH STUB] Расписание группы {validated_schedule.group} (ID: {group_id}) изменилось!"
                            )
                            print(
                                "🔔 [PUSH STUB] Имитация отправки push-уведомлений всем подписанным устройствам..."
                            )

                except ValidationError as e:
                    inst = raw_dict.get("institute", "???")
                    course = raw_dict.get("course", "?")
                    group = raw_dict.get("group", "???")
                    education_form = raw_dict.get("education_form", "???")
                    start = raw_dict.get("start_education_date", "??.??.??")
                    end = raw_dict.get("end_education_date", "??.??.??")
                    view_url = raw_dict.get("view_url", "https://???")
                    logger.error(
                        f"Ошибка валидации расписания: Институт '{inst}', Форма обучения '{education_form}', курс {course}"
                    )
                    logger.error(
                        f"Группа '{group}', Дата начала обучения {start}, Дата конца обучения '{end}'"
                    )
                    logger.error(f"Быстрый просмотр файла расписания: {view_url}")
                    debug(e)
                await r.xack(STREAM_NAME, GROUP_NAME, msg_id)
                # await r.xdel(STREAM_NAME, msg_id)

                raw_dict = {}

            except aioredis.ConnectionError:
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Непредвиденная ошибка воркера: {e}")
                await asyncio.sleep(5)

    except asyncio.CancelledError:
        print("🛑 Завершение работы воркера...")
    finally:
        await r.close()
