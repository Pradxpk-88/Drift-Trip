"""LangChain tool for flight search over flights.json."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from services.data_loader import get_flights
from utils.helper import cities_match, ensure_list, format_duration, parse_datetime
from utils.recommendation_helpers import collect_flight_cities, resolve_city_against_list


def _filter_flights(
    source: str,
    destination: str,
    airline: Optional[str] = None,
    travel_date: Optional[str] = None,
    route_only: bool = False,
) -> List[Dict[str, Any]]:
    """Filter flights by route; optionally by airline and exact travel date."""
    airline_list = ensure_list(airline)
    target_date = travel_date.strip() if travel_date else None

    matches: List[Dict[str, Any]] = []
    for flight in get_flights():
        if not cities_match(flight.get("source"), source):
            continue
        if not cities_match(flight.get("destination"), destination):
            continue
        if airline_list and flight.get("airline", "").lower() not in airline_list:
            continue
        if not route_only and target_date and flight.get("travel_date") != target_date:
            continue
        matches.append(flight)
    return matches


def _days_from_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _pick_by_mode(
    matches: List[Dict[str, Any]],
    mode: str,
) -> Dict[str, Any]:
    """Select one flight from matches according to mode."""
    if not matches:
        raise ValueError("No flights to pick from")
    mode_lower = (mode or "cheapest").lower().strip()
    if mode_lower == "fastest":
        return min(
            matches,
            key=lambda f: (
                f.get("duration_hours")
                if f.get("duration_hours") is not None
                else float("inf")
            ),
        )
    return min(matches, key=lambda f: f.get("price") or float("inf"))


def _format_flight(flight: Dict[str, Any]) -> Dict[str, Any]:
    """Format a flight record for tool output."""
    dep = parse_datetime(flight.get("departure"))
    arr = parse_datetime(flight.get("arrival"))
    return {
        "flight_id": flight.get("id"),
        "airline": flight.get("airline"),
        "departure": dep.isoformat() if dep else flight.get("departure"),
        "arrival": arr.isoformat() if arr else flight.get("arrival"),
        "duration": format_duration(flight.get("duration_hours")),
        "duration_hours": flight.get("duration_hours"),
        "price": flight.get("price"),
        "source": flight.get("source"),
        "destination": flight.get("destination"),
        "travel_date": flight.get("travel_date"),
    }


def search_flights(
    source: str,
    destination: str,
    mode: str = "cheapest",
    airline: Optional[str] = None,
    travel_date: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Search flights between cities.

  Route match (source → destination) is treated as an exact dataset match.
  Travel date is optional: dataset uses fixed sample dates, so a selected
  calendar date may not match — we still show all flights on that route.
    """
    all_flights = get_flights()
    flight_cities = collect_flight_cities(all_flights)
    resolved_source = resolve_city_against_list(source, flight_cities)
    resolved_dest = resolve_city_against_list(destination, flight_cities)

    # Step 1: All flights on this route (primary match)
    route_matches = _filter_flights(
        resolved_source,
        resolved_dest,
        airline,
        travel_date=None,
        route_only=True,
    )

    if not route_matches:
        # True missing route — try fallbacks
        from_source = [
            f for f in all_flights if cities_match(f.get("source"), resolved_source)
        ]
        if from_source:
            cheapest = min(from_source, key=lambda f: f.get("price") or float("inf"))
            route_matches = [cheapest]
            fallback_level = "cheapest_from_source"
            reasoning = (
                f"No direct flights from {source} to {destination} in the dataset. "
                f"Showing cheapest flight from {source} instead."
            )
        else:
            if all_flights:
                cheapest = min(all_flights, key=lambda f: f.get("price") or float("inf"))
                route_matches = [cheapest]
                fallback_level = "cheapest_overall"
                reasoning = (
                    f"No flights found for {source} → {destination}. "
                    "Showing cheapest flight in the dataset."
                )
            else:
                return {
                    "success": False,
                    "message": (
                        f"No flights in dataset for {source} → {destination}."
                    ),
                    "flights": [],
                    "matched_count": 0,
                    "route_match_count": 0,
                    "fallback_level": "none",
                }

        sorted_route = sorted(route_matches, key=lambda f: f.get("price") or float("inf"))
        selected = _pick_by_mode(sorted_route, mode)
        flights_out = [_format_flight(f) for f in sorted_route[:limit]]
        return {
            "success": True,
            "mode": (mode or "cheapest").lower(),
            "count": len(route_matches),
            "matched_count": len(route_matches),
            "route_match_count": len(route_matches),
            "selected": _format_flight(selected),
            "flights": flights_out,
            "reasoning": reasoning,
            "fallback_level": fallback_level,
            "relaxed_filters": ["route"],
            "resolved_source": resolved_source,
            "resolved_destination": resolved_dest,
            "date_matched": False,
        }

    # Route exists in dataset — exact route match
    fallback_level = "exact"
    date_matched = False
    date_note = ""
    relaxed_filters: List[str] = []

    pool = list(route_matches)
    target_date = travel_date.strip() if travel_date else None

    if target_date:
        on_date = [f for f in route_matches if f.get("travel_date") == target_date]
        if on_date:
            pool = on_date
            date_matched = True
            date_note = f"Matched your selected date ({target_date})."
        else:
            # Prefer flight closest to requested date for selection highlight
            req_dt = _days_from_date(target_date)
            if req_dt:

                def _date_distance_days(flight_date: Optional[str]) -> int:
                    fd = _days_from_date(flight_date)
                    if fd is None:
                        return 9999
                    return abs((fd - req_dt).days)

                pool = sorted(
                    route_matches,
                    key=lambda f: _date_distance_days(f.get("travel_date")),
                )
            available_dates = sorted(
                {f.get("travel_date") for f in route_matches if f.get("travel_date")}
            )
            dates_text = ", ".join(available_dates[:5])
            date_note = (
                f"Your selected date ({target_date}) is not in the dataset. "
                f"Showing {len(route_matches)} flight(s) on this route "
                f"(available dates: {dates_text})."
            )
            fallback_level = "exact"
            relaxed_filters.append("date_optional")

    sorted_pool = sorted(pool, key=lambda f: f.get("price") or float("inf"))
    mode_lower = (mode or "cheapest").lower().strip()

    if mode_lower == "all":
        display_list = sorted(route_matches, key=lambda f: f.get("price") or float("inf"))
        flights_out = [_format_flight(f) for f in display_list[:limit]]
        selected_raw = display_list[0] if display_list else sorted_pool[0]
        reasoning = (
            f"Found {len(route_matches)} flight(s) from {source} to {destination}. "
            f"{date_note}"
        ).strip()
    else:
        selected_raw = _pick_by_mode(sorted_pool, mode)
        flights_out = [
            _format_flight(f)
            for f in sorted(
                route_matches,
                key=lambda f: f.get("price") or float("inf"),
            )[: max(limit, 1)]
        ]
        reasoning = (
            f"Exact route match: {source} → {destination}. "
            f"Selected {mode_lower} option — {selected_raw.get('airline')} "
            f"on {selected_raw.get('travel_date')} "
            f"(₹{float(selected_raw.get('price') or 0):,.0f}). "
            f"{date_note}"
        ).strip()

    return {
        "success": True,
        "mode": mode_lower,
        "count": len(route_matches),
        "matched_count": len(route_matches),
        "route_match_count": len(route_matches),
        "selected": _format_flight(selected_raw),
        "flights": flights_out,
        "reasoning": reasoning,
        "fallback_level": fallback_level,
        "relaxed_filters": relaxed_filters,
        "resolved_source": resolved_source,
        "resolved_destination": resolved_dest,
        "date_matched": date_matched,
        "available_dates": sorted(
            {f.get("travel_date") for f in route_matches if f.get("travel_date")}
        ),
    }


@tool
def flight_search_tool(
    source: str,
    destination: str,
    mode: str = "cheapest",
    airline: str = "",
    travel_date: str = "",
) -> str:
    """
    Search flights between two cities from the flights dataset.

    Use mode 'cheapest' for lowest price, 'fastest' for shortest duration,
    or 'all' for multiple options. Optional airline and travel_date (YYYY-MM-DD).
    Returns airline, departure, arrival, duration, and price.
    """
    result = search_flights(
        source=source,
        destination=destination,
        mode=mode,
        airline=airline or None,
        travel_date=travel_date or None,
    )
    return json.dumps(result, indent=2)
