import redis.asyncio as aioredis
from pathlib import Path
import logging
import sys
from typing import Literal, List
from pydantic import BaseModel, ConfigDict, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

REDIS_URL = "redis://localhost:6379/0"
redis_pool = aioredis.Redis.from_url(REDIS_URL, decode_responses=True)

DOWNLOADER_QUEUE = "downloader:dowload_queue"

CPP_QUEUE = "parser:ready_schedules"  # Очередь для плюсового парсера

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOWNLOAD_DIR = str(
    PROJECT_ROOT / "temp_downloads"
)  # Временная папка. В докере поменяю на /dev/shm


DOWNLOADER_DLQ = "downloader:DLQ"
BAN_TIME = 1200  # 20 минут карантина
MAX_SHM_SIZE = 100 * 1024 * 1024  # 100 МБ - лимит папки /dev/shm
GROUP_NAME = "python_downloaders"
CONSUMER_NAME = "downloader-worker"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Downloader")


class ProxySettings(BaseSettings):
    PROXY_HOST: str
    PROXY_PORT: str
    PROXY_LOGIN_PARSING: str
    PROXY_PASSWORD_PARSING: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


try:
    proxy = ProxySettings()  # pyright: ignore[reportCallIssue]

except ValidationError as e:
    print("\n" + "=" * 50)
    print("🚨 ОШИБКА ЗАПУСКА: Отсутствуют или неверны настройки окружения!")
    print("Пожалуйста, убедись, что файл .env существует и заполнен корректно.")
    print("Или проверь секреты в твоем CI/CD пайплайне.")
    print("=" * 50)

    for error in e.errors():
        field_name = error["loc"][0]
        error_msg = error["msg"]
        print(f"❌ Проблема с полем '{field_name}': {error_msg}")
    print("=" * 50 + "\n")

    sys.exit(1)


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
