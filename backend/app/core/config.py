from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "RedScope"
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "mysql+pymysql://trendai:trendai_password@127.0.0.1:3307/trendai?charset=utf8mb4"

    crawler_profile_dir: str = "backend/.xhs-profile"
    crawler_headless: bool = True
    crawler_scroll_rounds: int = 6
    crawler_scroll_pause_ms: int = 1800
    crawler_navigation_timeout_ms: int = 45000
    crawler_debug_dir: str = "backend/.crawler-debug"
    crawler_cache_ttl_seconds: int = 900
    default_keywords: str = "AI工具,效率工具,职场效率"
    media_archive_enabled: bool = True
    media_archive_dir: str = "backend/.media-archive"
    media_archive_image_max_bytes: int = 25 * 1024 * 1024
    media_archive_video_max_bytes: int = 250 * 1024 * 1024

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def profile_path(self) -> Path:
        path = Path(self.crawler_profile_dir).expanduser()
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path.resolve()

    @property
    def debug_path(self) -> Path:
        path = Path(self.crawler_debug_dir).expanduser()
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path.resolve()

    @property
    def media_archive_path(self) -> Path:
        path = Path(self.media_archive_dir).expanduser()
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path.resolve()

    @property
    def default_keyword_list(self) -> list[str]:
        return [keyword.strip() for keyword in self.default_keywords.split(",") if keyword.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
