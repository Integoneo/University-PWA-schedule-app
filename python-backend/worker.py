import asyncio
from xxhash import xxh64
import json
from datetime import datetime, timezone
import redis.asyncio as aioredis
import redis
from sqlmodel import select, insert, delete, func

# Импортируем наш асинхронный движок и фабрику сессий
from app.db.engine import get_async_session
from app.models.schedule import Institute, Group, Teacher, Lesson
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
        raw_split = data.split()  # type: ignore
        short_name = []

        for i, word in enumerate(raw_split):
            if word.upper() in IGNORED_WORDS:
                raw_split[i] = word.lower()
                short_name.append(raw_split[i])
            else:
                raw_split[i] = word.capitalize()
                short_name.append(raw_split[i])

        name = " ".join(raw_split)
        short_name = "".join(short_name)
    return [name, short_name]


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

                            new_group = Group(
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

                            session.add(new_group)

                            await session.flush()

                        # 2. ИНСТИТУТ ЕСТЬ, НО ГРУППА НОВАЯ
                        elif inst_match and not group_match:
                            if inst_match.id is None:
                                raise ORMStateError(
                                    f"Аномалия ORM: Институт '{full_inst_name}' успешно прошел flush, "
                                    f"но база данных не вернула ID."
                                )

                            new_group = Group(
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

                            session.add(new_group)

                            await session.flush()

                        # 3. ИНСТИТУТ И ГРУППА УЖЕ СУЩЕСТВУЮТ
                        elif inst_match and group_match:
                            hash_from_db = group_match.data_hash

                            # ХЭШ ОДИНАКОВЫЙ - РАСПИСАНИЕ ГРУППЫ ДАЖЕ НЕ МЕНЯЛОСЬ - СКИП
                            if check_hash == hash_from_db:
                                # Можно прикрутить логгирование на уровне INFO
                                continue

                    print(
                        f"[{msg_id.decode('utf-8')}] Асинхронно обрабатываем JSON: {schedule_json.get('Group')}"
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
