"""Configurable fault injection: duplicates and temporal disorder (F4).

Both helpers are pure and deterministic given ``rng``:
- duplicates re-emit the same ``event_id`` (configurable rate);
- out-of-order keeps ``event_ts`` intact and only shifts ``arrival_ts``
  up to ``max_lag_sec`` (default 6h), then delivers by ``arrival_ts``.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from marketplace.producer import Event


def apply_duplicates(
    events: list,
    rng: random.Random,
    duplicate_rate: float,
    max_copies: int = 1,
) -> list:
    """Re-emit events with the same ID with probability ``duplicate_rate``."""
    if not 0 <= duplicate_rate <= 1:
        raise ValueError("duplicate_rate must be between 0 and 1.")
    if max_copies < 1:
        raise ValueError("max_copies must be >= 1.")

    output: list = []
    for event in events:
        output.append(event)
        if rng.random() < duplicate_rate:
            copies = rng.randint(1, max_copies)
            output.extend(event for _ in range(copies))
    return output


def apply_out_of_order(
    events: list,
    rng: random.Random,
    max_lag_sec: int = 21600,
) -> list:
    """Shift arrival times up to ``max_lag_sec`` and deliver by arrival."""
    if max_lag_sec < 0:
        raise ValueError("max_lag_sec must be >= 0.")
    if max_lag_sec > 21600:
        raise ValueError("max_lag_sec must not exceed 6 hours (21600s).")

    from datetime import timedelta

    shifted: list = []
    for event in events:
        lag = rng.uniform(0, max_lag_sec) if max_lag_sec else 0
        shifted.append(
            event.with_arrival(event.event_ts + timedelta(seconds=lag))
        )
    shifted.sort(key=lambda e: e.arrival_ts)
    return shifted
