import asyncio
import json
from datetime import datetime, timezone
import redis.asyncio as aioredis
from sqlmodel import select

# Импортируем наш асинхронный движок и фабрику сессий
from app.db.engine import async_session_maker
from app.models.schedule import Institute, Group, Teacher, Lesson
from app.db.config import settings

REDIS = settings.REDIS_URL


def merge_consecutive_lessons(raw_lessons: list[dict]) -> list[dict]:
    """
    Проходит по массиву сырых пар и склеивает те, которые идут подряд,
    в одной аудитории, у одного препода и совпадают по времени.
    """
    if not raw_lessons:
        return []

    merged = []

    for current in raw_lessons:
        if not merged:
            merged.append(current.copy())
            continue

        prev = merged[-1]

        # 1. Проверяем совпадение базовой метаинформации
        is_same_day = prev.get("day_of_week") == current.get("day_of_week")
        is_same_week = prev.get("is_even_week") == current.get("is_even_week")
        is_same_lesson = prev.get("lesson") == current.get("lesson")
        is_same_type = prev.get("type_of_lesson") == current.get("type_of_lesson")
        is_same_room = prev.get("classroom") == current.get("classroom")
        is_same_place = prev.get("educational_place") == current.get(
            "educational_place"
        )

        # 2. Проверяем идентичность списков преподавателей (сортируем для надежности)
        prev_teachers = sorted([str(t) for t in prev.get("teachers", [])])
        curr_teachers = sorted([str(t) for t in current.get("teachers", [])])
        is_same_teachers = prev_teachers == curr_teachers

        # 3. Главное условие: время окончания предыдущей == время начала текущей
        # В JSON это строки вида "11:30"
        is_consecutive_time = prev.get("end_time") == current.get("start_time")

        # Если ВСЕ условия совпали - склеиваем!
        if (
            is_same_day
            and is_same_week
            and is_same_lesson
            and is_same_type
            and is_same_room
            and is_same_place
            and is_same_teachers
            and is_consecutive_time
        ):
            # Магия здесь: просто растягиваем время окончания предыдущей пары
            prev["end_time"] = current.get("end_time")
        else:
            # Иначе добавляем текущую пару как новую независимую
            merged.append(current.copy())

    return merged


