"""Tests unitarios para el ciclo de vida de órdenes (F4)."""

from marketplace.lifecycle import (
    Order,
    CREATED, PAID, SHIPPED, DELIVERED, CANCELLED, RETURNED,
    TERMINAL_STATES, transition, InvalidTransitionError,
)


def test_happy_path():
    order = Order(
        order_id="ORD-1",
        sku="SKU-001",
        store_id="STO-1",
        seller_id="SEL-1",
        country="CO",
    )
    assert order.state == CREATED
    order.apply(PAID)
    assert order.state == PAID
    order.apply(SHIPPED)
    assert order.state == SHIPPED
    order.apply(DELIVERED)
    assert order.state == DELIVERED
    assert order.is_terminal


def test_cancel_before_dispatch():
    order = Order(
        order_id="ORD-2",
        sku="SKU-001",
        store_id="STO-1",
        seller_id="SEL-1",
        country="CO",
    )
    order.apply(PAID)
    order.apply(CANCELLED)
    assert order.state == CANCELLED
    assert order.is_terminal


def test_cancel_after_dispatch_becomes_return():
    new_state = transition(SHIPPED, CANCELLED)
    assert new_state == RETURNED


def test_invalid_transition_raises():
    order = Order(
        order_id="ORD-4",
        sku="SKU-001",
        store_id="STO-1",
        seller_id="SEL-1",
        country="CO",
    )
    try:
        order.apply(SHIPPED)
        assert False, "Should have raised InvalidTransitionError"
    except InvalidTransitionError:
        pass
