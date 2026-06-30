from fastapi import APIRouter, Depends, Header, Response, status, HTTPException
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from typing import AsyncIterator, List, Optional
import hashlib
import json
import redis.asyncio as aioredis

from app.db.engine import get_async_session  # Сессия для PostgreSQL
from app.db.cache import (
    get_redis_session,
    CacheKeys,
)  # Сессия для Redis и ключи для кэша

from app.models.api_dto import Institutes_PWA_schema, Groups_PWA_schema, LessonPWA
from app.models.schedule import AppConfig, Group, Institute, Lesson

router = APIRouter(prefix="/client", tags=["Client App"])


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
        # Если Редис упал, мы не роняем сервер, а просто логируем ошибку в консоль
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
            .options(selectinload(Institute.groups))  # pyright: ignore
            .order_by(Institute.id)  # type: ignore
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


@router.get("/groups/{group_id}/lessons")
async def get_group_schedule(
    group_id: int,
    response: Response,
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

    # 1. Защищенный запрос в Redis
    try:
        cached_schedule_str = await redis.get(cache_key)
    except Exception as e:
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

        # ИСПОЛЬЗУЕМ ЧИТ-КОД: Готовый data_hash из базы как ETag
        current_ETag = f'"{group_obj.data_hash}"'

        # Создаем Pydantic адаптер ТОЛЬКО для списка пар
        adapter = TypeAdapter(List[LessonPWA])
        pydantic_lessons = adapter.validate_python(group_obj.lessons)

        # Собираем финальный словарь ответа
        final_dict = {
            "status": group_obj.status.value,  # "ready", "updating" или "error"
            "lessons": adapter.dump_python(pydantic_lessons, mode="json"),
        }

        # Пакуем для Редиса вместе с ETag
        cached_data = {"value": final_dict, "ETag": current_ETag}
        cached_schedule_bytes = json.dumps(cached_data)

        # 2. Защищенная запись в Redis
        try:
            # Кэшируем на 1 неделю, так как если расписание изменится,
            # наш C++ воркер всё равно инвалидирует (удалит) этот ключ при записи!
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
