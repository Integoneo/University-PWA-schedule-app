import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Импортируем синхронные функции инициализации БД
from app.db.init_db import create_db_and_tables, insert_initial_config

# Импортируем нашего воркера
from worker import main_worker_loop
from dlq_watcher import dlq_watcher_loop

# Импортируем роутер
from app.api.router import api_router


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
app = FastAPI(title="University Schedule API", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")


# Простой тестовый эндпоинт
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "API works!"}
