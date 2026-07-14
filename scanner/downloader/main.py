import asyncio
import aiohttp
import aiofiles
import json
import logging
import uuid
import os
import zipfile
from time import time
from functools import wraps
from aiohttp import ClientSession

from shared import (
    redis_pool,
    DOWNLOADER_QUEUE,
    CPP_QUEUE,
    DOWNLOAD_DIR,
    BAN_TIME,
    MAX_SHM_SIZE,
    GROUP_NAME,
    CONSUMER_NAME,
    DOWNLOADER_DLQ,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Downloader")

# --- КОНФИГИ DOWNLOADER'А ---

# Создаем папку для загрузок, если её нет
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_dir_size(path=".") -> int:
    """Быстро вычисляет размер всех файлов в папке."""
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def fallback_download_DLQ(func):
    """
    Асинхронный декоратор-карантин.
    Ловит сетевые ошибки и битые файлы, делает 3 попытки,
    если не вышло - прячет ссылку в DOWNLOADER_DLQ на 20 минут.
    """

    @wraps(func)
    async def wrapper(session, file_url, filepath, expected_size=0, meta_info=None):
        if not file_url:
            return False

        # 1. Проверяем Карантин
        dlq_item_str = await redis_pool.hget(DOWNLOADER_DLQ, file_url)
        dlq_state = None
        base_count_attempt = 0

        if dlq_item_str:
            dlq_state = json.loads(dlq_item_str)
            failed_at = dlq_state.get("failed_at", 0)

            if time() - failed_at < BAN_TIME:
                logger.warning(f"Файл в карантине, пропускаем: {file_url}")
                return False
            else:
                base_count_attempt = len(dlq_state.get("attempts", []))
        else:
            dlq_state = {"meta_info": meta_info or {}, "attempts": []}

        # 2. Боевой цикл скачивания (3 попытки)
        for i in range(1, 4):
            current_attempt = base_count_attempt + i
            try:
                # Вызываем саму функцию скачивания
                result = await func(
                    session, file_url, filepath, expected_size, meta_info
                )

                if result:
                    # Успех! Очищаем из карантина, если он там был
                    if dlq_item_str:
                        await redis_pool.hdel(DOWNLOADER_DLQ, file_url)
                    return True

            except aiohttp.ClientResponseError as e:
                err_obj = {
                    "attempt": current_attempt,
                    "type": f"HTTP {e.status}",
                    "msg": e.message,
                }
            except asyncio.TimeoutError:
                err_obj = {
                    "attempt": current_attempt,
                    "type": "Timeout",
                    "details": "Превышено время скачивания",
                }
            except Exception as e:
                err_obj = {
                    "attempt": current_attempt,
                    "type": e.__class__.__name__,
                    "details": str(e),
                }

            logger.error(
                f"Сбой скачивания (попытка {current_attempt}/3): {err_obj['details'] if 'details' in err_obj else err_obj['msg']}"
            )
            dlq_state["attempts"].append(err_obj)

            # Удаляем огрызок битого файла с диска перед новой попыткой
            if os.path.exists(filepath):
                os.remove(filepath)

            if i < 3:
                await asyncio.sleep(2**i)  # Экспоненциальный бэкофф

        # 3. Фиксация провала
        dlq_state["failed_at"] = time()
        await redis_pool.hset(
            DOWNLOADER_DLQ, file_url, json.dumps(dlq_state, ensure_ascii=False)
        )
        logger.critical(f"ФАЙЛ УШЕЛ В DLQ: {file_url}")
        return False

    return wrapper


@fallback_download_DLQ
async def download_file(
    session: ClientSession,
    file_url: str,
    filepath: str,
    expected_size: int = 0,
    meta_info: dict | None = None,
) -> bool:
    """Сама логика скачивания и валидации файла."""

    # Даем серверу до 10 минут на отдачу медленного/большого файла
    timeout = aiohttp.ClientTimeout(total=600)

    async with session.get(file_url, allow_redirects=True, timeout=timeout) as response:
        response.raise_for_status()

        # Пишем файл на диск чанками по 8 КБ (Защита RAM)
        async with aiofiles.open(filepath, "wb") as f:
            async for chunk in response.content.iter_chunked(8192):
                await f.write(chunk)

    # --- ПРОВЕРКИ ЦЕЛОСТНОСТИ ---
    actual_size = os.path.getsize(filepath)

    # 1. Проверка размера (допускаем погрешность в 1024 байта на случай изменения заголовков сервером)
    if expected_size > 0 and abs(actual_size - expected_size) > 1024:
        raise Exception(
            f"Несовпадение размера! Ожидали ~{expected_size}, скачали {actual_size}."
        )

    # 2. Мгновенная проверка бинарной сигнатуры (любой .xlsx - это ZIP архив)
    if not zipfile.is_zipfile(filepath):
        raise Exception("Файл битый (не является валидным ZIP/XLSX архивом).")

    return True


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

    async with aiohttp.ClientSession(connector=conn) as session:
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

                for stream_name, messages in streams:
                    for message_id, message_data in messages:
                        payload_str = message_data.get("payload")
                        if not payload_str:
                            await redis_pool.xack(
                                DOWNLOADER_QUEUE, GROUP_NAME, message_id
                            )
                            continue

                        meta_info = json.loads(payload_str)
                        file_url = meta_info.get("file_url")
                        content_length_str = meta_info.get("Content-Length")

                        # Если размера нет, резервируем виртуальные 5 МБ для калькуляции
                        expected_size = (
                            int(content_length_str)
                            if content_length_str
                            else 5 * 1024 * 1024
                        )

                        logger.info(
                            f"Начинаю обработку: {meta_info.get('composite_key')}"
                        )

                        # --- BACKPRESSURE (ОБРАТНОЕ ДАВЛЕНИЕ) ---
                        while True:
                            current_size = get_dir_size(DOWNLOAD_DIR)
                            if current_size + expected_size > MAX_SHM_SIZE:
                                logger.warning(
                                    f"Папка переполнена ({current_size / 1024 / 1024:.1f} МБ). C++ парсер отстает. Ждем 5 сек..."
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
                            expected_size=int(content_length_str)
                            if content_length_str
                            else 0,
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
                                {
                                    "payload": json.dumps(
                                        cpp_payload, ensure_ascii=False
                                    )
                                },
                            )

                        # --- ГАРАНТИЯ ДОСТАВКИ ---
                        # Делаем XACK в любом случае! Если success=False, файл уже безопасно сидит в DLQ,
                        # нам нужно убрать его из основной очереди, чтобы не зациклить стрим.
                        await redis_pool.xack(DOWNLOADER_QUEUE, GROUP_NAME, message_id)
                        await redis_pool.xdel(DOWNLOADER_QUEUE, message_id)

            except Exception as e:
                logger.error(f"Критическая ошибка в цикле воркера: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
