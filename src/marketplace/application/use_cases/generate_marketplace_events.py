"""Use case: Generate marketplace events (F4).

Orchestrates marketplace order lifecycle event generation,
applying business rules, fault injection, and repository dispatch.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from marketplace.domain.entities.event import Event
from marketplace.domain.repositories.event_producer_repository import (
    EventProducerRepository,
)
from marketplace.application.use_cases.dto import EventDTO, GenerateEventsDTO


# Product categories for simulation
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

EVENT_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class GenerateMarketplaceEventsUseCase:
    """Use case to generate marketplace events (F4)."""

    def __init__(
        self,
        event_repository: EventProducerRepository,
        seed: int = 42,
        n_orders: int = 100,
        duplicate_rate: float = 0.0,
        ooo_enabled: bool = False,
        ooo_max_lag_sec: int = 21600,
        start: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc),
    ):
        self.event_repository = event_repository
        self.seed = seed
        self.n_orders = n_orders
        self.duplicate_rate = duplicate_rate
        self.ooo_enabled = ooo_enabled
        self.ooo_max_lag_sec = ooo_max_lag_sec
        self.start = start

    def _build_stores(self, seed: int) -> list:
        """Build deterministic stores by country."""
        random.Random(f"{seed}-stores")
        stores = []
        for country in COUNTRIES:
            for i in range(1, 3):
                stores.append({
                    "store_id": f"STO-{country}-FIS-{i:03d}",
                    "name": f"MercaAndes Fisica {country} {i}",
                    "country": country,
                    "channel": "Physical Store",
                    "seller_id": f"SEL-{country}-FIS-{i:03d}",
                })
            stores.append({
                "store_id": f"STO-{country}-ECOM-001",
                "name": f"MercaAndes E-commerce {country}",
                "country": country,
                "channel": "E-commerce Own",
                "seller_id": f"SEL-{country}-ECOM",
            })
            stores.append({
                "store_id": f"STO-{country}-MKT-001",
                "name": f"MercaAndes Marketplace {country}",
                "country": country,
                "channel": "Proprietary Marketplace",
                "seller_id": f"SEL-{country}-MKT",
            })
        return stores

    def _build_products(self, seed: int, per_category: int = 15) -> list:
        """Build deterministic products."""
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

    def _step_timestamps(self, rng: random.Random, base: datetime) -> dict:
        """Calculate lifecycle timestamps."""
        paid_at = base + timedelta(minutes=5, seconds=rng.randint(0, 600))
        shipped_at = paid_at + timedelta(hours=2, minutes=rng.randint(0, 60))
        final_at = shipped_at + timedelta(hours=24, minutes=rng.randint(0, 120))
        return {"paid": paid_at, "shipped": shipped_at, "final": final_at}

    def _generate_lifecycle(
        self,
        rng: random.Random,
        base: datetime,
        stamps: dict,
    ) -> list:
        """Generate order lifecycle states."""
        states = []
        if rng.random() < 0.06:
            states.append(("cancelled", base + timedelta(minutes=1)))
        else:
            states.append(("paid", stamps["paid"]))
            if rng.random() < 0.08:
                states.append(("cancelled", stamps["shipped"]))
            else:
                states.append(("shipped", stamps["shipped"]))
                roll = rng.random()
                if roll < 0.80:
                    states.append(("delivered", stamps["final"]))
                elif roll < 0.90:
                    states.append(("returned", stamps["final"]))
                else:
                    states.append(("cancelled", stamps["final"]))
                    states.append(("returned", stamps["final"]))
        return states

    def _apply_duplicates(self, events: List[Event], rng: random.Random) -> List[Event]:
        """Inject duplicate events with same event_id."""
        output = []
        for event in events:
            output.append(event)
            if rng.random() < self.duplicate_rate:
                copies = rng.randint(1, 1)
                output.extend(event for _ in range(copies))
        return output

    def _apply_out_of_order(self, events: List[Event], rng: random.Random) -> List[Event]:
        """Inject temporal disorder in arrival times."""
        shifted = []
        for event in events:
            lag = rng.uniform(0, self.ooo_max_lag_sec) if self.ooo_max_lag_sec else 0
            shifted.append(Event(
                event_id=event.event_id,
                order_id=event.order_id,
                event_type=event.event_type,
                sku=event.sku,
                store_id=event.store_id,
                seller_id=event.seller_id,
                country=event.country,
                quantity=event.quantity,
                unit_price=event.unit_price,
                event_ts=event.event_ts,
                arrival_ts=event.event_ts + timedelta(seconds=lag),
            ))
        shifted.sort(key=lambda e: e.arrival_ts)
        return shifted

    def execute(self) -> GenerateEventsDTO:
        """Execute full use case: generate events and send to repository."""
        stores = self._build_stores(self.seed)
        products = self._build_products(self.seed)
        rng = random.Random(f"{self.seed}-orders")

        price_by_sku = {p["sku"]: p["base_price_usd"] for p in products}

        ordered: List[Event] = []
        for i in range(self.n_orders):
            product = rng.choice(products)
            candidates = [s for s in stores if s["country"] == product["country"]]
            store = rng.choice(candidates)
            order_id = f"ORD-{self.seed}-{i:06d}"
            base = self.start + timedelta(seconds=i * 30)
            stamps = self._step_timestamps(rng, base)
            quantity = rng.randint(1, 3)
            unit_price = price_by_sku[product["sku"]]

            states = self._generate_lifecycle(rng, base, stamps)

            for seq, (state, ts) in enumerate([("created", base)] + states):
                event_id = str(uuid.uuid5(EVENT_NAMESPACE, f"{self.seed}-{order_id}-{seq}"))
                ordered.append(Event(
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
                ))

        # Inject faults
        rng_faults = random.Random(f"{self.seed}-faults")
        faulted = self._apply_duplicates(ordered, rng_faults)
        if self.ooo_enabled:
            faulted = self._apply_out_of_order(faulted, rng_faults)

        # Send to infrastructure repository
        self.event_repository.produce_events(faulted)

        # Convert to DTOs for presentation
        event_dtos = [
            EventDTO(
                event_id=e.event_id,
                order_id=e.order_id,
                event_type=e.event_type,
                sku=e.sku,
                store_id=e.store_id,
                seller_id=e.seller_id,
                country=e.country,
                quantity=e.quantity,
                unit_price=e.unit_price,
                event_ts=e.event_ts,
                arrival_ts=e.arrival_ts,
            )
            for e in faulted
        ]

        return GenerateEventsDTO(
            seed=self.seed,
            n_orders=self.n_orders,
            events_count=len(faulted),
            events=event_dtos,
        )
