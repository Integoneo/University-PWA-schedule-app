import redis.asyncio as aioredis
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal, List

import sys
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


# INFO: ================== PROXY =================================
class ProxySettings(BaseSettings):
    PROXY_HOST: str
    PROXY_PORT: str
    PROXY_LOGIN_PARSING: str
    PROXY_PASSWORD_PARSING: str
    REDIS_URL: str = "redis://localhost:6379/0"
    IS_PRODUCTION: bool = False
    KUMA_URL: str = ""
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


try:
    config = ProxySettings()  # pyright: ignore[reportCallIssue]

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

# INFO: ================== PROXY =================================
# INFO: =================== REDIS ===================================


STATS_KEY = "observer:stats:last_run"

SCHEDULES_KEY = "observer:schedules"

EXCEL_SRC_DLQ = "observer:DLQ:head_requests"
BAN_TIME = 1200  # Ссылки по которым не прошли head запросы, банятся на 20 минут

DOWNLOADER_QUEUE = "downloader:dowload_queue"

CPP_QUEUE = "parser:ready_schedules"  # Очередь для плюсового парсера


redis_pool = aioredis.Redis.from_url(config.REDIS_URL, decode_responses=True)


# INFO: =================== REDIS ===================================


# INFO: =================== SCHEMAS ===================================

URL_TO_PARSE = "https://rguk.ru/students/schedule/"


class NotCheckedURL(BaseModel):
    composite_key: str
    file_title: str
    institute: str
    study_form: str
    file_url: str
    view_url: str | None
    logo_url: str | None


class CheckedURL(NotCheckedURL):
    model_config = ConfigDict(populate_by_name=True)

    ETag: str | None
    LastModified: str | None = Field(alias="Last-Modified")
    ContentLength: str | None = Field(alias="Content-Length")


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


# INFO: =================== SCHEMAS ===================================


# INFO: =================== PARSER CONFIGS ===================================


BATCH_SIZE = 5


class InstituteSelectors:
    MAIN_CONTAINER = "contentmain"
    BLOCK_INST = "students-schedule-inst"
    BLOCK_IGNORE = "students-schedule-rasp"
    INFO_ROW = "logo-row"
    LOGO = "logo-schedule"
    NAME = "name-schedule"
    ACCORDION_ITEM = "accordion-item"
    ACCORDION_BTN = "accordion-button"
    DOCUMENT = "document"
    GRAPH_WRAPPER = "graph"
    ICONS = "icons"
    FILES = "files"


# INFO: КОРТЕЖИ КОТОРЫЕ Я ТУТ РАСПИСАЛ - РАСШИФРОВКА
# Tuple({True - срабатываение по % False по количеству}, {процентаж/количество})
THRESHOLDS = {
    "main_containers": (False, 1),
    "institutes": (False, 1),
    "logos": (True, 100.0),
    "study_forms": (True, 30.0),
    "valid_files": (True, 30.0),
    "office_views": (True, 30.0),
}


# INFO: =================== PARSER CONFIGS ===================================


# INFO: =================== CUSTOM ERRORS ===================================
class DOMStructureChangedError(Exception):
    pass


# INFO: =================== CUSTOM ERRORS ===================================
