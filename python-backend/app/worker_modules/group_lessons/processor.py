from typing import Tuple
from sqlmodel import select, delete, func, col
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schedule import (
    Educational_form,
    Institute,
    Group,
    Teacher,
    Lesson,
    GroupStatus,
    LessonTeacherLink,
)
from .schemas import SchedulePayloadSchema
from .utils import merge_lessons_logic
import redis.asyncio as aioredis
from app.db.cache import CacheKeys
from app.db.config import settings


class ORMStateError(Exception):
    pass


async def process_schedule(
    session: AsyncSession, schedule: SchedulePayloadSchema, raw_hash: str
) -> Tuple[int, bool]:
    """
    Основная логика обновления расписания.
    Принимает УЖЕ валидированные данные от Pydantic.
    """

    r = aioredis.from_url(settings.REDIS_URL)

    # === БЛОК 1: ИНСТИТУТ И ГРУППА ===
    request = select(Institute).where(
        func.similarity(Institute.name, schedule.institute) >= 0.90,
        Institute.short_name == schedule.institute_short_name,
    )
    inst_match = (await session.scalars(request)).first()

    request = select(Educational_form).where(
        func.similarity(Educational_form.name, schedule.education_form) >= 0.90,
    )
    edu_form_match = (await session.scalars(request)).first()

    if not edu_form_match:
        edu_form_match = Educational_form(name=schedule.education_form)  # type: ignore
        await session.flush()

    if not inst_match:
        inst_match = Institute(
            name=schedule.institute,
            short_name=schedule.institute_short_name,
            logo_url=schedule.logo_url,
        )

        session.add(inst_match)
        await r.delete(CacheKeys.institutes)
        await session.flush()

    # Pyright: Завали ебальник
    if inst_match.id is None or edu_form_match.id is None:
        raise ORMStateError(
            f"Аномалия БД: Институту '{schedule.institute}' не присвоен ID"
        )

    request = select(Group).where(
        col(Group.institute_id) == inst_match.id,
        Group.name == schedule.group,
    )
    group_match = (await session.scalars(request)).first()

    if schedule.logo_url != "" and schedule.logo_url != inst_match.logo_url:
        inst_match.logo_url = schedule.logo_url

    if not group_match:
        group_match = Group(
            name=schedule.group,
            course=schedule.course,
            education_form_id=edu_form_match.id,
            start_education_date=schedule.start_education_date,
            end_education_date=schedule.end_education_date,
            institute_id=inst_match.id,
            data_hash=raw_hash,
            view_url=schedule.view_url,
        )
        session.add(group_match)

        await r.delete(CacheKeys.institutes)

        await session.flush()
        notify_response = (group_match.id, False)  # Группа новая, уведомлять некого
    else:
        notify_response = (group_match.id, True)
        # Если хэши совпали - расписание не менялось
        if group_match.data_hash == raw_hash and group_match.id is not None:
            return (group_match.id, False)

        # 🛡 TYPE GUARD: Защита перед delete запросом
        if group_match.id is None:
            raise ORMStateError(
                f"Аномалия БД: Группе '{schedule.group}' не присвоен ID"
            )

        await r.delete(CacheKeys.group(group_match.id))

        subquery = select(Lesson.id).where(col(Lesson.group_id) == group_match.id)
        await session.execute(
            delete(LessonTeacherLink).where(
                col(LessonTeacherLink.lesson_id).in_(subquery)
            )
        )

        # Удаляем старые пары
        await session.execute(
            delete(Lesson).where(col(Lesson.group_id) == group_match.id)
        )

        group_match.data_hash = raw_hash
        group_match.start_education_date = schedule.start_education_date
        group_match.end_education_date = schedule.end_education_date
        session.add(group_match)
        await session.flush()

    if group_match.id is None:
        raise ORMStateError("Аномалия БД: Потерян ID группы перед сохранением пар")

    # === БЛОК 2: СОРТИРОВКА И СХЛОПЫВАНИЕ ПАР ===
    merged_lessons_list, unique_teacher_names = merge_lessons_logic(schedule.lessons)

    teacher_cache = {}
    if unique_teacher_names:
        request = select(Teacher).where(col(Teacher.name).in_(unique_teacher_names))
        existing_teachers = await session.scalars(request)
        teacher_cache = {t.name: t for t in existing_teachers if t.name}

        missing_names = unique_teacher_names - set(teacher_cache.keys())

        if missing_names:
            new_teachers = [Teacher(name=name) for name in missing_names]
            session.add_all(new_teachers)
            await session.flush()
            for t in new_teachers:
                if t.name:
                    teacher_cache[t.name] = t

    # === БЛОК 4: ДОБАВЛЕНИЕ ПАР В БД ===
    for lesson in merged_lessons_list:
        lesson_teacher_objs = [teacher_cache[name] for name in lesson.teachers]

        # 🛡 УСПОКАИВАЕМ PYRIGHT: Гарантируем, что алгоритм выше отработал верно
        assert lesson.number_of_lesson is not None, (
            "Логическая ошибка: паре не был присвоен номер!"
        )

        new_lesson = Lesson(
            day_of_week=lesson.day_of_week,
            start_time=lesson.start_time,
            end_time=lesson.end_time,
            lesson_name=lesson.lesson,
            educational_place=lesson.educational_place,
            is_even_week=lesson.is_even_week,
            number_of_lesson=lesson.number_of_lesson,
            classroom=lesson.classroom,
            type_of_lesson=lesson.type_of_lesson,
            group_id=group_match.id,
            teachers=lesson_teacher_objs,
        )
        session.add(new_lesson)

    group_match.status = GroupStatus.READY
    await session.commit()

    return notify_response  # type: ignore

    # TODO: МЕСТО ДЛЯ ОТПРАВКИ УВЕДОМЛЕНИЯ ОБ ИЗМЕНЕНИИ ПАР
