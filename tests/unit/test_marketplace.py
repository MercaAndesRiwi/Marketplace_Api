"""Unit tests for marketplace API (F4)."""

from marketplace.application.use_cases.generate_marketplace_events import (
    GenerateMarketplaceEventsUseCase,
)
from marketplace.domain.entities.event import Event


class FakeEventRepository:
    """Fake repository for tests."""

    def __init__(self):
        self.events = []

    def produce_event(self, event: Event) -> None:
        self.events.append(event)

    def produce_events(self, events: list) -> None:
        self.events.extend(events)


def test_generate_marketplace_events_deterministic():
    """Same seed should generate same events."""
    repo = FakeEventRepository()
    use_case = GenerateMarketplaceEventsUseCase(
        event_repository=repo,
        seed=42,
        n_orders=10,
        duplicate_rate=0.0,
        ooo_enabled=False,
    )

    result1 = use_case.execute()
    repo2 = FakeEventRepository()
    use_case2 = GenerateMarketplaceEventsUseCase(
        event_repository=repo2,
        seed=42,
        n_orders=10,
        duplicate_rate=0.0,
        ooo_enabled=False,
    )
    result2 = use_case2.execute()

    assert result1.events_count == result2.events_count
    assert [e.event_id for e in result1.events] == [e.event_id for e in result2.events]


def test_generate_marketplace_events_has_events():
    """Should generate at least one event per order."""
    repo = FakeEventRepository()
    use_case = GenerateMarketplaceEventsUseCase(
        event_repository=repo,
        seed=42,
        n_orders=5,
        duplicate_rate=0.0,
        ooo_enabled=False,
    )

    result = use_case.execute()
    assert result.events_count > 0
    assert len(result.events) >= result.n_orders  # At least one event per order


def test_generate_marketplace_events_duplicate_rate():
    """With high duplicate_rate there should be more events than orders."""
    repo = FakeEventRepository()
    use_case = GenerateMarketplaceEventsUseCase(
        event_repository=repo,
        seed=42,
        n_orders=10,
        duplicate_rate=1.0,
        ooo_enabled=False,
    )

    result = use_case.execute()
    assert result.events_count > result.n_orders  # There are duplicates


def test_generate_marketplace_events_ooo():
    """With ooo_enabled arrival_ts should differ from event_ts."""
    repo = FakeEventRepository()
    use_case = GenerateMarketplaceEventsUseCase(
        event_repository=repo,
        seed=42,
        n_orders=20,
        duplicate_rate=0.0,
        ooo_enabled=True,
        ooo_max_lag_sec=21600,
    )

    result = use_case.execute()
    # Verify at least one event has arrival different from event_ts
    ooo_events = [
        e for e in result.events if e.event_ts != e.arrival_ts
    ]
    assert len(ooo_events) > 0, "There should be at least one event with out-of-order"
