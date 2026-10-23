"""Data Transfer Objects for marketplace application layer."""

from __future__ import annotations

from typing import List
from datetime import datetime


class EventDTO:
    """DTO for a marketplace event."""

    def __init__(
        self,
        event_id: str,
        order_id: str,
        event_type: str,
        sku: str,
        store_id: str,
        seller_id: str,
        country: str,
        quantity: int,
        unit_price: float,
        event_ts: datetime,
        arrival_ts: datetime,
    ):
        self.event_id = event_id
        self.order_id = order_id
        self.event_type = event_type
        self.sku = sku
        self.store_id = store_id
        self.seller_id = seller_id
        self.country = country
        self.quantity = quantity
        self.unit_price = unit_price
        self.event_ts = event_ts
        self.arrival_ts = arrival_ts


class GenerateEventsDTO:
    """DTO for marketplace events generation response."""

    def __init__(
        self,
        seed: int,
        n_orders: int,
        events_count: int,
        events: List[EventDTO],
    ):
        self.seed = seed
        self.n_orders = n_orders
        self.events_count = events_count
        self.events = events
