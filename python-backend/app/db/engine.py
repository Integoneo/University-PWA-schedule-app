from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.config import settings


DATABASE_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # TODO: вынести это потом в .env в обьект настроки
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# Используем итератор а не генератор, благодоря чему можем не использовать костыль с AsyncGenerator[AsyncSession, None] и не плодим лишние сущности
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    Функция-итератор для получения асинхронной сессии БД.
    Идеально подходит для строгой типизации в FastAPI (Depends).
    """
    async with async_session_maker() as session:
        yield session
