"""Multi-city trip planning across sequential destinations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.travel_agent import plan_trip_structured


def plan_multi_city_trip(
    source: str,
    destinations: List[str],
    total_days: int,
    budget: Optional[float] = None,
    preferences: str = "",
    travel_date: Optional[str] = None,
    flight_mode: str = "cheapest",
    min_hotel_rating: float = 0.0,
    max_hotel_price: float = 0.0,
    amenities: str = "",
    place_category: str = "",
    use_agent: bool = False,
) -> Dict[str, Any]:
    """
    Plan a trip visiting multiple cities in sequence.

    Days are split evenly; budget is split per leg when provided.
    """
    cities = [c for c in destinations if c]
    if not cities:
        raise ValueError("At least one destination city is required.")

    num_legs = len(cities)
    days_per_leg = max(1, total_days // num_legs)
    remainder = total_days - days_per_leg * num_legs
    budget_per_leg = (budget / num_legs) if budget and budget > 0 else None

    legs: List[Dict[str, Any]] = []
    current_source = source
    all_itinerary: List[Dict[str, Any]] = []
    total_cost = 0.0
    day_offset = 0

    for idx, dest in enumerate(cities):
        leg_days = days_per_leg + (1 if idx < remainder else 0)
        leg = plan_trip_structured(
            source=current_source,
            destination=dest,
            num_days=leg_days,
            budget=budget_per_leg,
            preferences=preferences,
            travel_date=travel_date,
            flight_mode=flight_mode,
            min_hotel_rating=min_hotel_rating,
            max_hotel_price=max_hotel_price,
            amenities=amenities,
            place_category=place_category,
            use_agent=use_agent and idx == 0,
        )
        leg["leg_index"] = idx + 1
        legs.append(leg)

        breakdown = leg.get("budget_breakdown") or {}
        total_cost += float(breakdown.get("total_estimated_cost") or 0)

        for day in leg.get("day_wise_itinerary") or []:
            merged = {**day, "day": day.get("day", 0) + day_offset, "city": dest}
            all_itinerary.append(merged)
        day_offset += leg_days
        current_source = dest

    route = [source] + cities
    within_budget = True
    if budget and budget > 0:
        within_budget = total_cost <= budget

    combined = {
        "is_multi_city": True,
        "source": source,
        "destination": cities[-1],
        "cities_visited": route,
        "legs": legs,
        "num_days": total_days,
        "budget_limit": budget,
        "within_budget": within_budget,
        "preferences": preferences,
        "trip_summary": (
            f"Multi-city trip: {' → '.join(route)} over {total_days} days. "
            f"Estimated total: INR {total_cost:,.0f}. "
            + ("Within budget." if within_budget else "May exceed budget.")
        ),
        "day_wise_itinerary": all_itinerary,
        "selected_flight": legs[0].get("selected_flight") if legs else None,
        "selected_hotel": legs[-1].get("selected_hotel") if legs else None,
        "attractions": [],
        "weather_forecast": legs[-1].get("weather_forecast") if legs else {},
        "budget_breakdown": {
            "flights": sum(
                (lg.get("budget_breakdown") or {}).get("flights", 0) for lg in legs
            ),
            "hotels": sum(
                (lg.get("budget_breakdown") or {}).get("hotels", 0) for lg in legs
            ),
            "local_transport": sum(
                (lg.get("budget_breakdown") or {}).get("local_transport", 0) for lg in legs
            ),
            "food": sum((lg.get("budget_breakdown") or {}).get("food", 0) for lg in legs),
            "total_estimated_cost": round(total_cost, 2),
            "currency": "INR",
        },
        "flight_search": legs[0].get("flight_search") if legs else {},
        "hotel_search": legs[-1].get("hotel_search") if legs else {},
        "agent_narrative": legs[0].get("agent_narrative", "") if legs else "",
        "recommendation_reasoning": "",
        "generated_at": legs[0].get("generated_at") if legs else None,
    }

    for leg in legs:
        combined["attractions"].extend(leg.get("attractions") or [])

    return combined
