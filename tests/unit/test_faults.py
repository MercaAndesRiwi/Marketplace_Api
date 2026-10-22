"""Tests unitarios para inyección de fallos (F4)."""

from datetime import datetime, timezone
import random

from marketplace.faults import apply_duplicates, apply_out_of_order
from marketplace.producer import Event, generate_events, ProducerConfig


def _event(event_id: str, ts: datetime) -> Event:
    return Event(
        event_id=event_id,
        order_id="ORD-1",
        event_type="created",
        sku="SKU-X",
        store_id="STO",
        seller_id="SEL",
        country="CO",
        quantity=1,
        unit_price=10.0,
        event_ts=ts,
        arrival_ts=ts,
    )


def test_duplicates_disabled_by_default():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [_event(f"E{i}", base) for i in range(5)]
    out = apply_duplicates(events, random.Random(1), 0.0)
    assert [e.event_id for e in out] == [f"E{i}" for i in range(5)]


def test_duplicates_repeat_same_id_when_enabled():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [_event(f"E{i}", base) for i in range(20)]
    out = apply_duplicates(events, random.Random(2), 1.0)
    assert len(out) > len(events)
    assert {e.event_id for e in out} == {f"E{i}" for i in range(20)}


def test_out_of_order_capped_at_six_hours():
    events = generate_events(ProducerConfig(seed=11, n_orders=30, ooo_enabled=False))
    shifted = apply_out_of_order(events, random.Random(3), 21600)
    lags = [(e.arrival_ts - e.event_ts).total_seconds() for e in shifted]
    assert all(0 <= lag <= 21600 for lag in lags)
    assert [e.arrival_ts for e in shifted] == sorted(e.arrival_ts for e in shifted)