async def process_schedule_payload(payload: dict) -> str | None:
    """Нативная асинхронная функция БД со строгой типизацией"""

    async with async_session_maker() as session:
        # === 1. Извлечение и строгая типизация данных ===
        # Явно говорим линтеру: "Это точно будет строкой!"
        inst_name = str(payload.get("Institute", "Неизвестный институт"))
        group_name = str(payload.get("Group", "Неизвестная группа"))

        start_str = payload.get("Start-education-date")
        end_str = payload.get("End-education-date")

        start_date = (
            datetime.strptime(str(start_str), "%d.%m.%Y").date()
            if start_str
            else datetime.now(timezone.utc).date()
        )
        end_date = (
            datetime.strptime(str(end_str), "%d.%m.%Y").date()
            if end_str
            else datetime.now(timezone.utc).date()
        )

        # === 2. Институт (Используем execute + scalars) ===
        # Это классический способ SQLAlchemy, который Pyright понимает на 100%
        result_inst = await session.execute(
            select(Institute).where(Institute.name == inst_name)
        )
        institute = result_inst.scalars().first()

        if not institute:
            institute = Institute(name=inst_name)
            session.add(institute)
            await session.commit()
            await session.refresh(institute)

        # Гарантируем линтеру, что после сохранения в БД id точно существует
        assert institute.id is not None

        # === 3. Группа ===
        result_group = await session.execute(
            select(Group).where(Group.name == group_name)
        )
        group = result_group.scalars().first()

        if not group:
            group = Group(
                name=group_name,
                course=str(payload.get("Course", "")),
                education_form=str(payload.get("Education-form", "")),
                start_education_date=start_date,
                end_education_date=end_date,
                institute_id=institute.id,
            )
            session.add(group)
        else:
            group.start_education_date = start_date
            group.end_education_date = end_date
            group.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await session.commit()
        await session.refresh(group)

        assert group.id is not None

        # === 4. Очищаем старое расписание ===
        result_lessons = await session.execute(
            select(Lesson).where(Lesson.group_id == group.id)
        )
        existing_lessons = result_lessons.scalars().all()

        for old_lesson in existing_lessons:
            await session.delete(old_lesson)
        await session.commit()

        # === 7. Записываем новые пары ===
        raw_lessons_payload = payload.get("lessons")

        size_of_merged = 0

        if isinstance(raw_lessons_payload, list):
            # Прогоняем сырой массив через функцию склейки
            merged_lessons_payload = merge_consecutive_lessons(raw_lessons_payload)

            size_of_merged = len(merged_lessons_payload)

            # Теперь итерируемся уже по чистому, склеенному массиву
            for lesson_data in merged_lessons_payload:
                teachers_list = []

                t_payload = lesson_data.get("teachers", [])
                if isinstance(t_payload, list):
                    for t_name in t_payload:
                        t_name_str = str(t_name)
                        t_result = await session.execute(
                            select(Teacher).where(Teacher.name == t_name_str)
                        )
                        teacher = t_result.scalars().first()

                        if not teacher:
                            teacher = Teacher(name=t_name_str)
                            session.add(teacher)
                            await session.commit()
                            await session.refresh(teacher)
                        teachers_list.append(teacher)

                st_time_str = str(lesson_data.get("start_time", "00:00"))
                en_time_str = str(lesson_data.get("end_time", "00:00"))
                st_time = (
                    datetime.strptime(st_time_str, "%H:%M").time()
                    if st_time_str
                    else datetime.strptime("00:00", "%H:%M").time()
                )
                en_time = (
                    datetime.strptime(en_time_str, "%H:%M").time()
                    if en_time_str
                    else datetime.strptime("00:00", "%H:%M").time()
                )

                new_lesson = Lesson(
                    group_id=group.id,
                    day_of_week=str(lesson_data.get("day_of_week", "")),
                    number_of_lesson=int(lesson_data.get("number_of_lesson", 0)),
                    is_even_week=bool(lesson_data.get("is_even_week", False)),
                    start_time=st_time,
                    end_time=en_time,
                    lesson_name=str(lesson_data.get("lesson", "")),
                    type_of_lesson=str(lesson_data.get("type_of_lesson", "")),
                    classroom=str(lesson_data.get("classroom", "")),
                    educational_place=str(lesson_data.get("educational_place", "")),
                    teachers=teachers_list,
                )
                session.add(new_lesson)

        await session.commit()
        print(
            f"✅ Успешно обновлено расписание для: {group_name}, добавлено {size_of_merged} записей"
        )
        return group_name


async def main_worker_loop():
    print("🎧 Нативный Async Worker запущен и ждет расписания...")
    r = aioredis.from_url(REDIS)

    try:
        while True:
            # type: ignore спасает от кривых аннотаций типов в самой библиотеке redis
            result = await r.blpop("ready_schedules")  # type: ignore

            if result:
                _, raw_data = result
                try:
                    payload = json.loads(raw_data.decode("utf-8"))
                    group_name = await process_schedule_payload(payload)

                    if group_name:
                        cache_key = f"cache:schedule:{group_name}"
                        await r.delete(cache_key)  # type: ignore
                        print(f"🗑️ Кэш {cache_key} сброшен.")

                except Exception as e:
                    print(f"❌ Произошла ошибка при обработке: {e}")

    except asyncio.CancelledError:
        # Это исключение прилетит, когда сервер начнет выключаться
        print("🛑 Получен сигнал завершения. Воркер корректно останавливается...")
    finally:
        # Закрываем соединение с Redis
        await r.close()
        print("🔌 Соединение с Redis закрыто.")
