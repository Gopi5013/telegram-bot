from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Booking:
    id: int
    pickup: str
    dropoff: str
    vehicle: str
    status: str
    created_at: str

