"""Marketplace event producer repository implementation.

Writes events to JSONL file (current format) and is prepared
to send to Kafka in the future via data_platform.
"""

from __future__ import annotations

import json
from pathlib import Path
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
        """Append events to JSONL file idempotently (staging append-only without overwriting)."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        existing_event_ids: set[str] = set()
        if self.output_file.exists():
            with self.output_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            if "event_id" in record:
                                existing_event_ids.add(record["event_id"])
                        except Exception:
                            pass

        with self.output_file.open("a", encoding="utf-8") as fh:
            for event in events:
                if event.event_id not in existing_event_ids:
                    fh.write(json.dumps(self._event_to_dict(event)) + "\n")
                    existing_event_ids.add(event.event_id)

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
