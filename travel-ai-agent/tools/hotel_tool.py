"""LangChain tool for hotel recommendations over hotels.json."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from services.data_loader import get_hotels
from utils.helper import cities_match, ensure_list
from utils.recommendation_helpers import (
    filter_hotels_core,
    resolve_city_against_list,
)


def _format_hotel(hotel: Dict[str, Any]) -> Dict[str, Any]:
    """Format hotel for output."""
    return {
        "hotel_id": hotel.get("id"),
        "hotel_name": hotel.get("name"),
        "city": hotel.get("city"),
        "price": hotel.get("price"),
        "rating": hotel.get("rating"),
        "amenities": hotel.get("amenities") or [],
    }


def _sort_hotels(matches: List[Dict[str, Any]], sort_by: str) -> None:
    """Sort hotels in place."""
    sort_key = (sort_by or "rating").lower()
    if sort_key == "price":
        matches.sort(key=lambda h: h.get("price") or float("inf"))
    elif sort_key == "value":
        matches.sort(
            key=lambda h: (h.get("rating") or 0) / max(h.get("price") or 1, 1),
            reverse=True,
        )
    else:
        matches.sort(key=lambda h: h.get("rating") or 0, reverse=True)


def _hotels_in_city(hotels: List[Dict[str, Any]], city: str) -> List[Dict[str, Any]]:
    return [h for h in hotels if cities_match(h.get("city"), city)]


def recommend_hotels(
    city: str,
    min_rating: Optional[float] = None,
    max_price: Optional[float] = None,
    amenities: Optional[str] = None,
    sort_by: str = "rating",
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Recommend hotels with progressive filter relaxation and fuzzy city matching.

    Treats max_price <= 0 as no price cap. Ignores unrealistic caps (< ₹500/night)
    when they would eliminate all results.
    """
    all_hotels = get_hotels()
    hotel_cities = sorted({h["city"] for h in all_hotels if h.get("city")})
    resolved_city = resolve_city_against_list(city, hotel_cities)
    amenity_list = ensure_list(amenities)

    effective_max = max_price if max_price and max_price > 0 else None
    if effective_max is not None and effective_max < 500:
        effective_max = None  # UI typo / unrealistic cap

    fallback_level = "exact"
    relaxed: List[str] = []
    matches: List[Dict[str, Any]] = []

    # 1. Exact city + all filters
    matches = filter_hotels_core(
        all_hotels, resolved_city, min_rating, effective_max, amenity_list
    )

    # 2. Drop amenities
    if not matches and amenity_list:
        matches = filter_hotels_core(all_hotels, resolved_city, min_rating, effective_max, [])
        relaxed.append("amenities")
        fallback_level = "relaxed_amenities"

    # 3. Drop min rating
    if not matches and min_rating and min_rating > 0:
        matches = filter_hotels_core(all_hotels, resolved_city, None, effective_max, [])
        relaxed.append("min_rating")
        fallback_level = "relaxed_rating"

    # 4. Double max price, then remove cap
    if not matches and effective_max:
        matches = filter_hotels_core(
            all_hotels, resolved_city, None, effective_max * 2, []
        )
        if matches:
            relaxed.append("max_price_doubled")
            fallback_level = "relaxed_price"
        else:
            matches = filter_hotels_core(all_hotels, resolved_city, None, None, [])
            if matches:
                relaxed.append("max_price")
                fallback_level = "relaxed_price"

    # 5. City-only top rated
    if not matches:
        matches = _hotels_in_city(all_hotels, resolved_city)
        if matches:
            relaxed.append("all_filters")
            fallback_level = "city_only"

    # 6. Closest budget match in city
    if not matches:
        city_hotels = _hotels_in_city(all_hotels, resolved_city)
        if city_hotels:
            if effective_max:
                city_hotels.sort(
                    key=lambda h: abs((h.get("price") or 0) - effective_max)
                )
            else:
                _sort_hotels(city_hotels, sort_by)
            matches = city_hotels[:limit]
            relaxed.append("closest_budget")
            fallback_level = "closest_budget"

    # 7. Top hotels overall
    if not matches and all_hotels:
        matches = sorted(
            all_hotels,
            key=lambda h: h.get("rating") or 0,
            reverse=True,
        )[:limit]
        relaxed.append("global_fallback")
        fallback_level = "global_top"

    if not matches:
        return {
            "success": False,
            "message": f"No hotels available in dataset for {city}.",
            "hotels": [],
            "matched_count": 0,
            "fallback_level": "none",
        }

    _sort_hotels(matches, sort_by)
    formatted = [_format_hotel(h) for h in matches[:limit]]

    reasoning = f"Top {len(formatted)} hotels sorted by {sort_by}."
    if fallback_level != "exact":
        reasoning = (
            f"No hotels matched your strict filters in {city}. "
            f"Showing closest available options ({fallback_level.replace('_', ' ')})."
        )

    return {
        "success": True,
        "count": len(matches),
        "matched_count": len(matches),
        "selected": formatted[0],
        "hotels": formatted,
        "reasoning": reasoning,
        "fallback_level": fallback_level,
        "relaxed_filters": relaxed,
        "resolved_city": resolved_city,
    }


@tool
def hotel_recommendation_tool(
    city: str,
    min_rating: float = 0.0,
    max_price: float = 0.0,
    amenities: str = "",
    sort_by: str = "rating",
    limit: int = 5,
) -> str:
    """
    Find hotels in a city with optional rating, budget, and amenities filters.

    Pass min_rating and max_price as 0 to ignore. Amenities: comma-separated
    (e.g. wifi,pool). Returns hotel name, price, rating, and amenities.
    """
    result = recommend_hotels(
        city=city,
        min_rating=min_rating if min_rating > 0 else None,
        max_price=max_price if max_price > 0 else None,
        amenities=amenities or None,
        sort_by=sort_by,
        limit=limit,
    )
    return json.dumps(result, indent=2)
