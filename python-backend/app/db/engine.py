from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.config import settings


DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

engine = create_async_engine(
    DATABASE_URL, echo=False if settings.IS_PRODUCTION else True
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# Используем итератор а не генератор, благодоря чему можем не использовать костыль с AsyncGenerator[AsyncSession, None] и не плодим лишние сущности
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    Функция-итератор для получения асинхронной сессии БД.
    """
    async with async_session_maker() as session:
        yield session
