from pathlib import Path
from pydantic_settings import SettingsError
from pydantic_settings import BaseSettings
import shutil
import hashlib
from datetime import datetime, timezone
import redis.asyncio as aioredis
import json
import sys


class Settings(BaseSettings):
    DOWNLOAD_DIR: str = "./downloads"
    REDIS_URL: str = "redis://redis_db:6379"
    CPP_QUEUE: str = "parser:ready_schedules"  # Очередь для плюсового парсера


try:
    config = Settings()
except SettingsError as e:
    print("🚨 ОШИБКА ЗАПУСКА: Отсутствуют настройки окружения!")
    print(e)
    sys.exit(1)


mock_source = Path("./dist_excels")
target_dir = Path(config.DOWNLOAD_DIR)

redis_pool = aioredis.Redis.from_url(config.REDIS_URL, decode_responses=True)

mock_meta_info = [
    {  # INFO: mock_1
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 15.04.02 Технологические машины и оборудование",
            "institute": "Магистратура",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_2
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Технологический институт текстильной и легкой промышлености | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 29.03.05 Конструирование изделий легкой промышленности",
            "institute": "Технологический институт текстильной и легкой промышлености",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_3
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": 'Институт "Академия имени Маймонида" | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 53.03.05 Дирижирование',
            "institute": 'Институт "Академия имени Маймонида"',
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_4
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": 'Институт "Академия имени Маймонида" | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 53.03.02 Музыкально-инструментальное искусство',
            "institute": 'Институт "Академия имени Маймонида"',
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_5
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт славянской культуры | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 44.03.01 Педагогическое образование",
            "institute": "Институт славянской культуры",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_6
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт социальной инженерии | Очно-заочная форма обучения | 42.03.02 Журналистика",
            "institute": "Институт социальной инженерии",
            "logo_url": "",
            "view_url": "",
            "study_form": "Очно-заочная форма обучения",
        },
    },
    {  # INFO: mock_7
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт экономики и менеджмента | Очно-заочная форма обучения | 38.03.06 Торговое дело",
            "institute": "Институт экономики и менеджмента",
            "logo_url": "",
            "view_url": "",
            "study_form": "Очно-заочная форма обучения",
        },
    },
    {  # INFO: mock_8
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт экономики и менеджмента | Заочная форма обучения | 43.03.01 Сервис",
            "institute": "Институт экономики и менеджмента",
            "logo_url": "",
            "view_url": "",
            "study_form": "Заочная форма обучения",
        },
    },
    {  # INFO: mock_9
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт социальной инженерии | Очно-заочная форма обучения | 37.03.01 Психология",
            "institute": "Институт социальной инженерии",
            "logo_url": "",
            "view_url": "",
            "study_form": "Очно-заочная форма обучения",
        },
    },
    {  # INFO: mock_10
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Технологический институт текстильной и легкой промышлености | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 29.03.05 Конструирование изделий легкой промышленности",
            "institute": "Технологический институт текстильной и легкой промышлености",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_11
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 54.04.04 Реставрация",
            "institute": "МАГИСТРАТУРА",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_12
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 45.04.01 Филология",
            "institute": "МАГИСТРАТУРА",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_13
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 29.04.02 Технологии и проектирование текстильных изделий",
            "institute": "МАГИСТРАТУРА",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_14
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт искусств | Очно-заочная форма обучения | 1 курс",
            "institute": "Институт искусств",
            "logo_url": "",
            "view_url": "",
            "study_form": "Очно-заочная форма обучения",
        },
    },
    {  # INFO: mock_15
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт экономики и менеджмента | Очно-заочная форма обучения | 3 курс",
            "institute": "Институт экономики и менеджмента",
            "logo_url": "",
            "view_url": "",
            "study_form": "Очно-заочная форма обучения",
        },
    },
    {  # INFO: mock_16
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 27.04.04 Управление в технических системах",
            "institute": "МАГИСТРАТУРА",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_17
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт дизайна | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 3 курс",
            "institute": "Институт дизайна",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_18
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт социальной инженерии | Заочная форма обучения | 1 курс",
            "institute": "Институт социальной инженерии",
            "logo_url": "",
            "view_url": "",
            "study_form": "Заочная форма обучения",
        },
    },
    {  # INFO: mock_19
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 54.04.03 Искусство костюма и текстиля",
            "institute": "МАГИСТРАТУРА",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_20
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт славянской культуры | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 1 курс",
            "institute": "Институт славянской культуры",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_21
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт дизайна | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 1 курс",
            "institute": "Институт дизайна",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_22
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": 'Институт "Академия имени Маймонида" | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 3 курс',
            "institute": 'Институт "Академия имени Маймонида"',
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_23
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 29.04.01 Технология изделий легкой промышленности",
            "institute": "МАГИСТРАТУРА",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_24
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "МАГИСТРАТУРА | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 18.04.01 Химическая технология",
            "institute": "МАГИСТРАТУРА",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
    {  # INFO: mock_25
        "filepath": "",
        "meta_info": {
            "ETag": "",
            "Last-Modified": "",
            "composite_key": "Институт социальной инженерии | ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ) | 1 курс",
            "institute": "Институт социальной инженерии",
            "logo_url": "",
            "view_url": "",
            "study_form": "ОЧНАЯ ФОРМА ОБУЧЕНИЯ(ДНЕВНАЯ)",
        },
    },
]


def calculate_hash(target: Path) -> str:
    file_bytes = target.read_bytes()
    hexdigest = hashlib.md5(file_bytes).hexdigest()

    return f'"{hexdigest}"'


def get_file_http_date(target: Path) -> str:
    mtime = target.stat().st_mtime

    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)

    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def copy_files_build_msgs():
    target_dir.mkdir(parents=True, exist_ok=True)
    for i, excel_file in enumerate(mock_source.iterdir()):
        excel_name = excel_file.name
        shutil.copy(excel_file.absolute(), config.DOWNLOAD_DIR)
        filepath = target_dir.absolute() / excel_name
        mock_meta_info[i]["filepath"] = str(filepath)
        mock_meta_info[i]["meta_info"]["ETag"] = calculate_hash(filepath)
        mock_meta_info[i]["meta_info"]["Last-Modified"] = get_file_http_date(filepath)


async def push_messages_to_redis():

    for cpp_payload in mock_meta_info:
        await redis_pool.xadd(
            config.CPP_QUEUE,
            {"payload": json.dumps(cpp_payload, ensure_ascii=False)},
        )
