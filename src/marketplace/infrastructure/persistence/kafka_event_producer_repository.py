"""Kafka event producer repository implementation.

Publishes order events to Kafka topic for speed layer processing (US-02).
Uses store_id as message key for partitioning strategy (SCRUM-113).
"""

from __future__ import annotations

import json
import os
from typing import List

from confluent_kafka import Producer

from marketplace.domain.entities.event import Event
from marketplace.domain.repositories.event_producer_repository import (
    EventProducerRepository,
)


class KafkaEventProducerRepository(EventProducerRepository):
    """Implementation that publishes events to Kafka."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
    ):
        self.bootstrap_servers = (
            bootstrap_servers
            or os.getenv("KAFKA_BOOTSTRAP_SERVERS")
            or os.getenv("KAFKA_BOOTSTRAP_SERVERS_HOST")
            or "localhost:9092"
        )
        self.topic = topic or os.getenv("KAFKA_TOPIC_ORDERS") or "mercaandes.orders.events"
        self.producer = Producer({"bootstrap.servers": self.bootstrap_servers})

    def _on_delivery(self, err, msg) -> None:
        if err is not None:
            # Log delivery errors without breaking event generation
            print(f"Kafka delivery failed: {err}")
        # Delivery success - could add metrics here

    def produce_event(self, event: Event) -> None:
        """Produce one event to Kafka."""
        self.produce_events([event])

    def produce_events(self, events: List[Event]) -> None:
        """Publish multiple events to Kafka with store_id as key for partitioning."""
        for event in events:
            payload = self._event_to_dict(event)
            key = str(event.store_id).encode("utf-8")
            self.producer.produce(
                self.topic,
                key=key,
                value=json.dumps(payload).encode("utf-8"),
                callback=self._on_delivery,
            )
        timeout_seconds = int(os.getenv("KAFKA_PRODUCER_TIMEOUT_SECONDS", "10"))
        self.producer.flush(timeout=timeout_seconds)

    def _event_to_dict(self, event: Event) -> dict:
        """Convert an Event to a serializable dict (same schema as JSONL)."""
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
