"""Shared utilities for JSON loading, schema detection, and data normalization."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from utils.constants import (
    CITY_ALIASES,
    FLIGHT_FIELDS,
    HOTEL_FIELDS,
    PLACE_FIELDS,
)


def load_json_dataset(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load a JSON dataset from disk.

    Supports root-level arrays or objects with a list under common keys.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        for key in ("data", "records", "items", "flights", "hotels", "places"):
            value = raw.get(key)
            if isinstance(value, list):
                return value
        raise ValueError(f"Unsupported JSON structure in {file_path.name}")

    raise ValueError(f"Expected list or dict in {file_path.name}")


def _resolve_field(record: Dict[str, Any], aliases: List[str]) -> Any:
    """Return the first non-empty value for any alias key (case-insensitive)."""
    lower_map = {str(k).lower(): k for k in record.keys()}
    for alias in aliases:
        key = lower_map.get(alias.lower())
        if key is None:
            continue
        value = record[key]
        if value is not None and value != "" and value != []:
            return value
    return None


def normalize_text(value: Optional[str]) -> str:
    """Lowercase, strip, collapse internal whitespace."""
    if value is None or not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_city(city: Optional[str]) -> Optional[str]:
    """Normalize city names for consistent matching."""
    if not city or not isinstance(city, str):
        return None
    cleaned = re.sub(r"\s+", " ", city.strip().lower())
    if not cleaned:
        return None
    canonical = CITY_ALIASES.get(cleaned, cleaned)
    return canonical.title()


def normalize_category(value: Optional[str]) -> str:
    """Normalize place/attraction category tokens."""
    return normalize_text(value)


def cities_match(city_a: Optional[str], city_b: Optional[str]) -> bool:
    """Compare two city names after normalization."""
    norm_a = normalize_city(city_a)
    norm_b = normalize_city(city_b)
    if not norm_a or not norm_b:
        return False
    return norm_a.lower() == norm_b.lower()


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse ISO or common datetime string formats."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    formats = (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text[:19] if "T" in text else text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")[:19])
    except ValueError:
        return None


def parse_price(value: Any) -> Optional[float]:
    """Convert price values to float."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(text) if text else None
    except ValueError:
        return None


def parse_rating(value: Any) -> Optional[float]:
    """Convert rating to float."""
    if value is None or value == "":
        return None
    try:
        rating = float(value)
        return rating if 0 <= rating <= 5 else None
    except (TypeError, ValueError):
        return None


def parse_duration_hours(departure: Any, arrival: Any) -> Optional[float]:
    """Compute flight duration in hours from departure and arrival times."""
    dep = parse_datetime(departure)
    arr = parse_datetime(arrival)
    if not dep or not arr:
        return None
    delta = arr - dep
    if delta.total_seconds() < 0:
        delta = arr.replace(day=arr.day + 1) - dep  # overnight edge case
    hours = delta.total_seconds() / 3600
    return round(hours, 2) if hours >= 0 else None


def format_duration(hours: Optional[float]) -> str:
    """Format duration hours as human-readable string."""
    if hours is None:
        return "N/A"
    whole_hours = int(hours)
    minutes = int(round((hours - whole_hours) * 60))
    if whole_hours and minutes:
        return f"{whole_hours}h {minutes}m"
    if whole_hours:
        return f"{whole_hours}h"
    return f"{minutes}m"


def normalize_record(
    record: Dict[str, Any],
    field_map: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    """
    Map a raw record to canonical fields.

    Returns None if the record lacks minimum required identity fields.
    """
    if not isinstance(record, dict):
        return None

    normalized: Dict[str, Any] = {}
    for canonical, aliases in field_map.items():
        normalized[canonical] = _resolve_field(record, aliases)

    return normalized


def is_valid_flight(record: Dict[str, Any]) -> bool:
    """Check if normalized flight has required fields."""
    return bool(
        record.get("source")
        and record.get("destination")
        and record.get("airline")
        and parse_price(record.get("price")) is not None
    )


def is_valid_hotel(record: Dict[str, Any]) -> bool:
    """Check if normalized hotel has required fields."""
    return bool(record.get("name") and record.get("city"))


def is_valid_place(record: Dict[str, Any]) -> bool:
    """Check if normalized place has required fields."""
    return bool(record.get("name") and record.get("city"))


def load_and_normalize(
    file_path: Path,
    field_map: Dict[str, List[str]],
    validator,
) -> List[Dict[str, Any]]:
    """Load JSON, normalize records, and filter invalid entries."""
    raw_records = load_json_dataset(file_path)
    results: List[Dict[str, Any]] = []

    for raw in raw_records:
        if not isinstance(raw, dict):
            continue
        normalized = normalize_record(raw, field_map)
        if normalized and validator(normalized):
            results.append(normalized)

    return results


def ensure_list(value: Union[str, List[str], None]) -> List[str]:
    """Convert comma-separated string or list to lowercase string list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip().lower() for v in value if str(v).strip()]
    return [part.strip().lower() for part in str(value).split(",") if part.strip()]


def build_place_description(place: Dict[str, Any]) -> str:
    """Generate description when dataset has no description field."""
    existing = place.get("description")
    if existing and str(existing).strip():
        return str(existing).strip()
    name = place.get("name", "Attraction")
    category = place.get("category", "sightseeing")
    city = place.get("city", "")
    rating = place.get("rating")
    rating_text = f" Rated {rating}/5." if rating else ""
    return f"{name} is a popular {category} destination in {city}.{rating_text}"


def safe_json_dumps(data: Any, indent: int = 2) -> str:
    """Serialize data to JSON string with datetime handling."""

    def default(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(data, indent=indent, default=default)
