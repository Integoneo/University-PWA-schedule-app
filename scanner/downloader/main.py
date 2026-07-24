import asyncio
import aiohttp
import json
import uuid
import os

from shared import (
    redis_pool,
    logger,
    DOWNLOADER_QUEUE,
    CPP_QUEUE,
    DOWNLOAD_DIR,
    MAX_SHM_SIZE,
    GROUP_NAME,
    CONSUMER_NAME,
)

from utils import download_file, get_dir_size, HEADERS, send_tg_alert


# --- КОНФИГИ DOWNLOADER'А ---


async def main():
    logger.info("Запуск Downloader Worker'а...")

    try:
        await redis_pool.xgroup_create(
            DOWNLOADER_QUEUE, GROUP_NAME, id="0", mkstream=True
        )
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Ошибка создания группы: {e}")

    conn = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=conn, headers=HEADERS) as session:
        logger.info("Ожидание задач в очереди...")

        while True:
            try:
                streams = await redis_pool.xreadgroup(
                    GROUP_NAME,
                    CONSUMER_NAME,
                    {DOWNLOADER_QUEUE: ">"},
                    count=1,
                    block=2000,
                )

                if not streams:
                    continue

                _, messages = streams[0]  # pyright: ignore Завали ебальник
                message_id, message_data = messages[0]  # pyright: ignore Завали ебальник

                payload_str = message_data.get("payload")  # pyright: ignore Завали ебальник

                if not payload_str:
                    await redis_pool.xack(DOWNLOADER_QUEUE, GROUP_NAME, message_id)  # pyright: ignore Завали ебальник

                    continue

                meta_info = json.loads(payload_str)
                file_url = meta_info.get("file_url")
                content_length_str = meta_info.get("Content-Length")

                # Если размера нет, резервируем виртуальные 5 МБ для калькуляции
                expected_size = (
                    int(content_length_str) if content_length_str else 5 * 1024 * 1024
                )

                logger.info(f"Начинаю обработку: {meta_info.get('composite_key')}")

                # ---Контроль за переполнением---
                while True:
                    current_size = get_dir_size(DOWNLOAD_DIR)
                    if current_size + expected_size > MAX_SHM_SIZE:
                        logger.warning(
                            f"Папка переполнена ({current_size / 1024 / 1024:.1f} МБ). C++ парсер отстает. Ждем 5 сек..."
                        )
                        await send_tg_alert(
                            "CRITICAL",
                            "Переполнение /dev/shm/",
                            "Обьем папки достиг около 100 МБ",
                        )
                        await asyncio.sleep(5)
                    else:
                        break  # Место есть, выходим из спячки!

                # Генерируем безопасное имя
                safe_filename = f"{uuid.uuid4().hex}.xlsx"
                filepath = os.path.join(DOWNLOAD_DIR, safe_filename)

                # Скачиваем (Декоратор сам сделает 3 попытки, проверит на ZIP и запишет в DLQ при провале)
                success = await download_file(
                    session=session,
                    file_url=file_url,
                    filepath=filepath,
                    expected_size=int(content_length_str) if content_length_str else 0,
                    meta_info=meta_info,
                )

                if success:
                    logger.info(f"Файл идеален и сохранен как {safe_filename}")

                    # Передаем эстафету C++
                    cpp_payload = {
                        "filepath": filepath,
                        "meta_info": meta_info,
                    }
                    await redis_pool.xadd(
                        CPP_QUEUE,
                        {"payload": json.dumps(cpp_payload, ensure_ascii=False)},
                    )

                    await send_tg_alert(
                        "INFO",
                        "Успешное скачивание файла",
                        "Файл проверен и отправлен на обработку",
                    )

                # Делаем XACK в любом случае, что бы не засорить оперативку, если что файл и так в DLQ
                # нам нужно убрать его из основной очереди, чтобы не зациклить стрим.
                await redis_pool.xack(DOWNLOADER_QUEUE, GROUP_NAME, message_id)  # pyright: ignore Завали ебальник

                await redis_pool.xdel(DOWNLOADER_QUEUE, message_id)  # pyright: ignore Завали ебальник

            except Exception as e:
                await send_tg_alert("CRITICAL", e.__class__.__name__, str(e))
                logger.error(f"Критическая ошибка в цикле воркера: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
