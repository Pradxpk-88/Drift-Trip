# Project Report

## Agentic AI-Based Travel Planning Assistant Using LangChain

---

| **Field** | **Details** |
|-----------|-------------|
| **Project Title** | Agentic AI-Based Travel Planning Assistant Using LangChain |
| **Technologies** | Python, LangChain, LangGraph, Streamlit, OpenAI/Gemini, Open-Meteo |
| **Project Type** | AI / Agentic Application |
| **Interface** | Web Application (Streamlit) |

---

## 1. Introduction

### 1.1 Background

Travel planning involves searching flights, booking hotels, discovering attractions, checking weather, and managing budgets. Traditional tools require users to visit multiple websites manually. Recent advances in **Large Language Models (LLMs)** and **agentic AI frameworks** such as **LangChain** enable intelligent systems that can reason about user requests, call specialized tools, and produce structured travel plans automatically.

### 1.2 Problem Statement

Users need a single intelligent assistant that can:

- Search and recommend flights, hotels, and tourist places
- Provide live weather forecasts for destinations
- Estimate total trip cost within a given budget
- Generate day-wise itineraries
- Explain recommendations in plain language
- Support conversational follow-up questions

### 1.3 Objectives

1. Build a modular LangChain-based travel agent with multiple tools
2. Process real JSON datasets dynamically with robust error handling
3. Integrate live weather data via Open-Meteo API
4. Deliver a user-friendly Streamlit web interface
5. Support optional LLM providers (Google Gemini / OpenAI)
6. Provide export options and multi-city trip planning

### 1.4 Scope

**In scope:**
- Flight, hotel, and places search from local JSON files
- Weather forecasting (Open-Meteo)
- Budget estimation
- Itinerary generation
- LangChain tool-calling agent
- Streamlit UI with chat and exports

**Out of scope:**
- Real-time booking / payment integration
- Live flight/hotel API (Amadeus, Booking.com, etc.)
- User authentication and database persistence

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                     │
│  Sidebar inputs │ Tabs │ Chat │ Downloads │ Dark mode        │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│              Travel Agent (agents/travel_agent.py)           │
│         LangChain create_agent + Tool Calling Loop           │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────┐
│  LangChain    │   │   Services    │   │   External API    │
│  Tools (5)    │   │  Itinerary    │   │   Open-Meteo      │
│               │   │  Multi-city   │   │   (Weather)       │
│  Flight       │   │  Export PDF   │   └───────────────────┘
│  Hotel        │   │  Chat memory  │
│  Places       │   └───────────────┘
│  Weather      │
│  Budget       │
└───────┬───────┘
        ▼
┌───────────────────────────────────────┐
│  data/flights.json                      │
│  data/hotels.json                       │
│  data/places.json                       │
└───────────────────────────────────────┘
```

### 2.2 Design Pattern

- **Modular architecture** — separation of tools, services, agents, and UI
- **Agentic pattern** — LLM decides which tools to invoke
- **Fallback pipeline** — deterministic tool execution when agent/LLM unavailable
- **Session state** — Streamlit stores trip plan, chat history, preferences

### 2.3 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Agent framework | LangChain 1.x, LangGraph |
| LLM | Google Gemini 2.5 Flash / OpenAI GPT-4o-mini |
| Data processing | Python, Pydantic |
| Weather | Open-Meteo REST API |
| PDF export | fpdf2 |
| Config | python-dotenv |

---

## 3. Data Layer

### 3.1 Datasets

Three JSON files in `data/`:

| File | Records | Key fields |
|------|---------|------------|
| `flights.json` | Flight listings | airline, from, to, departure_time, arrival_time, price |
| `hotels.json` | Hotel listings | name, city, stars, price_per_night, amenities |
| `places.json` | Attractions | name, city, type, rating |

### 3.2 Dynamic Field Mapping

The `utils/helper.py` module automatically maps alternate field names:

- `from` / `source` / `origin` → source city
- `stars` / `rating` → hotel rating
- `type` / `category` → place category

### 3.3 Data Validation

Invalid records are filtered when:

- Required fields are missing or empty
- Price or rating cannot be parsed
- City names fail normalization

City aliases support: Bangalore/Bengaluru, Mumbai/Bombay, Delhi/New Delhi, etc.

---

## 4. LangChain Tools

### 4.1 Flight Search Tool

**Purpose:** Find flights between two cities.

**Capabilities:**
- Cheapest flight selection
- Fastest flight selection
- List all matching flights
- Filter by airline and travel date

**Output:** airline, departure, arrival, duration, price

### 4.2 Hotel Recommendation Tool

**Purpose:** Recommend hotels in destination city.

**Capabilities:**
- Filter by minimum star rating
- Filter by maximum price per night
- Filter by amenities (wifi, pool, gym, etc.)
- Sort by rating, price, or value score

### 4.3 Places Discovery Tool

**Purpose:** Discover tourist attractions.

**Capabilities:**
- Filter by city and category (temple, museum, fort, beach, etc.)
- Sort by rating (popularity)

### 4.4 Weather Forecast Tool

**Purpose:** Fetch live weather using Open-Meteo.

**Capabilities:**
- Current temperature, humidity, wind, conditions
- Multi-day forecast (up to 7 days)
- No API key required

### 4.5 Budget Estimation Tool

**Purpose:** Calculate total estimated trip cost.

**Components:**
- Flight fare
- Hotel (nights × nightly rate)
- Local transport (default ₹800/day)
- Food (default ₹1200/day)
- Optional extra expenses

---

## 5. Agent Implementation

### 5.1 Agent Type

**LangChain Tool-Calling Agent** (`create_agent` from LangChain 1.x)

The agent:
1. Receives natural language travel requests
2. Selects appropriate tools
3. Processes tool results
4. Produces human-readable recommendations

### 5.2 System Prompt

The agent is instructed to:
- Use only real tool outputs (no hallucinated flights/hotels)
- Prefer cheapest flights unless specified otherwise
- Match hotels to budget and preferences
- Provide clear summaries without exposing debug data

### 5.3 LLM Configuration

| Provider | Environment variables |
|----------|----------------------|
| Gemini (default) | `LLM_PROVIDER=gemini`, `GOOGLE_API_KEY`, `GEMINI_MODEL` |
| OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` |

