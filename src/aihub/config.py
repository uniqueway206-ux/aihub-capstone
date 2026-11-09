"""Central, validated configuration (12-factor: everything comes from env vars)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    api_key: str = ""  # optional shared secret for /api/*
    data_dir: Path = Path("data")
    sql_database_path: Path = Path("data/demo.db")
    max_upload_mb: int = 20
    rate_limit: str = "60 per minute"
    log_level: str = "INFO"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4
    max_history_turns: int = 10
    sql_row_limit: int = 50

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
