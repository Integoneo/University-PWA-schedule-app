from typing import Tuple, Dict, List, Optional
from urllib.parse import urljoin
from functools import wraps
from time import time
import random
import bs4
import aiohttp
import asyncio
import logging
import json


from redis_db import redis_pool

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Observer")


class InstituteSelectors:
    MAIN_CONTAINER = "contentmain"
    BLOCK_INST = "students-schedule-inst"
    BLOCK_IGNORE = "students-schedule-rasp"
    INFO_ROW = "logo-row"
    LOGO = "logo-schedule"
    NAME = "name-schedule"
    ACCORDION_ITEM = "accordion-item"
    ACCORDION_BTN = "accordion-button"
    DOCUMENT = "document"
    GRAPH_WRAPPER = "graph"
    ICONS = "icons"
    FILES = "files"


# INFO: КОРТЕЖИ КОТОРЫЕ Я ТУТ РАСПИСАЛ - РАСШИФРОВКА
# Tuple({True - срабатываение по % False по количеству}, {процентаж/количество})
THRESHOLDS = {
    "main_containers": (False, 1),
    "institutes": (False, 1),
    "logos": (True, 100.0),
    "study_forms": (True, 30.0),
    "valid_files": (True, 30.0),
    "office_views": (True, 30.0),
}


# TODO: Придумать как вынести это в отдельный настроечный файл
STATS_KEY = "observer:stats:last_run"
SCHEDULES_KEY = "observer:schedules"

EXCEL_SRC_DLQ = "observer:DLQ:head_requests"
BAN_TIME = 1200  # Ссылки по которым не прошли head запросы, банятся на 20 минут

BATCH_SIZE = 5


# TODO: В будущем вынести это в отдельный файл для кастомных ошибок
class DOMStructureChangedError(Exception):
    pass


def parse_and_count_schedule(
    soup: bs4.BeautifulSoup, base_url: str = "https://rguk.ru"
) -> Tuple[Dict[str, int], List[Dict]]:
    """Парсит страницу, собирает метрики и формирует плоский список словарей для Redis."""
    stats = {
        "main_containers": 0,
        "institutes": 0,
        "logos": 0,
        "study_forms": 0,
        "valid_files": 0,
        "office_views": 0,
    }

    results = []

    # Находим по айдишнику основной контейнер где лежат все блоки институтов
    main_container = soup.find(id=InstituteSelectors.MAIN_CONTAINER)

    if main_container:
        stats["main_containers"] += 1
    # Если основного контейнера нет то нет смысла дальше что либо делать - парсинг сломан
    else:
        return stats, results

    # Ищем все блоки институтов
    institutes = main_container.find_all("div", class_=InstituteSelectors.BLOCK_INST)

    # Проходимся по всем блокам институтов
    for inst in institutes:
        # Собираем все классы блока институтов, что бы скипать блоки
        # с ненужными классами, ну или потом будем делать их обработку
        # INFO: В классе Institutes.BLOCK_IGNORE инфа не мусорная, но парсить мы будем ее потом
        # а сейчас пока будем скипать
        inst_classes = inst.get("class", None)

        # INFO: В данном блоке находится важная мета инфа - все аудитории которые существуют в вузе
        # Актуальная инфа о четных и нечетных неделях в семестре, но пока мы не будем это парсить
        if inst_classes and InstituteSelectors.BLOCK_IGNORE in inst_classes:
            continue

        inst_name_tag = inst.find(class_=InstituteSelectors.NAME)

        institute_count_flag = False

        # Ищем тег с названием института
        inst_name = inst_name_tag.get_text(strip=True) if inst_name_tag else "Unknown"
        # Ищем лого в институте(его может и не быть)
        logo_img = inst.find("img", class_=InstituteSelectors.LOGO)
        logo_url = None
        if logo_img:
            # Считаем логотипы
            stats["logos"] += 1
            # Достаем ссылки на логотипы
            src = logo_img.get("src")
            if isinstance(src, str):
                logo_url = urljoin(base_url, src)

        # Внитри институтов достаем все формы обучения которые у него есть
        accordions = inst.find_all(class_=InstituteSelectors.ACCORDION_ITEM)
        # Считаем формы обучения внутри института
        stats["study_forms"] += len(accordions)

        # Запускаем цикл по формам обучения
        for acc in accordions:
            # Достаем кнопку в которой написана форма обучения
            btn = acc.find(class_=InstituteSelectors.ACCORDION_BTN)
            # Достаем текст формы обучения
            study_form = btn.get_text(strip=True) if btn else "Unknown"

            # Внутри формы обучения достаем все блоки со ссылками файлы(включая мусорные)
            documents = acc.find_all(class_=InstituteSelectors.DOCUMENT)

            # Запускаем цикл по всем блокам со ссылками на файлы
            for doc in documents:
                # Скипаем мусор - графики обучения - мы это не парсим
                if doc.find_parent(class_=InstituteSelectors.GRAPH_WRAPPER):
                    continue
                # Вот это уже наше, достаем эти экселевские файлы
                files_div = doc.find(class_=InstituteSelectors.FILES)
                if not files_div:
                    continue

                # Используя callback функцию достаем ссылку на эксель файлы
                file_a = files_div.find(
                    "a",
                    href=lambda h: bool(h and h.lower().endswith((".xls", ".xlsx"))),
                )
                if file_a:
                    # Сделал этот флаг что бы считать только те институты внутри которых мы нашли эксель файлы
                    if not institute_count_flag:
                        institute_count_flag = True
                        stats["institutes"] += 1
                    # Считаем валидные эксель файлы
                    stats["valid_files"] += 1
                    # Достаем ссылку на эксель файл
                    file_href = file_a.get("href")

                    # if что бы pyright не ругался на аннотацию типов
                    if not isinstance(file_href, str):
                        continue

                    # Соединяем пути, что бы получить нормальную сслыку на файл
                    file_url = urljoin(base_url, file_href)

                    file_title = file_a.get_text(strip=True)

                    view_url = None
                    # Ищем внутри документа так же ссылку на просмотр через view.office
                    icons_div = doc.find(class_=InstituteSelectors.ICONS)
                    if icons_div and icons_div.find(
                        "a", href=bool(lambda h: h and "view.officeapps.live.com" in h)
                    ):
                        icons_div_a = icons_div.find("a")
                        if icons_div_a is None:
                            continue

                        view_url = icons_div_a.get(
                            "href"
                        )  # Берем первую ссылку из иконок
                        stats["office_views"] += 1

                    # INFO:
                    # Собираем финальный композитный ключ из
                    # Названия института
                    # Названия формы обучения
                    # Названия файла(обычно там пишут например "1 курс")
                    composite_key = f"{inst_name} | {study_form} | {file_title}"

                    results.append(
                        {
                            "composite_key": composite_key,
                            "file_title": file_title,
                            "institution": inst_name,
                            "study_form": study_form,
                            "file_url": file_url,
                            "view_url": view_url,
                            "logo_url": logo_url,
                        }
                    )

    if stats["institutes"] > 0 and stats["valid_files"] == 0:
        raise DOMStructureChangedError(
            "DOM broken: Institutes found, but 0 valid Excel files."
        )

    return stats, results


