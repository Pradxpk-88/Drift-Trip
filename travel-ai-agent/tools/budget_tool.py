"""LangChain tool for trip budget estimation."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from langchain_core.tools import tool

from utils.constants import DEFAULT_FOOD_PER_DAY, DEFAULT_LOCAL_TRANSPORT_PER_DAY


def calculate_budget(
    flight_price: float = 0.0,
    hotel_price_per_night: float = 0.0,
    num_days: int = 1,
    local_transport_per_day: Optional[float] = None,
    food_per_day: Optional[float] = None,
    extra_expenses: float = 0.0,
    currency: str = "INR",
) -> Dict[str, Any]:
    """
    Calculate total estimated trip cost.

    Components: flights (one-way/round as provided), hotels (nights),
    local transport, food, and extras.
    """
    days = max(1, int(num_days))
    transport_rate = (
        local_transport_per_day
        if local_transport_per_day is not None
        else DEFAULT_LOCAL_TRANSPORT_PER_DAY
    )
    food_rate = food_per_day if food_per_day is not None else DEFAULT_FOOD_PER_DAY

    flight_total = float(flight_price or 0)
    hotel_nights = days
    hotel_total = float(hotel_price_per_night or 0) * hotel_nights
    transport_total = transport_rate * days
    food_total = food_rate * days
    extras = float(extra_expenses or 0)

    breakdown = {
        "flights": round(flight_total, 2),
        "hotels": round(hotel_total, 2),
        "hotel_nights": hotel_nights,
        "local_transport": round(transport_total, 2),
        "food": round(food_total, 2),
        "extra_expenses": round(extras, 2),
    }
    total = sum(
        [
            breakdown["flights"],
            breakdown["hotels"],
            breakdown["local_transport"],
            breakdown["food"],
            breakdown["extra_expenses"],
        ]
    )
    breakdown["total_estimated_cost"] = round(total, 2)
    breakdown["currency"] = currency
    breakdown["num_days"] = days

    return {
        "success": True,
        "breakdown": breakdown,
        "reasoning": (
            f"Estimated {days}-day trip: flight {breakdown['flights']}, "
            f"hotel {breakdown['hotels']} ({hotel_nights} nights), "
            f"transport {breakdown['local_transport']}, "
            f"food {breakdown['food']}."
        ),
    }


@tool
def budget_estimation_tool(
    flight_price: float,
    hotel_price_per_night: float,
    num_days: int,
    local_transport_per_day: float = 0.0,
    food_per_day: float = 0.0,
    extra_expenses: float = 0.0,
) -> str:
    """
    Calculate total trip budget from flight price, hotel nightly rate, and trip length.

    Use 0 for transport/food per day to apply defaults. Returns itemized breakdown
    and total estimated cost in INR.
    """
    result = calculate_budget(
        flight_price=flight_price,
        hotel_price_per_night=hotel_price_per_night,
        num_days=num_days,
        local_transport_per_day=(
            local_transport_per_day if local_transport_per_day > 0 else None
        ),
        food_per_day=food_per_day if food_per_day > 0 else None,
        extra_expenses=extra_expenses,
    )
    return json.dumps(result, indent=2)
