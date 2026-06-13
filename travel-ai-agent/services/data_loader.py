"""Cached dataset loaders for flights, hotels, and places."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List

from utils.constants import FLIGHTS_FILE, HOTELS_FILE, PLACES_FILE
from utils.helper import (
    build_place_description,
    is_valid_flight,
    is_valid_hotel,
    is_valid_place,
    load_and_normalize,
    normalize_city,
    parse_datetime,
    parse_duration_hours,
    parse_price,
    parse_rating,
)
from utils.constants import FLIGHT_FIELDS, HOTEL_FIELDS, PLACE_FIELDS


def _enrich_flight(record: Dict[str, Any]) -> Dict[str, Any]:
    """Add computed fields to a normalized flight record."""
    duration_h = parse_duration_hours(record.get("departure"), record.get("arrival"))
    dep_dt = parse_datetime(record.get("departure"))
    return {
        **record,
        "source": normalize_city(record.get("source")),
        "destination": normalize_city(record.get("destination")),
        "price": parse_price(record.get("price")),
        "duration_hours": duration_h,
        "duration": duration_h,
        "travel_date": dep_dt.date().isoformat() if dep_dt else None,
    }


def _enrich_hotel(record: Dict[str, Any]) -> Dict[str, Any]:
    """Add computed fields to a normalized hotel record."""
    amenities = record.get("amenities")
    if isinstance(amenities, str):
        amenities = [a.strip() for a in amenities.split(",") if a.strip()]
    elif not isinstance(amenities, list):
        amenities = []
    return {
        **record,
        "city": normalize_city(record.get("city")),
        "rating": parse_rating(record.get("rating")),
        "price": parse_price(record.get("price")),
        "amenities": [str(a).lower() for a in amenities],
    }


def _enrich_place(record: Dict[str, Any]) -> Dict[str, Any]:
    """Add computed fields to a normalized place record."""
    enriched = {
        **record,
        "city": normalize_city(record.get("city")),
        "category": str(record.get("category") or "general").lower(),
        "rating": parse_rating(record.get("rating")),
    }
    enriched["description"] = build_place_description(enriched)
    return enriched


@lru_cache(maxsize=1)
def get_flights() -> List[Dict[str, Any]]:
    """Load and cache all valid flights."""
    records = load_and_normalize(FLIGHTS_FILE, FLIGHT_FIELDS, is_valid_flight)
    return [_enrich_flight(r) for r in records]


@lru_cache(maxsize=1)
def get_hotels() -> List[Dict[str, Any]]:
    """Load and cache all valid hotels."""
    records = load_and_normalize(HOTELS_FILE, HOTEL_FIELDS, is_valid_hotel)
    return [_enrich_hotel(r) for r in records]


@lru_cache(maxsize=1)
def get_places() -> List[Dict[str, Any]]:
    """Load and cache all valid places."""
    records = load_and_normalize(PLACES_FILE, PLACE_FIELDS, is_valid_place)
    return [_enrich_place(r) for r in records]


def get_place_category_vocab() -> set[str]:
    """Distinct place categories/types from the dataset (lowercase)."""
    return {p.get("category", "").lower() for p in get_places() if p.get("category")}


def get_dataset_counts() -> Dict[str, int]:
    """Row counts for debug / health checks."""
    return {
        "flights": len(get_flights()),
        "hotels": len(get_hotels()),
        "places": len(get_places()),
    }


def get_available_cities() -> Dict[str, List[str]]:
    """Return cities present in each dataset."""
    flight_cities = set()
    for f in get_flights():
        if f.get("source"):
            flight_cities.add(f["source"])
        if f.get("destination"):
            flight_cities.add(f["destination"])
    return {
        "flight_cities": sorted(flight_cities),
        "hotel_cities": sorted({h["city"] for h in get_hotels() if h.get("city")}),
        "place_cities": sorted({p["city"] for p in get_places() if p.get("city")}),
    }
