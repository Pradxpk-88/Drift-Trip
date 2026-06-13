"""Autonomous LangChain travel planning agent with tool calling."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field

from tools import ALL_TOOLS
from tools.budget_tool import calculate_budget
from tools.flight_tool import search_flights
from tools.hotel_tool import recommend_hotels
from tools.places_tool import discover_places
from tools.weather_tool import fetch_weather
from services.itinerary_service import assemble_trip_plan
from utils.insights import sanitize_agent_output
from utils.recommendation_helpers import effective_hotel_max_price
from utils.constants import (
    AGENT_VERBOSE,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    ENV_GEMINI_MODEL,
    ENV_GOOGLE_API_KEY,
    ENV_LLM_PROVIDER,
    ENV_OPENAI_API_KEY,
    ENV_OPENAI_MODEL,
)

load_dotenv()


SYSTEM_PROMPT = """You are an expert AI Travel Planning Assistant.

You have access to tools that search real flight, hotel, and attraction datasets,
fetch live weather from Open-Meteo, and estimate trip budgets.

For every travel request:
1. Analyze the user's source, destination, dates, budget, and preferences.
2. Call the appropriate tools in a logical order (typically flights, hotels, places, weather, budget).
3. Reason step-by-step about trade-offs (price vs comfort, weather impact, budget fit).
4. Prefer cheapest flights unless the user asks for fastest or a specific airline.
5. Match hotels to budget and amenity preferences when provided.
6. Use actual tool outputs only — never invent flight, hotel, or place data.

After using tools, provide a clear summary with recommendations and rationale.
"""


class TravelAgentResponse(BaseModel):
    """Structured agent reasoning output."""

    reasoning_steps: List[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning",
    )
    summary: str = Field(description="Final travel recommendation summary")


def _get_model_identifier() -> str:
    """Return LangChain model string for create_agent."""
    provider = (os.getenv(ENV_LLM_PROVIDER) or "openai").lower().strip()
    if provider == "gemini":
        model = os.getenv(ENV_GEMINI_MODEL, DEFAULT_GEMINI_MODEL)
        return f"google_genai:{model}"
    model = os.getenv(ENV_OPENAI_MODEL, DEFAULT_OPENAI_MODEL)
    return f"openai:{model}"


def _validate_credentials() -> None:
    """Ensure API keys exist for selected provider."""
    provider = (os.getenv(ENV_LLM_PROVIDER) or "openai").lower().strip()
    if provider == "gemini" and not os.getenv(ENV_GOOGLE_API_KEY):
        raise ValueError(f"{ENV_GOOGLE_API_KEY} is required when LLM_PROVIDER=gemini")
    if provider != "gemini" and not os.getenv(ENV_OPENAI_API_KEY):
        raise ValueError(f"{ENV_OPENAI_API_KEY} is required when LLM_PROVIDER=openai")


def create_travel_agent():
    """Build LangChain 1.x tool-calling agent graph with all travel tools."""
    _validate_credentials()
    return create_agent(
        _get_model_identifier(),
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        debug=AGENT_VERBOSE,
    )


def _content_to_text(content: Any) -> str:
    """Normalize Gemini/OpenAI message content to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def _final_output(messages: List[Any]) -> str:
    """Extract last AI message content as agent output."""
    for msg in reversed(messages or []):
        if isinstance(msg, AIMessage) and msg.content:
            return _content_to_text(msg.content)
    return ""


def run_agent_query(user_input: str) -> Dict[str, Any]:
    """Run the LangChain agent on a natural language or structured query."""
    graph = create_travel_agent()
    result = graph.invoke({"messages": [HumanMessage(content=user_input)]})
    messages = result.get("messages", [])
    raw_output = _final_output(messages)
    return {
        "output": sanitize_agent_output(raw_output),
        "messages": messages,
    }