**Verbose mode:** Disabled (`AGENT_VERBOSE = False`)

### 5.4 Fallback Pipeline

When the agent is disabled or API fails, `plan_trip_structured()` runs all tools directly and assembles output via `itinerary_service.py`. The application remains fully functional.

---

## 6. Services

### 6.1 Itinerary Service

- Distributes attractions across trip days
- Builds time-slotted activity schedules
- Merges multi-city leg itineraries with city labels

### 6.2 Multi-City Service

- Plans sequential legs: Source → City1 → City2 → …
- Splits days and budget across legs
- Aggregates total cost and combined itinerary

### 6.3 Export Service

| Format | Method |
|--------|--------|
| JSON | Full structured plan |
| Markdown | Human-readable itinerary |
| Plain text | Simplified text version |
| PDF | fpdf2 generated document |

### 6.4 Chat Service

- Maintains session chat history
- Passes trip context as system message
- Supports conversational memory (last 8 turns)
- Sanitizes agent output (no tool traces shown to user)

---

## 7. User Interface

### 7.1 Streamlit Application

**Brand:** Voyager AI

**Main sections:**
1. **Sidebar** — Trip configuration (route, dates, budget, filters, agent toggle, dark mode)
2. **Travel chat** — Conversational assistant tab
3. **Trip planner** — Results with 7 sub-tabs

### 7.2 Tabs

| Tab | Content |
|-----|---------|
| Overview | Trip insights, explanations, downloads |
| Flight | Selected flight details |
| Hotel | Selected hotel details |
| Sights | Attraction cards |
| Weather | Current + forecast |
| Itinerary | Timeline view + downloads |
| Budget | Cost breakdown + chart |

### 7.3 UX Enhancements

- Clean insight cards (success/warning/info) — no raw LangChain logs
- Recommendation explanation expanders
- Dark mode theme toggle
- High-contrast sidebar input fields
- Route banner with multi-city support
- HTML timeline for itinerary (proper markdown rendering)

---

## 8. Implementation Details

### 8.1 Key Modules

| Module | Responsibility |
|--------|----------------|
| `app.py` | Streamlit UI orchestration |
| `agents/travel_agent.py` | Agent creation, trip planning pipeline |
| `tools/*.py` | LangChain tool definitions |
| `services/data_loader.py` | Cached JSON loading |
| `utils/helper.py` | Schema detection, normalization |
| `utils/insights.py` | User-facing insight cards |
| `utils/explanations.py` | Recommendation reasoning |
| `utils/theme.py` | Light/dark CSS themes |

### 8.2 Error Handling

- Missing JSON files → `FileNotFoundError` with clear message
- Invalid records → skipped silently during load
- Weather API failure → graceful warning in UI
- Agent API failure → fallback to direct tool pipeline
- PDF export → ImportError hint if fpdf2 missing

### 8.3 Security

