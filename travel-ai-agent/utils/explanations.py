"""Structured recommendation explanations for the UI."""

from __future__ import annotations

from typing import Any, Dict, List


def build_recommendation_explanations(plan: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build human-readable 'why we picked this' explanations from trip data.

    Returns list of {title, explanation, category}.
    """
    explanations: List[Dict[str, str]] = []
    source = plan.get("source", "")
    destination = plan.get("destination", "")
    prefs = plan.get("preferences") or ""
    flight_mode = (plan.get("flight_mode") or "cheapest").lower()

    flight = plan.get("selected_flight")
    if flight:
        why = (
            f"Selected as the {flight_mode} option on the {source} → {destination} route "
            f"at ₹{float(flight.get('price') or 0):,.0f} with {flight.get('duration', 'N/A')} travel time."
        )
        if prefs:
            why += f" Your preferences ({prefs}) were considered alongside price and duration."
        explanations.append({
            "category": "flight",
            "title": f"✈️ {flight.get('airline', 'Flight')} recommendation",
            "explanation": why,
        })
    else:
        explanations.append({
            "category": "flight",
            "title": "✈️ Flight recommendation",
            "explanation": (
                f"No direct flights in our dataset for {source} → {destination}. "
                "Consider a nearby hub or different travel dates."
            ),
        })

    hotel = plan.get("selected_hotel")
    if hotel:
        amenities = ", ".join(hotel.get("amenities") or [])
        explanations.append({
            "category": "hotel",
            "title": f"🏨 {hotel.get('hotel_name', 'Hotel')} recommendation",
            "explanation": (
                f"Chosen for ★ {hotel.get('rating', '—')} rating at "
                f"₹{float(hotel.get('price') or 0):,.0f}/night in {destination}. "
                f"Amenities: {amenities or 'standard'}."
            ),
        })
    else:
        explanations.append({
            "category": "hotel",
            "title": "🏨 Hotel recommendation",
            "explanation": (
                f"No hotel matched your filters in {destination}. "
                "Try increasing budget or lowering minimum stars."
            ),
        })

    places = plan.get("attractions") or []
    if places:
        top = places[0].get("attraction_name", "attraction")
        explanations.append({
            "category": "places",
            "title": "🗺️ Attractions selection",
            "explanation": (
                f"Curated {len(places)} top-rated sights in {destination}, "
                f"led by {top}, spread across your {plan.get('num_days', 0)}-day itinerary."
            ),
        })

    weather = plan.get("weather_forecast") or {}
    if weather.get("success"):
        current = weather.get("current") or {}
        explanations.append({
            "category": "weather",
            "title": "🌤️ Weather consideration",
            "explanation": (
                f"Live forecast shows {current.get('condition', 'conditions')} at "
                f"{current.get('temperature_c', '—')}°C — useful for outdoor vs indoor planning."
            ),
        })

    breakdown = plan.get("budget_breakdown") or {}
    if breakdown:
        total = breakdown.get("total_estimated_cost", 0)
        explanations.append({
            "category": "budget",
            "title": "💰 Budget breakdown logic",
            "explanation": (
                f"Total ₹{total:,.0f} includes flight (₹{breakdown.get('flights', 0):,.0f}), "
                f"hotel stays (₹{breakdown.get('hotels', 0):,.0f}), local transport, and meals "
                f"for {plan.get('num_days', 0)} days."
            ),
        })

    if plan.get("is_multi_city"):
        cities = plan.get("cities_visited") or []
        explanations.append({
            "category": "route",
            "title": "🌍 Multi-city route",
            "explanation": (
                f"Trip spans {len(cities)} cities: {' → '.join(cities)}. "
                "Days and budget are split across each leg."
            ),
        })

    return explanations
