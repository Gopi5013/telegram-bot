from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from taxi_bot.config import get_settings
from taxi_bot.database import list_bookings_for_user, upsert_user
from taxi_bot.keyboards.menu import main_menu_keyboard
from taxi_bot.utils.helpers import VEHICLE_LABELS


async def my_bookings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    settings = get_settings()
    tg_user = update.effective_user
    if tg_user is None:
        await query.message.reply_text("Could not identify you.", reply_markup=main_menu_keyboard())
        return

    user_id = upsert_user(settings, tg_user.id, tg_user.full_name)
    rows = list_bookings_for_user(settings, user_id, limit=10)

    if not rows:
        await query.message.reply_text(
            "No bookings yet. Tap *Book Taxi* to create one.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines: list[str] = ["Your recent bookings:\n"]
    for r in rows:
        vehicle_label = VEHICLE_LABELS.get(str(r["vehicle"]), str(r["vehicle"]))
        lines.append(
            f"#{r['id']} • {vehicle_label}\n"
            f"Pickup: {r['pickup']}\n"
            f"Drop: {r['drop']}\n"
            f"Status: {r['status']} • {r['created_at']}\n"
        )

    await query.message.reply_text("\n".join(lines), reply_markup=main_menu_keyboard())
