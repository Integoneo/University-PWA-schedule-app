import asyncio
import aiohttp
import bs4
import json
import logging
from time import time
from utils import (
    parse_and_count_schedule,
    check_anomaly_and_save_stats,
    parse_head_info,
    process_schedules_to_redis,
)
from shared import DOMStructureChangedError

# Базовые настройки логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Observer")

# TODO: Придумать как вынести это в отдельный настроечный файл


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
}


async def main():
    START_TIME = time()

    logger.info("Запуск Observer...")

    # Отключаем проверку SSL для aiohttp
    conn = aiohttp.TCPConnector(ssl=False)

    try:
        async with aiohttp.ClientSession(connector=conn, headers=HEADERS) as session:
            logger.info("Скачиваем страницу...")
            async with session.get("https://rguk.ru/students/schedule/") as response:
                # Проверяем ответ от сайта вуза на успешность
                response.raise_for_status()
                html = await response.text()

                soup = bs4.BeautifulSoup(html, "lxml")

                # 2. Парсим данные
                logger.info("Запускаем парсер...")
                current_stats, parsed_data = await asyncio.to_thread(
                    parse_and_count_schedule, soup
                )
                logger.info(f"Текущая статистика: {current_stats}")

                # 3. Проверка на аномалии (Sanity Check)
                # Если будет выброшен DOMStructureChangedError, скрипт прервется и до сохранения данных не дойдет
                await check_anomaly_and_save_stats(current_stats)

                parsed_data = await parse_head_info(session, parsed_data)

                # 4. Обработка и сохранение данных в Redis
                await process_schedules_to_redis(parsed_data)

                dumped_data = [item.model_dump(by_alias=True) for item in parsed_data]
                pretty_json = json.dumps(dumped_data, indent=4, ensure_ascii=False)
                logger.info(f"Получены данные:\n{pretty_json}")
                logging.info(f"Время работы: {time() - START_TIME}")

    except DOMStructureChangedError as e:
        logger.critical(f"РАБОТА ОСТАНОВЛЕНА: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())
