from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional

from flask import Flask, jsonify, request
from telegram import Update

from taxi_bot.bot import build_application
from taxi_bot.config import get_settings


log = logging.getLogger(__name__)

app = Flask(__name__)

# We run python-telegram-bot's async Application in a background event loop thread.
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_ptb_app = build_application()


def _start_background_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()

    def runner() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=runner, name="ptb-event-loop", daemon=True)
    thread.start()

    global _loop, _loop_thread
    _loop = loop
    _loop_thread = thread
    return loop


async def _ptb_initialize_and_set_webhook() -> None:
    settings = get_settings()
    await _ptb_app.initialize()
    await _ptb_app.start()

    if not settings.webhook_url:
        raise RuntimeError("WEBHOOK_URL is missing in taxi_bot/.env")

    # Telegram will POST updates to: {WEBHOOK_URL}/telegram
    webhook_full = settings.webhook_url.rstrip("/") + "/telegram"
    await _ptb_app.bot.set_webhook(url=webhook_full)
    log.info("Webhook set to %s", webhook_full)


def _ensure_started() -> None:
    global _loop
    if _loop is None:
        _loop = _start_background_loop()
        fut = asyncio.run_coroutine_threadsafe(_ptb_initialize_and_set_webhook(), _loop)
        fut.result(timeout=30)


@app.get("/health")
def health() -> tuple[str, int]:
    return "ok", 200


@app.post("/telegram")
def telegram_webhook() -> tuple[object, int]:
    _ensure_started()
    assert _loop is not None

    data = request.get_json(force=True, silent=False)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "invalid json"}), 400

    update = Update.de_json(data, _ptb_app.bot)
    asyncio.run_coroutine_threadsafe(_ptb_app.process_update(update), _loop)
    return jsonify({"ok": True}), 200


def run_flask() -> None:
    _ensure_started()
    # Flask dev server (good enough for local + ngrok testing).
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    run_flask()

