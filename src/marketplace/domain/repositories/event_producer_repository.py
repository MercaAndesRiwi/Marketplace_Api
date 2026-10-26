"""Domain repository interface for marketplace event producer."""

from __future__ import annotations

from typing import List

from marketplace.domain.entities.event import Event


class EventProducerRepository:
    """Interface for marketplace event producer repository."""

    def produce_event(self, event: Event) -> None:
        """Produce one event to the output medium."""
        raise NotImplementedError

    def produce_events(self, events: List[Event]) -> None:
        """Produce multiple events to the output medium."""
        raise NotImplementedError
