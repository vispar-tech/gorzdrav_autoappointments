from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL


class Settings(BaseSettings):
    """Settings for the bot."""

    BOT_TOKEN: str = Field(default=...)

    DB_HOST: str = "localhost"
    DB_PORT: int = 5442
    DB_USER: str = "gorzdrav_bot"
    DB_PASS: str = Field(default="gorzdrav_bot")
    DB_BASE: str = "gorzdrav_bot"
    DB_ECHO: bool = False

    # Ограничения для пациентов
    MAX_SUBSCRIBED_PATIENTS: int = Field(
        default=10,
        description="Максимальное количество пациентов для подписчиков",
    )
    MAX_UNSUBSCRIBED_PATIENTS: int = Field(
        default=1,
        description="Максимальное количество пациентов для бесплатных пользователей",
    )

    # Ограничения для расписаний
    MAX_SUBSCRIBED_SCHEDULES: int = Field(
        default=10,
        description="Максимальное количество активных расписаний для подписчиков",
    )
    MAX_UNSUBSCRIBED_SCHEDULES: int = Field(
        default=2,
        description=(
            "Максимальное количество активных расписаний для бесплатных пользователей"
        ),
    )

    @property
    def db_url(self) -> URL:
        """
        Assemble database URL from settings.

        :return: database URL.
        """
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.DB_HOST,
            port=self.DB_PORT,
            user=self.DB_USER,
            password=self.DB_PASS,
            path=f"/{self.DB_BASE}",
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
