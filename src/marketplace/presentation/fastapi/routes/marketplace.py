"""Route for marketplace event producer (F4) and customer purchases."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Query, status
import pika
from pydantic import BaseModel, Field

from marketplace.application.use_cases.generate_marketplace_events import (
    GenerateMarketplaceEventsUseCase,
)
from marketplace.presentation.fastapi.deps import get_generate_events_use_case

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace"])

# In-memory order timeline registry for simulated/generated orders (RF-02)
ORDER_TIMELINE_REGISTRY: dict[str, list[dict]] = {}


class ProductItem(BaseModel):
    name: str = Field(default="Aceite de Oliva Extra Virgen (500ml)")
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(default=35000.0, ge=0)


class PurchaseRequest(BaseModel):
    customer_name: str = Field(default="Luigui Garizado", description="Nombre del cliente")
    customer_email: str = Field(default="luiguigarizadocotes@gmail.com", description="Correo del cliente para factura y notificaciones")
    delivery_address: str = Field(default="Carrera 43A # 1-50, El Poblado, Medellín", description="Dirección física de entrega del pedido")
    country: str = Field(default="CO", description="País: CO (Colombia), PE (Perú), CL (Chile), EC (Ecuador), BO (Bolivia)")
    currency: str = Field(default="COP", description="Moneda: COP, PEN, CLP, USD, BOB")
    products: list[ProductItem] = Field(
        default=[
            ProductItem(name="Aceite de Oliva Extra Virgen (500ml)", quantity=1, unit_price=35000.0),
            ProductItem(name="Café Molido Especial (500g)", quantity=2, unit_price=24000.0),
        ]
    )


def _progress_order_lifecycle(order_id: str, customer_name: str, delivery_address: str, country: str, interval_seconds: int = 120):
    """Avanza automáticamente el ciclo de vida de la orden en segundo plano cada 2 minutos."""
    try:
        # Paso 1: Espera 2 minutos -> Despacho en camino
        time.sleep(interval_seconds)
        if order_id in ORDER_TIMELINE_REGISTRY:
            current_states = [e.get("status") for e in ORDER_TIMELINE_REGISTRY[order_id]]
            if "shipped" not in current_states and "delivered" not in current_states and "cancelled" not in current_states:
                ORDER_TIMELINE_REGISTRY[order_id].append({
                    "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                    "status": "shipped",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "country": country,
                    "detail": f"Pedido {order_id} despachado del Centro Logístico MercaAndes ({country}) en camino a: {delivery_address}",
                })

        # Paso 2: Espera otros 2 minutos -> Entrega final al cliente
        time.sleep(interval_seconds)
        if order_id in ORDER_TIMELINE_REGISTRY:
            current_states = [e.get("status") for e in ORDER_TIMELINE_REGISTRY[order_id]]
            if "delivered" not in current_states and "cancelled" not in current_states:
                ORDER_TIMELINE_REGISTRY[order_id].append({
                    "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                    "status": "delivered",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "country": country,
                    "detail": f"Pedido {order_id} entregado con éxito a {customer_name} en: {delivery_address}",
                })
    except Exception as exc:
        print(f"[ORDER_LIFECYCLE_ERROR] {order_id}: {exc}")


@router.post(
    "/purchase",
    status_code=status.HTTP_201_CREATED,
    summary="Simular compra real y disparar notificación por correo",
    description="Recibe una compra desde Swagger, genera la orden, envía la factura por RabbitMQ y programa el ciclo de vida.",
)
def create_purchase(request: PurchaseRequest):
    order_id = f"MA-2026-{uuid.uuid4().hex[:5].upper()}"
    now_utc = datetime.now(timezone.utc)
    purchase_date = now_utc.strftime("%d-%m-%Y")

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
        "delivery_address": request.delivery_address,
        "country": request.country,
        "currency": request.currency,
        "products": items,
        "total_paid": total_paid,
        "simulated_at": now_utc.isoformat(),
    }

    # Register initial timeline events for RF-02
    ORDER_TIMELINE_REGISTRY[order_id] = [
        {
            "event_id": f"evt-{uuid.uuid4().hex[:8]}",
            "status": "created",
            "timestamp": now_utc.isoformat(),
            "country": request.country,
            "detail": f"Orden {order_id} creada por {request.customer_name} ({request.country}) - Destino: {request.delivery_address}",
        },
        {
            "event_id": f"evt-{uuid.uuid4().hex[:8]}",
            "status": "paid",
            "timestamp": now_utc.isoformat(),
            "country": request.country,
            "detail": f"Pago confirmado por {total_paid:.2f} {request.currency}",
        },
    ]

    # Iniciar temporizador de 2 minutos en segundo plano
    progression_thread = threading.Thread(
        target=_progress_order_lifecycle,
        args=(order_id, request.customer_name, request.delivery_address, request.country, 120),
        daemon=True,
    )
    progression_thread.start()

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
        "message": f"Compra procesada exitosamente en {request.currency}. Notificación enviada a RabbitMQ. El pedido pasará a 'shipped' en 2 min y 'delivered' en 4 min.",
        "order_id": order_id,
        "country": request.country,
        "currency": request.currency,
        "delivery_address": request.delivery_address,
        "customer_email": request.customer_email,
        "total_paid": total_paid,
    }


@router.post(
    "/orders/{order_id}/advance",
    status_code=status.HTTP_200_OK,
    summary="Avanzar manualmente el estado de una orden (RF-02)",
    description="Permite forzar el avance del ciclo de vida (shipped, delivered, returned, cancelled) inmediatamente sin esperar los 2 minutos.",
)
def advance_order_status(
    order_id: str = PathParam(..., description="ID de la orden (ej: MA-2026-XXXXX)"),
    target_status: str = Query("shipped", enum=["shipped", "delivered", "returned", "cancelled"]),
):
    if order_id not in ORDER_TIMELINE_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found in registry",
        )
    
    current_events = ORDER_TIMELINE_REGISTRY[order_id]
    current_status = current_events[-1].get("status") if current_events else "unknown"
    
    now_str = datetime.now(timezone.utc).isoformat()
    ORDER_TIMELINE_REGISTRY[order_id].append({
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "status": target_status,
        "timestamp": now_str,
        "detail": f"Transición manual a estado '{target_status}' registrada exitosamente para la orden {order_id}",
    })
    
    return {
        "order_id": order_id,
        "previous_status": current_status,
        "current_status": target_status,
        "total_events": len(ORDER_TIMELINE_REGISTRY[order_id]),
        "timeline": ORDER_TIMELINE_REGISTRY[order_id],
    }


@router.get(
    "/orders/{order_id}/timeline",
    status_code=status.HTTP_200_OK,
    summary="Order status query with event timeline (RF-02)",
    description="Returns current order status and chronological timeline of events for an order.",
)
def get_order_timeline(
    order_id: str = PathParam(..., description="Unique order identifier (e.g. MA-2026-XXXXX)"),
):
    """Exposes an order status query with its chronological event timeline (RF-02)."""
    timeline_events: list[dict] = []

    # 1. Check in-memory registry
    if order_id in ORDER_TIMELINE_REGISTRY:
        timeline_events.extend(ORDER_TIMELINE_REGISTRY[order_id])

    # 2. Check JSONL events storage if present
    events_file = Path("data/raw/events.jsonl")
    if events_file.exists():
        try:
            with events_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    if rec.get("order_id") == order_id:
                        timeline_events.append({
                            "event_id": rec.get("event_id", f"evt-{uuid.uuid4().hex[:6]}"),
                            "status": rec.get("event_type", "unknown").lower(),
                            "timestamp": rec.get("event_ts", datetime.now(timezone.utc).isoformat()),
                            "sku": rec.get("sku"),
                            "store_id": rec.get("store_id"),
                            "detail": f"Marketplace event: {rec.get('event_type')}",
                        })
        except Exception:
            pass

    if not timeline_events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order '{order_id}' not found",
        )

    # Sort chronologically by timestamp
    timeline_events.sort(key=lambda x: x.get("timestamp", ""))

    current_status = timeline_events[-1].get("status", "created")

    return {
        "order_id": order_id,
        "current_status": current_status,
        "total_events": len(timeline_events),
        "timeline": timeline_events,
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

    # Track generated events in timeline registry
    for e in result.events:
        ORDER_TIMELINE_REGISTRY.setdefault(e.order_id, []).append({
            "event_id": e.event_id,
            "status": e.event_type.lower(),
            "timestamp": e.event_ts.isoformat(),
            "sku": e.sku,
            "store_id": e.store_id,
            "seller_id": e.seller_id,
            "country": e.country,
            "detail": f"Event {e.event_type} registered",
        })

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
