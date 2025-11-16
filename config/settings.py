from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str
    gemini_api_key: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
