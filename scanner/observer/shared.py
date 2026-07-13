import redis.asyncio as aioredis
from pydantic import BaseModel, Field, ConfigDict


# INFO: =================== REDIS ===================================

REDIS_URL = "redis://localhost:6379/0"

STATS_KEY = "observer:stats:last_run"

SCHEDULES_KEY = "observer:schedules"

EXCEL_SRC_DLQ = "observer:DLQ:head_requests"
BAN_TIME = 1200  # Ссылки по которым не прошли head запросы, банятся на 20 минут

DOWNLOADER_QUEUE = "downloader:dowload_queue"

CPP_QUEUE = "parser:ready_schedules"  # Очередь для плюсового парсера
DOWNLOAD_DIR = "./temp_downloads"  # Временная папка. В докере поменяем на /dev/shm


redis_pool = aioredis.Redis.from_url(REDIS_URL, decode_responses=True)


# INFO: =================== REDIS ===================================


# INFO: =================== SCHEMAS ===================================


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
