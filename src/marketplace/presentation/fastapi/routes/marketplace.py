"""Route for marketplace event producer (F4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from marketplace.application.use_cases.generate_marketplace_events import (
    GenerateMarketplaceEventsUseCase,
)
from marketplace.presentation.fastapi.deps import get_generate_events_use_case

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


@router.post(
    "/events", status_code=status.HTTP_201_CREATED,
    summary="Generate marketplace events (F4)",
    description="Generates order lifecycle events with configurable fault injection.",
)
def generate_events(
    orders: int = Query(100, ge=1, description="Number of orders to generate"),
    seed: int = Query(42, ge=1, description="Seed for deterministic generation"),
    duplicate_rate: float = Query(0.0, ge=0.0, le=1.0, description="Duplicate rate"),
    ooo_enabled: bool = Query(False, description="Enable out-of-order"),
    max_lag: int = Query(21600, ge=0, le=21600, description="Max lag in seconds"),
    use_case: GenerateMarketplaceEventsUseCase = Depends(get_generate_events_use_case),
):
    """Generate marketplace events and send to repository (JSONL file)."""
    # Override use_case parameters with request values
    use_case.seed = seed
    use_case.n_orders = orders
    use_case.duplicate_rate = duplicate_rate
    use_case.ooo_enabled = ooo_enabled
    use_case.ooo_max_lag_sec = max_lag

    result = use_case.execute()

    return {
        "seed": result.seed,
        "n_orders": result.n_orders,
        "events_count": result.events_count,
        "events": [
            {
                "event_id": e.event_id,
                "order_id": e.order_id,
                "event_type": e.event_type,
                "sku": e.sku,
                "store_id": e.store_id,
                "seller_id": e.seller_id,
                "country": e.country,
                "quantity": e.quantity,
                "unit_price": e.unit_price,
                "event_ts": e.event_ts.isoformat(),
                "arrival_ts": e.arrival_ts.isoformat(),
            }
            for e in result.events
        ],
    }
