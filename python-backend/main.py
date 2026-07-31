import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Импортируем синхронные функции инициализации БД
from app.db.init_db import create_db_and_tables, insert_initial_config

# Импортируем нашего воркера
from worker import main_worker_loop
from dlq_watcher import dlq_watcher_loop
from app.utils import get_logger, send_tg_alert
from app.db.config import settings

# Импортируем роутер
from app.api.router import api_router


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========================================
    # ⬆️ Инициализируем API
    # ========================================
    print("🚀 Инициализация системы...")

    # 1. Запускаем синхронные функции БД в отдельном потоке (Thread),
    # чтобы не блокировать асинхронный Event Loop сервера.
    await asyncio.to_thread(create_db_and_tables)
    await asyncio.to_thread(insert_initial_config)

    # 2. Запускаем воркер в фоновом режиме
    worker_task = asyncio.create_task(main_worker_loop())
    dlq_watcher_task = asyncio.create_task(dlq_watcher_loop())

    yield

    # ========================================
    # ⬇️ ФАЗА ВЫКЛЮЧЕНИЯ
    # ========================================
    print("🛑 Завершение работы сервера...")

    # 3. Отправляем сигнал отмены в бесконечный цикл воркера
    worker_task.cancel()
    dlq_watcher_task.cancel()

    # 4. Ждем, пока воркер завершит свои текущие дела (допишет в БД) и остановится
    try:
        await worker_task
    except asyncio.CancelledError:
        pass  # Мы ожидаем эту ошибку, это нормально

    print("✅ Сервер успешно выключен. Все фоновые задачи завершены.")


# Инициализация приложения FastAPI
app = FastAPI(
    title="Schedule API",
    docs_url=None if settings.IS_PRODUCTION else "/docs",
    redoc_url=None if settings.IS_PRODUCTION else "/redoc",
    openapi_url=None if settings.IS_PRODUCTION else "/openapi.json",
    lifespan=lifespan,
)

# 2. Настраиваем CORS
if settings.IS_PRODUCTION:
    # На проде разрешаем запросы ТОЛЬКО с твоего домена
    origins = [
        "https://kosyga.ru",
        "https://www.kosyga.ru",
    ]
else:
    # Для локальной разработки разрешаем всё
    origins = [
        "http://192.168.31.233",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = uuid.uuid4().hex[:8]

    logger.error(
        f"[ErrorID: {error_id}] Необработанное исключение: {request.method} {request.url.path}",
        exc_info=exc,
    )

    # 1. Забираем только название ошибки (например, ValidationError или ValueError)
    exc_type = type(exc).__name__

    # 2. Обрезаем само тело ошибки, если оно длиннее 200 символов
    exc_msg = str(exc)
    short_exc_msg = exc_msg[:200] + "..." if len(exc_msg) > 200 else exc_msg

    await send_tg_alert(
        service="Fastapi server",
        msg_level="ERROR",
        msg=f"Сбой эндпоинта {request.method} {request.url.path} ({exc_type}: {short_exc_msg})",
        details=f"ErrorID: {error_id}",
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Внутренняя ошибка сервера. Разработчик уже в курсе об этом.",
            "error_id": error_id,
        },
    )


app.include_router(api_router, prefix="/api/v1")


@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "API works!"}
