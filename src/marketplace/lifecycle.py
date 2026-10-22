"""Order lifecycle state machine for marketplace events (F4).

Valid lifecycle:
  created -> paid -> shipped -> delivered
    |           |          |
    v           v          v
  cancelled  cancelled  returned   (cancel after dispatch = return)
  delivered -> returned

Terminal states: delivered, cancelled, returned (returned is absorbing).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class InvalidTransitionError(ValueError):
    """Raised when an event is not allowed from the current state."""


CREATED = "created"
PAID = "paid"
SHIPPED = "shipped"
DELIVERED = "delivered"
CANCELLED = "cancelled"
RETURNED = "returned"

TERMINAL_STATES = frozenset({DELIVERED, CANCELLED, RETURNED})

_ALLOWED: dict[str, frozenset[str]] = {
    PAID: frozenset({CREATED}),
    SHIPPED: frozenset({PAID}),
    DELIVERED: frozenset({SHIPPED}),
    CANCELLED: frozenset({CREATED, PAID}),
    RETURNED: frozenset({SHIPPED, DELIVERED}),
}


def transition(current: str, requested: str) -> str:
    """Apply one event and return the new state.

    Post-dispatch rule: requesting ``cancelled`` from ``shipped``
    yields ``returned`` instead of raising.
    """
    if requested == CANCELLED and current == SHIPPED:
        return RETURNED
    allowed_from = _ALLOWED.get(requested)
    if allowed_from is None:
        raise InvalidTransitionError(f"Unknown event {requested!r}.")
    if current not in allowed_from:
        raise InvalidTransitionError(
            f"Cannot apply {requested!r} from {current!r}."
        )
    return requested


@dataclass
class Order:
    order_id: str
    sku: str
    store_id: str
    seller_id: str
    country: str
    state: str = CREATED
    history: list[str] = field(default_factory=lambda: [CREATED])

    def apply(self, event_type: str) -> str:
        """Validate, advance state and record history."""
        self.state = transition(self.state, event_type)
        self.history.append(self.state)
        return self.state

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
