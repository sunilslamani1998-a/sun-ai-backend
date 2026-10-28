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
    gemini_model: str = "gemini-2.5-flash"
    database_path: str = "./data/sunai.db"
    session_secret: SecretStr = Field(
        default=SecretStr(""),
        alias="SESSION_SECRET",
    )
    max_prompt_length: int = 12000
    max_memory_items: int = 100
    request_timeout_seconds: int = 45

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    def ensure_database_directory(self) -> None:
        database_file = Path(self.database_path).expanduser()
        database_file.parent.mkdir(parents=True, exist_ok=True)

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
