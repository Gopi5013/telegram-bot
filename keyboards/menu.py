from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Book Taxi", callback_data="MENU_BOOK")],
            [InlineKeyboardButton("My Bookings", callback_data="MENU_MY_BOOKINGS")],
            [InlineKeyboardButton("Help", callback_data="MENU_HELP")],
        ]
    )


def vehicle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Mini 🚗", callback_data="VEHICLE_MINI"),
                InlineKeyboardButton("Sedan 🚙", callback_data="VEHICLE_SEDAN"),
            ],
            [InlineKeyboardButton("SUV 🚐", callback_data="VEHICLE_SUV")],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes", callback_data="CONFIRM_YES"),
                InlineKeyboardButton("❌ No", callback_data="CONFIRM_NO"),
            ]
        ]
    )

