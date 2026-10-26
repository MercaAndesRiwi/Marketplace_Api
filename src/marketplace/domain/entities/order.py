"""Domain entity: Order (marketplace order)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Order:
    """Domain entity: Marketplace order."""

    order_id: str
    sku: str
    store_id: str
    seller_id: str
    country: str
    state: str = "created"
    history: list = field(default_factory=lambda: ["created"])

    @property
    def is_terminal(self) -> bool:
        """Indicates if the order is in a terminal state."""
        return self.state in {"delivered", "cancelled", "returned"}

    def apply(self, event_type: str) -> str:
        """Validate and advance the order state.

        Valid transitions:
        - created -> paid, cancelled
        - paid -> shipped, cancelled
        - shipped -> delivered, cancelled (becomes returned), returned
        """
        allowed_transitions = {
            "created": {"paid", "cancelled"},
            "paid": {"shipped", "cancelled"},
            "shipped": {"delivered", "cancelled", "returned"},
            "delivered": set(),  
            "cancelled": set(), 
            "returned": set(),   
        }

        if event_type not in allowed_transitions.get(self.state, set()):
            raise ValueError(
                f"Cannot apply {event_type} from state {self.state}"
            )

        # Post-dispatch rule: cancelling from shipped becomes returned
        if event_type == "cancelled" and self.state == "shipped":
            self.state = "returned"
        else:
            self.state = event_type

        self.history.append(self.state)
        return self.state
