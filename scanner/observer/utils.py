from typing import Literal, Tuple, Dict, List, Optional
from urllib.parse import urljoin
from functools import wraps
from time import time
import random
import bs4
import aiohttp
import asyncio
import logging
import json

from shared import NewMessage, proxy

from shared import (
    CheckedURL,
    redis_pool,
    NotCheckedURL,
    InstituteSelectors,
    THRESHOLDS,
    STATS_KEY,
    SCHEDULES_KEY,
    EXCEL_SRC_DLQ,
    BAN_TIME,
    BATCH_SIZE,
    DOWNLOADER_QUEUE,
    DOMStructureChangedError,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Observer")


PROXY_URL_PARSING = f"http://{proxy.PROXY_LOGIN_PARSING}:{proxy.PROXY_PASSWORD_PARSING}@{proxy.PROXY_HOST}:{proxy.PROXY_PORT}"


def parse_and_count_schedule(
    soup: bs4.BeautifulSoup, base_url: str = "https://rguk.ru"
) -> Tuple[Dict[str, int], List[NotCheckedURL]]:
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

                    url_object = NotCheckedURL(
                        composite_key=composite_key,
                        file_title=file_title,
                        institute=inst_name,
                        study_form=study_form,
                        file_url=file_url,
                        view_url=view_url,  # pyright: ignore
                        logo_url=logo_url,
                    )

                    results.append(url_object)

    return stats, results


async def check_anomaly_and_save_stats(current_stats: dict):
    """Сверяет текущие метрики с прошлыми из Redis. Если всё ок - перезаписывает."""

    # Пытаемся получить прошлые метрики
    past_stats_raw = await redis_pool.hgetall(STATS_KEY)

    if past_stats_raw:
        past_stats = {k: int(v) for k, v in past_stats_raw.items()}
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
            logger.error(anomaly_reasons)
            await send_tg_alert(
                "DEAD",
                "АНОМАЛИЯ ПАРСИНГА! Обнаружено критическое падение тегов",
                anomaly_reasons,
            )
            raise DOMStructureChangedError("Anomaly detected. Halting execution.")

        # Если аномалий нет, но были любые изменения — просто шлем инфо-уведомление
        elif info_changes:
            await send_tg_alert(
                msg_level="INFO",
                msg="Изменение в структуре (в пределах нормы)",
                details=info_changes,
            )

    else:
        logger.info("Прошлые метрики не найдены. Это первый запуск (Холодный старт).")

    # Если всё хорошо (нет критических аномалий или первый запуск) — сохраняем новые метрики
    await redis_pool.hset(STATS_KEY, mapping=current_stats)
    logger.info("Метрики успешно сохранены в Redis.")


def fallback_head_DLQ(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # 1. Легкое извлечение URL
        url_obj = kwargs.get("url_obj")
        if not url_obj and len(args) >= 2:
            url_obj = args[1]

        url = None

        if url_obj is None:
            return None

        url = getattr(url_obj, "file_url", None)

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
            dlq_state = {"meta_info": url_obj.model_dump(), "attempts": []}

        # 3. БОЕВОЙ ЦИКЛ (3 попытки)
        for i in range(1, 4):
            current_attempt = base_count_attempt + i

            try:
                result: Optional[NotCheckedURL] = await func(*args, **kwargs)

                if result is None:
                    raise Exception("Сервер ответил но все заголовки оказались пустыми")
                # Если успех — вычищаем ссылку из Карантина
                if dlq_item_str:
                    await redis_pool.hdel(EXCEL_SRC_DLQ, url)

                return result

            except aiohttp.ClientResponseError as e:
                err_obj = {
                    "attempt": current_attempt,
                    "msg": "HTTP Error",
                    "details": e.status,
                }
            except aiohttp.ClientConnectionError as e:
                err_obj = {
                    "attempt": current_attempt,
                    "msg": "ConnectionError",
                    "details": str(e),
                }
            except asyncio.TimeoutError:
                err_obj = {
                    "attempt": current_attempt,
                    "msg": "Timeout",
                    "details": "Превышено время ожидания",
                }
            except Exception as e:
                err_obj = {
                    "attempt": current_attempt,
                    "msg": e.__class__.__name__,
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

        # Отправляю только 1 сообщение, поскольку 1 сообщение = 1 файл
        # нет смысла сыпать весь dlq_state
        last_attempt = dlq_state["attempts"][-1]
        await send_tg_alert(
            msg_level="WARN",
            msg="Ссылка по HEAD-запросу попала в DLQ",
            details=last_attempt["msg"],
        )

        # Возвращаем None, так как получить Response не удалось
        return None

    return wrapper


@fallback_head_DLQ
async def check_single_url(
    session: aiohttp.ClientSession, url_obj: NotCheckedURL
) -> Optional[CheckedURL]:
    """
    Функция  которая возвращает ответ в виде обьекта response по конкретно одной ссылке excel
    """

    url_excel = url_obj.file_url

    if not url_excel:
        return None

    async with session.head(
        url_excel, allow_redirects=True, proxy=PROXY_URL_PARSING
    ) as response:
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

        if not has_valid_headers:
            # HACK: Отправляем в DLQ
            return None
        else:
            result = CheckedURL(
                **url_obj.model_dump(),
                ETag=ETag,
                LastModified=Last_Modified,  # pyright: ignore
                ContentLength=Content_Length,  # pyright: ignore
            )

            return result


async def parse_head_info(
    session: aiohttp.ClientSession, parsed_data: List[NotCheckedURL]
) -> List[CheckedURL]:
    """
    Принимает спаршенные из HTML ссылки на эксель файлы
    и делает по каждой из них HEAD-запрос, что бы в каждый словарь ссылки
    добавить поля "Etag" и "Last-Modified"
    """

    def chunker(items: List[NotCheckedURL], slice_size: int = BATCH_SIZE):
        for position in range(0, len(items), slice_size):
            yield items[position : position + slice_size]

    sucsess_src = 0
    failed_src = 0

    result: List[CheckedURL] = []

    for slice in chunker(parsed_data):
        task_queue = [check_single_url(session, url_obj) for url_obj in slice]

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


async def process_schedules_to_redis(parsed_data: List[CheckedURL]):
    """
    Записывает расписания в Redis и логирует изменения.
    Сравнивает новые данные (ETag, Last-Modified) с кэшем для выявления обновлений.
    """
    new_files_count = 0
    updated_files_count = 0

    for item in parsed_data:
        key = item.composite_key

        # Пытаемся достать старую запись из Redis
        existing_item_str = await redis_pool.hget(SCHEDULES_KEY, key)

        if not existing_item_str:
            # СЦЕНАРИЙ 1: Абсолютно новый файл (раньше этого ключа не было)
            new_files_count += 1

            item_json = item.model_dump_json(by_alias=True)
            await redis_pool.hset(SCHEDULES_KEY, key, item_json)

            await redis_pool.xadd(
                DOWNLOADER_QUEUE, {"payload": item_json, "type": "lessons"}
            )

            await send_tg_alert(
                msg_level="INFO",
                msg="Файл отправлен на скачивание",
                details="Новый эксель файл",
            )

        else:
            # СЦЕНАРИЙ 2: Файл уже есть в базе. Нужно сравнить на изменения.
            existing_item = json.loads(existing_item_str)
            is_changed = False

            # Проверяем все возможные маркеры изменений:

            # 1. Изменилась сама ссылка (админ удалил старый файл и залил новый с другим именем)
            if item.file_url != existing_item.get("file_url"):
                is_changed = True

            # 2. Изменился ETag (самый надежный маркер)
            elif item.ETag and item.ETag != existing_item.get("ETag"):
                is_changed = True

            # 3. Изменилась дата модификации (запасной вариант)
            elif item.LastModified and item.LastModified != existing_item.get(
                "Last-Modified"
            ):
                is_changed = True

            # 4. Изменился размер файла (фоллбэк, если сервер не отдал ни ETag, ни дату)
            elif item.ContentLength and item.ContentLength != existing_item.get(
                "Content-Length"
            ):
                is_changed = True

            # Если обнаружили изменения — обновляем кэш и кидаем задачу на скачивание
            if is_changed:
                updated_files_count += 1
                item_json = item.model_dump_json(by_alias=True)
                await redis_pool.hset(SCHEDULES_KEY, key, item_json)

                # ПУШ В STREAM
                await redis_pool.xadd(
                    DOWNLOADER_QUEUE, {"payload": item_json, "type": "lessons"}
                )

                await send_tg_alert(
                    msg_level="INFO",
                    msg="Файл отправлен на скачивание",
                    details="Обновление эксель файла",
                )

    logger.info(
        f"Скан завершен. Всего файлов: {len(parsed_data)}. "
        f"Новых: {new_files_count}. Обновленных: {updated_files_count}."
    )


async def send_tg_alert(
    msg_level: Literal["INFO", "WARN", "ERROR", "CRITICAL", "DEAD"],
    msg: str,
    details: List[str] | str,
):
    new_message = NewMessage(
        service="Observer",
        msg_level=msg_level,
        msg=msg,
        details=details,  # pyright: ignore завали ебальник
    )

    # Готовим плоский словарь для Redis XADD
    payload = {
        "service": new_message.service,
        "msg_level": new_message.msg_level,
        "msg": new_message.msg,
    }

    # Тот самый нюанс: если кто-то из микросервисов передаст сюда список,
    # нам нужно превратить его в JSON-строку, чтобы Redis его съел.
    if isinstance(new_message.details, list):
        payload["details"] = json.dumps(new_message.details, ensure_ascii=False)
    else:
        payload["details"] = new_message.details

    try:
        await redis_pool.xadd("notifier:queue", payload)  # pyright: ignore
    except Exception as e:
        print(f"⚠️ Ошибка отправки алерта в очередь: {e}")
