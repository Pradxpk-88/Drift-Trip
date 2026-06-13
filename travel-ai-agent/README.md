# Agentic AI-Based Travel Planning Assistant Using LangChain

A production-ready **AI travel planning web application** that combines **LangChain tool-calling agents**, **real JSON travel datasets**, **live weather (Open-Meteo)**, and a modern **Streamlit** interface.

**Project title:** Agentic AI-Based Travel Planning Assistant Using LangChain

---

## Overview

Voyager AI helps users plan trips by searching flights, hotels, and attractions from local datasets, fetching live weather, estimating budgets, and generating day-wise itineraries. An optional **Gemini/OpenAI LangChain agent** orchestrates tools and answers follow-up questions in chat.

| Item | Detail |
|------|--------|
| **Language** | Python 3.10+ |
| **Frameworks** | LangChain, Streamlit, LangGraph |
| **LLM** | Google Gemini (default) or OpenAI |
| **Weather API** | [Open-Meteo](https://open-meteo.com/) (no API key) |
| **Data** | `flights.json`, `hotels.json`, `places.json` |

---

## Features

### Core
- Dynamic JSON loading with automatic field mapping
- Invalid/missing record handling
- Five LangChain tools: Flight, Hotel, Places, Weather, Budget
- Tool-calling agent (Gemini / OpenAI)
- Deterministic fallback (works without API keys)
- Day-wise itinerary generation
- Structured trip JSON output

### UI & UX
- Modern Streamlit dashboard (Voyager AI)
- Trip insights with clean alert cards (no debug logs)
- Recommendation explanations (“Why we recommend this”)
- Dark mode toggle
- Readable sidebar inputs (dark text on white fields)

### Bonus
- Multi-city trip planning
- Travel chat with session history & memory
- Export: JSON, Markdown, Text, **PDF**
- Downloadable itinerary

---

## Project structure

```
travel-ai-agent/
├── app.py                      # Streamlit UI entry point
├── requirements.txt
├── README.md
├── PROJECT_REPORT.md           # Full project documentation
├── .env.example
├── .streamlit/config.toml
│
├── data/
│   ├── flights.json
│   ├── hotels.json
│   └── places.json
│
├── agents/
│   └── travel_agent.py         # LangChain agent + trip pipeline
│
├── tools/
│   ├── flight_tool.py
│   ├── hotel_tool.py
│   ├── places_tool.py
│   ├── weather_tool.py
│   └── budget_tool.py
│
├── services/
│   ├── data_loader.py
│   ├── itinerary_service.py
│   ├── export_service.py       # PDF / MD / TXT export
│   ├── multi_city_service.py
│   └── chat_service.py
│
├── utils/
│   ├── helper.py
│   ├── constants.py
│   ├── insights.py
│   ├── explanations.py
│   └── theme.py
│
└── output/
    ├── sample_output.json
    └── latest_trip_plan.json
```

---

## Installation

### 1. Prerequisites
- Python 3.10 or higher
- pip

### 2. Clone / open project

```bash
cd travel-ai-agent
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment setup

```bash
copy .env.example .env
```

Edit `.env`:

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.5-flash
```

For OpenAI instead:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

> **Note:** Trip planning works without any API key. Keys are only required for the LangChain agent and chat.

---

## How to run

```bash
cd travel-ai-agent
python -m streamlit run app.py
```

Open: **http://localhost:8501**

### Quick start
1. Set **Source** and **Destination** (e.g. Hyderabad → Delhi)
2. Set **Days** and **Budget**
3. Enable **LangChain agent** (if API key is set)
4. Click **Plan my trip →**
5. Explore tabs: Overview, Flight, Hotel, Sights, Weather, Itinerary, Budget
6. Use **Travel chat** for follow-up questions

### Multi-city
1. Check **Multi-city trip** in sidebar
2. Select cities in visit order
3. Plan trip — days and budget split across legs

---

## LangChain tools

| Tool | Function | Data source |
|------|----------|-------------|
| `flight_search_tool` | Cheapest / fastest / all flights | `flights.json` |
| `hotel_recommendation_tool` | Hotels by city, rating, price, amenities | `hotels.json` |
| `places_discovery_tool` | Attractions by city & category | `places.json` |
| `weather_forecast_tool` | Current + forecast weather | Open-Meteo API |
| `budget_estimation_tool` | Total trip cost breakdown | Computed |

---

## Testing LangChain

### Check API key

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); from agents.travel_agent import _has_llm_credentials; print(_has_llm_credentials())"
```

### Test agent

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()
from agents.travel_agent import run_agent_query
r = run_agent_query('Find cheapest flight Hyderabad to Delhi')
print(r['output'])
"
```

### Test full pipeline (no agent)

```bash
python -c "
from agents.travel_agent import plan_trip_structured
p = plan_trip_structured('Hyderabad','Delhi',3,budget=25000,use_agent=False)
print(p['trip_summary'])
"
```

---

## Programmatic usage

```python
from dotenv import load_dotenv
load_dotenv()

from agents.travel_agent import plan_trip_structured

plan = plan_trip_structured(
    source="Hyderabad",
    destination="Delhi",
    num_days=3,
    budget=25000,
    preferences="temples, museums",
    flight_mode="cheapest",
    use_agent=True,
)

print(plan["trip_summary"])
print(plan["selected_flight"])
print(plan["day_wise_itinerary"])
```

---

## Output format

Each trip plan includes:

| Field | Description |
|-------|-------------|
| `trip_summary` | One-line trip overview |
| `selected_flight` | Best flight details |
| `selected_hotel` | Recommended hotel |
| `attractions` | Top places list |
| `weather_forecast` | Live weather data |
| `day_wise_itinerary` | Scheduled activities per day |
| `budget_breakdown` | Cost itemization |
| `within_budget` | Budget fit flag |

Sample: `output/sample_output.json`

---

## Cities in dataset

Delhi, Mumbai, Goa, Bangalore, Chennai, Hyderabad, Kolkata, Jaipur

Use routes that exist in `flights.json` (e.g. Hyderabad → Delhi).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No flights found | Route not in dataset; try Hyderabad→Delhi |
| Agent quota error (429) | Use `gemini-2.5-flash` in `.env` |
| PDF export fails | `pip install fpdf2` |
| Sidebar text invisible | Refresh app (CSS fix applied) |
| Duplicate button error | Fixed with unique `key` on downloads |

---

## Security

- Never commit `.env` or API keys to Git
- Regenerate keys if exposed publicly
- `.gitignore` excludes `.env` and sensitive output

---

## Documentation

- **README.md** — Setup and usage (this file)
- **PROJECT_REPORT.md** — Full project report for submission

---

## License

Educational / academic project use.

---

## Author

AI-Based Travel Planning Project — LangChain + Streamlit + Gemini
