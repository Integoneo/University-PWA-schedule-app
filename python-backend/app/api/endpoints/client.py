from fastapi import APIRouter, Depends, Header, Response, status
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select
from sqlalchemy.orm import selectinload
from typing import AsyncIterator, List, Optional
import hashlib
import json
import redis.asyncio as aioredis

from app.db.engine import get_async_session  # Сессия для PostgreSQL
from app.db.cache import get_redis_session  # Сессия для Redis

from app.models.api_dto import Institutes_PWA_schema, Groups_PWA_schema
from app.models.schedule import AppConfig, Group, Institute


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
    cache_key = "pwa:system:config"

    # Благодаря decode_responses=True это будет строка (str) или None
    cached_config_str = await redis.get(cache_key)

    # TODO: добавить поддержку отвалов реддиса - запросы должны идти в таком случае в обход редиса
    # Притом нужно рассчитать специальный кожфициент который знает какая нагрузка сейчас на сервер
    # Если допустим больше 0.5 - значит бд захлебнется от такого количества запросов и надо выдавать заглушку

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

        # ⚠️ ПРАВКА 1: Оборачиваем хэш в кавычки по стандарту HTTP
        raw_hash = hashlib.md5(config_json_bytes).hexdigest()
        current_ETag = f'"{raw_hash}"'

        # Твоя крутая оптимизация: кладем ETag вместе с данными!
        cached_config = {"value": config.value, "ETag": current_ETag}

        # ⚠️ ПРАВКА 2: Не делаем .encode("utf-8"), так как aioredis сам это сделает
        config_dict_str = json.dumps(cached_config, sort_keys=True)
        await redis.set(cache_key, config_dict_str, ex=86400)

    else:
        # Разворачиваем строку из Редиса обратно в словарь
        cached_config = json.loads(cached_config_str)

    # Проверяем хэш, который прислал клиент
    if if_none_match == cached_config["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Записываем хэш в заголовки ответа
    response.headers["ETag"] = cached_config["ETag"]

    # Отдаем чистое значение конфига, без ETag (PWA само превратит это в JSON)
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
    cached_institutes_key = "pwa:users:institutes"
    cached_institutes_str = await redis.get(cached_institutes_key)

    if not cached_institutes_str:
        # 1. Делаем запрос в базу
        query = (
            select(Institute)
            .options(selectinload(Institute.groups))  # pyright: ignore
            .order_by(Institute.id)  # type: ignore
        )
        result = await session.execute(query)

        # Обязательно unique(), так как мы используем загрузку связей
        institutes_obj = result.scalars().unique().all()

        # 2. Создаем TypeAdapter ДЛЯ СПИСКА СХЕМ!
        adapter = TypeAdapter(List[Institutes_PWA_schema])

        # 3. ВАЖНО: Сначала ПРЕВРАЩАЕМ объекты ORM в объекты Pydantic
        # Благодаря from_attributes=True в схемах, Pydantic сам подтянет группы
        pydantic_models = adapter.validate_python(institutes_obj)

        # 4. Теперь выгружаем это в JSON-байты (для хэша)
        institutes_json_bytes = adapter.dump_json(pydantic_models)

        # 5. И выгружаем в обычный словарь (чтобы положить в кэш)
        # mode="json" гарантирует, что внутри не останется сложных типов типа datetime
        institutes_dict = adapter.dump_python(pydantic_models, mode="json")

        # 6. Считаем хэш
        raw_hash = hashlib.md5(institutes_json_bytes).hexdigest()
        current_ETag = f'"{raw_hash}"'

        # 7. Формируем финальный кэш-объект и сохраняем
        cached_institutes = {"value": institutes_dict, "ETag": current_ETag}
        cached_institutes_bytes = json.dumps(cached_institutes)

        await redis.set(cached_institutes_key, cached_institutes_bytes, ex=2_592_000)

    else:
        # Если данные есть в кэше, просто парсим их
        cached_institutes = json.loads(cached_institutes_str)

    # Логика 304 Not Modified
    if if_none_match == cached_institutes["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Записываем хэш в заголовки ответа
    response.headers["ETag"] = cached_institutes["ETag"]

    # Отдаем чистое значение (FastAPI сам поймет, что это List[Institutes_PWA_schema])
    return cached_institutes["value"]
