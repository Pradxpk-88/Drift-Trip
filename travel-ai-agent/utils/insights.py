"""User-facing trip insights — no LangChain debug or raw tool traces."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, List, Optional

from utils.helper import format_duration, parse_datetime

# Patterns that indicate internal/debug output (never show in UI)
_DEBUG_LINE_PATTERNS = [
    re.compile(r"^Called\s+[\w_]+", re.IGNORECASE),
    re.compile(r"^Tool result:", re.IGNORECASE),
    re.compile(r"^Invoking:", re.IGNORECASE),
    re.compile(r"^>\s*Entering", re.IGNORECASE),
    re.compile(r"signature", re.IGNORECASE),
    re.compile(r"extras", re.IGNORECASE),
    re.compile(r"tool_call_id", re.IGNORECASE),
    re.compile(r"^[{\[].*['\"]type['\"].*['\"]text['\"]", re.IGNORECASE),
]

_METADATA_JSON_KEYS = frozenset({
    "signature",
    "extras",
    "metadata",
    "tool_call_id",
    "id",
    "token",
    "hash",
    "response_metadata",
    "usage_metadata",
})


def content_to_text(content: Any) -> str:
    """Normalize LLM message content (str, blocks, dict) to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return _strip_wrappers(content)
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        return str(text).strip() if text else ""
    return _strip_wrappers(str(content))


def _strip_wrappers(text: str) -> str:
    """Remove Agent: prefix and similar wrappers."""
    cleaned = text.strip()
    if cleaned.lower().startswith("agent:"):
        cleaned = cleaned[6:].strip()
    return cleaned


def _extract_text_from_repr(text: str) -> str:
    """Pull readable text from Python/JSON repr of content blocks."""
    # Try JSON parse
    try:
        data = json.loads(text)
        return content_to_text(data)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try literal_eval for Python repr
    try:
        data = ast.literal_eval(text)
        return content_to_text(data)
    except (SyntaxError, ValueError):
        pass

    # Regex extract 'text': '...' or "text": "..."
    matches = re.findall(
        r"['\"]text['\"]\s*:\s*['\"](.+?)['\"](?:\s*,|\s*})",
        text,
        re.DOTALL,
    )
    if matches:
        return " ".join(m.replace("\\n", "\n") for m in matches)

    return text


def _is_debug_line(line: str) -> bool:
    """True if a line looks like internal agent/tool debug output."""
    stripped = line.strip()
    if not stripped:
        return True
    if len(stripped) > 800 and ("signature" in stripped.lower() or "extras" in stripped.lower()):
        return True
    for pattern in _DEBUG_LINE_PATTERNS:
        if pattern.search(stripped):
            return True
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict) and _METADATA_JSON_KEYS.intersection(obj.keys()):
                return True
        except json.JSONDecodeError:
            pass
    return False


