from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


@dataclass(frozen=True)
class Settings:
    bot_token: str
    webhook_url: str | None
    sqlite_path: Path
    log_level: str


def get_settings() -> Settings:
    bot_token = _get_env("BOT_TOKEN")
    if not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
        raise RuntimeError(
            "BOT_TOKEN is missing. Set it in taxi_bot/.env (get one from @BotFather)."
        )

    webhook_url = _get_env("WEBHOOK_URL", None)
    sqlite_path = Path(_get_env("SQLITE_PATH", "taxi_bot.db")).expanduser()
    if not sqlite_path.is_absolute():
        sqlite_path = (PROJECT_DIR / sqlite_path).resolve()

    log_level = _get_env("LOG_LEVEL", "INFO") or "INFO"

    return Settings(
        bot_token=bot_token,
        webhook_url=webhook_url,
        sqlite_path=sqlite_path,
        log_level=log_level.upper(),
    )

