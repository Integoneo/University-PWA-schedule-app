import os
import json
from typing import Literal, List
import aiofiles
import asyncio
import zipfile
import aiohttp
from time import time
from functools import wraps
from aiohttp import ClientSession
from shared import (
    BAN_TIME,
    DOWNLOAD_DIR,
    NewMessage,
    redis_pool,
    logger,
    proxy,
    DOWNLOADER_DLQ,
)


# Создаем папку для загрузок, если её нет
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
}

PROXY_URL_PARSING = f"http://{proxy.PROXY_LOGIN_PARSING}:{proxy.PROXY_PASSWORD_PARSING}@{proxy.PROXY_HOST}:{proxy.PROXY_PORT}"


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

        # 2. 3 попытки скачивания
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
                    "msg": f"HTTP {e.status} во время скачивания файла",
                    "details": e.message,
                }
            except asyncio.TimeoutError:
                err_obj = {
                    "attempt": current_attempt,
                    "msg": "Timeout",
                    "details": "Превышено время скачивания",
                }
            except Exception as e:
                err_obj = {
                    "attempt": current_attempt,
                    "msg": e.__class__.__name__,
                    "details": str(e),
                }

            logger.error(
                f"Сбой скачивания (попытка {current_attempt}/3): {err_obj['details'] if 'details' in err_obj else err_obj['msg']}"  # pyright: ignore Завали ебальник
            )
            dlq_state["attempts"].append(err_obj)  # pyright: ignore Завали ебальник

            # Удаляем огрызок битого файла с диска перед новой попыткой
            if os.path.exists(filepath):
                os.remove(filepath)

            if i < 3:
                await asyncio.sleep(2**i)  # Задержка перед попыткой

        # Отправляю последнюю ошибку, поскольку если отправить сразу все три ошибки о файле, то возникнет диссонанс и это будет выглядеть как путанница
        last_attempt = dlq_state["attempts"][-1]
        await send_tg_alert(
            msg_level="WARN", msg=last_attempt["msg"], details=last_attempt["details"]
        )

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
    timeout = aiohttp.ClientTimeout(total=60)

    async with session.get(
        file_url, allow_redirects=True, timeout=timeout, proxy=PROXY_URL_PARSING
    ) as response:
        response.raise_for_status()

        # Пишем файл на диск чанками по 8 КБ (Защита RAM)
        async with aiofiles.open(filepath, "wb") as f:
            async for chunk in response.content.iter_chunked(8192):
                await f.write(chunk)

    # --- ПРОВЕРКИ ЦЕЛОСТНОСТИ ---
    actual_size = os.path.getsize(filepath)

    # 1. Проверка размера с небольшой погрешностью
    if expected_size > 0 and abs(actual_size - expected_size) > 1024:
        raise Exception(
            f"Несовпадение размера! Ожидали ~{expected_size}, скачали {actual_size}."
        )

    # 2. Проверяю эксель файл как Zip архив
    if not zipfile.is_zipfile(filepath):
        raise Exception("Файл битый (не является валидным ZIP/XLSX архивом).")

    return True


async def send_tg_alert(
    msg_level: Literal["INFO", "WARN", "ERROR", "CRITICAL", "DEAD"],
    msg: str,
    details: List[str] | str,
):
    new_message = NewMessage(
        service="Downloader",
        msg_level=msg_level,
        msg=msg,
        details=details,  # pyright: ignore завали ебальник
    )

    # плоский словарь для Redis XADD
    payload = {
        "service": new_message.service,
        "msg_level": new_message.msg_level,
        "msg": new_message.msg,
    }

    if isinstance(new_message.details, list):
        payload["details"] = json.dumps(new_message.details, ensure_ascii=False)
    else:
        payload["details"] = new_message.details

    try:
        await redis_pool.xadd("notifier:queue", payload)  # pyright: ignore
    except Exception as e:
        print(f"⚠️ Ошибка отправки алерта в очередь: {e}")
