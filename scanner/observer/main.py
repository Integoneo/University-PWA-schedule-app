import asyncio
import aiohttp
import bs4
import logging
from time import perf_counter, time
from utils import (
    parse_and_count_schedule,
    check_anomaly_and_save_stats,
    parse_head_info,
    process_schedules_to_redis,
    send_tg_alert,
)
from shared import DOMStructureChangedError
import random

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

    logger.info("Запуск Observer...")

    # Отключаем проверку SSL для aiohttp
    conn = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=conn, headers=HEADERS) as session:
            while True:
                START_TIME = perf_counter()
                logger.info("Скачиваем страницу...")
                async with session.get(
                    "https://rguk.ru/students/schedule/"
                ) as response:
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

                    print(f"Время цикла сканирования: {perf_counter() - START_TIME}")

                    jitter = random.uniform(
                        80.0, 100.0
                    )  # TODO: Сделать промежуток 80-100 секунд

                    await send_tg_alert(
                        "INFO",
                        "Успешно завершен цикл сканирования",
                        "Без смертельных ошибок",
                    )  # TODO: Убрать этот алерт в проде

                    await asyncio.sleep(jitter)

                # dumped_data = [item.model_dump(by_alias=True) for item in parsed_data]
                # pretty_json = json.dumps(dumped_data, indent=4, ensure_ascii=False)
                # logger.info(f"Получены данные:\n{pretty_json}")
    except aiohttp.ClientResponseError as e:
        msg = f"HTTP {e.status} во время скачивания HTML странички"
        details = e.message
        logger.error(f"{msg}")
        logger.error(f"{details}")
        await send_tg_alert("CRITICAL", msg, details)
    except aiohttp.ClientError as e:
        msg = f"{e.__class__.__name__} во время скачивания HTML странички"
        details = str(e)
        logger.error(f"{msg}")
        logger.error(f"{details}")
        await send_tg_alert("CRITICAL", msg, details)
    except DOMStructureChangedError as e:
        logger.critical(f"РАБОТА ОСТАНОВЛЕНА: {e}")
    except Exception as e:
        msg = f"{e.__class__.__name__} во время скачивания HTML странички"
        details = str(e)
        logger.error(f"{msg}")
        logger.error(f"{details}")
        await send_tg_alert("DEAD", msg, details)


if __name__ == "__main__":
    asyncio.run(main())
