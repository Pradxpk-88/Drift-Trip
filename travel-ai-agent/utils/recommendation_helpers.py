"""Robust matching, fuzzy resolution, and filter relaxation for recommendations."""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from utils.helper import cities_match, ensure_list, normalize_city, normalize_text


def fuzzy_closest(
    query: str,
    candidates: List[str],
    cutoff: float = 0.65,
    n: int = 1,
) -> Optional[str]:
    """Return best fuzzy match from candidates, or None."""
    if not query or not candidates:
        return None
    q = normalize_text(query)
    uniq = sorted({c for c in candidates if c})
    if not uniq:
        return None
    matches = difflib.get_close_matches(q, [normalize_text(c) for c in uniq], n=n, cutoff=cutoff)
    if not matches:
        return None
    m = matches[0]
    for c in uniq:
        if normalize_text(c) == m:
            return c
    return None


def resolve_city_against_list(user_city: str, known_cities: List[str]) -> str:
    """
    Resolve user input to a canonical city from known_cities.

    Uses normalize_city + aliases, then fuzzy match on display names.
    """
    if not user_city or not str(user_city).strip():
        return ""
    normalized = normalize_city(user_city)
    if not normalized:
        return str(user_city).strip()
    key = normalized.lower()
    for c in known_cities:
        if c and normalize_text(c) == key:
            return c
    fuzzy = fuzzy_closest(user_city, known_cities, cutoff=0.55)
    return fuzzy if fuzzy else normalized


def collect_flight_cities(flights: List[Dict[str, Any]]) -> List[str]:
    """Unique cities appearing in flight records."""
    cities: Set[str] = set()
    for f in flights:
        if f.get("source"):
            cities.add(f["source"])
        if f.get("destination"):
            cities.add(f["destination"])
    return sorted(cities)


def is_likely_city_name(name: str, place_cities: List[str]) -> bool:
    """True if string matches a known place city (user may have confused field)."""
    if not name:
        return False
    n = normalize_text(name)
    for c in place_cities:
        if c and normalize_text(c) == n:
            return True
    return False


def resolve_place_categories(
    category_input: Optional[str],
    valid_categories: Set[str],
    place_cities: List[str],
) -> Tuple[Optional[List[str]], str]:
    """
    Parse category filter; ignore if empty, invalid, or looks like a city name.

    Returns (list of valid category tokens or None for 'no filter', note).
    """
    if not category_input or not str(category_input).strip():
        return None, ""

    raw_parts = ensure_list(category_input)
    if not raw_parts:
        return None, ""

    # User typed a city name as "category" — ignore filter
    if len(raw_parts) == 1 and is_likely_city_name(raw_parts[0], place_cities):
        return None, "ignored_category_looks_like_city"

    resolved: List[str] = []
    unknown: List[str] = []
    valid_lower = {normalize_text(v) for v in valid_categories}

    for part in raw_parts:
        pl = normalize_text(part)
        if not pl:
            continue
        if pl in valid_lower:
            resolved.append(pl)
            continue
        # Fuzzy match to known category
        close = fuzzy_closest(part, list(valid_categories), cutoff=0.72)
        if close:
            resolved.append(normalize_text(close))
            continue
        unknown.append(part)

    if unknown and not resolved:
        return None, f"ignored_unknown_categories:{','.join(unknown)}"

    if unknown:
        return (resolved if resolved else None), f"partial_unknown:{','.join(unknown)}"

    return (resolved if resolved else None), ""


def hotel_amenity_match_required(hotel_amenities: List[str], required: List[str]) -> bool:
    """True if hotel has all required amenities (case-insensitive)."""
    hset = {normalize_text(a) for a in (hotel_amenities or [])}
    for req in required:
        r = normalize_text(req)
        if not r:
            continue
        if r not in hset:
            return False
    return True


def filter_hotels_core(
    hotels: List[Dict[str, Any]],
    city: str,
    min_rating: Optional[float],
    max_price: Optional[float],
    amenity_list: List[str],
) -> List[Dict[str, Any]]:
    """Apply filters; city must already match canonical."""
    matches: List[Dict[str, Any]] = []
    for hotel in hotels:
        if not cities_match(hotel.get("city"), city):
            continue
        rating = hotel.get("rating")
        if min_rating is not None and min_rating > 0 and (rating is None or rating < min_rating):
            continue
        if max_price is not None and max_price > 0:
            price = hotel.get("price")
            if price is None or price > max_price:
                continue
        if amenity_list and not hotel_amenity_match_required(hotel.get("amenities") or [], amenity_list):
            continue
        matches.append(hotel)
    return matches


def effective_hotel_max_price(
    max_hotel_price: float,
    budget: Optional[float],
    num_days: int,
) -> Optional[float]:
    """Ignore unrealistic caps (e.g. ₹1); derive from budget when unset."""
    if max_hotel_price and max_hotel_price >= 500:
        return max_hotel_price
    if budget and num_days:
        return budget / num_days * 0.45
    return None
