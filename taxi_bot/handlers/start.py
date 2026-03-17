from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from taxi_bot.keyboards.menu import main_menu_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.full_name if user else "there"

    if update.message:
        await update.message.reply_text(
            f"Hi {name}! 🚖\n\nWelcome to Taxi Booking Bot.\nChoose an option:",
            reply_markup=main_menu_keyboard(),
        )


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text(
            "Help:\n"
            "• Tap *Book Taxi* to start a booking.\n"
            "• Use /cancel anytime to stop the booking flow.\n"
            "• Tap *My Bookings* to see your recent bookings.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

