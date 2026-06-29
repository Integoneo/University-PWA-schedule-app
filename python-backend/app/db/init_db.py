from sqlmodel import SQLModel, Session, create_engine
from app.db.config import settings

# Импортируем ВСЕ модели, чтобы Алхимия знала о них при создании таблиц
from app.models.schedule import (
    AppConfig,
    # Institute,
    # Group,
    # Teacher,
    # Lesson,
    # LessonTeacherLink,
)


# Для создания таблиц мы используем СИНХРОННЫЙ URL (без asyncpg)
SYNC_DATABASE_URL = (
    f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)
sync_engine = create_engine(SYNC_DATABASE_URL, echo=True)


def create_db_and_tables():
    print("============================================")
    print("В РЕЖИМЕ РАЗРАБОТКИ - УДАЛЯЕМ ВСЕ ТАБЛИЦЫ В БД")
    print("============================================")
    # SQLModel.metadata.drop_all(sync_engine)
    print("⏳ Создание таблиц...")
    SQLModel.metadata.create_all(sync_engine)


def insert_initial_config():
    print("🚀 Записываю системные настройки (якорную неделю)...")

    with Session(sync_engine) as session:
        # Проверяем, нет ли уже этой настройки в базе
        existing_config = session.get(AppConfig, "semester_config")

        if not existing_config:
            config_data = {
                "semester_anchor_date": "2026-03-23",
                "anchor_is_even": False,  # В JSON можно сразу использовать булево значение, а не строку "false"
            }

            # Создаем одну запись в базе, передавая словарь в ваше JSON-поле
            anchor_config = AppConfig(key="semester_config", value=config_data)

            session.add(anchor_config)
            session.commit()
            print("✅ Настройки успешно сохранены!")
        else:
            print("⚡ Настройки уже существуют, пропускаем запись.")


if __name__ == "__main__":
    create_db_and_tables()
    insert_initial_config()
