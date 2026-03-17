from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Optional

from flask import Flask, jsonify, request
from telegram import Update
from telegram.ext import Application as PTBApplication

from taxi_bot.bot import build_application
from taxi_bot.config import get_settings


log = logging.getLogger(__name__)

app = Flask(__name__)

# We run python-telegram-bot's async Application in a background event loop thread.
_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread] = None
_ptb_app: Optional[PTBApplication] = None
_started = False
_start_lock = threading.Lock()
_ready_event = threading.Event()


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


async def _ptb_initialize_only() -> None:
    # In a WSGI + threads setup (gunicorn), calling Application.start() can be
    # problematic depending on event-loop/signal handling. For basic webhook
    # bots, initialize() is sufficient for process_update().
    global _ptb_app
    log.info("Initializing python-telegram-bot application...")
    if _ptb_app is None:
        # Build lazily so the WSGI server can bind its port even if BOT_TOKEN
        # or other env vars are misconfigured (that would otherwise crash on import).
        _ptb_app = build_application()
    await _ptb_app.initialize()
    log.info("python-telegram-bot application initialized.")


async def _ptb_set_webhook_only() -> None:
    settings = get_settings()
    if _ptb_app is None:
        log.warning("PTB app not initialized yet; skipping automatic setWebhook.")
        return
    if not settings.webhook_url:
        log.warning("WEBHOOK_URL is not set; skipping automatic setWebhook.")
        return

    webhook_full = settings.webhook_url.rstrip("/") + "/telegram"
    await _ptb_app.bot.set_webhook(url=webhook_full)
    log.info("Webhook set to %s", webhook_full)


def _ensure_started(wait: bool = True, timeout_s: float = 5.0) -> bool:
    global _loop, _started
    if _started:
        return _ready_event.is_set()

    with _start_lock:
        if _started:
            return _ready_event.is_set()
        if _loop is None:
            _loop = _start_background_loop()
            fut = asyncio.run_coroutine_threadsafe(_ptb_initialize_only(), _loop)

            def _mark_ready(f) -> None:  # type: ignore[no-untyped-def]
                try:
                    f.result()
                    _ready_event.set()
                except Exception:
                    log.exception("PTB initialize/start failed; webhook handling will retry.")

            fut.add_done_callback(_mark_ready)

            # Set webhook separately so a slow/failed Telegram API call doesn't
            # block the bot from becoming ready to process updates.
            def _set_webhook_later() -> None:
                try:
                    asyncio.run_coroutine_threadsafe(_ptb_set_webhook_only(), _loop).result(timeout=20)
                except Exception:
                    log.exception("setWebhook failed (you can set it manually).")

            threading.Thread(target=_set_webhook_later, name="set-webhook", daemon=True).start()
        _started = True

    if not wait:
        return _ready_event.is_set()

    return _ready_event.wait(timeout=timeout_s)


@app.get("/health")
def health() -> tuple[str, int]:
    return "ok", 200


@app.get("/")
def index() -> tuple[str, int]:
    return "Taxi bot is running. Use /health or Telegram webhook at /telegram.", 200


@app.get("/telegram")
def telegram_webhook_get() -> tuple[object, int]:
    # Browsers send GET; Telegram sends POST. This endpoint is not meant to be opened in a browser.
    return jsonify({"ok": True, "message": "Webhook endpoint. Telegram will POST updates here."}), 200


@app.post("/telegram")
def telegram_webhook() -> tuple[object, int]:
    # Telegram expects a quick response; wait a bit for startup, then return 503
    # so Telegram can retry if we're still warming up.
    ready = _ensure_started(wait=True, timeout_s=20.0)
    if not ready:
        # Avoid hanging requests (Telegram will retry).
        return jsonify({"ok": False, "error": "bot not ready"}), 503
    assert _loop is not None
    if _ptb_app is None:
        return jsonify({"ok": False, "error": "bot not initialized"}), 503

    data = request.get_json(force=True, silent=False)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "invalid json"}), 400

    log.debug("Incoming update_id=%s", data.get("update_id"))
    update = Update.de_json(data, _ptb_app.bot)
    asyncio.run_coroutine_threadsafe(_ptb_app.process_update(update), _loop)
    return jsonify({"ok": True}), 200


def run_flask() -> None:
    _ensure_started(wait=False)
    # Flask dev server (good enough for local + ngrok testing).
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)


def _start_in_background() -> None:
    # Best-effort startup for WSGI servers (gunicorn). We can't rely on Flask lifecycle
    # hooks across versions, so we kick off initialization in a daemon thread.
    def runner() -> None:
        # Don't block the web server startup. If Telegram/API calls fail, the app
        # will still come up and can be validated via /health. Webhook setup can
        # be retried by redeploying, hitting /telegram, or setting it manually.
        try:
            _ensure_started(wait=True, timeout_s=30.0)
        except Exception:
            log.exception("Startup failed (webhook not set yet). Will retry on next /telegram request.")

    threading.Thread(target=runner, name="startup", daemon=True).start()


_start_in_background()


if __name__ == "__main__":
    run_flask()
