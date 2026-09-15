"""
Central configuration, loaded from environment variables (.env).
No secrets are hard-coded; nothing here requires a paid API key.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _bool(env_val: str | None, default: bool) -> bool:
    if env_val is None:
        return default
    return env_val.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    APP_NAME: str = "HOMELANDER"

    # --- Model backend ---
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "ollama")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama3.1:8b")

    # --- Storage ---
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    DB_PATH: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "homelander.db")))
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads")))
    VECTOR_STORE_DIR: Path = Path(os.getenv("VECTOR_STORE_DIR", str(BASE_DIR / "data" / "vectors")))

    # --- Web search ---
    WEB_SEARCH_PROVIDER: str = os.getenv("WEB_SEARCH_PROVIDER", "duckduckgo")

    # --- Security / limits ---
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
    ALLOWED_UPLOAD_EXTENSIONS: set[str] = {
        ".pdf", ".docx", ".txt", ".csv", ".xlsx", ".pptx", ".json",
        ".py", ".js", ".ts", ".java", ".c", ".cpp", ".html", ".css", ".sql",
        ".png", ".jpg", ".jpeg", ".webp",
    }
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    REQUIRE_API_KEY_FOR_REMOTE: bool = _bool(os.getenv("REQUIRE_API_KEY_FOR_REMOTE"), False)
    HOMELANDER_API_KEY: str | None = os.getenv("HOMELANDER_API_KEY")

    # --- Privacy ---
    LOCAL_ONLY_MODE: bool = _bool(os.getenv("LOCAL_ONLY_MODE"), False)


settings = Settings()

# Ensure data directories exist on import.
for _dir in (settings.DATA_DIR, settings.UPLOAD_DIR, settings.VECTOR_STORE_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
