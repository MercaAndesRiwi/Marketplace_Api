"""Dependency injection for FastAPI (marketplace).

Connects the presentation layer with infrastructure and application.
"""

from __future__ import annotations


from fastapi import Depends

from marketplace.infrastructure.config import (
    MASTER_SEED,
    F4_DUPLICATE_RATE,
    F4_OOO_ENABLED,
    F4_OOO_MAX_LAG_SEC,
    OUTPUT_FILE,
)
from marketplace.infrastructure.persistence.marketplace_producer_repository import (
    JsonlEventProducerRepository,
)
from marketplace.application.use_cases.generate_marketplace_events import (
    GenerateMarketplaceEventsUseCase,
)


def get_event_repository() -> JsonlEventProducerRepository:
    """Provide the event producer repository."""
    return JsonlEventProducerRepository(output_file=OUTPUT_FILE)


def get_generate_events_use_case(
    repo: JsonlEventProducerRepository = Depends(get_event_repository),
) -> GenerateMarketplaceEventsUseCase:
    """Provide the marketplace event generation use case."""
    return GenerateMarketplaceEventsUseCase(
        event_repository=repo,
        seed=MASTER_SEED,
        n_orders=100,
        duplicate_rate=F4_DUPLICATE_RATE,
        ooo_enabled=F4_OOO_ENABLED,
        ooo_max_lag_sec=F4_OOO_MAX_LAG_SEC,
    )
