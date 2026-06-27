from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Optional
import hashlib
import json
import redis.asyncio as aioredis

from app.db.engine import get_async_session  # Сессия для PostgreSQL
from app.db.cache import get_redis_session  # Сессия для Redis
from app.models.schedule import AppConfig

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