async def check_anomaly_and_save_stats(
    r, current_stats: dict
):  # type hint: r: aioredis.Redis
    """Сверяет текущие метрики с прошлыми из Redis. Если всё ок - перезаписывает."""

    # Пытаемся получить прошлые метрики
    past_stats_raw = await r.hgetall(STATS_KEY)

    if past_stats_raw:
        # Redis возвращает байты и для ключей, и для значений (например b'140').
        # Декодируем ключ в строку, а значение в строку и затем в int.
        past_stats = {
            k.decode("utf-8"): int(v.decode("utf-8")) for k, v in past_stats_raw.items()
        }
        logger.info(f"Прошлые метрики из Redis: {past_stats}")

        is_anomalous = False
        anomaly_reasons = []
        info_changes = []  # Для обычных уведомлений (не критичных)

        # Сравниваем каждый ключ
        for key, current_val in current_stats.items():
            past_val = past_stats.get(key, 0)

            # Собираем инфу обо всех изменениях для обычного алерта (не крашащего парсер)
            if past_val != current_val:
                info_changes.append(f"{key}: {past_val} -> {current_val}")

            # Логика критических аномалий (только если значения УПАЛИ)
            if past_val > current_val:
                # Получаем правило из словаря (по умолчанию ставим % и 30.0, если ключа нет)
                is_percent, threshold = THRESHOLDS.get(key, (True, 30.0))

                if is_percent:
                    drop_percent = ((past_val - current_val) / past_val) * 100
                    if drop_percent >= threshold:
                        is_anomalous = True
                        anomaly_reasons.append(
                            f"{key}: {past_val} -> {current_val} (падение на {drop_percent:.1f}%, порог: {threshold}%)"
                        )
                else:
                    drop_abs = past_val - current_val
                    if drop_abs >= threshold:
                        is_anomalous = True
                        anomaly_reasons.append(
                            f"{key}: {past_val} -> {current_val} (пропало: {drop_abs}, порог: {threshold})"
                        )

        # Если сработал хотя бы один триггер из THRESHOLDS — рубим пайплайн
        if is_anomalous:
            alert_msg = (
                "🚨 АНОМАЛИЯ ПАРСИНГА! Обнаружено критическое падение тегов:\n"
                + "\n".join(anomaly_reasons)
            )
            logger.error(alert_msg)
            # ТУТ ЗАГЛУШКА ДЛЯ ТЕЛЕГРАМА (КРИТИЧЕСКИЙ АЛЕРТ)
            # await send_telegram_alert(alert_msg, level="CRITICAL")
            raise DOMStructureChangedError("Anomaly detected. Halting execution.")

        # Если аномалий нет, но были любые изменения — просто шлем инфо-уведомление
        # elif info_changes:
        #     info_msg = "ℹ️ Изменение в структуре (в пределах нормы):\n" + "\n".join(info_changes)
        #     await send_telegram_alert(info_msg, level="INFO")

    else:
        logger.info("Прошлые метрики не найдены. Это первый запуск (Холодный старт).")

    # Если всё хорошо (нет критических аномалий или первый запуск) — сохраняем новые метрики
    await r.hset(STATS_KEY, mapping=current_stats)
    logger.info("Метрики успешно сохранены в Redis.")


