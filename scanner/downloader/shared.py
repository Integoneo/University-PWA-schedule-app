import redis.asyncio as aioredis
from pathlib import Path
import logging
import sys
from typing import Literal, List
from pydantic import BaseModel, ConfigDict, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

DOWNLOADER_QUEUE = "downloader:dowload_queue"

CPP_QUEUE = "parser:ready_schedules"  # Очередь для плюсового парсера

# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


DOWNLOADER_DLQ = "downloader:DLQ"
BAN_TIME = 1200  # 20 минут карантина
MAX_SHM_SIZE = 100 * 1024 * 1024  # 100 МБ - лимит папки /dev/shm
GROUP_NAME = "python_downloaders"
CONSUMER_NAME = "downloader-worker"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Downloader")


class AppSettings(BaseSettings):
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    # Пути
    DOWNLOAD_DIR: str = "/dev/shm"

    # Прокси парсинг
    PROXY_HOST: str = ""
    PROXY_PORT: str = ""
    PROXY_LOGIN_PARSING: str = ""
    PROXY_PASSWORD_PARSING: str = ""
    KUMA_URL: str = ""

    IS_PRODUCTION: bool = False
    # Игнорируем лишние переменные из .env, которые не нужны этому скрипту
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


try:
    config = AppSettings()
except ValidationError as e:
    print("🚨 ОШИБКА ЗАПУСКА: Отсутствуют настройки окружения!")
    print(e)
    sys.exit(1)


PROXY_URL_PARSING = None

if config.IS_PRODUCTION:
    PROXY_URL_PARSING = f"http://{config.PROXY_LOGIN_PARSING}:{config.PROXY_PASSWORD_PARSING}@{config.PROXY_HOST}:{config.PROXY_PORT}"


# Создаем папки физически, чтобы скрипт не падал при первом запуске
Path(config.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


redis_pool = aioredis.Redis.from_url(config.REDIS_URL, decode_responses=True)

# INFO: Схема для сообщения в тг


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
