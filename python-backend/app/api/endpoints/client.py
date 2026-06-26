from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Optional
import hashlib
import json

from app.db.engine import get_async_session
from app.models.schedule import AppConfig

router = APIRouter(prefix="/client", tags=["Client App"])


@router.get("/config")
async def get_app_config(
    response: Response,
    if_none_match: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Возвращает системный конфиг. Поддерживает HTTP Caching (304 Not Modified) через ETags.
    """

    query = select(AppConfig).where(AppConfig.key == "semester_config")
    result = await session.execute(query)
    config = result.scalars().first()

    if not config:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND, content="Системный конфиг не найден"
        )

    config_json_bytes = json.dumps(config.value, sort_keys=True).encode("utf-8")
    config_hash = hashlib.md5(config_json_bytes).hexdigest()

    current_etag = f'W/"{config_hash}"'

    if if_none_match == current_etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    response.headers["ETag"] = current_etag

    return config
