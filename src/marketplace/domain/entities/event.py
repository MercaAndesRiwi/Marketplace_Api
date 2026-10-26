"""Domain entity: Event (marketplace event)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """Domain entity: Marketplace event.

    Represents an event in the lifecycle of a marketplace order.
    """

    event_id: str
    order_id: str
    event_type: str  # created, paid, shipped, delivered, cancelled, returned
    sku: str
    store_id: str
    seller_id: str
    country: str
    quantity: int
    unit_price: float
    event_ts: datetime
    arrival_ts: datetime