def fallback_head_DLQ(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # 1. Легкое извлечение URL
        url_dict = kwargs.get("url_dict")
        if not url_dict and len(args) >= 2:
            url_dict = args[1]

        url = url_dict.get("file_url") if url_dict else None

        if not url:
            # Если URL вообще не пришел, даже не пытаемся стучаться
            return None

        # 2. ФЕЙСКОНТРОЛЬ (Проверка Карантина)
        # Делаем один запрос в Redis, чтобы забрать текущее состояние
        dlq_item_str = await redis_pool.hget(EXCEL_SRC_DLQ, url)

        dlq_state = None
        base_count_attempt = 0

        if dlq_item_str:
            dlq_state = json.loads(dlq_item_str)
            failed_at = dlq_state.get("failed_at", 0)

            # Проверяем, прошло ли 20 минут
            if time() - failed_at < BAN_TIME:
                # Время не вышло. Молча возвращаем None, не трогая сеть.
                return None
            else:
                # Время вышло. Выпускаем из карантина, но запоминаем прошлые ошибки
                base_count_attempt = len(dlq_state.get("attempts", []))
        else:
            dlq_state = {"meta_info": url_dict, "attempts": []}

        # 3. БОЕВОЙ ЦИКЛ (3 попытки)
        for i in range(1, 4):
            current_attempt = base_count_attempt + i

            try:
                result: Optional[Dict[str, Optional[str]]] = await func(*args, **kwargs)

                if result is None:
                    raise Exception("Сервер ответил но все заголовки оказались пустыми")
                # Если успех — вычищаем ссылку из Карантина
                if dlq_item_str:
                    await redis_pool.hdel(EXCEL_SRC_DLQ, url)

                return result

            except aiohttp.ClientResponseError as e:
                err_obj = {
                    "attempt": current_attempt,
                    "type": f"HTTP {e.status}",
                    "msg": e.message,
                }
            except aiohttp.ClientConnectionError as e:
                err_obj = {
                    "attempt": current_attempt,
                    "type": "ConnectionError",
                    "details": str(e),
                }
            except asyncio.TimeoutError:
                err_obj = {
                    "attempt": current_attempt,
                    "type": "Timeout",
                    "details": "Превышено время ожидания",
                }
            except Exception as e:
                err_obj = {
                    "attempt": current_attempt,
                    "type": e.__class__.__name__,
                    "details": str(e),
                }

            # Складываем ошибку в локальный массив
            dlq_state["attempts"].append(err_obj)

            # Exponential Backoff: перед 2-й попыткой спим 2 сек, перед 3-й спим 4 сек
            if i < 3:
                await asyncio.sleep(2**i)

        # 4. ФИКСАЦИЯ ПРОВАЛА
        # Если цикл закончился, и мы не сделали return result, значит все 3 попытки сгорели.
        # Обновляем время падения и пишем в Redis ОДИН РАЗ.
        dlq_state["failed_at"] = time()

        await redis_pool.hset(
            EXCEL_SRC_DLQ, url, json.dumps(dlq_state, ensure_ascii=False)
        )

        # Возвращаем None, так как получить Response не удалось
        return None

    return wrapper


@fallback_head_DLQ
async def check_single_url(
    session: aiohttp.ClientSession, url_dict: Dict
) -> Optional[Dict[str, Optional[str]]]:
    """
    Функция  которая возвращает ответ в виде обьекта response по конкретно одной ссылке excel
    """

    url_excel = url_dict.get("file_url", None)

    if not url_excel:
        return None

    async with session.head(url_excel, allow_redirects=True) as response:
        response.raise_for_status()

        ETag = response.headers.get("ETag", "")
        Last_Modified = response.headers.get("Last-Modified", "")
        Content_Length = response.headers.get("Content-Length", "")

        # Если хотя бы один имеет значение то не отправляем в DLQ
        has_valid_headers = (
            bool(ETag and ETag.strip())
            or bool(Last_Modified and Last_Modified.strip())
            or bool(Content_Length and Content_Length.strip())
        )

        url_dict["Etag"] = ETag
        url_dict["Last_Modified"] = Last_Modified
        url_dict["Content-Length"] = Content_Length

        if not has_valid_headers:
            # TODO: Как то добавить в DLQ
            # Впринципе можно это и в декораторе сделать, проверкой result на None
            return None
        else:
            return url_dict


async def parse_head_info(session: aiohttp.ClientSession, parsed_data: List[Dict]):
    """
    Принимает спаршенные из HTML ссылки на эксель файлы
    и делает по каждой из них HEAD-запрос, что бы в каждый словарь ссылки
    добавить поля "Etag" и "Last-Modified"
    """

    def chunker(items: List[Dict], slice_size: int = BATCH_SIZE):
        for position in range(0, len(items), slice_size):
            yield items[position : position + slice_size]

    sucsess_src = 0
    failed_src = 0

    result = []

    for slice in chunker(parsed_data):
        task_queue = [check_single_url(session, url_dict) for url_dict in slice]

        batch_result = await asyncio.gather(*task_queue)

        for url_result in batch_result:
            if not url_result:
                failed_src += 1  # ХЗ
                continue
            sucsess_src += 1  # ХЗ
            result.append(url_result)

        jitter = random.uniform(0.5, 1.5)

        await asyncio.sleep(jitter)

    return result


async def process_schedules_to_redis(parsed_data: List[Dict]):
    """
    Записывает расписания в Redis и логирует изменения.
    Сравнивает новые данные (ETag, Last-Modified) с кэшем для выявления обновлений.
    """
    new_files_count = 0
    updated_files_count = 0

    for item in parsed_data:
        key = item.get("composite_key")
        if not key:
            continue

        # Пытаемся достать старую запись из Redis
        existing_item_str = await redis_pool.hget(SCHEDULES_KEY, key)

        if not existing_item_str:
            # СЦЕНАРИЙ 1: Абсолютно новый файл (раньше этого ключа не было)
            new_files_count += 1

            item_json = json.dumps(item, ensure_ascii=False)
            await redis_pool.hset(SCHEDULES_KEY, key, item_json)

            # TODO: Пуш в очередь Downloader'а
            # await redis_pool.lpush(DOWNLOADER_QUEUE, item_json)

        else:
            # СЦЕНАРИЙ 2: Файл уже есть в базе. Нужно сравнить на изменения.
            existing_item = json.loads(existing_item_str)
            is_changed = False

            # Проверяем все возможные маркеры изменений:

            # 1. Изменилась сама ссылка (админ удалил старый файл и залил новый с другим именем)
            if item.get("file_url") != existing_item.get("file_url"):
                is_changed = True

            # 2. Изменился ETag (самый надежный маркер)
            elif item.get("Etag") and item.get("Etag") != existing_item.get("Etag"):
                is_changed = True

            # 3. Изменилась дата модификации (запасной вариант)
            elif item.get("Last_Modified") and item.get(
                "Last_Modified"
            ) != existing_item.get("Last_Modified"):
                is_changed = True

            # 4. Изменился размер файла (фоллбэк, если сервер не отдал ни ETag, ни дату)
            elif item.get("Content-Length") and item.get(
                "Content-Length"
            ) != existing_item.get("Content-Length"):
                is_changed = True

            # Если обнаружили изменения — обновляем кэш и кидаем задачу на скачивание
            if is_changed:
                updated_files_count += 1

                item_json = json.dumps(item, ensure_ascii=False)
                await redis_pool.hset(SCHEDULES_KEY, key, item_json)

                # TODO: Пуш в очередь Downloader'а
                # await redis_pool.lpush(DOWNLOADER_QUEUE, item_json)

    logger.info(
        f"Скан завершен. Всего файлов: {len(parsed_data)}. "
        f"Новых: {new_files_count}. Обновленных: {updated_files_count}."
    )
