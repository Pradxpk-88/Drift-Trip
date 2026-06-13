"""
Agentic AI-Based Travel Planning Assistant — Streamlit UI.

Run: streamlit run app.py
"""

from __future__ import annotations

import html as html_module
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.travel_agent import _has_llm_credentials, plan_trip_structured
from services.chat_service import append_chat_turn, run_travel_chat
from services.data_loader import get_available_cities
from services.export_service import (
    itinerary_to_markdown,
    itinerary_to_pdf_bytes,
    itinerary_to_text,
)
from services.multi_city_service import plan_multi_city_trip
from utils.constants import OUTPUT_DIR
from utils.debug_info import build_debug_summary
from utils.explanations import build_recommendation_explanations
from utils.helper import safe_json_dumps
from utils.insights import _format_flight_datetime, build_trip_insights
from utils.theme import get_theme_css

load_dotenv()

st.set_page_config(
    page_title="DriftTrip | Travel Planning",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fraunces:opsz,wght@9..144,600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background: transparent;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2f4f36 0%, #7da07c 100%);
}
/* Sidebar labels & headings — light text on dark background */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span:not([data-baseweb]),
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .sidebar-brand,
section[data-testid="stSidebar"] .sidebar-tagline,
section[data-testid="stSidebar"] .sidebar-section {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-family: 'Fraunces', serif !important;
    color: #f0fdfa !important;
}
/* Sidebar inputs — white background + dark text (readable while typing) */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    background-color: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    caret-color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
}
section[data-testid="stSidebar"] input::placeholder,
section[data-testid="stSidebar"] textarea::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="input"] > div {
    background-color: #ffffff !important;
    border-color: #cbd5e1 !important;
    border-radius: 10px !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] span,
section[data-testid="stSidebar"] [data-baseweb="select"] div[value] {
    color: #0f172a !important;
}
section[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: #e2e8f0 !important;
    color: #0f172a !important;
}
section[data-testid="stSidebar"] .stCheckbox label span {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stSlider label {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #516140, #37432b) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.65rem 1rem !important;
    box-shadow: 0 4px 14px rgba(81, 97, 64, 0.35);
}
section[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(81, 97, 64, 0.45);
}
.sidebar-brand {
    font-family: 'Fraunces', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: #f0fdfa;
    margin-bottom: 0.25rem;
}
.sidebar-tagline {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-bottom: 1.25rem;
    line-height: 1.4;
}
.sidebar-section {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #5eead4;
    margin: 1rem 0 0.5rem 0;
    font-weight: 600;
}

/* Hero */
.hero-wrap {
    background: linear-gradient(135deg, #516140 0%, #37432b 50%, #697857 100%);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.75rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 20px 50px -12px rgba(29, 36, 21, 0.55);
}
.hero-wrap::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(173, 179, 173, 0.25) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-title {
    font-family: 'Fraunces', serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 0.35rem 0;
    position: relative;
}
.hero-sub {
    color: #e6ebdd;
    font-size: 1.05rem;
    margin: 0;
    position: relative;
    opacity: 0.95;
}
.hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1.25rem;
    position: relative;
}
.hero-badge {
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.24);
    color: #ffffff;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 500;
}

