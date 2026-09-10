from fastapi import APIRouter, Depends, Header, Response, status, HTTPException
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
import hashlib
import json
import redis.asyncio as aioredis

from app.db import cache
from app.db.engine import get_async_session  # Сессия для PostgreSQL
from app.db.cache import (
    get_redis_session,
    CacheKeys,
)  # Сессия для Redis и ключи для кэша
from app.api.endpoints.stats import track_activity_buffer
from app.models.api_dto import (
    GroupScheduleResponse,
    Institutes_PWA_schema,
    LessonPWA,
    TeacherPWA,
    TeacherScheduleResponse,
    TeacherLessonPWA,
)
from app.models.schedule import (
    AppConfig,
    Group,
    Institute,
    Lesson,
    Teacher,
    LessonTeacherLink,
)
from app.utils import send_tg_alert
from xxhash import xxh64

router = APIRouter(
    prefix="/client",
    tags=["Client App"],
    dependencies=[Depends(track_activity_buffer)],
)


@router.get("/config")
async def get_app_config(
    response: Response,
    if_none_match: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_session),
):
    """
    Возвращает системный конфиг. Поддерживает HTTP Caching (304 Not Modified) через ETags.
    """

    cache_key = CacheKeys.configs
    cached_config_str = None

    # 1. Безопасно пытаемся прочитать из Редиса
    try:
        cached_config_str = await redis.get(cache_key)
    except Exception as e:
        print(
            f"⚠️ [Redis Error on GET]: {e}. Блокировка кэша, идем напрямую в Postgres."
        )

    if not cached_config_str:
        query = select(AppConfig).where(AppConfig.key == "semester_config")
        result = await session.execute(query)
        config = result.scalars().first()

        if not config:
            return Response(
                status_code=status.HTTP_404_NOT_FOUND,
                content="Системный конфиг не найден",
            )

        config_json_bytes = json.dumps(config.value, sort_keys=True).encode("utf-8")

        raw_hash = hashlib.md5(config_json_bytes).hexdigest()
        current_ETag = f'"{raw_hash}"'

        cached_config = {"value": config.value, "ETag": current_ETag}
        config_dict_str = json.dumps(cached_config, sort_keys=True)

        # 2. Безопасно пытаемся записать в Редис
        try:
            await redis.set(cache_key, config_dict_str, ex=86400)
        except Exception as e:
            print(f"⚠️ [Redis Error on SET]: {e}. Не удалось обновить кэш.")

    else:
        cached_config = json.loads(cached_config_str)

    if if_none_match == cached_config["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    response.headers["ETag"] = cached_config["ETag"]
    return cached_config["value"]


@router.get("/institutes", response_model=List[Institutes_PWA_schema])
async def institutes_and_groups(
    response: Response,
    if_none_match: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_session),
):
    """
    Возвращает список обьектов институтов и всех групп относящихся к ним
    """

    cached_institutes_key = CacheKeys.institutes
    cached_institutes_str = None

    # 1. Безопасно пытаемся прочитать из Редиса
    try:
        cached_institutes_str = await redis.get(cached_institutes_key)
    except Exception as e:
        print(
            f"⚠️ [Redis Error on GET]: {e}. Блокировка кэша, идем напрямую в Postgres."
        )

    if not cached_institutes_str:
        query = (
            select(Institute)
            .options(
                selectinload(Institute.groups).selectinload(Group.educational_form_obj)  # pyright: ignore
            )
            .order_by(col(Institute.id))
        )
        result = await session.execute(query)
        institutes_obj = result.scalars().unique().all()

        adapter = TypeAdapter(List[Institutes_PWA_schema])
        pydantic_models = adapter.validate_python(institutes_obj)

        institutes_json_bytes = adapter.dump_json(pydantic_models)
        institutes_dict = adapter.dump_python(pydantic_models, mode="json")

        raw_hash = hashlib.md5(institutes_json_bytes).hexdigest()
        current_ETag = f'"{raw_hash}"'

        cached_institutes = {"value": institutes_dict, "ETag": current_ETag}
        cached_institutes_bytes = json.dumps(cached_institutes)

        # 2. Безопасно пытаемся записать в Редис
        try:
            await redis.set(
                cached_institutes_key, cached_institutes_bytes, ex=2_592_000
            )
        except Exception as e:
            print(f"⚠️ ⚠️ Не удалось записать кэш в Редис: {e}")

    else:
        cached_institutes = json.loads(cached_institutes_str)

    if if_none_match == cached_institutes["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    response.headers["ETag"] = cached_institutes["ETag"]
    return cached_institutes["value"]


@router.get("/groups/{group_id}/lessons", response_model=GroupScheduleResponse)
async def get_group_schedule(
    response: Response,
    group_id: int,
    if_none_match: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_session),
):
    """
    Отдает расписание конкретной группы по её ID.
    Оптимизировано для PWA, кэшируется в Redis, поддерживает ETag.
    """
    cache_key = CacheKeys.group(group_id)
    cached_schedule_str = None

    if group_id < 1 or group_id > 100_000:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    try:
        cached_schedule_str = await redis.get(cache_key)
    except Exception as e:
        await send_tg_alert(
            "Fastapi server",
            "CRITICAL",
            "Ошибка при подключении к Redis",
            f"{e.__class__.__name__}",
        )
        print(f"⚠️ [Redis Error GET]: {e}. Идем в БД за расписанием группы {group_id}")

    # Если в кэше пусто (или Редис лежит)
    if not cached_schedule_str:
        # ВАЖНО: Двойной selectinload.
        # Сначала подтягиваем пары группы, а к парам — преподавателей!
        query = (
            select(Group)
            .where(Group.id == group_id)
            .options(
                selectinload(Group.lessons).selectinload(Lesson.teachers)  # pyright: ignore
            )
        )
        result = await session.execute(query)
        group_obj = result.scalars().first()

        # Если юзер прислал левый ID группы
        if not group_obj:
            raise HTTPException(status_code=404, detail="Группа не найдена")

        # Используем готовый хэш из базы для ETag
        current_ETag = f'"{group_obj.data_hash}"'

        # Создаем Pydantic адаптер ТОЛЬКО для списка пар
        adapter = TypeAdapter(List[LessonPWA])
        pydantic_lessons = adapter.validate_python(group_obj.lessons)

        # Собираем финальный словарь ответа
        final_dict = {
            "status": group_obj.status.value,  # "ready", "updating" или "error"
            "start_education_date": group_obj.start_education_date.isoformat()
            if group_obj.start_education_date is not None
            else None,
            "end_education_date": group_obj.end_education_date.isoformat()
            if group_obj.end_education_date is not None
            else None,
            "lessons": adapter.dump_python(pydantic_lessons, mode="json"),
            "view_url": group_obj.view_url,
        }

        # Пакуем для Редиса вместе с ETag
        cached_data = {"value": final_dict, "ETag": current_ETag}
        cached_schedule_bytes = json.dumps(cached_data)

        try:
            await redis.set(cache_key, cached_schedule_bytes, ex=604800)
        except Exception as e:
            print(
                f"⚠️ [Redis Error SET]: {e}. Не удалось закэшировать расписание {group_id}"
            )

    else:
        # Если данные нашлись в кэше
        cached_data = json.loads(cached_schedule_str)

    # 3. HTTP Кэширование на стороне телефона
    if if_none_match == cached_data["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    response.headers["ETag"] = cached_data["ETag"]

    # FastAPI сам отдаст этот словарь как JSON со статусом 200 OK
    return cached_data["value"]


@router.get("/teachers", response_model=List[TeacherPWA])
async def get_teacher_list(
    response: Response,
    if_none_match: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_session),
):
    """
    Эндпоинт для получения списка всех доступных учителей в вузе
    Поддерживает HTTP Кэширование и Redis-cache
    """

    cache_key = CacheKeys.teachers
    cached_teachers_str = None

    # 1. Безопасно пытаемся прочитать из Редиса
    try:
        cached_teachers_str = await redis.get(cache_key)
    except Exception as e:
        await send_tg_alert(
            "Fastapi server",
            "CRITICAL",
            "Ошибка при подключении к Redis",
            f"{e.__class__.__name__}",
        )
        print(f"⚠️ [Redis Error GET]: {e}. Идем в БД за списком учителей")

    # 2. Если данных в кэше нет — идем в БД
    if not cached_teachers_str:
        has_lessons_subquery = (
            select(LessonTeacherLink.teacher_id).where(
                LessonTeacherLink.teacher_id == Teacher.id
            )
        ).exists()

        query = (
            select(Teacher.id, Teacher.name)
            .where(
                Teacher.canonical_id.is_(None)  # pyright: ignore
            )
            .where(has_lessons_subquery)
            .order_by(Teacher.name)
        )

        result = await session.execute(query)
        # mappings() гарантирует, что мы получим dict-подобные объекты
        teachers_obj = result.mappings().all()

        adapter = TypeAdapter(List[TeacherPWA])
        pydantic_models = adapter.validate_python(teachers_obj)

        teachers_json_bytes = adapter.dump_json(pydantic_models)
        teachers_dict = adapter.dump_python(pydantic_models, mode="json")

        current_ETag = xxh64(teachers_json_bytes).hexdigest()

        cached_data = {"value": teachers_dict, "ETag": current_ETag}
        cached_data_bytes = json.dumps(cached_data)

        try:
            await redis.set(cache_key, cached_data_bytes, ex=604800)
        except Exception as e:
            await send_tg_alert(
                "Fastapi server",
                "CRITICAL",
                "Ошибка при подключении к Redis",
                f"{e.__class__.__name__}",
            )
            print(f"⚠️ [Redis Error SET]: {e}. Невозможно добавить кэш")

    else:
        # Если данные нашлись в кэше
        cached_data = json.loads(cached_teachers_str)

    # 3. HTTP Кэширование на стороне телефона (ОБЩИЙ БЛОК ДЛЯ ВСЕХ ИСХОДОВ)
    if if_none_match == cached_data["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Обязательно отдаем ETag, чтобы в следующий раз клиент прислал if_none_match
    response.headers["ETag"] = cached_data["ETag"]

    # FastAPI сам отдаст этот словарь как JSON со статусом 200 OK
    return cached_data["value"]


@router.get("/teachers/{teacher_id}/schedule", response_model=TeacherScheduleResponse)
async def get_teacher_schedule(
    response: Response,
    teacher_id: int,
    if_none_match: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_session),
):
    """
    Получение расписания преподавателя.
    Оптимизировано для PWA, кэшируется в Redis, поддерживает ETag.
    Склеивает пары каноничного профиля и всех его мусорных алиасов.
    """

    # Базовая валидация ID
    if teacher_id < 1 or teacher_id > 100_000:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")

    cache_key = CacheKeys.one_teacher(teacher_id)
    cached_schedule_str = None

    # 1. Читаем из Redis
    try:
        cached_schedule_str = await redis.get(cache_key)
    except Exception as e:
        await send_tg_alert(
            "Fastapi server",
            "CRITICAL",
            "Ошибка при подключении к Redis",
            f"{e.__class__.__name__}",
        )
        print(
            f"⚠️ [Redis Error GET]: {e}. Идем в БД за расписанием препода {teacher_id}"
        )

    # 2. Если в кэше пусто (или Редис лежит) - собираем данные из БД
    if not cached_schedule_str:
        # Сначала быстрая проверка: существует ли вообще такой преподаватель?
        # (Чтобы не возвращать пустой список пар для несуществующего ID, а честно отдавать 404)
        teacher_exists = await session.scalar(
            select(Teacher.id).where(Teacher.id == teacher_id)
        )
        if not teacher_exists:
            raise HTTPException(status_code=404, detail="Преподаватель не найден")

        # Наш SQL-монстр со склейкой алиасов и агрегацией групп
        query = (
            select(  # pyright: ignore
                Lesson.day_of_week,
                Lesson.is_even_week,
                Lesson.lesson_name,
                Lesson.type_of_lesson,
                Lesson.classroom,
                Lesson.educational_place,
                Lesson.start_time,
                Lesson.end_time,
                func.array_agg(func.distinct(Group.name)).label("groups"),
            )
            .select_from(Teacher)
            .join(LessonTeacherLink, LessonTeacherLink.teacher_id == Teacher.id)
            .join(Lesson, Lesson.id == LessonTeacherLink.lesson_id)
            .join(Group, Group.id == Lesson.group_id)
            .where(or_(Teacher.id == teacher_id, Teacher.canonical_id == teacher_id))
            .group_by(
                Lesson.day_of_week,
                Lesson.is_even_week,
                Lesson.lesson_name,
                Lesson.type_of_lesson,
                Lesson.classroom,
                Lesson.educational_place,
                Lesson.start_time,
                Lesson.end_time,
            )
            .order_by(
                Lesson.is_even_week.asc(),  # pyright: ignore
                Lesson.day_of_week.asc(),  # pyright: ignore
                Lesson.start_time.asc(),  # pyright: ignore
            )
        )

        result = await session.execute(query)
        schedule_data = result.mappings().all()

        # Валидируем массив пар через Pydantic
        adapter = TypeAdapter(List[TeacherLessonPWA])
        pydantic_lessons = adapter.validate_python(schedule_data)

        # Формируем итоговый словарь. Для препода метаданных меньше,
        # но мы сохраняем общую структуру словаря с ключом "lessons"
        final_dict = {"lessons": adapter.dump_python(pydantic_lessons, mode="json")}

        # Генерируем ETag на лету, так как у нас нет готового хэша в базе
        final_json_bytes = json.dumps(final_dict).encode("utf-8")
        current_ETag = f'"{xxh64(final_json_bytes).hexdigest()}"'

        # Пакуем для Редиса
        cached_data = {"value": final_dict, "ETag": current_ETag}
        cached_schedule_bytes = json.dumps(cached_data)

        try:
            await redis.set(cache_key, cached_schedule_bytes, ex=604800)  # 7 дней
        except Exception as e:
            print(
                f"⚠️ [Redis Error SET]: {e}. Не удалось закэшировать расписание препода {teacher_id}"
            )

    else:
        # Если данные нашлись в кэше
        cached_data = json.loads(cached_schedule_str)

    # 3. HTTP Кэширование на стороне телефона (ОБЩИЙ БЛОК)
    if if_none_match == cached_data["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    response.headers["ETag"] = cached_data["ETag"]

    # Отдаем JSON клиенту
    return cached_data["value"]
