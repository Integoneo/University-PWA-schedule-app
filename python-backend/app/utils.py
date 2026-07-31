from typing import Literal, List
from pydantic import BaseModel, ConfigDict, field_validator
import json
import logging
import redis.asyncio as aioredis
from app.db.config import settings
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(module_name):
    return logging.getLogger(module_name)


logger = get_logger(__name__)


REDIS = settings.REDIS_URL

redis_client = aioredis.from_url(REDIS)


def ping_kuma_sync(url: str):
    """Синхронная функция, которая быстро отправляет GET-запрос"""
    try:
        # timeout=2 означает, что если Кума тупит, мы не ждем дольше 2 секунд
        urllib.request.urlopen(url, timeout=2)
    except Exception as e:
        logger.warning(f"Не удалось отправить пинг в Kuma: {e}")


class NewMessage(BaseModel):
    service: str
    msg_level: Literal["INFO", "WARN", "ERROR", "CRITICAL", "DEAD"] = "INFO"
    msg: str
    details: List[str]
    model_config = ConfigDict(populate_by_name=True)

    @field_validator("details", mode="before")
    @classmethod
    def to_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v


async def send_tg_alert(
    service: Literal["Python worker", "Fastapi server"],
    msg_level: Literal["INFO", "WARN", "ERROR", "CRITICAL", "DEAD"],
    msg: str,
    details: List[str] | str,
):
    new_message = NewMessage(
        service=service,
        msg_level=msg_level,
        msg=msg,
        details=details,  # pyright: ignore завали ебальник
    )

    # Готовим плоский словарь для Redis XADD
    payload = {
        "service": new_message.service,
        "msg_level": new_message.msg_level,
        "msg": new_message.msg,
    }

    if isinstance(new_message.details, list):
        payload["details"] = json.dumps(new_message.details, ensure_ascii=False)
    else:
        payload["details"] = new_message.details

    try:
        await redis_client.xadd("notifier:queue", payload)  # pyright: ignore
    except Exception as e:
        logger.error(f"⚠️ Ошибка отправки алерта в очередь: {e}")
