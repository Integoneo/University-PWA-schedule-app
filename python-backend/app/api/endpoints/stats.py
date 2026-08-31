from fastapi import APIRouter, Depends, Header, Request, Response, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib

import redis.asyncio as aioredis

from datetime import datetime
import json
from app.utils import get_logger
from app.db.engine import get_async_session  # Сессия для PostgreSQL
from app.db.cache import (
    get_redis_session,
    CacheKeys,
)  # Сессия для Redis и ключи для кэша

from app.models.api_dto import InstallPWAPayload
from app.models.schedule import PWAInstalls, get_moscow_now
from user_agents import parse


logger = get_logger("API stats")

router = APIRouter(prefix="/client/stats", tags=["Client App"])


async def track_activity_buffer(
    request: Request,
    x_device_id: str | None = Header(None, alias="X-Device-ID"),
    redis: aioredis.Redis = Depends(get_redis_session),
):
    if not x_device_id:
        return

    # Берем IP - обновляем
    client_ip = request.headers.get("X-Real-IP")
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown_IP"
    ip_hash = hashlib.md5(client_ip.encode()).hexdigest()[:16]

    # Формируем payload только с теми полями, которые хотим обновить
    payload = {"last_activity": get_moscow_now().isoformat(), "ip_hash": ip_hash}

    # HSET атомарно перезапишет данные для этого device_id
    if redis:
        await redis.hset(CacheKeys.activity_tasks, x_device_id, json.dumps(payload))


@router.post("/install")
async def pwa_install(
    payload: InstallPWAPayload,
    request: Request,
    response: Response,
    user_agent: str = Header(None),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_session),
):

    client_ip = request.headers.get("X-Real-IP")
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown_IP"
    ip_hash = hashlib.md5(client_ip.encode()).hexdigest()[:16]
    # --- 1. АНТИ-СПАМ (Redis) ---
    redis_key = CacheKeys.install_rate_limit

    if redis is not None:
        try:
            # hincrby: внутри хэша redis_key находим поле ip_hash и прибавляем 1
            installs_count = await redis.hincrby(redis_key, ip_hash, 1)

            # Если это первая установка с этого IP, ставим индивидуальный таймер на поле
            if installs_count == 1:
                # Ставим TTL 3600 секунд (1 час) именно на конкретный ip_hash
                await redis.hexpire(redis_key, 3600, ip_hash)

            if installs_count > 1500:  # Лимит установок от ddos
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Слишком много попыток установки с этого устройства.",
                    headers={"Retry-After": "3600"},
                )

        except HTTPException:
            # Это наша ошибка превышения лимита — прокидываем её юзеру
            raise

        except aioredis.RedisError:
            # Регистрация в обход редиса в случае его падения
            pass
    # --- 2. ПАРСИНГ ДАННЫХ ---
    ua = parse(user_agent or "")
    device_type = (
        "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop")
    )
    os_info = f"{ua.os.family} {ua.os.version_string}".strip()[:64]
    browser_info = f"{ua.browser.family} {ua.browser.version_string}".strip()[:64]
    device_model = (ua.device.model or ua.device.family or "Unknown")[:64]

    screen_resolution = f"{payload.screen_width}x{payload.screen_height}"[:16]

    # --- 3. ЗАПИСЬ В БАЗУ ДАННЫХ (last_activity будет NULL) ---
    new_install = PWAInstalls(
        ip_hash=ip_hash,
        os=os_info,
        browser=browser_info,
        device_model=device_model,
        device_type=device_type,
        screen_resolution=screen_resolution,
        device_ram_GB=payload.device_ram_GB,
        device_cpu_count=payload.device_cpu_count,
        last_activity=None,
    )

    session.add(new_install)
    await session.commit()
    await session.refresh(new_install)

    # --- 4. ОТВЕТ ФРОНТЕНДУ ---
    return {"device_id": str(new_install.device_id)}
