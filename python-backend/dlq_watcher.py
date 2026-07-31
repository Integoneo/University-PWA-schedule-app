import asyncio
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from redis.asyncio import Redis
import logging
from app.utils import redis_client
from app.db.config import settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("DLQ_Watcher")


DOWNLOAD_DIR = Path(f"{settings.DOWNLOAD_DIR}")

# Папка DLQ
DLQ_DIR = Path(f"{settings.DLQ_DIR}")

# --- Конфигурация Redis ---
DLQ_QUEUE_KEY = "parser:dlq"
READY_SCHEDULES_KEY = "parser:ready_schedules"

DLQ_DIR.mkdir(parents=True, exist_ok=True)


def get_last_modified_by(filepath: str) -> str | None:
    """Синхронно читаем метаданные ZIP-архива (Excel)"""
    try:
        with zipfile.ZipFile(filepath, "r") as z:
            with z.open("docProps/core.xml") as core_xml:
                tree = ET.parse(core_xml)
                root = tree.getroot()

                namespaces = {
                    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                }
                modifier = root.find("cp:lastModifiedBy", namespaces)

                if modifier is not None and modifier.text:
                    return modifier.text.strip()
                return None
    except Exception as e:
        logger.warning(
            f"Не удалось прочитать метаданные (возможно файл еще пишется) {filepath}: {e}"
        )
        return None


async def check_dlq_files(redis_client: Redis):
    dlq_items = await redis_client.hgetall(DLQ_QUEUE_KEY)  # type: ignore

    if not dlq_items:
        return

    # В dlq_items: ключ - это ИМЯ ФАЙЛА, значение - сырой JSON payload
    for raw_filename, raw_payload in dlq_items.items():
        try:
            # Раскодируем байты в нормальные строки
            filename = raw_filename.decode("utf-8")
            payload_str = raw_payload.decode("utf-8")
            dlq_filepath = DLQ_DIR / filename

            # 1. Если файла физически нет в DLQ (удалили руками как мусор)
            if not dlq_filepath.exists():
                logger.info(f"Файл {filename} удален из папки DLQ. Очищаем из Redis.")
                await redis_client.hdel(DLQ_QUEUE_KEY, filename)  # type: ignore
                continue

            # 2. Получаем автора последнего изменения
            last_modified_by = await asyncio.to_thread(
                get_last_modified_by, str(dlq_filepath)
            )

            # 3. Если атрибут пуст (None) или отличен от "C++", значит файл лечили
            if last_modified_by != "C++":
                logger.info(
                    f"Обнаружены правки (автор: '{last_modified_by}') в {filename}! Возвращаем в парсер."
                )

                download_filepath = DOWNLOAD_DIR / filename

                # 4. Копируем обратно в temp_downloads, где его ждут плюсы
                shutil.copy2(dlq_filepath, download_filepath)

                # 5. Пушим СЫРОЙ payload_str обратно в очередь! Без парсинга!
                await redis_client.xadd(READY_SCHEDULES_KEY, {"payload": payload_str})

                # 6. Удаляем из DLQ-хэша
                await redis_client.hdel(DLQ_QUEUE_KEY, filename)  # type: ignore

        except Exception as e:
            logger.error(f"Ошибка при обработке файла {filename}: {e}")


async def dlq_watcher_loop():
    """Главный цикл демона"""
    logger.info(f"Запуск DLQ Watcher. Ждем файлов в папке: {DLQ_DIR} ...")

    while True:
        try:
            await check_dlq_files(redis_client)
        except Exception as e:
            logger.error(f"Ошибка в цикле DLQ Watcher: {e}")

        await asyncio.sleep(15)