- API keys stored in `.env` (not committed)
- HTML output escaped via `html.escape`
- Agent output sanitized to remove signatures and debug metadata

---

## 9. Sample Workflow

### Example: Hyderabad → Delhi (3 days, ₹25,000 budget)

1. User selects Hyderabad as source, Delhi as destination
2. User sets 3 days, budget ₹25,000, preferences "temples"
3. User clicks **Plan my trip**
4. System executes:
   - Flight search → IndiGo cheapest flight (~₹2,907)
   - Hotel search → Best value hotel in Delhi
   - Places discovery → Top temples/museums
   - Weather → Live Delhi forecast
   - Budget → Total ~₹17,000 (within budget)
5. Itinerary builder schedules attractions across 3 days
6. UI displays insights, tabs, and download options
7. User can chat: "Suggest indoor activities if it rains"

---

## 10. Testing

### 10.1 Test Cases

| Test | Expected result |
|------|-----------------|
| Load datasets | All JSON files parsed, invalid records filtered |
| Flight search Hyderabad→Delhi | At least one flight returned |
| Flight search Bangalore→Chennai | No flight (if not in data) — warning shown |
| Weather Delhi | Current temp + forecast returned |
| Budget calculation | Itemized breakdown with total |
| Agent with Gemini key | Clean text output, no tool logs in UI |
| Plan without API key | Full trip via fallback pipeline |
| PDF export | Valid PDF bytes generated |
| Multi-city Hyderabad→Delhi→Mumbai | Combined plan with legs |

### 10.2 How to Run Tests

```bash
cd travel-ai-agent
pip install -r requirements.txt

# Tool pipeline
python -c "from agents.travel_agent import plan_trip_structured; print(plan_trip_structured('Hyderabad','Delhi',2,use_agent=False)['trip_summary'])"

# Agent (requires .env)
python -c "from dotenv import load_dotenv; load_dotenv(); from agents.travel_agent import run_agent_query; print(run_agent_query('Find flight Hyderabad to Delhi')['output'])"
```

---

## 11. Results

### 11.1 Achievements

- Fully functional agentic travel planner with 5 LangChain tools
- Real dataset integration (no mock data generation)
- Live weather integration
- Professional Streamlit UI with dark mode
- Multi-city support
- Chat with conversational memory
- Multiple export formats including PDF
- Clean user-facing insights (debug-free)

### 11.2 Sample Output

See `output/sample_output.json` for a complete structured trip plan example.

### 11.3 Limitations

- Flight/hotel data is static JSON (not live industry APIs)
- Agent depends on LLM API quota and availability
- Chat memory is session-only (not persisted to database)
- PDF uses basic formatting (Helvetica, Latin-1 safe text)

---

## 12. Future Enhancements

1. Integration with real flight/hotel APIs (Amadeus, Skyscanner)
2. User accounts and saved trip history (database)
3. Google Maps / distance-based routing
4. Email itinerary delivery
5. Voice input for travel queries
6. RAG over travel guides and reviews
7. Mobile-responsive PWA version

---

## 13. Conclusion

The **Agentic AI-Based Travel Planning Assistant Using LangChain** successfully demonstrates how modern AI agent frameworks can orchestrate specialized tools to deliver end-to-end travel planning. By combining structured JSON datasets, live weather APIs, LangChain tool-calling agents, and an intuitive Streamlit interface, the project provides a practical, extensible foundation for intelligent travel assistance suitable for academic demonstration and further production development.

---

## 14. References

1. LangChain Documentation — https://docs.langchain.com/
2. Streamlit Documentation — https://docs.streamlit.io/
3. Open-Meteo API — https://open-meteo.com/
4. Google Gemini API — https://ai.google.dev/
5. OpenAI API — https://platform.openai.com/
6. fpdf2 Library — https://py-pdf.github.io/fpdf2/

---

## 15. Appendix

### A. Project Directory Tree

```
travel-ai-agent/
├── app.py
├── requirements.txt
├── README.md
├── PROJECT_REPORT.md
├── .env.example
├── agents/travel_agent.py
├── tools/ (5 tool modules)
├── services/ (5 service modules)
├── utils/ (5 utility modules)
├── data/ (3 JSON datasets)
└── output/ (generated plans)
```

### B. Environment Variables

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

### C. Commands Quick Reference

```bash
# Install
pip install -r requirements.txt

# Run app
python -m streamlit run app.py

# Test credentials
python -c "from dotenv import load_dotenv; load_dotenv(); from agents.travel_agent import _has_llm_credentials; print(_has_llm_credentials())"
```

---

**End of Project Report**
