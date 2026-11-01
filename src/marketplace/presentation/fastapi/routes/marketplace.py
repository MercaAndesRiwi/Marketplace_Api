"""Route for marketplace event producer (F4) and customer purchases."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
import pika
from pydantic import BaseModel, Field

from marketplace.application.use_cases.generate_marketplace_events import (
    GenerateMarketplaceEventsUseCase,
)
from marketplace.presentation.fastapi.deps import get_generate_events_use_case

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])


class ProductItem(BaseModel):
    name: str = Field(default="Aceite de Oliva Extra Virgen (500ml)")
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(default=35000.0, ge=0)


class PurchaseRequest(BaseModel):
    customer_name: str = Field(default="Luigui Garizado")
    customer_email: str = Field(default="luiguigarizadocotes@gmail.com")
    products: list[ProductItem] = Field(
        default=[
            ProductItem(name="Aceite de Oliva Extra Virgen (500ml)", quantity=1, unit_price=35000.0),
            ProductItem(name="Café Molido Especial (500g)", quantity=2, unit_price=24000.0),
        ]
    )


@router.post(
    "/purchase",
    status_code=status.HTTP_201_CREATED,
    summary="Simular compra real y disparar notificación por correo",
    description="Recibe una compra desde Swagger, genera la orden y la despacha a RabbitMQ.",
)
def create_purchase(request: PurchaseRequest):
    order_id = f"MA-2026-{uuid.uuid4().hex[:5].upper()}"
    purchase_date = datetime.now(timezone.utc).strftime("%d-%m-%Y")

    items = []
    total_paid = 0.0
    for prod in request.products:
        subtotal = prod.quantity * prod.unit_price
        total_paid += subtotal
        items.append({
            "name": prod.name,
            "quantity": prod.quantity,
            "unit_price": prod.unit_price,
            "subtotal": subtotal,
        })

    payload = {
        "event_type": "PURCHASE_CONFIRMED",
        "company": "MercaAndes",
        "order_id": order_id,
        "status": "Confirmado / En preparación",
        "purchase_date": purchase_date,
        "customer_name": request.customer_name,
        "customer_email": request.customer_email,
        "products": items,
        "total_paid": total_paid,
        "simulated_at": datetime.now(timezone.utc).isoformat(),
    }

    host = os.environ.get("RABBITMQ_HOST") or "localhost"
    port_raw = os.environ.get("RABBITMQ_PORT") or "5672"
    user = os.environ.get("RABBITMQ_USER") or "guest_user"
    password = os.environ.get("RABBITMQ_PASSWORD") or "MercaAndes2026!"
    vhost = os.environ.get("RABBITMQ_VHOST") or "/"
    queue_name = os.environ.get("RABBITMQ_QUEUE_PURCHASE_NOTIFICATIONS") or "mercaandes.notifications.purchase"

    try:
        credentials = pika.PlainCredentials(user, password)
        parameters = pika.ConnectionParameters(
            host=host,
            port=int(port_raw),
            virtual_host=vhost,
            credentials=credentials,
            connection_attempts=3,
            retry_delay=1,
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
        connection.close()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not publish purchase event to RabbitMQ: {exc}",
        ) from exc

    return {
        "status": "success",
        "message": "Compra procesada exitosamente y enviada a RabbitMQ",
        "order_id": order_id,
        "customer_email": request.customer_email,
        "total_paid": total_paid,
    }


@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
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
