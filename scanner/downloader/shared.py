import redis.asyncio as aioredis
from pathlib import Path


REDIS_URL = "redis://localhost:6379/0"
redis_pool = aioredis.Redis.from_url(REDIS_URL, decode_responses=True)

DOWNLOADER_QUEUE = "downloader:dowload_queue"

CPP_QUEUE = "parser:ready_schedules"  # Очередь для плюсового парсера

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOWNLOAD_DIR = str(
    PROJECT_ROOT / "temp_downloads"
)  # Временная папка. В докере поменяем на /dev/shm


DOWNLOADER_DLQ = "downloader:DLQ:failed_downloads"
BAN_TIME = 1200  # 20 минут карантина
MAX_SHM_SIZE = 100 * 1024 * 1024  # 100 МБ - лимит папки /dev/shm
GROUP_NAME = "python_downloaders"
CONSUMER_NAME = "downloader-worker"
