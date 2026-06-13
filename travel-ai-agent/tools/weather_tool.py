"""LangChain tool for weather via Open-Meteo API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from langchain_core.tools import tool

from utils.constants import OPEN_METEO_FORECAST_URL, OPEN_METEO_GEOCODE_URL
from utils.helper import normalize_city


# WMO weather code descriptions (subset)
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


def _geocode_city(city: str) -> Optional[Dict[str, float]]:
    """Resolve city name to latitude/longitude using Open-Meteo geocoding."""
    params = {
        "name": city,
        "count": 5,
        "language": "en",
        "format": "json",
    }
    try:
        response = requests.get(OPEN_METEO_GEOCODE_URL, params=params, timeout=15)
        response.raise_for_status()
        results = response.json().get("results") or []
        if not results:
            return None
        # Prefer India for Indian city dataset
        for item in results:
            if item.get("country_code") == "IN":
                return {"latitude": item["latitude"], "longitude": item["longitude"]}
        first = results[0]
        return {"latitude": first["latitude"], "longitude": first["longitude"]}
    except requests.RequestException:
        return None


def fetch_weather(city: str, forecast_days: int = 7) -> Dict[str, Any]:
    """
    Fetch current conditions and daily forecast from Open-Meteo.

    Args:
        city: City name.
        forecast_days: Number of forecast days (1-16).
    """
    normalized = normalize_city(city) or city
    coords = _geocode_city(normalized)
    if not coords:
        return {
            "success": False,
            "message": f"Could not geocode city: {city}",
            "city": normalized,
        }

    days = max(1, min(int(forecast_days), 16))
    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
        "forecast_days": days,
    }

    try:
        response = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return {
            "success": False,
            "message": f"Weather API error: {exc}",
            "city": normalized,
        }

    current = data.get("current") or {}
    daily = data.get("daily") or {}
    dates = daily.get("time") or []

    forecast: List[Dict[str, Any]] = []
    for idx, date_str in enumerate(dates):
        code = (daily.get("weather_code") or [None])[idx]
        forecast.append({
            "date": date_str,
            "condition": WMO_CODES.get(code, f"Weather code {code}"),
            "temp_max_c": (daily.get("temperature_2m_max") or [None])[idx],
            "temp_min_c": (daily.get("temperature_2m_min") or [None])[idx],
            "precipitation_mm": (daily.get("precipitation_sum") or [None])[idx],
        })

    current_code = current.get("weather_code")
    return {
        "success": True,
        "city": normalized,
        "coordinates": coords,
        "current": {
            "temperature_c": current.get("temperature_2m"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "condition": WMO_CODES.get(current_code, f"Weather code {current_code}"),
            "observed_at": current.get("time"),
        },
        "forecast": forecast,
        "forecast_days": len(forecast),
    }


@tool
def weather_forecast_tool(city: str, forecast_days: int = 7) -> str:
    """
    Get current weather and daily forecast for a city using Open-Meteo (no API key).

    Returns temperature, conditions, and multi-day forecast.
    """
    result = fetch_weather(city, forecast_days)
    return json.dumps(result, indent=2)
