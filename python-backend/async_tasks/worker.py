import asyncio
import json
from xxhash import xxh64
from pydantic import ValidationError
import redis.asyncio as aioredis

from app.db.engine import get_async_session
from app.utils import get_logger, send_tg_alert, redis_client

from app.worker_modules.group_lessons.schemas import SchedulePayloadSchema
from app.worker_modules.group_lessons.processor import process_schedule
from app.db.config import settings
from app.utils import ping_kuma_sync


logger = get_logger(__name__)


async def main_worker_loop():
    logger.info("🎧 Нативный Async Worker запущен и ждет расписания...")
    STREAM_NAME, GROUP_NAME, CONSUMER_NAME = (
        "db:parsed_lessons",
        "python",
        "python-worker",
    )

    try:
        await redis_client.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            await send_tg_alert(
                "Python worker",
                "CRITICAL",
                "Ошибка подключения к Redis",
                e.__class__.__name__,
            )

    try:
        log_waiting_flag = (
            True  # Переменная для того что бы вывести надпись об ожидании 1 раз
        )
        while True:
            if settings.KUMA_URL:
                # Запускаем пинг в отдельном легком потоке, чтобы не тормозить цикл
                asyncio.create_task(
                    asyncio.to_thread(ping_kuma_sync, settings.KUMA_URL)
                )

            raw_dict = {}
            try:
                response = await redis_client.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=2000
                )

                has_response = bool(response)

                if not has_response:
                    if log_waiting_flag:
                        logger.info("Нахожусь в режиме ожидания")
                        log_waiting_flag = False

                    continue

                log_waiting_flag = True

                _, messages = response[0]  # type: ignore
                msg_id, data = messages[0]  # type: ignore
                try:
                    payload_bytes = data.get(b"payload")  # type: ignore
                    raw_dict = json.loads(payload_bytes)  # type: ignore

                    check_hash = xxh64(payload_bytes).hexdigest()  # type: ignore

                    validated_schedule = SchedulePayloadSchema(**raw_dict)

                    async for session in get_async_session():
                        #  ЛОВИМ КОРТЕЖ ИЗ ФУНКЦИИ
                        group_id, should_notify = await process_schedule(
                            session, validated_schedule, check_hash
                        )

                        logger.info(
                            f"[{msg_id.decode()}] Успех: {validated_schedule.group}"  # type: ignore
                        )

                        if should_notify:
                            # BIG TODO: Настроить подписки на GOOGLE Firebase что бы отправлять уведолмения
                            # об изменении расписания студентам
                            # но это вообще на потом
                            await send_tg_alert(
                                "Python worker",
                                "INFO",
                                "Обновлено расписание группы",
                                validated_schedule.institute,
                            )
                            logger.info(
                                f"🔔 [PUSH STUB] Расписание группы {validated_schedule.group} (ID: {group_id}) изменилось!"
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
                    await send_tg_alert(
                        "Python worker", "ERROR", "Ошибка валидации расписания", inst
                    )
                    logger.error(str(e))
                await redis_client.xack(STREAM_NAME, GROUP_NAME, msg_id)  # type: ignore
                await redis_client.xdel(STREAM_NAME, msg_id)  # type: ignore

                raw_dict = {}

            except aioredis.ConnectionError as e:
                await asyncio.sleep(5)
                await send_tg_alert(
                    "Python worker",
                    "CRITICAL",
                    "Ошибка подключения к Redis",
                    e.__class__.__name__,
                )
            except Exception as e:
                logger.error(f"Непредвиденная ошибка воркера: {e}")

                await send_tg_alert(
                    "Python worker",
                    "CRITICAL",
                    "Неизвестная ошибка",
                    e.__class__.__name__,
                )
                await asyncio.sleep(5)

    except asyncio.CancelledError:
        logger.info("🛑 Завершение работы воркера...")
    finally:
        await redis_client.close()
