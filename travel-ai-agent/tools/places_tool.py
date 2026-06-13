"""LangChain tool for places discovery over places.json."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from services.data_loader import get_place_category_vocab, get_places
from utils.helper import cities_match, normalize_text
from utils.recommendation_helpers import resolve_city_against_list, resolve_place_categories


def _filter_places_by_city(
    places: List[Dict[str, Any]],
    city: str,
) -> List[Dict[str, Any]]:
    return [p for p in places if cities_match(p.get("city"), city)]


def _filter_places_by_categories(
    places: List[Dict[str, Any]],
    categories: Optional[List[str]],
) -> List[Dict[str, Any]]:
    if not categories:
        return list(places)
    cat_set = {normalize_text(c) for c in categories}
    return [
        p for p in places
        if normalize_text(p.get("category", "")) in cat_set
    ]


def _format_place(place: Dict[str, Any]) -> Dict[str, Any]:
    """Format place for output."""
    return {
        "place_id": place.get("id"),
        "attraction_name": place.get("name"),
        "type": place.get("category"),
        "category": place.get("category"),
        "rating": place.get("rating"),
        "description": place.get("description"),
        "city": place.get("city"),
    }


def discover_places(
    city: str,
    category: Optional[str] = None,
    sort_by: str = "rating",
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Discover attractions with fuzzy city match, valid category filter, and fallbacks.
    """
    all_places = get_places()
    place_cities = sorted({p["city"] for p in all_places if p.get("city")})
    resolved_city = resolve_city_against_list(city, place_cities)
    vocab = get_place_category_vocab()
    categories, cat_note = resolve_place_categories(category, vocab, place_cities)

    fallback_level = "exact"
    relaxed: List[str] = []
    city_places = _filter_places_by_city(all_places, resolved_city)
    matches = _filter_places_by_categories(city_places, categories)

    if cat_note.startswith("ignored"):
        relaxed.append(cat_note)

    if not matches and categories:
        matches = list(city_places)
        if matches:
            relaxed.append("category")
            fallback_level = "city_top_rated"

    if not matches and city_places:
        matches = city_places
        fallback_level = "city_only"

    if not matches and all_places:
        matches = sorted(
            all_places,
            key=lambda p: p.get("rating") or 0,
            reverse=True,
        )[:limit]
        relaxed.append("global_fallback")
        fallback_level = "global_top"

    if not matches:
        return {
            "success": False,
            "message": f"No places in dataset for {city}.",
            "places": [],
            "matched_count": 0,
            "fallback_level": "none",
        }

    matches.sort(key=lambda p: p.get("rating") or 0, reverse=True)
    formatted = [_format_place(p) for p in matches[:limit]]

    reasoning = f"Top {len(formatted)} attractions by {sort_by}."
    if fallback_level != "exact":
        reasoning = (
            f"No places matched your filters in {city}. "
            f"Showing top-rated alternatives ({fallback_level.replace('_', ' ')})."
        )
    if cat_note == "ignored_category_looks_like_city":
        reasoning += " Place type filter looked like a city name and was ignored."

    return {
        "success": True,
        "count": len(matches),
        "matched_count": len(matches),
        "places": formatted,
        "reasoning": reasoning,
        "fallback_level": fallback_level,
        "relaxed_filters": relaxed,
        "resolved_city": resolved_city,
        "applied_categories": categories,
    }


@tool
def places_discovery_tool(
    city: str,
    category: str = "",
    limit: int = 10,
) -> str:
    """
    Discover tourist attractions in a city from the places dataset.

    Optional category filter (comma-separated): temple, museum, fort, beach, etc.
    Invalid categories are ignored. Returns attraction name, type, rating, description.
    """
    result = discover_places(
        city=city,
        category=category or None,
        limit=limit,
    )
    return json.dumps(result, indent=2)
