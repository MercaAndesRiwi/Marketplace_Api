"""Unit tests for marketplace event producer."""

from marketplace.application.use_cases.generate_marketplace_events import (
    GenerateMarketplaceEventsUseCase,
)
from marketplace.domain.entities.event import Event


class FakeEventRepository:
    """Fake repository for producer tests."""

    def __init__(self):
        self.events = []

    def produce_event(self, event: Event) -> None:
        self.events.append(event)

    def produce_events(self, events: list) -> None:
        self.events.extend(events)


def test_producer_receives_events():
    """Repository should receive all generated events."""
    repo = FakeEventRepository()
    use_case = GenerateMarketplaceEventsUseCase(
        event_repository=repo,
        seed=42,
        n_orders=5,
        duplicate_rate=0.0,
        ooo_enabled=False,
    )

    result = use_case.execute()
    assert len(repo.events) == result.events_count

    # Verify all repository events are in the result
    repo_ids = {e.event_id for e in repo.events}
    result_ids = {e.event_id for e in result.events}
    assert repo_ids == result_ids


def test_event_entity_creation():
    """Should create Event entity correctly."""
    from datetime import datetime, timezone

    event = Event(
        event_id="evt-001",
        order_id="ORD-001",
        event_type="created",
        sku="SKU-001",
        store_id="STO-CO-FIS-001",
        seller_id="SEL-CO-PRV-001",
        country="CO",
        quantity=1,
        unit_price=100.0,
        event_ts=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        arrival_ts=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert event.event_id == "evt-001"
    assert event.order_id == "ORD-001"
    assert event.event_type == "created"
    assert event.country == "CO"
