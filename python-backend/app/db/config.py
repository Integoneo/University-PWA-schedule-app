import sys

from pydantic import ValidationError

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


try:
    settings = Settings()  # pyright: ignore[reportCallIssue]

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

    # Жестко убиваем процесс с кодом ошибки 1 (чтобы Docker/CI понял, что всё сломалось)
    sys.exit(1)
