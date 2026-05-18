import asyncio
from collections import defaultdict
from xxhash import xxh64
from enum import IntEnum
import json
from datetime import datetime
import redis.asyncio as aioredis
from sqlmodel import select, delete, func, col

# Импортируем наш асинхронный движок и фабрику сессий
from app.db.engine import get_async_session
from app.models.schedule import Institute, Group, Teacher, Lesson, GroupStatus
from app.db.config import settings

REDIS = settings.REDIS_URL


class ORMStateError(Exception):
    """
    Вызывается при неадекватном поведении ORM или БД.
    Например: когда после flush() объекту не был присвоен ID.
    """

    pass


class MissingCriticalFieldErorr(ValueError):
    """Вызывается, если в JSON из Redis отсутствует обязательные поля:
    "Institute", "Group", "lessons", "Start-education-date","End-education-date"
    """

    pass


def normalize_name(data: str) -> list:
    """
    Нормализует название института делает полное имя формата "Институт Мехатроники и Робототехники"
    а так же возвращает короткое имя института формата "ИМиР"
    """
    if isinstance(data, str):
        IGNORED_WORDS = {
            "И",
            "В",
            "НА",
            "С",
            "К",
            "ПО",
            "ЗА",
            "О",
            "ОБ",
            "У",
            "А",
            "НО",
        }
        raw_split = data.split()
        short_name = []

        for i, word in enumerate(raw_split):
            if word.upper() in IGNORED_WORDS:
                raw_split[i] = word.lower()
                # Для предлогов берем первую маленькую букву
                short_name.append(raw_split[i][0])
            else:
                raw_split[i] = word.capitalize()
                # ИСПРАВЛЕНИЕ: берем ТОЛЬКО первую букву (она уже заглавная)
                short_name.append(raw_split[i][0])

        name = " ".join(raw_split)
        short_name = "".join(short_name)

        return [name, short_name]


class DLQFormatError(Exception):
    pass


class DayOfWeek(IntEnum):
    MO = ПН = ПО = 0
    TU = ВТ = 1
    WE = СР = 2
    TH = ЧТ = ЧЕ = 3
    FR = ПТ = ПЯ = 4
    SA = СБ = СУ = 5
    SU = ВС = ВО = 6


# Выносим настройки схемы JSON на уровень модуля
KNOWN_FIELDS = {
    "day_of_week",
    "start_time",
    "end_time",
    "educational_place",
    "lesson",
    "is_even_week",
    "classroom",
    "type_of_lesson",
    "teachers",
    "number_of_lesson",
}

REQUIRED_FIELDS = {
    "day_of_week",
    "start_time",
    "end_time",
    "educational_place",
    "lesson",
    "is_even_week",
}

TIME_FIELDS = {"start_time", "end_time"}
REQ_STR_FIELDS = {"educational_place", "lesson"}
OPT_STR_FIELDS = {"classroom", "type_of_lesson"}


def format_and_validate_lesson(lesson: dict) -> None:
    # 1. МГНОВЕННАЯ СТРОГАЯ ПРОВЕРКА СХЕМЫ (Математика множеств)
    input_keys = set(lesson.keys())

    # Есть ли неизвестный мусор?
    unknown_fields = input_keys - KNOWN_FIELDS
    if unknown_fields:
        raise DLQFormatError(f"Обнаружены неизвестные поля: {unknown_fields}")

    # Все ли обязательные поля на месте?
    missing_fields = REQUIRED_FIELDS - input_keys
    if missing_fields:
        raise DLQFormatError(f"Отсутствуют обязательные поля: {missing_fields}")

    # 2. ОДИН ПРОХОД ПО ДАННЫМ
    # Оборачиваем в list(), потому что мы будем менять словарь in-place во время цикла
    for key, val in list(lesson.items()):
        if key == "day_of_week":
            if not isinstance(val, str):
                raise DLQFormatError("day_of_week не является строкой")
            prefix = val.strip().upper()[:2]
            try:
                lesson[key] = DayOfWeek[prefix].value
            except KeyError:
                raise DLQFormatError(f"Неизвестный формат дня недели: {prefix}")

        elif key in TIME_FIELDS:
            if not isinstance(val, str):
                raise DLQFormatError(f"{key} не является строкой")
            try:
                lesson[key] = datetime.strptime(val.strip(), "%H:%M").time()
            except ValueError:
                raise DLQFormatError(f"Неверный формат времени для {key}: {val}")

        elif key in REQ_STR_FIELDS:
            if not isinstance(val, str) or not val.strip():
                raise DLQFormatError(f"Поле {key} пустое или не строка")
            lesson[key] = val.strip()

        elif key == "is_even_week":
            if not isinstance(val, bool):
                raise DLQFormatError("is_even_week не является boolean")

        elif key in OPT_STR_FIELDS:
            if not val or isinstance(val, list):
                lesson[key] = ""
            else:
                lesson[key] = str(val).strip()

        elif key == "teachers":
            if not isinstance(val, list):
                raise DLQFormatError("Поле teachers не является списком")
            # Можно добавить валидацию, что внутри списка только строки
        elif key == "number_of_lesson":
            try:
                lesson[key] = int(val)
            except ValueError:
                raise DLQFormatError(
                    "Поле number_of_lesson не является числом или числовой строкой"
                )

    # 3. ДОЗАПОЛНЕНИЕ ОПЦИОНАЛЬНЫХ ПОЛЕЙ (если их вообще не прислали)
    if "teachers" not in lesson:
        lesson["teachers"] = []
    for opt_field in OPT_STR_FIELDS:
        if opt_field not in lesson:
            lesson[opt_field] = ""


