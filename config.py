from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SUN.AI Advanced"
    app_env: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    sunai_api_token: SecretStr = Field(
        default=SecretStr(""),
        alias="SUNAI_API_TOKEN",
    )

    gemini_api_key: SecretStr = Field(
        default=SecretStr(""),
        alias="GEMINI_API_KEY",
    )

    gemini_model: str = Field(
        default="gemini-2.5-flash",
        alias="GEMINI_MODEL",
    )

    gemini_live_model: str = Field(
        default="",
        alias="GEMINI_LIVE_MODEL",
    )

    gemini_live_voice: str = Field(
        default="Kore",
        alias="GEMINI_LIVE_VOICE",
    )

    tavily_api_key: SecretStr = Field(
        default=SecretStr(""),
        alias="TAVILY_API_KEY",
    )

    research_timeout_seconds: int = 25
    research_max_results: int = 5

    database_path: str = "./data/sunai.db"

    session_secret: SecretStr = Field(
        default=SecretStr(""),
        alias="SESSION_SECRET",
    )

    max_prompt_length: int = 12000
    max_memory_items: int = 100

    # Allow more time for Gemini responses during troubleshooting.
    request_timeout_seconds: int = Field(
        default=90,
        alias="REQUEST_TIMEOUT_SECONDS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    def ensure_database_directory(self) -> None:
        Path(self.database_path).expanduser().parent.mkdir(
            parents=True,
            exist_ok=True,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