def looks_like_debug_output(text: str) -> bool:
    """True if entire blob should be hidden from users."""
    if not text or not text.strip():
        return True
    lower = text.lower()
    debug_markers = (
        "called flight_search",
        "called hotel_",
        "called places_",
        "called weather_",
        "called budget_",
        "tool result:",
        "tool_call_id",
        "'signature'",
        '"signature"',
        "resource_exhausted",
    )
    if any(m in lower for m in debug_markers):
        return True
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return True
    debug_count = sum(1 for ln in lines if _is_debug_line(ln))
    return debug_count >= max(1, len(lines) // 2)


def sanitize_agent_output(raw: Any) -> str:
    """
    Extract only user-readable travel advice from agent output.

    Strips tool traces, JSON payloads, signatures, and metadata.
    """
    text = content_to_text(raw)
    if not text:
        return ""

    if text.strip().startswith(("[", "{")):
        text = _extract_text_from_repr(text)

    text = _strip_wrappers(text)

    clean_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("agent:"):
            stripped = stripped[6:].strip()
        if not stripped or _is_debug_line(stripped):
            continue
        # Skip JSON tool response dumps
        if stripped.startswith("{") and '"success"' in stripped:
            continue
        clean_lines.append(stripped)

    result = "\n\n".join(clean_lines).strip()
    if looks_like_debug_output(result):
        return ""
    return result


def _format_flight_datetime(value: Any) -> str:
    """Human-readable departure/arrival for insight cards."""
    dt = parse_datetime(value)
    if dt:
        return dt.strftime("%d %b %Y, %H:%M")
    return str(value) if value else "—"


def format_flight_insight_summary(flight: Dict[str, Any]) -> str:
    """One-line flight summary (fallback when rich UI is unavailable)."""
    airline = flight.get("airline") or "Airline"
    flight_id = flight.get("flight_id") or "—"
    src = flight.get("source") or "—"
    dest = flight.get("destination") or "—"
    price = float(flight.get("price") or 0)
    duration = flight.get("duration") or format_duration(flight.get("duration_hours")) or "—"
    travel_date = flight.get("travel_date") or "—"
    dep = _format_flight_datetime(flight.get("departure"))
    arr = _format_flight_datetime(flight.get("arrival"))
    return (
        f"Best flight: {airline} ({flight_id}) — {src} → {dest} · "
        f"₹{price:,.0f} · {duration} · {travel_date} · "
        f"departs {dep} · arrives {arr}"
    )


def build_trip_insights(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build structured insight cards from trip plan data (not raw agent logs).

    Each item: level (success|warning|info|error), icon, message.
    """
    insights: List[Dict[str, str]] = []
    source = plan.get("source") or "origin"
    destination = plan.get("destination") or "destination"
    num_days = plan.get("num_days", 0)

    # Budget
    if plan.get("budget_limit"):
        if plan.get("within_budget"):
            total = (plan.get("budget_breakdown") or {}).get("total_estimated_cost", 0)
            insights.append({
                "level": "success",
                "icon": "✅",
                "message": (
                    f"Budget-friendly trip — estimated ₹{total:,.0f} "
                    f"within your ₹{plan['budget_limit']:,.0f} limit."
                ),
            })
        else:
            insights.append({
                "level": "warning",
                "icon": "💰",
                "message": (
                    f"Estimated cost may exceed your budget of "
                    f"₹{plan['budget_limit']:,.0f}. Consider adjusting hotels or days."
                ),
            })

    # Flights — rich card in UI (kind=flight); message is plain-text fallback
    flight = plan.get("selected_flight")
    flight_search = plan.get("flight_search") or {}
    if flight:
        note = ""
        if flight_search.get("fallback_level") not in (None, "exact"):
            note = flight_search.get("reasoning", "")
        elif not flight_search.get("date_matched", True) and flight_search.get("reasoning"):
            note = flight_search["reasoning"]
        insights.append({
            "level": "success",
            "icon": "✈️",
            "kind": "flight",
            "flight": flight,
            "note": note,
            "message": format_flight_insight_summary(flight),
        })
    else:
        msg = flight_search.get("message") or (
            f"No flights found from {source} to {destination}."
        )
        insights.append({
            "level": "warning",
            "icon": "⚠️",
            "message": f"{msg} Try different dates or nearby cities.",
        })

    # Hotels
    hotel = plan.get("selected_hotel")
    hotel_search = plan.get("hotel_search") or {}
    if hotel:
        msg = (
            f"Recommended stay: {hotel.get('hotel_name', 'Hotel')} — "
            f"★ {hotel.get('rating', '—')}, "
            f"₹{float(hotel.get('price') or 0):,.0f}/night."
        )
        if hotel_search.get("fallback_level") not in (None, "exact"):
            msg = hotel_search.get("reasoning", msg)
            level = "info"
        else:
            level = "success"
        insights.append({"level": level, "icon": "🏨", "message": msg})
    else:
        msg = hotel_search.get("message") or (
            f"No hotels available in {destination} for your filters."
        )
        insights.append({
            "level": "warning",
            "icon": "🏨",
            "message": (
                f"No hotels matched your strict filters. {msg} "
                "Try raising max price or lowering minimum stars."
            ),
        })

    # Places
    places = plan.get("attractions") or []
    places_search = plan.get("places_search") or {}
    if places:
        msg = (
            f"{len(places)} top attractions curated for your "
            f"{num_days}-day stay in {destination}."
        )
        if places_search.get("fallback_level") not in (None, "exact"):
            msg = places_search.get("reasoning", msg)
        insights.append({"level": "success", "icon": "🗺️", "message": msg})
    else:
        insights.append({
            "level": "info",
            "icon": "🗺️",
            "message": (
                places_search.get("message")
                or f"No attractions matched filters in {destination}. "
                "Clear place type or pick temple, museum, fort, beach, park."
            ),
        })

    # Weather
    weather = plan.get("weather_forecast") or {}
    if weather.get("success"):
        current = weather.get("current") or {}
        cond = current.get("condition", "available")
        temp = current.get("temperature_c", "—")
        insights.append({
            "level": "info",
            "icon": "🌤️",
            "message": (
                f"Weather in {destination}: {cond}, "
                f"currently {temp}°C — plan outdoor activities accordingly."
            ),
        })
    else:
        insights.append({
            "level": "info",
            "icon": "🌤️",
            "message": (
                weather.get("message")
                or f"Weather forecast temporarily unavailable for {destination}."
            ),
        })

    # Clean agent tip (optional, only if readable)
    agent_tip = sanitize_agent_output(plan.get("agent_narrative"))
    if agent_tip and len(agent_tip) > 15:
        insights.append({
            "level": "info",
            "icon": "🤖",
            "message": agent_tip[:600] + ("…" if len(agent_tip) > 600 else ""),
        })

    return insights
