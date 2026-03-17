from __future__ import annotations

import asyncio
import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from taxi_bot.config import get_settings
from taxi_bot.database import init_db
from taxi_bot.handlers.booking import booking_conversation_handler
from taxi_bot.handlers.start import help_menu, start_command
from taxi_bot.handlers.user import my_bookings_menu
from taxi_bot.keyboards.menu import main_menu_keyboard


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.getLogger(__name__).exception("Unhandled error", exc_info=context.error)
    if isinstance(update, Update):
        message = update.effective_message
        if message:
            await message.reply_text(
                "Something went wrong. Please try again or type /start.",
                reply_markup=main_menu_keyboard(),
            )


def build_application() -> Application:
    settings = get_settings()
    _configure_logging(settings.log_level)
    init_db(settings)

    application = Application.builder().token(settings.bot_token).build()

    # Conversation handler should come before generic callback handlers.
    application.add_handler(booking_conversation_handler())

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", _help_command))
    application.add_handler(CommandHandler("cancel", _cancel_alias))

    application.add_handler(CallbackQueryHandler(my_bookings_menu, pattern=r"^MENU_MY_BOOKINGS$"))
    application.add_handler(CallbackQueryHandler(help_menu, pattern=r"^MENU_HELP$"))

    application.add_error_handler(_error_handler)
    return application


async def _help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Use the menu to book a taxi or view bookings.\n"
            "Commands:\n"
            "• /start - show menu\n"
            "• /cancel - cancel booking flow\n",
            reply_markup=main_menu_keyboard(),
        )


async def _cancel_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # If /cancel is used outside the conversation, show the main menu.
    if update.message:
        await update.message.reply_text("Back to menu:", reply_markup=main_menu_keyboard())


def run_polling() -> None:
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_polling()
