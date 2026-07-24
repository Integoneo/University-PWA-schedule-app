import os
import logging
import asyncio
from typing import Dict, Literal, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError, BaseModel, ConfigDict, field_validator
import redis.asyncio as aioredis
import sys
import json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Notifier")


class ProxySettings(BaseSettings):
    PROXY_HOST: str
    PROXY_PORT: str
    PROXY_LOGIN_TG: str
    PROXY_PASSWORD_TG: str
    TG_BOT_TOKEN: str
    TG_CHAT_ID: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


try:
    proxy = ProxySettings()  # pyright: ignore
except ValidationError as e:
    logger.fatal("🚨 ОШИБКА ЗАПУСКА: Отсутствуют или неверны настройки окружения!")
    for error in e.errors():
        logger.fatal(f"❌ Проблема с полем '{error['loc'][0]}': {error['msg']}")
    os._exit(0)


REDIS_URL = "redis://localhost:6379/0"
STREAM_NAME = "notifier:queue"
GROUP_NAME = "notifier"
CONSUMER_NAME = "notifier"
HASH_NAME = "notifier:sended_messages"


def fatal_die(message: str, exit_code: int = 1):
    """
    Логирует фатальную ошибку, сбрасывает все системные буферы и жестко убивает процесс.
    """
    # 1. Отправляем сообщение в логгер
    logger.fatal(f"💀 ФАТАЛЬНАЯ ОШИБКА: {message}")

    # 2. Корректно завершаем работу системы логирования (сбрасывает буферы всех хендлеров)
    logging.shutdown()

    # 3. На всякий случай принудительно сбрасываем стандартные потоки ОС
    sys.stdout.flush()
    sys.stderr.flush()

    # 4. Жестко убиваем процесс.
    # В Linux код 1 означает "завершение с ошибкой" (0 - это успешное завершение).
    # Docker поймет код 1 и правильно пометит контейнер как упавший (Exited (1)).
    os._exit(exit_code)


class SafeRedis:
    def __init__(self) -> None:
        self.redis_pool = aioredis.from_url(REDIS_URL, decode_responses=True)
        self.is_redis_alive = False

    async def _ensure_connection(self):
        waiting_flag = False
        while not self.is_redis_alive:
            try:
                await self.redis_pool.ping()
                logger.info("🟢 Связь с Redis установлена/восстановлена!")
                self.is_redis_alive = True
            except Exception:
                if not waiting_flag:
                    logger.error("Ожидаю починки редиса в режиме пинга!")
                    waiting_flag = True
                await asyncio.sleep(2)

    # ================= Явные методы =================

    async def xgroup_create(
        self, stream: str, group: str, mkstream: bool = True, id: str = "0"
    ):
        while True:
            try:
                return await self.redis_pool.xgroup_create(
                    stream, group, id=id, mkstream=mkstream
                )
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.ResponseError as err:
                # BUSYGROUP - штатная ситуация, группа уже есть
                if "BUSYGROUP" in str(err):
                    return
                logger.fatal(f"Фатальная ошибка создания группы: {err}")
                fatal_die(
                    f"Ошибка в логике общения с редис (xgroup_create): {str(err)}"
                )
            except aioredis.RedisError as err:
                logger.fatal(
                    f"Фатальная ошибка в логике общения с редис (xgroup_create): {str(err)}"
                )
                fatal_die(
                    f"Ошибка в логике общения с редис (xgroup_create): {str(err)}"
                )

    async def xreadgroup(
        self, group: str, consumer: str, streams: dict, count: int, block: int
    ):
        while True:
            try:
                return await self.redis_pool.xreadgroup(
                    group, consumer, streams, count=count, block=block
                )
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                logger.warning("🔴 Потеряна связь (xreadgroup). Реконнект...")
                await self._ensure_connection()
            except aioredis.RedisError as err:
                if "NOGROUP" in str(err):
                    stream_name = list(streams.keys())[0]
                    logger.warning(f"Ключ {stream_name} был удален, создаю его заново")
                    await self.xgroup_create(stream_name, group)
                else:
                    fatal_die(
                        f"Ошибка в логике общения с редис (xreadgroup): {str(err)}"
                    )

    async def hexists(self, name: str, key: str) -> bool:
        while True:
            try:
                return await self.redis_pool.hexists(name, key)
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.RedisError as err:
                fatal_die(f"Ошибка в логике общения с редис (hexists): {str(err)}")

    async def hget(self, name: str, key: str):
        while True:
            try:
                return await self.redis_pool.hget(name, key)
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.RedisError as err:
                fatal_die(f"Ошибка в логике общения с редис (hget): {str(err)}")

    async def hset(self, name: str, key: str, value: str):
        while True:
            try:
                return await self.redis_pool.hset(name, key, value)
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.RedisError as err:
                fatal_die(f"Ошибка в логике общения с редис (hset): {str(err)}")

    async def hexpire(self, name: str, seconds: int, key: str):
        while True:
            try:
                try:
                    return await self.redis_pool.hexpire(name, seconds, key)
                except AttributeError:
                    return await self.redis_pool.execute_command(
                        "HEXPIRE", name, seconds, "FIELDS", 1, key
                    )
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.RedisError as err:
                fatal_die(f"Ошибка в логике общения с редис (hexpire): {str(err)}")

    async def xadd(self, stream: str, fields: dict, maxlen: int = 1000):
        while True:
            try:
                # approximate=True (~ maxlen) обрезает стрим мягко, не нагружая процессор Redis
                return await self.redis_pool.xadd(
                    stream, fields, maxlen=maxlen, approximate=True
                )
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.RedisError as err:
                fatal_die(f"Ошибка в логике общения с редис (xadd): {str(err)}")

    async def xack(self, stream: str, group: str, msg_id: str):
        while True:
            try:
                return await self.redis_pool.xack(stream, group, msg_id)
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.RedisError as err:
                fatal_die(f"Ошибка в логике общения с редис (xack): {str(err)}")

    async def xdel(self, stream: str, msg_id: str):
        while True:
            try:
                return await self.redis_pool.xdel(stream, msg_id)
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                self.is_redis_alive = False
                await self._ensure_connection()
            except aioredis.RedisError as err:
                fatal_die(f"Ошибка в логике общения с редис (xdel): {str(err)}")


redis_pool = SafeRedis()

# ================= СХЕМЫ =================


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
            try:
                v = json.loads(v)
            except Exception as _:
                return [v]

        return v


class OldMessage(BaseModel):
    service: str
    msg_level: Literal["INFO", "WARN", "ERROR", "CRITICAL", "DEAD"]
    msg: str
    sub_msg: Dict[str, int]
    model_config = ConfigDict(populate_by_name=True)


class OldMessageHash(BaseModel):
    tg_id_msg: int
    payload: OldMessage
    model_config = ConfigDict(populate_by_name=True)
