"""Conversational chat with trip context and session memory."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.travel_agent import create_travel_agent, _has_llm_credentials
from utils.insights import sanitize_agent_output


def _trip_context_message(plan: Optional[Dict[str, Any]]) -> str:
    """Build system context from current trip plan."""
    if not plan:
        return (
            "You are Voyager AI, a friendly travel assistant. "
            "The user has not planned a trip yet. Help them choose cities and dates."
        )
    summary = plan.get("trip_summary", "")
    source = plan.get("source", "")
    dest = plan.get("destination", "")
    days = plan.get("num_days", "")
    budget = plan.get("budget_limit", "")
    return (
        "You are Voyager AI, a travel assistant. Answer based on the user's current trip plan. "
        "Do not show tool logs, JSON, or debug traces. Be concise and helpful.\n\n"
        f"Trip: {summary}\n"
        f"Route: {source} → {dest}, {days} days, budget limit: {budget}\n"
        f"Flight: {plan.get('selected_flight')}\n"
        f"Hotel: {plan.get('selected_hotel')}\n"
    )


def append_chat_turn(
    role: str,
    content: str,
    history: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """Append a message to chat history."""
    updated = list(history)
    updated.append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    return updated


def run_travel_chat(
    user_message: str,
    trip_plan: Optional[Dict[str, Any]],
    chat_history: List[Dict[str, str]],
    max_history_turns: int = 8,
) -> str:
    """
    Run a conversational turn with memory from prior chat and trip context.

    Returns sanitized assistant reply text.
    """
    if not _has_llm_credentials():
        return (
            "Chat requires a Gemini or OpenAI API key in `.env`. "
            "You can still use Plan my trip without chat."
        )

    messages: List[Any] = [SystemMessage(content=_trip_context_message(trip_plan))]

    recent = chat_history[-max_history_turns * 2 :] if chat_history else []
    for turn in recent:
        if turn.get("role") == "user":
            messages.append(HumanMessage(content=turn.get("content", "")))
        elif turn.get("role") == "assistant":
            messages.append(AIMessage(content=turn.get("content", "")))

    messages.append(HumanMessage(content=user_message))

    try:
        graph = create_travel_agent()
        result = graph.invoke({"messages": messages})
        out_messages = result.get("messages", [])
        for msg in reversed(out_messages):
            if isinstance(msg, AIMessage) and msg.content:
                raw = msg.content
                if isinstance(raw, list):
                    parts = [
                        b.get("text", "") for b in raw
                        if isinstance(b, dict) and b.get("text")
                    ]
                    raw = "\n".join(parts)
                return sanitize_agent_output(str(raw))
        return "I could not generate a response. Please try again."
    except Exception as exc:
        return f"Chat is temporarily unavailable: {exc}"
