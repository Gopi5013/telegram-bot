from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from taxi_bot.config import get_settings
from taxi_bot.database import create_booking, upsert_user
from taxi_bot.keyboards.menu import confirm_keyboard, main_menu_keyboard, vehicle_keyboard
from taxi_bot.utils.helpers import VEHICLE_LABELS, format_booking_summary, normalize_location


log = logging.getLogger(__name__)

PICKUP, DROPOFF, VEHICLE, CONFIRM = range(4)


def booking_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_booking, pattern=r"^MENU_BOOK$")],
        states={
            PICKUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pickup_received),
                MessageHandler(filters.ALL, pickup_invalid),
            ],
            DROPOFF: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, dropoff_received),
                MessageHandler(filters.ALL, dropoff_invalid),
            ],
            VEHICLE: [
                CallbackQueryHandler(vehicle_selected, pattern=r"^VEHICLE_(MINI|SEDAN|SUV)$")
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_selected, pattern=r"^CONFIRM_(YES|NO)$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_booking)],
        name="booking_conversation",
        persistent=False,
        allow_reentry=True,
        per_message=True,
    )


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    await query.answer()

    context.user_data["booking"] = {}
    await query.message.reply_text(
        "📍 Enter your *pickup location* (text):",
        parse_mode="Markdown",
    )
    return PICKUP


async def pickup_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_location(update.message.text if update.message else "")
    if len(text) < 3:
        await update.message.reply_text("Pickup location looks too short. Please type it again:")
        return PICKUP

    context.user_data.setdefault("booking", {})["pickup"] = text
    await update.message.reply_text(
        "📍 Enter your *drop location* (text):",
        parse_mode="Markdown",
    )
    return DROPOFF


async def pickup_invalid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Please send the pickup location as text (example: 'MG Road, Bangalore').")
    return PICKUP


async def dropoff_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_location(update.message.text if update.message else "")
    if len(text) < 3:
        await update.message.reply_text("Drop location looks too short. Please type it again:")
        return DROPOFF

    booking = context.user_data.setdefault("booking", {})
    booking["drop"] = text

    await update.message.reply_text("🚘 Choose a vehicle type:", reply_markup=vehicle_keyboard())
    return VEHICLE


async def dropoff_invalid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Please send the drop location as text (example: 'Indiranagar Metro').")
    return DROPOFF


async def vehicle_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    await query.answer()

    vehicle = query.data.replace("VEHICLE_", "").strip()
    booking = context.user_data.setdefault("booking", {})
    booking["vehicle"] = vehicle

    pickup = booking.get("pickup", "")
    dropoff = booking.get("drop", "")
    summary = format_booking_summary(pickup, dropoff, vehicle)

    await query.message.reply_text(summary, reply_markup=confirm_keyboard())
    return CONFIRM


async def confirm_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    await query.answer()

    selection = query.data.replace("CONFIRM_", "").strip()
    if selection == "NO":
        await query.message.reply_text("Booking cancelled.", reply_markup=main_menu_keyboard())
        context.user_data.pop("booking", None)
        return ConversationHandler.END

    settings = get_settings()
    tg_user = update.effective_user
    if tg_user is None:
        await query.message.reply_text("Could not identify you.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    booking = context.user_data.get("booking") or {}
    pickup = str(booking.get("pickup", "")).strip()
    dropoff = str(booking.get("drop", "")).strip()
    vehicle = str(booking.get("vehicle", "")).strip()

    if not pickup or not dropoff or not vehicle:
        await query.message.reply_text(
            "Your booking data looks incomplete. Please start again.",
            reply_markup=main_menu_keyboard(),
        )
        context.user_data.pop("booking", None)
        return ConversationHandler.END

    user_id = upsert_user(settings, tg_user.id, tg_user.full_name)
    booking_id = create_booking(settings, user_id, pickup, dropoff, vehicle, status="CONFIRMED")

    vehicle_label = VEHICLE_LABELS.get(vehicle, vehicle)
    await query.message.reply_text(
        "✅ Booking confirmed!\n\n"
        f"Booking ID: #{booking_id}\n"
        f"Pickup: {pickup}\n"
        f"Drop: {dropoff}\n"
        f"Vehicle: {vehicle_label}\n"
        "Status: CONFIRMED\n",
        reply_markup=main_menu_keyboard(),
    )

    context.user_data.pop("booking", None)
    return ConversationHandler.END


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("booking", None)
    if update.message:
        await update.message.reply_text("Cancelled. Back to menu:", reply_markup=main_menu_keyboard())
    return ConversationHandler.END
