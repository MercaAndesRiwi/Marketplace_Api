"""Unit tests for RF-02: Order status query with event timeline."""

from fastapi.testclient import TestClient
import pytest

from marketplace.presentation.fastapi.main import app
from marketplace.presentation.fastapi.routes.marketplace import ORDER_TIMELINE_REGISTRY


@pytest.fixture
def client():
    return TestClient(app)


def test_order_timeline_not_found(client):
    """TC-RF02-01: Non-existent order returns 404."""
    response = client.get("/api/v1/marketplace/orders/NON-EXISTENT-9999/timeline")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_order_timeline_with_registered_order(client):
    """TC-RF02-02: Query order timeline returns chronological sequence and current status."""
    order_id = "MA-TEST-ORDER-001"
    ORDER_TIMELINE_REGISTRY[order_id] = [
        {"event_id": "evt-01", "status": "created", "timestamp": "2026-11-06T10:00:00Z"},
        {"event_id": "evt-02", "status": "paid", "timestamp": "2026-11-06T10:05:00Z"},
        {"event_id": "evt-03", "status": "shipped", "timestamp": "2026-11-06T14:30:00Z"},
        {"event_id": "evt-04", "status": "delivered", "timestamp": "2026-11-07T09:15:00Z"},
    ]

    response = client.get(f"/api/v1/marketplace/orders/{order_id}/timeline")
    assert response.status_code == 200
    data = response.json()

    assert data["order_id"] == order_id
    assert data["current_status"] == "delivered"
    assert data["total_events"] == 4
    assert len(data["timeline"]) == 4
    assert data["timeline"][0]["status"] == "created"
    assert data["timeline"][-1]["status"] == "delivered"
