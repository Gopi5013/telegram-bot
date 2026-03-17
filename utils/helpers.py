from __future__ import annotations

from typing import Final


VEHICLE_LABELS: Final[dict[str, str]] = {
    "MINI": "Mini 🚗",
    "SEDAN": "Sedan 🚙",
    "SUV": "SUV 🚐",
}


def normalize_location(text: str) -> str:
    return " ".join((text or "").strip().split())


def format_booking_summary(pickup: str, dropoff: str, vehicle: str) -> str:
    vehicle_label = VEHICLE_LABELS.get(vehicle, vehicle)
    return (
        "Please confirm your booking:\n\n"
        f"• Pickup: {pickup}\n"
        f"• Drop: {dropoff}\n"
        f"• Vehicle: {vehicle_label}\n"
    )

