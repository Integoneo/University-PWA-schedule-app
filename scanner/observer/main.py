import asyncio
import aiohttp
import bs4
import logging

# from time import perf_counter
from utils import (
    parse_and_count_schedule,
    check_anomaly_and_save_stats,
    parse_head_info,
    process_schedules_to_redis,
    fetch_html_with_retries,
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

    # Отключаем проверку SSL для aiohttp. (force_close пока не ставим, проверим так)
    conn = aiohttp.TCPConnector(ssl=False)

    # Открываем сессию ОДИН РАЗ на всё время работы скрипта
    async with aiohttp.ClientSession(connector=conn, headers=HEADERS) as session:
        while True:
            # START_TIME = perf_counter()

            try:
                # 1. Скачиваем HTML (функция заблокирует выполнение, пока не скачает успешно)
                html = await fetch_html_with_retries(session)

                # 2. Парсим данные
                soup = bs4.BeautifulSoup(html, "lxml")
                logger.info("Запускаем парсер...")
                current_stats, parsed_data = await asyncio.to_thread(
                    parse_and_count_schedule, soup
                )
                logger.info(f"Текущая статистика: {current_stats}")

                # 3. Проверка на аномалии (Sanity Check)
                # Если будет выброшен DOMStructureChangedError, мы поймаем его в except ниже и УБЬЕМ скрипт
                await check_anomaly_and_save_stats(current_stats)

                # 4. Скачиваем заголовки HEAD
                parsed_data = await parse_head_info(session, parsed_data)

                # 5. Обработка и сохранение данных в Redis
                await process_schedules_to_redis(parsed_data)

                # print(f"Время цикла сканирования: {perf_counter() - START_TIME}")

                # 6. Успешный финал цикла, ждем перед следующим
                jitter = random.uniform(80.0, 100.0)  # Промежуток 80-100 секунд

                #     "INFO",
                #     "Успешно завершен цикл сканирования",
                #     f"Время выполнения: {perf_counter() - START_TIME:.2f} сек",
                # )  # TODO: Убрать этот алерт в проде

                await asyncio.sleep(jitter)

            except DOMStructureChangedError as e:
                # ЕДИНСТВЕННАЯ ошибка, которая может сломать этот цикл и завершить скрипт
                logger.critical(f"РАБОТА ОСТАНОВЛЕНА: {e}")
                await send_tg_alert(
                    "CRITICAL", "РАБОТА ОСТАНОВЛЕНА (DOM изменился)", str(e)
                )
                break  # Выходим из while True, скрипт завершается

            except Exception as e:
                # Если упало где-то ВНУТРИ парсинга или Redis (не при скачивании)
                msg = f"Непредвиденная ошибка в основном цикле: {e.__class__.__name__}"
                logger.error(f"{msg}. Детали: {e}")
                await send_tg_alert("ERROR", msg, str(e))
                # Не прерываем скрипт, просто ждем минуту и пробуем начать цикл заново
                await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
