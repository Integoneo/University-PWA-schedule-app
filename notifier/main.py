import asyncio
import aiohttp
from pydantic import ValidationError
from collections import Counter

from shared import (
    logger,
    redis_pool,
    STREAM_NAME,
    GROUP_NAME,
    CONSUMER_NAME,
    HASH_NAME,
    NewMessage,
    OldMessage,
    OldMessageHash,
)
from utils import ping_kuma, send_message, edit_message


async def main():
    logger.info("Запуск Telegram Notifier...")

    await redis_pool._ensure_connection()
    await redis_pool.xgroup_create(STREAM_NAME, GROUP_NAME, mkstream=True)

    conn = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=conn) as session:
        waiting_flag = False

        while True:
            is_pending_task = False
            await ping_kuma(session)

            # 1. Сначала ищем НОВЫЕ сообщения (приоритет)
            response = await redis_pool.xreadgroup(
                GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=2000
            )

            if not response:
                # 2. Новых нет. Проверяем зависшие (PEL) сообщения
                response = await redis_pool.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: "0"}, count=1, block=0
                )

                # Если и в PEL пусто — уходим на следующий круг
                if not response or not response[0][1]:  # pyright: ignore
                    if not waiting_flag:
                        waiting_flag = True
                        logger.info("Нахожусь в режиме ожидания")
                    continue
                else:
                    is_pending_task = True

            waiting_flag = False

            _, messages = response[0]  # pyright: ignore
            redis_msg_id, data = messages[0]  # pyright: ignore

            try:
                new_message = NewMessage.model_validate(data)
            except ValidationError as e:
                logger.error(f"Невалидный JSON: {e}")
                # Сразу XACK, такое мы никогда не сможем распарсить
                await redis_pool.xack(STREAM_NAME, GROUP_NAME, redis_msg_id)  # pyright: ignore
                continue

            composite_key = (
                f"{new_message.service} | {new_message.msg_level} | {new_message.msg}"
            )
            massage_was_sended = await redis_pool.hexists(HASH_NAME, composite_key)

            new_nofifies = Counter(new_message.details)

            try:
                if massage_was_sended:
                    raw_message = await redis_pool.hget(HASH_NAME, composite_key)
                    parsed_message = OldMessageHash.model_validate_json(raw_message)  # pyright: ignore

                    updated_sub_msg = (
                        Counter(parsed_message.payload.sub_msg) + new_nofifies
                    )
                    parsed_message.payload.sub_msg = dict(updated_sub_msg)

                    # Пытаемся обновить
                    tg_msg_id = await edit_message(session, parsed_message)

                    if tg_msg_id == -1:
                        logger.error(
                            f"Битое сообщение (Edit). Отправляю в DLQ: {redis_msg_id}"
                        )
                        await redis_pool.xadd(
                            "notifier:dlq", {"raw_data": str(data), "error": "edit_400"}
                        )
                    else:
                        await redis_pool.hset(
                            HASH_NAME, composite_key, parsed_message.model_dump_json()
                        )
                        await redis_pool.hexpire(HASH_NAME, 86400, composite_key)

                else:
                    # Пытаемся отправить
                    tg_msg_id = await send_message(session, new_message)

                    if tg_msg_id == -1:
                        logger.error(
                            f"Битое сообщение (Send). Отправляю в DLQ: {redis_msg_id}"
                        )
                        await redis_pool.xadd(
                            "notifier:dlq", {"raw_data": str(data), "error": "send_400"}
                        )
                    else:
                        hash_payload = OldMessage(
                            service=new_message.service,
                            msg_level=new_message.msg_level,
                            msg=new_message.msg,
                            sub_msg=dict(new_nofifies),
                        )

                        hash_item = OldMessageHash(
                            tg_id_msg=tg_msg_id, payload=hash_payload
                        )

                        await redis_pool.hset(
                            HASH_NAME, composite_key, hash_item.model_dump_json()
                        )
                        await redis_pool.hexpire(HASH_NAME, 86400, composite_key)

                logger.info(f"Успешно обработано сообщение, ключ: {composite_key}")
                await redis_pool.xack(STREAM_NAME, GROUP_NAME, redis_msg_id)  # pyright: ignore
                await redis_pool.xdel(STREAM_NAME, redis_msg_id)  # pyright: ignore

                if is_pending_task:
                    logger.info(f"✅ Успешно разобрана зависшая задача: {redis_msg_id}")

            except Exception as e:
                logger.error(f"Критическая ошибка при обработке алерта: {e}")
                # Мы НЕ делаем xack. Сообщение остается в PEL и мы вернемся к нему позже
                await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