def can_merge_lessons(lesson1: dict, lesson2: dict) -> bool:
    """
    Проверяет, можно ли склеить две пары в одну.
    Условие: стыковка по времени и полное совпадение метаданных.
    """
    # 1. Проверяем непрерывность времени (конец первой == начало второй)
    if lesson1["end_time"] != lesson2["start_time"]:
        return False

    # 2. Проверяем строковые поля
    fields_to_match = ["lesson", "classroom", "educational_place", "type_of_lesson"]
    for field in fields_to_match:
        if lesson1.get(field) != lesson2.get(field):
            return False

    # 3. Проверяем преподавателей (через множества, чтобы игнорировать порядок)
    if set(lesson1.get("teachers", [])) != set(lesson2.get("teachers", [])):
        return False

    return True


async def main_worker_loop():
    print("🎧 Нативный Async Worker запущен и ждет расписания...")
    r = aioredis.from_url(REDIS)

    STREAM_NAME = "ready_schedules"
    GROUP_NAME = "python"
    CONSUMER_NAME = "python-worker"

    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
    except aioredis.ResponseError:
        pass

    try:
        while True:
            # === ОБЕРТКА 1: REDIS (СЕТЬ) ===
            try:
                # Чтение с таймаутом в 2 секунды (block=2000), чтобы ловить CancelledError при выключении
                response = await r.xreadgroup(
                    GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=2000
                )

                if not response:
                    continue

                stream_name, messages = response[0]
                msg_id, data = messages[0]

                # === ОБЕРТКА 2: ВАЛИДАЦИЯ И БД ===
                try:
                    # Ключ в словаре приходит в байтах, поэтому использую b"payload"
                    payload = data.get(b"payload")
                    schedule_json = json.loads(payload)
                    check_hash = xxh64(
                        json.dumps(schedule_json).encode("utf-8")
                    ).hexdigest()

                    required_fields = {
                        "Institute",
                        "Group",
                        "lessons",
                        "Start-education-date",
                        "End-education-date",
                    }

                    if not (required_fields <= schedule_json.keys()):
                        # TODO: ========================
                        # TODO: =        Сделать       =
                        # TODO: =      Логгирование    =
                        # TODO: ========================
                        missing = required_fields - schedule_json.keys()
                        raise MissingCriticalFieldErorr(f"Отсутствуют поля: {missing}")

                    if not all(schedule_json[field] for field in required_fields):
                        # Находим, какие именно поля оказались пустыми, для точного лога
                        empty_fields = [
                            field
                            for field in required_fields
                            if not schedule_json[field]
                        ]
                        raise MissingCriticalFieldErorr(
                            f"Поля присутствуют, но они пустые: {empty_fields}"
                        )

                    # ==========НОРМАЛИЗАЦИЯ ИМЕН: ГРУППЫ И ИНСТИТУТА===============
                    full_inst_name, short_inst_name = normalize_name(
                        schedule_json.get("Institute")
                    )

                    schedule_json["Institute"] = full_inst_name
                    schedule_json["Short_name"] = short_inst_name

                    raw_group_name = schedule_json["Group"]

                    normalized_group_name = (
                        raw_group_name.strip().upper().replace(" ", "")
                    )

                    schedule_json["Group"] = normalized_group_name
                    # ==========НОРМАЛИЗАЦИЯ ИМЕН: ГРУППЫ И ИНСТИТУТА===============
                    # --------------------------------------------------------------
                    # ======================ВАЛИДАЦИЯ ДАТ===========================
                    raw_start = schedule_json["Start-education-date"]
                    raw_end = schedule_json["End-education-date"]
                    try:
                        schedule_json["Start-education-date"] = datetime.strptime(
                            schedule_json["Start-education-date"], "%d.%m.%Y"
                        ).date()
                        schedule_json["End-education-date"] = datetime.strptime(
                            schedule_json["End-education-date"], "%d.%m.%Y"
                        ).date()
                    except ValueError:
                        raise ValueError(
                            f"Неверный формат дат обучения у группы {schedule_json['Group']}. "
                            f"Ожидается 'ДД.ММ.ГГГГ', получено: start='{raw_start}', end='{raw_end}'"
                        )
                    # ======================ВАЛИДАЦИЯ ДАТ===========================

                    async for session in get_async_session():
                        # Структура json которая будет приходить с плюсового воркера,
                        # я ее такой и оставлю навсегда
                        # {
                        #     "Course": "3",                                  // OPT:
                        #     "Education-form": "очная",                      // OPT:
                        #     "End-education-date": "21.06.2026",             // REQ:
                        #     "Group": "ммц-123",                             // REQ:
                        #     "Institute": "институт мехатроники...",         // REQ:
                        #     "Institute-icon-url": "https://...",            // OPT:
                        #     "Start-education-date": "05.03.2026",           // REQ:
                        #     "lessons": [                                    // REQ:
                        #         {
                        #             "classroom": "6206",                    // OPT:
                        #             "day_of_week": "ПН",                    // REQ:
                        #             "educational_place": "Учебная площадка",// REQ:
                        #             "end_time": "11:30",                    // REQ:
                        #             "is_even_week": false,                  // REQ:
                        #             "lesson": "Основы дизайна",             // REQ:
                        #             "start_time": "10:50",                  // REQ:
                        #             "number_of_lesson": 1                   // OPT:
                        #
                        #             "teachers": [                           // OPT:
                        #                 "Чугуй Н.В."
                        #             ],
                        #             "type_of_lesson": "Лек"                 // OPT:
                        #         },
                        #         ...
                        #     ]
                        # }
                        #
                        #   1. Ищу такой институт в базе, так же на всякий случай применяю расстояние Левенштейна
                        #
                        request = select(Institute).where(
                            func.similarity(Institute.name, full_inst_name) >= 0.90,
                            Institute.short_name == short_inst_name,
                        )

                        request = request.order_by(
                            func.similarity(Institute.name, full_inst_name).desc()
                        )

                        exec = await session.scalars(request)

                        inst_match = exec.first()

                        request = (
                            select(Group)
                            .join(Institute)
                            .where(
                                func.similarity(Institute.name, full_inst_name) >= 0.90,
                                Group.name == schedule_json["Group"],
                            )
                        )

                        exec = await session.scalars(request)
                        group_match = exec.first()

                        # 1. НЕТ ИНСТИТУТА ЗНАЧИТ И ГРУППЫ НЕТ
                        if not inst_match:
                            new_inst = Institute(
                                name=full_inst_name, short_name=short_inst_name
                            )

                            session.add(new_inst)
                            await session.flush()

                            if new_inst.id is None:
                                raise ORMStateError(
                                    f"Аномалия ORM: Институт '{full_inst_name}' успешно прошел flush, "
                                    f"но база данных не вернула ID."
                                )

                            group_match = Group(
                                name=schedule_json["Group"],
                                course=schedule_json.get("Course", None),
                                education_form=schedule_json.get(
                                    "Education-form", None
                                ),
                                start_education_date=schedule_json[
                                    "Start-education-date"
                                ],
                                end_education_date=schedule_json["End-education-date"],
                                institute_id=new_inst.id,
                                data_hash=check_hash,
                            )

                            session.add(group_match)

                            await session.flush()

                        # 2. ИНСТИТУТ ЕСТЬ, НО ГРУППА НОВАЯ
                        elif inst_match and not group_match:
                            if inst_match.id is None:
                                raise ORMStateError(
                                    f"Аномалия ORM: Институт '{full_inst_name}' успешно прошел flush, "
                                    f"но база данных не вернула ID."
                                )

                            group_match = Group(
                                name=schedule_json["Group"],
                                course=schedule_json.get("Course", None),
                                education_form=schedule_json.get(
                                    "Education-form", None
                                ),
                                start_education_date=schedule_json[
                                    "Start-education-date"
                                ],
                                end_education_date=schedule_json["End-education-date"],
                                institute_id=inst_match.id,
                                data_hash=check_hash,
                            )

                            session.add(group_match)

                            await session.flush()

                        # 3. ИНСТИТУТ И ГРУППА УЖЕ СУЩЕСТВУЮТ
                        elif inst_match and group_match:
                            hash_from_db = group_match.data_hash

                            # ХЭШ ОДИНАКОВЫЙ - РАСПИСАНИЕ ГРУППЫ ДАЖЕ НЕ МЕНЯЛОСЬ - СКИП
                            if check_hash == hash_from_db:
                                # Можно прикрутить логгирование на уровне INFO
                                break

                            # ХЭШИ РАЗЛИЧАЮТСЯ, УДАЛЕМ ПРОШЛОЕ РАСПИСАНИЕ ГРУППЫ ПОЛНСТЬЮ

                            if group_match.id is None:
                                raise ORMStateError(
                                    f"Аномалия ORM: В группе '{normalized_group_name}' нашлась в БД, "
                                    f"но база данных не вернула ID."
                                )

                            await session.execute(
                                delete(Lesson).where(
                                    col(Lesson.group_id) == group_match.id
                                )
                            )

                            # 2. Обновляем хэш и даты у существующей группы
                            group_match.data_hash = check_hash
                            group_match.start_education_date = schedule_json[
                                "Start-education-date"
                            ]
                            group_match.end_education_date = schedule_json[
                                "End-education-date"
                            ]
                            group_match.course = schedule_json["Course"]
                            group_match.education_form = schedule_json.get(
                                "Education-form"
                            )

                            # Сохраняем изменения группы
                            session.add(group_match)
                            await session.flush()

                        # В этом словаре ключем является поле из json is_even_week
                        # Значением является словарь с ключами от 0-6 -> понедельник-воскресенье
                        # Значения во вложенном словаре -> список пар
                        lessons_by_week = {
                            False: defaultdict(list),
                            True: defaultdict(list),
                        }

                        # Разложим пары по дням в удобном словаре
                        for lesson in schedule_json["lessons"]:
                            format_and_validate_lesson(lesson)

                            lessons_by_week[lesson["is_even_week"]][
                                lesson["day_of_week"]
                            ].append(lesson)

                        # Отсортируем пары внутри каждого дня
                        for is_even in lessons_by_week:
                            for day in lessons_by_week[is_even]:
                                # Сортируем по полю start_time
                                lessons_by_week[is_even][day].sort(
                                    key=lambda x: x["start_time"]
                                )

                        # ====================== СХЛОПЫВАНИЕ ПАР ============================
                        for is_even in lessons_by_week:
                            for day in lessons_by_week[is_even]:
                                daily_lessons = lessons_by_week[is_even][day]

                                # Если пар в этот день нет - пропускаем
                                if not daily_lessons:
                                    continue

                                merged_day = []
                                # Берем первую пару за основу (работаем с оригинальной ссылкой)
                                current_lesson = daily_lessons[0]

                                # Начинаем проверять со второй пары и дальше
                                for next_lesson in daily_lessons[1:]:
                                    if can_merge_lessons(current_lesson, next_lesson):
                                        # Схлопываем! Просто отодвигаем время конца у текущей пары
                                        current_lesson["end_time"] = next_lesson[
                                            "end_time"
                                        ]
                                        # Заметь: next_lesson мы никуда не сохраняем, она просто исчезнет из памяти
                                    else:
                                        # Схлопывание прервалось. Текущая пара сформирована окончательно.
                                        merged_day.append(current_lesson)
                                        # Начинаем собирать новую пару
                                        current_lesson = next_lesson

                                # Не забываем добавить самую последнюю пару, на которой закончился цикл
                                merged_day.append(current_lesson)

                                # Теперь, когда пары окончательно сформированы, проставляем им реальные номера по порядку
                                for index, final_lesson in enumerate(merged_day):
                                    final_lesson["number_of_lesson"] = (
                                        index + 1
                                    )  # 0-й индекс станет 1-й парой

                                # Заменяем старый сырой список на новый, отфильтрованный и схлопнутый
                                lessons_by_week[is_even][day] = merged_day
                        # ===================================================================

                        # ====================== ФИНАЛ: ЗАГРУЗКА В БД =======================

                        # 1. Выгружаем ВСЕХ существующих преподавателей из базы одним запросом
                        # (Если у тебя в базе 1000 преподов, это займет копейки времени)
                        request = select(Teacher)
                        existing_teachers = await session.scalars(request)

                        # 2. Создаем In-Memory Кэш (Словарь).
                        # Ключ - имя строкой, Значение - сам объект БД Teacher.
                        # Это позволит нам искать преподов за О(1) и не дергать базу.
                        teacher_cache = {t.name: t for t in existing_teachers}

                        # Убеждаемся, что Pyright спокоен насчет ID группы
                        if group_match == None or group_match.id == None:
                            raise ORMStateError(
                                f"Аномалия ORM: Институт '{group_match}' успешно прошел flush, "
                                f"но база данных не вернула ID или сам обьект группы"
                            )

                        # 3. Финальный проход по очищенным и схлопнутым данным
                        for is_even in lessons_by_week:
                            for day in lessons_by_week[is_even]:
                                for lesson_dict in lessons_by_week[is_even][day]:
                                    # --- БЛОК УЧИТЕЛЕЙ ---
                                    # Собираем объекты преподавателей для текущей пары
                                    lesson_teacher_objs = []

                                    for teacher_name in lesson_dict["teachers"]:
                                        # Если препода нет в нашем кэше (и в базе соответственно)
                                        if teacher_name not in teacher_cache:
                                            # Создаем нового
                                            new_teacher = Teacher(name=teacher_name)
                                            # Регистрируем в Алхимии (она пока просто запомнит его)
                                            session.add(new_teacher)
                                            # КРИТИЧЕСКИ ВАЖНО: Добавляем в локальный кэш!
                                            # Если он встретится на следующей паре, мы возьмем его отсюда, а не создадим клона.
                                            teacher_cache[teacher_name] = new_teacher

                                        # Кладем готовый объект (старый или только что созданный) в список для пары
                                        lesson_teacher_objs.append(
                                            teacher_cache[teacher_name]
                                        )

                                    # --- БЛОК СОЗДАНИЯ ПАРЫ И СВЯЗЕЙ ---
                                    new_lesson = Lesson(
                                        # Простые поля
                                        day_of_week=lesson_dict["day_of_week"],
                                        start_time=lesson_dict["start_time"],
                                        end_time=lesson_dict["end_time"],
                                        lesson_name=lesson_dict["lesson"],
                                        educational_place=lesson_dict[
                                            "educational_place"
                                        ],
                                        is_even_week=is_even,  # Берем прямо из ключа внешнего цикла
                                        number_of_lesson=lesson_dict[
                                            "number_of_lesson"
                                        ],
                                        # Опциональные поля
                                        classroom=lesson_dict["classroom"],
                                        type_of_lesson=lesson_dict["type_of_lesson"],
                                        # МАГИЯ ОТНОШЕНИЙ SQLALCHEMY
                                        # 1. Связь с группой (передаем просто числовой ID)
                                        group_id=group_match.id,
                                        # 2. Связь с учителями (передаем список ПИТОНОВСКИХ ОБЪЕКТОВ)
                                        # ORM сама распарсит их ID и заполнит скрытую промежуточную таблицу (LinkTable)
                                        teachers=lesson_teacher_objs,
                                    )
                                    # Добавляем готовую пару в сессию
                                    session.add(new_lesson)

                        group_match.status = GroupStatus.READY
                        await session.commit()
                    # ===================================================================

                    print(
                        f"[{msg_id.decode('utf-8')}] Асинхронно обрабатал JSON: {schedule_json.get('Group')}"
                    )

                except MissingCriticalFieldErorr as e:
                    print(f"[{msg_id.decode('utf-8')}] Выкинут бракованный JSON: {e}")
                    pass

                await r.xack(STREAM_NAME, GROUP_NAME, msg_id)
                await r.xdel(STREAM_NAME, msg_id)

            except aioredis.ConnectionError:
                # Ловим отвал сети
                await asyncio.sleep(5)
            except Exception as e:
                # Ловим прочие непредвиденные ошибки
                print(f"Ошибка в цикле: {e}")
                await asyncio.sleep(5)

    except asyncio.CancelledError:
        # Это исключение прилетит, когда сервер начнет выключаться
        print("🛑 Получен сигнал завершения. Воркер корректно останавливается...")
    finally:
        # Закрываем соединение с Redis
        await r.close()
        print("🔌 Соединение с Redis закрыто.")
