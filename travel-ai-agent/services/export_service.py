"""Export trip plans as PDF, Markdown, and plain text."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List


def itinerary_to_markdown(plan: Dict[str, Any]) -> str:
    """Convert trip plan to downloadable Markdown."""
    lines: List[str] = [
        "# Voyager AI — Travel Itinerary",
        "",
        f"**Route:** {plan.get('source')} → {plan.get('destination')}",
        f"**Duration:** {plan.get('num_days')} days",
        f"**Generated:** {plan.get('generated_at', datetime.utcnow().isoformat())}",
        "",
        "## Summary",
        plan.get("trip_summary", ""),
        "",
    ]

    if plan.get("is_multi_city"):
        lines.append("## Multi-city legs")
        for leg in plan.get("legs") or []:
            lines.append(
                f"- {leg.get('source')} → {leg.get('destination')} "
                f"({leg.get('num_days')} days)"
            )
        lines.append("")

    flight = plan.get("selected_flight")
    if flight:
        lines.extend([
            "## Flight",
            f"- **Airline:** {flight.get('airline')}",
            f"- **Price:** ₹{float(flight.get('price') or 0):,.0f}",
            f"- **Duration:** {flight.get('duration')}",
            f"- **Departure:** {flight.get('departure')}",
            f"- **Arrival:** {flight.get('arrival')}",
            "",
        ])

    hotel = plan.get("selected_hotel")
    if hotel:
        lines.extend([
            "## Hotel",
            f"- **Name:** {hotel.get('hotel_name')}",
            f"- **Rating:** {hotel.get('rating')} ★",
            f"- **Price/night:** ₹{float(hotel.get('price') or 0):,.0f}",
            f"- **Amenities:** {', '.join(hotel.get('amenities') or [])}",
            "",
        ])

    lines.append("## Day-wise itinerary")
    for day in plan.get("day_wise_itinerary") or []:
        lines.append(f"### Day {day.get('day')} — {day.get('theme')} ({day.get('date', 'TBD')})")
        for act in day.get("activities") or []:
            lines.append(
                f"- **{act.get('time')}** {act.get('title')} ({act.get('category', '')})"
            )
        lines.append("")

    breakdown = plan.get("budget_breakdown") or {}
    if breakdown:
        lines.extend([
            "## Budget",
            f"- Flights: ₹{breakdown.get('flights', 0):,.0f}",
            f"- Hotels: ₹{breakdown.get('hotels', 0):,.0f}",
            f"- Transport: ₹{breakdown.get('local_transport', 0):,.0f}",
            f"- Food: ₹{breakdown.get('food', 0):,.0f}",
            f"- **Total:** ₹{breakdown.get('total_estimated_cost', 0):,.0f}",
            "",
        ])

    return "\n".join(lines)


def itinerary_to_text(plan: Dict[str, Any]) -> str:
    """Plain-text itinerary for simple download."""
    md = itinerary_to_markdown(plan)
    return md.replace("**", "").replace("#", "").replace("- ", "• ")


def _pdf_safe(text: str) -> str:
    """Strip characters unsupported by core PDF fonts."""
    return (
        str(text)
        .replace("₹", "INR ")
        .replace("★", "*")
        .replace("→", "->")
        .replace("—", "-")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


def itinerary_to_pdf_bytes(plan: Dict[str, Any]) -> bytes:
    """
    Generate PDF bytes from trip plan.

    Uses fpdf2 when installed; otherwise raises ImportError with hint.
    """
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise ImportError(
            "Install fpdf2 for PDF export: pip install fpdf2"
        ) from exc

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    width = pdf.epw

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Voyager AI - Travel Itinerary", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, _pdf_safe(f"Route: {plan.get('source')} -> {plan.get('destination')}"), ln=True)
    pdf.cell(0, 8, _pdf_safe(f"Days: {plan.get('num_days')}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(width, 6, _pdf_safe(str(plan.get("trip_summary", ""))))
    pdf.ln(3)

    flight = plan.get("selected_flight")
    if flight:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Flight", ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(
            width,
            6,
            _pdf_safe(
                f"{flight.get('airline')} | INR {float(flight.get('price') or 0):,.0f} | "
                f"{flight.get('duration')}"
            ),
        )
        pdf.ln(2)

    hotel = plan.get("selected_hotel")
    if hotel:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Hotel", ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(
            width,
            6,
            _pdf_safe(
                f"{hotel.get('hotel_name')} | {hotel.get('rating')} stars | "
                f"INR {float(hotel.get('price') or 0):,.0f}/night"
            ),
        )
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Itinerary", ln=True)
    pdf.set_font("Helvetica", size=10)
    for day in plan.get("day_wise_itinerary") or []:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(
            width,
            7,
            _pdf_safe(f"Day {day.get('day')} - {day.get('theme')}"),
        )
        pdf.set_font("Helvetica", size=10)
        for act in day.get("activities") or []:
            line = f"  {act.get('time')} - {act.get('title')} ({act.get('category', '')})"
            pdf.multi_cell(width, 5, _pdf_safe(line))

    breakdown = plan.get("budget_breakdown") or {}
    if breakdown:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Budget", ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(
            width,
            6,
            _pdf_safe(f"Total: INR {breakdown.get('total_estimated_cost', 0):,.0f}"),
        )

    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
