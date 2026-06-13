"""Developer debug summaries for dataset and match counts."""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.data_loader import get_dataset_counts


def build_debug_summary(plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build debug panel data for st.expander('Debug info')."""
    counts = get_dataset_counts()
    summary: Dict[str, Any] = {
        "dataset_loaded": counts,
        "matches_found": {},
        "fallback_levels": {},
    }
    if not plan:
        return summary

    flight = plan.get("flight_search") or {}
    hotel = plan.get("hotel_search") or {}
    places = plan.get("places_search") or {}

    summary["matches_found"] = {
        "flights": flight.get("matched_count", flight.get("count", 0)),
        "hotels": hotel.get("matched_count", hotel.get("count", 0)),
        "places": places.get("matched_count", places.get("count", 0)),
    }
    summary["fallback_levels"] = {
        "flights": flight.get("fallback_level", "n/a"),
        "hotels": hotel.get("fallback_level", "n/a"),
        "places": places.get("fallback_level", "n/a"),
    }
    summary["resolved_cities"] = {
        "flight_source": flight.get("resolved_source"),
        "flight_destination": flight.get("resolved_destination"),
        "hotel_city": hotel.get("resolved_city"),
        "place_city": places.get("resolved_city"),
    }
    summary["relaxed_filters"] = {
        "flights": flight.get("relaxed_filters", []),
        "hotels": hotel.get("relaxed_filters", []),
        "places": places.get("relaxed_filters", []),
    }
    return summary
