"""Marketplace event producer repository implementation.

Writes events to JSONL file (current format) and is prepared
to send to Kafka in the future via data_platform.
"""

from __future__ import annotations

import json
from pathlib import Pathm   
from typing import List

from marketplace.domain.entities.event import Event
from marketplace.domain.repositories.event_producer_repository import (
    EventProducerRepository,
)


class JsonlEventProducerRepository(EventProducerRepository):
    """Implementation that writes events to JSONL file."""

    def __init__(self, output_file: str = "data/raw/events.jsonl"):
        self.output_file = Path(output_file)

    def produce_event(self, event: Event) -> None:
        """Produce one event to JSONL file."""
        self.produce_events([event])

    def produce_events(self, events: List[Event]) -> None:
        """Write multiple events to JSONL file."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with self.output_file.open("w", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(self._event_to_dict(event)) + "\n")

    def _event_to_dict(self, event: Event) -> dict:
        """Convert an Event to a serializable dict."""
        return {
            "event_id": event.event_id,
            "order_id": event.order_id,
            "event_type": event.event_type,
            "sku": event.sku,
            "store_id": event.store_id,
            "seller_id": event.seller_id,
            "country": event.country,
            "quantity": event.quantity,
            "unit_price": event.unit_price,
            "event_ts": event.event_ts.isoformat(),
            "arrival_ts": event.arrival_ts.isoformat(),
        }
