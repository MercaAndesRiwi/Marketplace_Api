"""Seeded marketplace event producer (F4): lifecycle + faults + peak mode.

All producers share IDs from a built-in catalog. Event IDs are
deterministic ``uuid5`` so duplicate injection re-emits the same ID.
Timestamps are logical (no sleep); peak throughput is pure compute.

Validaciones integradas (autónoma, sin depender de orquestador externo):
- Verifica MASTER_SEED, F4_DUPLICATE_RATE, F4_OOO_MAX_LAG_SEC.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from marketplace.config import (
    MASTER_SEED,
    F4_DUPLICATE_RATE,
    F4_OOO_ENABLED,
    F4_OOO_MAX_LAG_SEC,
    OUTPUT_FILE,
)
from marketplace.lifecycle import (
    CREATED, PAID, SHIPPED, DELIVERED, CANCELLED, RETURNED, Order,
)


EVENT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Catálogo maestro simplificado (autocontenido, sin dependencias externas)
CATEGORIES = (
    "health_beauty", "computers_accessories", "auto", "bed_bath_table",
    "furniture_decor", "sports_leisure", "perfumery", "housewares",
    "telephony", "watches_gifts", "food_drink", "baby", "stationery",
    "tablets_printing_image", "toys", "fixed_telephony", "garden_tools",
    "fashion_bags_accessories", "small_appliances", "consoles_games",
    "audio", "fashion_shoes", "cool_stuff", "luggage_accessories",
    "air_conditioning", "construction_tools_construction",
    "kitchen_dining_laundry_garden_furniture", "costruction_tools_garden",
    "fashion_male_clothing", "pet_shop", "office_furniture", "market_place",
    "electronics", "home_appliances", "party_supplies", "home_confort",
    "costruction_tools_tools", "agro_industry_and_commerce",
    "furniture_mattress_and_upholstery", "books_technical",
    "home_construction", "musical_instruments", "furniture_living_room",
    "construction_tools_lights", "industry_commerce_and_business",
    "food", "art", "furniture_bedroom", "books_general_interest",
    "construction_tools_safety", "fashion_underwear_beach",
    "fashion_sport", "signaling_and_security", "computers",
    "christmas_supplies", "fashio_female_clothing", "home_appliances_2",
    "books_imported", "drinks", "cine_photo", "la_cuisine", "music",
    "home_comfort_2", "small_appliances_home_oven_and_coffee",
    "cds_dvds_musicals", "dvds_blu_ray", "flowers",
    "arts_and_craftsmanship", "diapers_and_hygiene",
    "fashion_childrens_clothes", "security_and_services",
)

COUNTRIES = ("CO", "PE", "EC", "BO", "CL")


def _build_stores(seed: int) -> list[dict]:
    """Construye tiendas deterministas."""
    rng = random.Random(f"{seed}-stores")
    stores = []
    for country in COUNTRIES:
        for i in range(1, 3):
            stores.append({
                "store_id": f"STO-{country}-FIS-{i:03d}",
                "name": f"MercaAndes Fisica {country} {i}",
                "country": country,
                "channel": "Tienda Fisica",
                "seller_id": f"SEL-{country}-FIS-{i:03d}",
            })
        stores.append({
            "store_id": f"STO-{country}-ECOM-001",
            "name": f"MercaAndes E-commerce {country}",
            "country": country,
            "channel": "E-commerce Propio",
            "seller_id": f"SEL-{country}-ECOM",
        })
        stores.append({
            "store_id": f"STO-{country}-MKT-001",
            "name": f"MercaAndes Marketplace {country}",
            "country": country,
            "channel": "Marketplace Propietario",
            "seller_id": f"SEL-{country}-MKT",
        })
    return stores


def _build_products(seed: int, per_category: int = 15) -> list[dict]:
    """Construye productos deterministas."""
    rng = random.Random(f"{seed}-products")
    products = []
    seq = 1
    for category in CATEGORIES:
        for _ in range(per_category):
            country = rng.choice(COUNTRIES)
            sku = f"SKU-{category[:3].upper()}-{country}-{seq:05d}"
            products.append({
                "sku": sku,
                "name": f"{category.replace('_', ' ').title()} Item {seq:05d} ({country})",
                "category": category,
                "country": country,
                "seller_id": f"SEL-{country}-PROD-{seq:05d}",
                "base_price_usd": round(rng.uniform(12.0, 1200.0), 2),
            })
            seq += 1
    return products


def validate_environment() -> None:
    """Valida variables de entorno y parámetros."""
    if not 0 <= F4_DUPLICATE_RATE <= 1:
        print(f"ERROR: F4_DUPLICATE_RATE debe estar entre 0 y 1. Valor actual: {F4_DUPLICATE_RATE}")
        sys.exit(1)

    if F4_OOO_MAX_LAG_SEC < 0 or F4_OOO_MAX_LAG_SEC > 21600:
        print(f"ERROR: F4_OOO_MAX_LAG_SEC debe estar entre 0 y 21600. Valor actual: {F4_OOO_MAX_LAG_SEC}")
        sys.exit(1)

    if MASTER_SEED <= 0:
        print(f"ERROR: MASTER_SEED debe ser un entero positivo. Valor actual: {MASTER_SEED}")
        sys.exit(1)

    print("Validación de entorno: OK")


@dataclass(frozen=True)
class Event:
    event_id: str
    order_id: str
    event_type: str
    sku: str
    store_id: str
    seller_id: str
    country: str
    quantity: int
    unit_price: float
    event_ts: datetime
    arrival_ts: datetime

    def with_arrival(self, arrival_ts: datetime) -> Event:
        return replace(self, arrival_ts=arrival_ts)

    def to_json(self) -> str:
        payload = asdict(self)
        payload["event_ts"] = self.event_ts.isoformat()
        payload["arrival_ts"] = self.arrival_ts.isoformat()
        return json.dumps(payload)


@dataclass
class ProducerConfig:
    seed: int = MASTER_SEED
    n_orders: int = 100
    duplicate_rate: float = F4_DUPLICATE_RATE
    ooo_enabled: bool = F4_OOO_ENABLED
    ooo_max_lag_sec: int = F4_OOO_MAX_LAG_SEC
    start: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __post_init__(self) -> None:
        if self.n_orders <= 0:
            raise ValueError("n_orders must be positive.")
        if not 0 <= self.duplicate_rate <= 1:
            raise ValueError("duplicate_rate must be between 0 and 1.")
        if self.ooo_max_lag_sec < 0 or self.ooo_max_lag_sec > 21600:
            raise ValueError("ooo_max_lag_sec must be in [0, 21600].")


def _step_timestamps(rng: random.Random, base: datetime) -> dict[str, datetime]:
    paid_at = base + timedelta(minutes=5, seconds=rng.randint(0, 600))
    shipped_at = paid_at + timedelta(hours=2, minutes=rng.randint(0, 60))
    final_at = shipped_at + timedelta(hours=24, minutes=rng.randint(0, 120))
    return {"paid": paid_at, "shipped": shipped_at, "final": final_at}


def generate_events(config: ProducerConfig) -> list:
    """Generate arrival-ordered events for ``n_orders`` seeded orders."""
    stores = _build_stores(config.seed)
    products = _build_products(config.seed)
    rng = random.Random(f"{config.seed}-orders")

    price_by_sku = {p["sku"]: p["base_price_usd"] for p in products}

    ordered: list = []
    for i in range(config.n_orders):
        product = rng.choice(products)
        candidates = [s for s in stores if s["country"] == product["country"]]
        store = rng.choice(candidates)
        order_id = f"ORD-{config.seed}-{i:06d}"
        base = config.start + timedelta(seconds=i * 30)
        stamps = _step_timestamps(rng, base)
        quantity = rng.randint(1, 3)
        unit_price = price_by_sku[product["sku"]]

        order = Order(
            order_id=order_id,
            sku=product["sku"],
            store_id=store["store_id"],
            seller_id=product["seller_id"],
            country=product["country"],
        )
        if rng.random() < 0.06:
            states = [(CANCELLED, base + timedelta(minutes=1))]
            order.apply(CANCELLED)
        else:
            order.apply(PAID)
            states = [(PAID, stamps["paid"])]
            if rng.random() < 0.08:
                order.apply(CANCELLED)
                states.append((CANCELLED, stamps["shipped"]))
            else:
                order.apply(SHIPPED)
                states.append((SHIPPED, stamps["shipped"]))
                roll = rng.random()
                if roll < 0.80:
                    order.apply(DELIVERED)
                    states.append((DELIVERED, stamps["final"]))
                elif roll < 0.90:
                    order.apply(RETURNED)
                    states.append((RETURNED, stamps["final"]))
                else:
                    order.apply(CANCELLED)
                    states.append((RETURNED, stamps["final"]))

        for seq, (state, ts) in enumerate([(CREATED, base)] + states):
            event_id = str(uuid.uuid5(EVENT_NAMESPACE, f"{config.seed}-{order_id}-{seq}"))
            ordered.append(
                Event(
                    event_id=event_id,
                    order_id=order_id,
                    event_type=state,
                    sku=product["sku"],
                    store_id=store["store_id"],
                    seller_id=product["seller_id"],
                    country=product["country"],
                    quantity=quantity,
                    unit_price=unit_price,
                    event_ts=ts,
                    arrival_ts=ts,
                )
            )

    rng_faults = random.Random(f"{config.seed}-faults")
    from marketplace.faults import apply_duplicates, apply_out_of_order
    faulted = apply_duplicates(ordered, rng_faults, config.duplicate_rate)
    if config.ooo_enabled:
        faulted = apply_out_of_order(faulted, rng_faults, config.ooo_max_lag_sec)
    return faulted


def write_jsonl(events: list, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(event.to_json() + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seeded F4 event producer.")
    parser.add_argument("--seed", type=int, default=MASTER_SEED)
    parser.add_argument("--orders", type=int, default=100)
    parser.add_argument("--duplicate-rate", type=float, default=F4_DUPLICATE_RATE)
    parser.add_argument("--ooo", action="store_true")
    parser.add_argument("--max-lag", type=int, default=F4_OOO_MAX_LAG_SEC)
    parser.add_argument("--start", default="2026-01-01T00:00:00+00:00")
    parser.add_argument("--out", default=OUTPUT_FILE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    validate_environment()

    args = parse_args(argv)
    config = ProducerConfig(
        seed=args.seed,
        n_orders=args.orders,
        duplicate_rate=args.duplicate_rate,
        ooo_enabled=bool(args.ooo),
        ooo_max_lag_sec=args.max_lag,
        start=datetime.fromisoformat(args.start),
    )
    started = time.perf_counter()
    events = generate_events(config)
    elapsed = time.perf_counter() - started
    write_jsonl(events, Path(args.out))
    eps = len(events) / elapsed if elapsed > 0 else float("inf")
    print(f"orders={config.n_orders} events={len(events)} eps={eps:.1f}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