/* Route banner */
.route-banner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.5rem;
    background: white;
    border-radius: 16px;
    padding: 1.25rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px rgba(15, 23, 42, 0.08);
    border: 1px solid #e2e8f0;
}
.route-city {
    text-align: center;
    flex: 1;
}
.route-city .label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }
.route-city .name { font-family: 'Fraunces', serif; font-size: 1.6rem; color: #0f172a; font-weight: 700; }
.route-arrow {
    font-size: 1.75rem;
    color: #0d9488;
    background: #f0fdfa;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.route-meta {
    text-align: center;
    font-size: 0.85rem;
    color: #64748b;
    margin-top: 0.5rem;
}

/* Cards */
.stat-card {
    background: white;
    border-radius: 14px;
    padding: 1.1rem 1.25rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
    height: 100%;
    transition: box-shadow 0.2s ease;
}
.stat-card:hover {
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}
.stat-card .icon { font-size: 1.5rem; margin-bottom: 0.35rem; }
.stat-card .label { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
.stat-card .value { font-size: 1.35rem; font-weight: 700; color: #0f172a; margin-top: 0.15rem; }
.stat-card .sub { font-size: 0.8rem; color: #0d9488; margin-top: 0.2rem; }

.place-card {
    background: white;
    border-radius: 14px;
    padding: 1rem 1.15rem;
    border-left: 4px solid #14b8a6;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
    margin-bottom: 0.75rem;
}
.place-card h4 { margin: 0 0 0.35rem 0; color: #0f172a; font-size: 1rem; }
.place-card .meta { font-size: 0.8rem; color: #64748b; }
.place-card .desc { font-size: 0.85rem; color: #475569; margin-top: 0.5rem; line-height: 1.45; }
.rating-pill {
    display: inline-block;
    background: #fef3c7;
    color: #b45309;
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
}

.weather-now {
    background: linear-gradient(135deg, #ecfeff, #f0fdfa);
    border-radius: 16px;
    padding: 1.5rem;
    border: 1px solid #99f6e4;
    text-align: center;
    margin-bottom: 1rem;
}
.weather-now .temp { font-size: 2.5rem; font-weight: 700; color: #0f766e; }
.weather-now .cond { color: #115e59; font-size: 1rem; }

.weather-day {
    background: white;
    border-radius: 12px;
    padding: 0.85rem;
    text-align: center;
    border: 1px solid #e2e8f0;
    font-size: 0.85rem;
}
.weather-day .d { font-weight: 600; color: #334155; }
.weather-day .t { color: #0d9488; font-weight: 600; margin-top: 0.25rem; }

.timeline-day {
    background: white;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
}
.timeline-day .day-head {
    font-family: 'Fraunces', serif;
    font-size: 1.15rem;
    color: #0f172a;
    margin-bottom: 1rem;
    padding-bottom: 0.65rem;
    border-bottom: 2px solid #ccfbf1;
}
.timeline-day .day-date {
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 400;
    font-family: 'Outfit', sans-serif;
}
.timeline-item {
    display: flex;
    gap: 15px;
    padding: 14px;
    margin-bottom: 15px;
    border-left: 4px solid #14b8a6;
    background: #f8fafc;
    border-radius: 10px;
}
.timeline-item:last-child {
    margin-bottom: 0;
}
.timeline-item .time {
    font-weight: bold;
    color: #14b8a6;
    min-width: 80px;
    font-size: 0.95rem;
}
.timeline-item .title {
    font-size: 18px;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 4px;
}
.timeline-item .subtitle {
    font-size: 14px;
    color: #64748b;
}
.timeline-item .desc {
    font-size: 13px;
    color: #475569;
    margin-top: 6px;
    line-height: 1.4;
}

.budget-total {
    background: linear-gradient(135deg, #0f766e, #0d9488);
    color: white;
    border-radius: 14px;
    padding: 1.25rem;
    text-align: center;
}
.budget-total .amt { font-size: 2rem; font-weight: 700; font-family: 'Fraunces', serif; }

.empty-state {
    text-align: center;
    padding: 3rem 2rem;
    background: white;
    border-radius: 20px;
    border: 2px dashed #cbd5e1;
}
.empty-state .icon { font-size: 3.5rem; margin-bottom: 1rem; }
.empty-state h3 { font-family: 'Fraunces', serif; color: #0f172a; margin: 0 0 0.5rem 0; }
.empty-state p { color: #64748b; max-width: 420px; margin: 0 auto 1.5rem; }

.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-top: 1.5rem;
    text-align: left;
}
.feature-item {
    background: #f8fafc;
    padding: 1rem;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}
.feature-item strong { color: #0f172a; display: block; margin-bottom: 0.25rem; }
.feature-item span { font-size: 0.85rem; color: #64748b; }

.summary-box {
    background: #f0fdfa;
    border-left: 4px solid #14b8a6;
    padding: 1rem 1.25rem;
    border-radius: 0 12px 12px 0;
    margin-bottom: 1rem;
    color: #134e4a;
    line-height: 1.55;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: #f1f5f9;
    padding: 6px;
    border-radius: 14px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    font-weight: 600;
    color: #64748b;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #0f766e !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

@media (max-width: 768px) {
    .feature-grid { grid-template-columns: 1fr; }
    .route-banner { flex-direction: column; gap: 0.75rem; }
}
"""

def _inject_app_css(dark_mode: bool = False) -> None:
    """Inject global and theme-aware styles."""
    st.markdown(
        f"<style>{APP_CSS}{get_theme_css(dark_mode)}</style>",
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    defaults = {
        "trip_plan": None,
        "chat_history": [],
        "dark_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _esc(text: Any) -> str:
    """Escape text for safe HTML embedding."""
    return html_module.escape(str(text) if text is not None else "")


def _html(content: str) -> None:
    """Render HTML via markdown (dedented to avoid code-block escaping)."""
    st.markdown(textwrap.dedent(content).strip(), unsafe_allow_html=True)


def _inject_timeline_css() -> None:
    """Inject timeline styles (also in APP_CSS; ensures tab render)."""
    if st.session_state.get("_timeline_css_loaded"):
        return
    st.session_state["_timeline_css_loaded"] = True
    st.markdown(
        """
        <style>
        .timeline-item {
            display: flex;
            gap: 15px;
            padding: 14px;
            margin-bottom: 15px;
            border-left: 4px solid #14b8a6;
            background: #f8fafc;
            border-radius: 10px;
        }
        .timeline-item .time {
            font-weight: bold;
            color: #14b8a6;
            min-width: 80px;
        }
        .timeline-item .title {
            font-size: 18px;
            font-weight: 600;
            color: #0f172a;
        }
        .timeline-item .subtitle {
            font-size: 14px;
            color: #64748b;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _hero() -> None:
    _html("""
    <div class="hero-wrap">
        <h1 class="hero-title">DriftTrip</h1>
        <p class="hero-sub">Agentic travel planning with LangChain — flights, stays, sights & live weather</p>
        <div class="hero-badges">
            <span class="hero-badge">✈️ Smart flights</span>
            <span class="hero-badge">🏨 Hotel match</span>
            <span class="hero-badge">🗺️ Day itineraries</span>
            <span class="hero-badge">🌤️ Open-Meteo</span>
        </div>
    </div>
    """)


def _route_banner(
    source: str,
    dest: str,
    days: int,
    budget: Optional[float],
    cities_route: Optional[List[str]] = None,
) -> None:
    budget_txt = f" · Budget ₹{budget:,.0f}" if budget else ""
    if cities_route and len(cities_route) > 2:
        route_text = " → ".join(_esc(c) for c in cities_route)
        _html(f"""
        <div class="route-banner">
            <div class="route-city" style="flex:2;">
                <div class="label">Multi-city route</div>
                <div class="name" style="font-size:1.2rem;">{route_text}</div>
            </div>
        </div>
        <p class="route-meta" style="text-align:center;">{days} days{budget_txt}</p>
        """)
        return
    _html(f"""
    <div class="route-banner">
        <div class="route-city">
            <div class="label">From</div>
            <div class="name">{_esc(source)}</div>
        </div>
        <div class="route-arrow">✈</div>
        <div class="route-city">
            <div class="label">To</div>
            <div class="name">{_esc(dest)}</div>
        </div>
    </div>
    <p class="route-meta" style="text-align:center;">{days} days{budget_txt}</p>
    """)


def _stat_card(icon: str, label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f"""
    <div class="stat-card">
        <div class="icon">{icon}</div>
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {sub_html}
    </div>
    """


def _render_sidebar() -> dict:
    st.sidebar.markdown('<p class="sidebar-brand">✈️ Trip Planner</p>', unsafe_allow_html=True)
    st.sidebar.markdown(
        '<p class="sidebar-tagline">Configure your journey — AI tools search real datasets</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<p class="sidebar-section">Route</p>', unsafe_allow_html=True)

    cities_info = get_available_cities()
    all_cities = sorted(
        set(cities_info["flight_cities"])
        | set(cities_info["hotel_cities"])
        | set(cities_info["place_cities"])
    )

    st.session_state.dark_mode = st.sidebar.toggle(
        "🌙 Dark mode",
        value=st.session_state.get("dark_mode", False),
    )

    multi_city = st.sidebar.checkbox("🌍 Multi-city trip", value=False)
    source = st.sidebar.selectbox("🛫 Source city", all_cities, index=0)
    dest_options = [c for c in all_cities if c != source]

    extra_destinations: List[str] = []
    if multi_city:
        extra_destinations = st.sidebar.multiselect(
            "🗺️ Cities to visit (in order)",
            [c for c in all_cities if c != source],
            default=dest_options[:2] if len(dest_options) >= 2 else dest_options[:1],
        )
        destination = extra_destinations[-1] if extra_destinations else (
            dest_options[0] if dest_options else source
        )
    else:
        destination = st.sidebar.selectbox(
            "🛬 Destination",
            dest_options or all_cities,
            index=0 if dest_options else 0,
        )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        travel_date = st.date_input("📅 Start date", value=None)
    with col2:
        num_days = st.number_input("🗓️ Days", min_value=1, max_value=30, value=3)

    st.sidebar.markdown('<p class="sidebar-section">Trip settings</p>', unsafe_allow_html=True)
    budget = st.sidebar.number_input("💰 Budget (INR)", min_value=0, value=25000, step=1000)
    preferences = st.sidebar.text_area(
        "✨ Preferences",
        placeholder="temples, beaches, relaxed pace…",
        height=80,
    )

    st.sidebar.markdown('<p class="sidebar-section">Filters</p>', unsafe_allow_html=True)
    flight_mode = st.sidebar.selectbox("Flight", ["cheapest", "fastest", "all"])
    min_rating = st.sidebar.slider("Min hotel ★", 0.0, 5.0, 0.0, 0.5)
    max_hotel_price = st.sidebar.number_input("Max ₹/night (0=auto)", min_value=0, value=0)
    amenities = st.sidebar.text_input("Amenities", "wifi,pool")
    place_category = st.sidebar.text_input(
        "Place type",
        "",
        placeholder="temple, beach, museum (optional)",
    )

    has_llm = _has_llm_credentials()
    use_agent = st.sidebar.checkbox(
        "🤖 LangChain agent",
        value=True if has_llm else False,
        disabled=not has_llm,
    )
    if has_llm:
        st.sidebar.success("Gemini agent active")
    else:
        st.sidebar.caption("Add API keys in `.env` for agent mode")

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    plan_btn = st.sidebar.button("Plan my trip →", type="primary", use_container_width=True)

    return {
        "source": source,
        "destination": destination,
        "multi_city": multi_city,
        "extra_destinations": extra_destinations,
        "travel_date": travel_date.isoformat() if travel_date else None,
        "num_days": int(num_days),
        "budget": float(budget) if budget > 0 else None,
        "preferences": preferences,
        "flight_mode": flight_mode,
        "min_hotel_rating": min_rating,
        "max_hotel_price": float(max_hotel_price),
        "amenities": amenities,
        "place_category": place_category,
        "use_agent": use_agent,
        "plan_btn": plan_btn,
    }


def _render_explanations(plan: dict) -> None:
    """Show why each recommendation was chosen."""
    explanations = build_recommendation_explanations(plan)
    if not explanations:
        return
    st.markdown("##### 💡 Why we recommend this")
    for item in explanations:
        with st.expander(item.get("title", "Recommendation"), expanded=False):
            st.markdown(item.get("explanation", ""))


def _render_downloads(plan: dict, key_prefix: str = "overview") -> None:
    """Download buttons for JSON, Markdown, text, and PDF."""
    st.markdown("##### ⬇️ Download your trip")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button(
            "JSON",
            data=safe_json_dumps(plan),
            file_name="trip_plan.json",
            mime="application/json",
            use_container_width=True,
            key=f"{key_prefix}_download_json",
        )
    with c2:
        st.download_button(
            "Markdown",
            data=itinerary_to_markdown(plan),
            file_name="itinerary.md",
            mime="text/markdown",
            use_container_width=True,
            key=f"{key_prefix}_download_markdown",
        )
    with c3:
        st.download_button(
            "Text",
            data=itinerary_to_text(plan),
            file_name="itinerary.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"{key_prefix}_download_text",
        )
    with c4:
        try:
            pdf_bytes = itinerary_to_pdf_bytes(plan)
            st.download_button(
                "PDF",
                data=pdf_bytes,
                file_name="itinerary.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"{key_prefix}_download_pdf",
            )
        except ImportError:
            st.caption("Install fpdf2 for PDF export")


def _render_chat(plan: Optional[dict]) -> None:
    """Conversational assistant with memory."""
    st.markdown("Ask follow-up questions about your trip. Chat history is saved this session.")

    history: List[Dict[str, str]] = st.session_state.get("chat_history", [])
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                st.markdown(content)

    if prompt := st.chat_input("Ask about flights, hotels, weather, or itinerary…"):
        st.session_state.chat_history = append_chat_turn("user", prompt, history)
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.spinner("Thinking…"):
            reply = run_travel_chat(prompt, plan, st.session_state.chat_history)
        st.session_state.chat_history = append_chat_turn(
            "assistant", reply, st.session_state.chat_history
        )
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.rerun()

    if history and st.button("Clear chat history", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()


def _render_flight_insight_card(flight: dict, note: str = "") -> None:
    """Rich flight details inside Trip insights."""
    airline = _esc(flight.get("airline") or "—")
    flight_id = _esc(flight.get("flight_id") or "—")
    src = _esc(flight.get("source") or "—")
    dest = _esc(flight.get("destination") or "—")
    price = float(flight.get("price") or 0)
    duration = _esc(flight.get("duration") or "—")
    travel_date = _esc(flight.get("travel_date") or "—")
    dep = _esc(_format_flight_datetime(flight.get("departure")))
    arr = _esc(_format_flight_datetime(flight.get("arrival")))

    st.markdown(
        f"#### ✈️ Best flight — {airline} · `{flight_id}`",
        unsafe_allow_html=True,
    )
    if note:
        st.caption(note)

    cols = st.columns(5)
    cards = [
        ("🎫", "Flight no.", flight_id, ""),
        ("🛫", "Route", f"{src} → {dest}", ""),
        ("📅", "Travel date", travel_date, ""),
        ("⏱️", "Duration", duration, ""),
        ("💰", "Fare", f"₹{price:,.0f}", "INR"),
    ]
    for col, (icon, label, val, sub) in zip(cols, cards):
        with col:
            _html(_stat_card(icon, label, str(val), sub))

    c1, c2 = st.columns(2)
    with c1:
        _html(
            f"""
        <div class="stat-card" style="margin-top:0.5rem;">
            <div class="label">Departure</div>
            <div class="value" style="font-size:0.95rem;">{dep}</div>
        </div>
        """
        )
    with c2:
        _html(
            f"""
        <div class="stat-card" style="margin-top:0.5rem;">
            <div class="label">Arrival</div>
            <div class="value" style="font-size:0.95rem;">{arr}</div>
        </div>
        """
        )


def _render_trip_insights(plan: dict) -> None:
    """Display clean, user-friendly insight cards (no debug/tool traces)."""
    insights = build_trip_insights(plan)
    if not insights:
        st.info("Your trip plan is ready. Explore the tabs below for full details.")
        return

    renderers = {
        "success": st.success,
        "warning": st.warning,
        "info": st.info,
        "error": st.error,
    }
    for item in insights:
        if item.get("kind") == "flight" and item.get("flight"):
            _render_flight_insight_card(item["flight"], item.get("note") or "")
            continue
        level = item.get("level", "info")
        icon = item.get("icon", "•")
        message = item.get("message", "")
        renderer = renderers.get(level, st.info)
        renderer(f"{icon} {message}")


def _render_debug_panel(plan: Optional[dict]) -> None:
    """Developer-only dataset and match statistics."""
    with st.expander("Debug info"):
        st.json(build_debug_summary(plan))


def _render_flight(plan: dict) -> None:
    flight = plan.get("selected_flight")
    flight_search = plan.get("flight_search") or {}
    if not flight:
        source = plan.get("source", "")
        dest = plan.get("destination", "")
        st.warning(
            flight_search.get("message")
            or f"No flights found from {source} to {dest}. "
            "Try different travel dates, another route, or switch flight mode to 'all'."
        )
        return
    if flight_search.get("relaxed_filters") or not flight_search.get("date_matched", True):
        if flight_search.get("reasoning"):
            st.info(flight_search["reasoning"])
    elif flight_search.get("fallback_level") not in (None, "exact"):
        st.info(flight_search.get("reasoning", "Showing closest available flight."))

    all_flights = flight_search.get("flights") or []
    if len(all_flights) > 1:
        st.markdown("**All flights on this route (dataset)**")
        for idx, f in enumerate(all_flights, 1):
            st.markdown(
                f"{idx}. **{f.get('airline', '—')}** — "
                f"₹{float(f.get('price') or 0):,.0f} · "
                f"{f.get('duration', '—')} · "
                f"departs **{f.get('travel_date', '—')}** "
                f"({f.get('flight_id', '')})"
            )

    cols = st.columns(4)
    cards = [
        ("✈️", "Airline", flight.get("airline", "—"), ""),
        ("💰", "Fare", f"₹{flight.get('price', 0):,.0f}", "INR"),
        ("⏱️", "Duration", flight.get("duration", "—"), ""),
        ("📅", "Date", flight.get("travel_date", "—"), ""),
    ]
    for col, (icon, label, val, sub) in zip(cols, cards):
        with col:
            _html(_stat_card(icon, label, str(val), sub))

    c1, c2 = st.columns(2)
    with c1:
        _html(f"""
        <div class="stat-card" style="margin-top:1rem;">
            <div class="label">Departure</div>
            <div class="value" style="font-size:1rem;">{flight.get('departure', '—')}</div>
        </div>
        """)
    with c2:
        _html(f"""
        <div class="stat-card" style="margin-top:1rem;">
            <div class="label">Arrival</div>
            <div class="value" style="font-size:1rem;">{flight.get('arrival', '—')}</div>
        </div>
        """)


def _render_hotel(plan: dict) -> None:
    hotel = plan.get("selected_hotel")
    hotel_search = plan.get("hotel_search") or {}
    if not hotel:
        dest = plan.get("destination", "your destination")
        st.warning(
            hotel_search.get("message")
            or f"No hotels available in {dest} within your selected budget or filters. "
            "Try raising max price per night or lowering minimum star rating."
        )
        return
    if hotel_search.get("fallback_level") not in (None, "exact"):
        st.info(
            hotel_search.get(
                "reasoning",
                "No hotels matched your strict filters. Showing closest available options.",
            )
        )
    cols = st.columns(3)
    amenities = ", ".join(hotel.get("amenities") or []) or "—"
    for col, (icon, label, val) in zip(
        cols,
        [
            ("🏨", "Hotel", hotel.get("hotel_name", "—")),
            ("⭐", "Rating", f"{hotel.get('rating', '—')} / 5"),
            ("💳", "Per night", f"₹{hotel.get('price', 0):,.0f}"),
        ],
    ):
        with col:
            _html(_stat_card(icon, label, str(val)))
    _html(f"""
    <div class="stat-card" style="margin-top:1rem;">
        <div class="label">Amenities</div>
        <div class="value" style="font-size:1rem;">{amenities}</div>
    </div>
    """)


def _render_weather(plan: dict) -> None:
    weather = plan.get("weather_forecast") or {}
    if not weather.get("success"):
        st.warning(weather.get("message", "Weather unavailable."))
        return
    current = weather.get("current") or {}
    _html(f"""
    <div class="weather-now">
        <div class="temp">{current.get('temperature_c', '—')}°C</div>
        <div class="cond">{current.get('condition', '')}</div>
        <div style="font-size:0.85rem;color:#0f766e;margin-top:0.5rem;">
            Humidity {current.get('humidity_percent', '—')}% · Wind {current.get('wind_speed_kmh', '—')} km/h
        </div>
    </div>
    """)
    forecast = (weather.get("forecast") or [])[:5]
    if forecast:
        cols = st.columns(len(forecast))
        for col, day in zip(cols, forecast):
            with col:
                date_short = (day.get("date") or "")[-5:]
                _html(f"""
                <div class="weather-day">
                    <div class="d">{date_short}</div>
                    <div style="font-size:0.75rem;color:#64748b;">{day.get('condition', '')}</div>
                    <div class="t">{day.get('temp_min_c')}° – {day.get('temp_max_c')}°</div>
                </div>
                """)


def _timeline_item_html(activity: Dict[str, Any]) -> str:
    """Build a single timeline activity card."""
    time_val = _esc(activity.get("time", ""))
    title = _esc(activity.get("title", ""))
    category = _esc(activity.get("category", ""))
    description = activity.get("description") or activity.get("notes") or ""
    desc_html = (
        f'<div class="desc">{_esc(description)}</div>' if description else ""
    )
    return f"""
<div class="timeline-item">
    <span class="time">{time_val}</span>
    <div>
        <div class="title">{title}</div>
        <div class="subtitle">{category}</div>
        {desc_html}
    </div>
</div>
"""


def _render_itinerary(plan: dict) -> None:
    """Render day-wise itinerary as styled HTML timeline cards."""
    days = plan.get("day_wise_itinerary") or []
    if not days:
        st.info("No itinerary available for this trip.")
        return

    if plan.get("is_multi_city") and plan.get("legs"):
        st.markdown("##### 🌍 Legs overview")
        for leg in plan["legs"]:
            st.caption(
                f"**Leg {leg.get('leg_index')}:** {leg.get('source')} → "
                f"{leg.get('destination')} ({leg.get('num_days')} days)"
            )

    _inject_timeline_css()

    for day in days:
        day_num = _esc(day.get("day", ""))
        theme = _esc(day.get("theme", "Explore"))
        date_val = _esc(day.get("date", "TBD"))
        city_tag = day.get("city")
        city_html = (
            f' <span class="day-date">· {_esc(city_tag)}</span>' if city_tag else ""
        )
        activities = day.get("activities") or []

        if not activities:
            items_html = """
<div class="timeline-item">
    <span class="time">—</span>
    <div>
        <div class="title">Free exploration</div>
        <div class="subtitle">Flexible schedule</div>
    </div>
</div>
"""
        else:
            items_html = "".join(
                _timeline_item_html(act).strip() for act in activities
            )

        day_block = f"""
<div class="timeline-day">
    <div class="day-head">
        Day {day_num} — {theme}
        <span class="day-date">({date_val})</span>{city_html}
    </div>
    {items_html}
</div>
"""
        st.markdown(textwrap.dedent(day_block).strip(), unsafe_allow_html=True)

    st.markdown("---")
    _render_downloads(plan, key_prefix="itinerary")


def _render_budget(plan: dict) -> None:
    breakdown = plan.get("budget_breakdown") or {}
    if not breakdown:
        return

    total = breakdown.get("total_estimated_cost", 0)
    limit = plan.get("budget_limit")
    pct = min(100, int((total / limit) * 100)) if limit and limit > 0 else 0

    st.progress(pct / 100 if limit else 0.5)
    if limit:
        status = "✅ Within budget" if plan.get("within_budget") else "⚠️ Over budget"
        st.caption(f"{status} — limit ₹{limit:,.0f}")

    cols = st.columns(5)
    items = [
        ("✈️", "Flights", breakdown.get("flights", 0)),
        ("🏨", "Hotels", breakdown.get("hotels", 0)),
        ("🚕", "Transport", breakdown.get("local_transport", 0)),
        ("🍽️", "Food", breakdown.get("food", 0)),
    ]
    for col, (icon, label, val) in zip(cols[:4], items):
        with col:
            _html(_stat_card(icon, label, f"₹{val:,.0f}"))

    with cols[4]:
        _html(f"""
        <div class="budget-total">
            <div style="font-size:0.75rem;opacity:0.9;text-transform:uppercase;">Total</div>
            <div class="amt">₹{total:,.0f}</div>
        </div>
        """)

    chart_df = pd.DataFrame({
        "Category": ["Flights", "Hotels", "Transport", "Food"],
        "Amount (INR)": [
            breakdown.get("flights", 0),
            breakdown.get("hotels", 0),
            breakdown.get("local_transport", 0),
            breakdown.get("food", 0),
        ],
    })
    st.bar_chart(chart_df.set_index("Category"))


def _render_attractions(plan: dict) -> None:
    places = (plan.get("attractions") or [])[:8]
    if not places:
        st.info("No attractions found.")
        return
    cols = st.columns(2)
    for i, place in enumerate(places):
        with cols[i % 2]:
            rating = place.get("rating", "—")
            _html(f"""
            <div class="place-card">
                <h4>{place.get('attraction_name', '')}</h4>
                <div class="meta">
                    {place.get('category', '')} ·
                    <span class="rating-pill">★ {rating}</span>
                </div>
                <div class="desc">{place.get('description', '')}</div>
            </div>
            """)


def _empty_state() -> None:
    _html("""
    <div class="empty-state">
        <div class="icon">🌍</div>
        <h3>Ready to explore?</h3>
        <p>Set your route in the sidebar and hit <strong>Plan my trip</strong> to get
        flights, hotels, weather, and a day-by-day itinerary.</p>
        <div class="feature-grid">
            <div class="feature-item">
                <strong>✈️ Flights</strong>
                <span>Cheapest or fastest from your dataset</span>
            </div>
            <div class="feature-item">
                <strong>🏨 Hotels</strong>
                <span>Filter by rating, price & amenities</span>
            </div>
            <div class="feature-item">
                <strong>🗺️ Itinerary</strong>
                <span>Attractions spread across your trip days</span>
            </div>
        </div>
    </div>
    """)


def main() -> None:
    _init_session_state()
    _inject_app_css(st.session_state.get("dark_mode", False))
    _hero()

    form = _render_sidebar()

    if form["plan_btn"]:
        if form["multi_city"] and not form["extra_destinations"]:
            st.sidebar.error("Select at least one city for multi-city mode.")
        else:
            _run_trip_planning(form)

    tab_chat, tab_main = st.tabs(["💬 Travel chat", "🧳 Trip planner"])

    with tab_chat:
        _render_chat(st.session_state.trip_plan)

    with tab_main:
        plan = st.session_state.trip_plan
        if not plan:
            _empty_state()
            with st.expander("📍 Cities in dataset"):
                st.json(get_available_cities())
            _render_debug_panel(None)
        else:
            _render_main_planner_body(plan)


def _run_trip_planning(form: dict) -> None:
    """Execute single or multi-city trip planning."""
    with st.spinner("✨ Crafting your perfect trip…"):
        try:
            if form["multi_city"] and form["extra_destinations"]:
                plan = plan_multi_city_trip(
                    source=form["source"],
                    destinations=form["extra_destinations"],
                    total_days=form["num_days"],
                    budget=form["budget"],
                    preferences=form["preferences"],
                    travel_date=form["travel_date"],
                    flight_mode=form["flight_mode"],
                    min_hotel_rating=form["min_hotel_rating"],
                    max_hotel_price=form["max_hotel_price"],
                    amenities=form["amenities"],
                    place_category=form["place_category"],
                    use_agent=form["use_agent"],
                )
            else:
                plan = plan_trip_structured(
                    source=form["source"],
                    destination=form["destination"],
                    num_days=form["num_days"],
                    budget=form["budget"],
                    preferences=form["preferences"],
                    travel_date=form["travel_date"],
                    flight_mode=form["flight_mode"],
                    min_hotel_rating=form["min_hotel_rating"],
                    max_hotel_price=form["max_hotel_price"],
                    amenities=form["amenities"],
                    place_category=form["place_category"],
                    use_agent=form["use_agent"],
                )
            plan["flight_mode"] = form["flight_mode"]
            st.session_state.trip_plan = plan
            st.session_state.chat_history = append_chat_turn(
                "assistant",
                f"Planned your trip: {plan.get('trip_summary', '')}",
                st.session_state.get("chat_history", []),
            )
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_DIR / "latest_trip_plan.json", "w", encoding="utf-8") as f:
                f.write(safe_json_dumps(plan))
        except Exception as exc:
            st.error(f"Planning failed: {exc}")
            st.session_state.trip_plan = None


def _render_main_planner_body(plan: dict) -> None:
    """Render planned trip tabs."""
    route_cities = plan.get("cities_visited") if plan.get("is_multi_city") else None
    _route_banner(
        plan.get("source", ""),
        plan.get("destination", ""),
        plan.get("num_days", 0),
        plan.get("budget_limit"),
        cities_route=route_cities,
    )

    summary = plan.get("trip_summary", "Trip planned successfully.")
    within = "✅" if plan.get("within_budget", True) else "⚠️"
    _html(f'<div class="summary-box">{within} {_esc(summary)}</div>')

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "📋 Overview",
            "✈️ Flight",
            "🏨 Hotel",
            "🗺️ Sights",
            "🌤️ Weather",
            "📅 Itinerary",
            "💰 Budget",
        ]
    )

    with tab1:
        st.markdown("#### Trip insights")
        _render_trip_insights(plan)
        _render_explanations(plan)
        _render_downloads(plan, key_prefix="overview")
        _render_debug_panel(plan)

    with tab2:
        _render_flight(plan)
    with tab3:
        _render_hotel(plan)
    with tab4:
        _render_attractions(plan)
    with tab5:
        _render_weather(plan)
    with tab6:
        _render_itinerary(plan)
    with tab7:
        _render_budget(plan)


if __name__ == "__main__":
    main()