def plan_trip_structured(
    source: str,
    destination: str,
    num_days: int,
    budget: Optional[float] = None,
    preferences: str = "",
    travel_date: Optional[str] = None,
    flight_mode: str = "cheapest",
    min_hotel_rating: float = 0.0,
    max_hotel_price: float = 0.0,
    amenities: str = "",
    place_category: str = "",
    use_agent: bool = True,
) -> Dict[str, Any]:
    """
    Full trip planning pipeline: tools + optional LLM agent + structured output.

    When use_agent is True and API keys are set, the agent orchestrates tools.
    Otherwise, tools run deterministically (no LLM required).
    """
    agent_output = ""

    if use_agent and _has_llm_credentials():
        query = _build_agent_query(
            source,
            destination,
            num_days,
            budget,
            preferences,
            travel_date,
            flight_mode,
            min_hotel_rating,
            max_hotel_price,
            amenities,
        )
        try:
            agent_result = run_agent_query(query)
            agent_output = agent_result.get("output", "")
        except Exception:
            agent_output = ""

    flight_result = search_flights(
        source=source,
        destination=destination,
        mode=flight_mode,
        travel_date=travel_date,
    )
    hotel_result = recommend_hotels(
        city=destination,
        min_rating=min_hotel_rating if min_hotel_rating > 0 else None,
        max_price=effective_hotel_max_price(max_hotel_price, budget, num_days),
        amenities=amenities or None,
        sort_by="value" if budget else "rating",
    )
    places_result = discover_places(
        city=destination,
        category=place_category or None,
        limit=max(10, num_days * 2),
    )
    weather_result = fetch_weather(destination, forecast_days=min(num_days, 7))

    flight_price = 0.0
    if flight_result.get("selected"):
        flight_price = float(flight_result["selected"].get("price") or 0)
    elif flight_result.get("flights"):
        flight_price = float(flight_result["flights"][0].get("price") or 0)

    hotel_price = 0.0
    if hotel_result.get("selected"):
        hotel_price = float(hotel_result["selected"].get("price") or 0)
    elif hotel_result.get("hotels"):
        hotel_price = float(hotel_result["hotels"][0].get("price") or 0)

    budget_result = calculate_budget(
        flight_price=flight_price,
        hotel_price_per_night=hotel_price,
        num_days=num_days,
    )

    plan = assemble_trip_plan(
        source=source,
        destination=destination,
        num_days=num_days,
        budget_limit=budget,
        preferences=preferences,
        flight_result=flight_result,
        hotel_result=hotel_result,
        weather_result=weather_result,
        budget_result=budget_result,
        places_result=places_result,
        agent_summary=agent_output,
        start_date=travel_date,
    )
    plan["agent_narrative"] = sanitize_agent_output(agent_output)
    plan["flight_search"] = flight_result
    plan["hotel_search"] = hotel_result
    plan["places_search"] = places_result
    plan["recommendation_reasoning"] = ""
    return plan


def _has_llm_credentials() -> bool:
    """Check if any supported LLM API key is configured."""
    provider = (os.getenv(ENV_LLM_PROVIDER) or "openai").lower()
    if provider == "gemini":
        return bool(os.getenv(ENV_GOOGLE_API_KEY))
    return bool(os.getenv(ENV_OPENAI_API_KEY))


def _build_agent_query(
    source: str,
    destination: str,
    num_days: int,
    budget: Optional[float],
    preferences: str,
    travel_date: Optional[str],
    flight_mode: str,
    min_hotel_rating: float,
    max_hotel_price: float,
    amenities: str,
) -> str:
    """Format structured trip request for the agent."""
    parts = [
        f"Plan a {num_days}-day trip from {source} to {destination}.",
        f"Flight preference: {flight_mode}.",
    ]
    if travel_date:
        parts.append(f"Travel date: {travel_date}.")
    if budget:
        parts.append(f"Total budget: INR {budget}.")
    if preferences:
        parts.append(f"Preferences: {preferences}.")
    if min_hotel_rating > 0:
        parts.append(f"Minimum hotel rating: {min_hotel_rating}.")
    if max_hotel_price > 0:
        parts.append(f"Max hotel price per night: INR {max_hotel_price}.")
    if amenities:
        parts.append(f"Required amenities: {amenities}.")
    parts.append(
        "Use tools to find flights, hotels, attractions, weather, and compute budget. "
        "Explain your reasoning."
    )
    return " ".join(parts)
