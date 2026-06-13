"""Day-wise itinerary builder from attractions and trip parameters."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tools.places_tool import discover_places


def build_day_wise_itinerary(
    destination: str,
    num_days: int,
    places: Optional[List[Dict[str, Any]]] = None,
    preferences: Optional[str] = None,
    start_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Distribute attractions across trip days.

    Args:
        destination: City to visit.
        num_days: Trip length in days.
        places: Pre-fetched places; loaded from dataset if None.
        preferences: Optional text hint (used in activity notes).
        start_date: ISO date string for day labels.
    """
    days = max(1, int(num_days))
    if places is None:
        discovery = discover_places(city=destination, limit=days * 3)
        places = discovery.get("places") or []

    if not places:
        return [
            {
                "day": d + 1,
                "date": _day_date(start_date, d),
                "theme": "Explore locally",
                "activities": [
                    {
                        "time": "10:00",
                        "title": f"Free exploration in {destination}",
                        "notes": "Discover local culture and cuisine.",
                    }
                ],
            }
            for d in range(days)
        ]

    per_day = max(1, len(places) // days)
    itinerary: List[Dict[str, Any]] = []
    idx = 0

    for day_num in range(days):
        day_places = places[idx : idx + per_day]
        if day_num == days - 1:
            day_places = places[idx:]
        idx += len(day_places)

        activities = []
        times = ["09:30", "12:30", "15:30", "18:00"]
        for i, place in enumerate(day_places):
            activities.append({
                "time": times[i % len(times)],
                "title": place.get("attraction_name") or place.get("name"),
                "category": place.get("category") or place.get("type"),
                "rating": place.get("rating"),
                "description": place.get("description"),
            })

        if not activities:
            activities.append({
                "time": "10:00",
                "title": "Leisure / shopping",
                "notes": f"Flexible day based on preferences: {preferences or 'general'}",
            })

        theme = _day_theme(day_places)
        itinerary.append({
            "day": day_num + 1,
            "date": _day_date(start_date, day_num),
            "theme": theme,
            "activities": activities,
        })

    return itinerary


def _day_date(start_date: Optional[str], offset: int) -> Optional[str]:
    """Compute calendar date for itinerary day."""
    if not start_date:
        return None
    try:
        base = datetime.strptime(start_date[:10], "%Y-%m-%d")
        return (base + timedelta(days=offset)).date().isoformat()
    except ValueError:
        return None


def _day_theme(places: List[Dict[str, Any]]) -> str:
    """Derive a day theme from place categories."""
    categories = [
        p.get("category") or p.get("type")
        for p in places
        if p.get("category") or p.get("type")
    ]
    if not categories:
        return "Sightseeing"
    unique = sorted(set(categories))
    return ", ".join(unique[:3]).title()


def assemble_trip_plan(
    source: str,
    destination: str,
    num_days: int,
    budget_limit: Optional[float],
    preferences: str,
    flight_result: Dict[str, Any],
    hotel_result: Dict[str, Any],
    weather_result: Dict[str, Any],
    budget_result: Dict[str, Any],
    places_result: Dict[str, Any],
    agent_summary: str = "",
    start_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Merge tool outputs into final structured trip plan."""
    selected_flight = (
        flight_result.get("selected")
        or (flight_result.get("flights") or [None])[0]
    )
    selected_hotel = (
        hotel_result.get("selected")
        or (hotel_result.get("hotels") or [None])[0]
    )
    places = places_result.get("places") or []
    itinerary = build_day_wise_itinerary(
        destination=destination,
        num_days=num_days,
        places=places,
        preferences=preferences,
        start_date=start_date,
    )

    breakdown = budget_result.get("breakdown") or {}
    total_cost = breakdown.get("total_estimated_cost", 0)
    within_budget = True
    if budget_limit and budget_limit > 0:
        within_budget = total_cost <= budget_limit

    summary = (
        f"{num_days}-day trip from {source} to {destination}. "
        f"Estimated cost: {breakdown.get('currency', 'INR')} {total_cost}. "
    )
    if budget_limit:
        summary += (
            "Within budget."
            if within_budget
            else f"Exceeds budget by {total_cost - budget_limit:.0f}."
        )

    return {
        "trip_summary": summary,
        "source": source,
        "destination": destination,
        "num_days": num_days,
        "budget_limit": budget_limit,
        "within_budget": within_budget,
        "preferences": preferences,
        "selected_flight": selected_flight,
        "selected_hotel": selected_hotel,
        "weather_forecast": weather_result,
        "attractions": places,
        "day_wise_itinerary": itinerary,
        "budget_breakdown": breakdown,
        "recommendation_reasoning": "",
        "agent_narrative": agent_summary,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
