"""Application-wide constants and field mapping definitions."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

FLIGHTS_FILE = DATA_DIR / "flights.json"
HOTELS_FILE = DATA_DIR / "hotels.json"
PLACES_FILE = DATA_DIR / "places.json"

# Canonical field names after normalization
FLIGHT_FIELDS = {
    "id": ["flight_id", "id", "flightId"],
    "airline": ["airline", "carrier", "airline_name"],
    "source": ["from", "source", "origin", "departure_city", "from_city"],
    "destination": ["to", "destination", "dest", "arrival_city", "to_city"],
    "departure": ["departure_time", "departure", "depart_time", "dep_time"],
    "arrival": ["arrival_time", "arrival", "arr_time", "arrive_time"],
    "price": ["price", "fare", "cost", "ticket_price"],
    "date": ["date", "travel_date", "departure_date"],
}

HOTEL_FIELDS = {
    "id": ["hotel_id", "id", "hotelId"],
    "name": ["name", "hotel_name", "title"],
    "city": ["city", "location", "destination"],
    "rating": ["stars", "rating", "star_rating", "review_score"],
    "price": ["price_per_night", "price", "nightly_rate", "rate"],
    "amenities": ["amenities", "facilities", "features"],
}

PLACE_FIELDS = {
    "id": ["place_id", "id", "placeId"],
    "name": ["name", "place_name", "attraction", "title"],
    "city": ["city", "location", "destination"],
    "category": ["type", "category", "place_type", "kind"],
    "rating": ["rating", "score", "popularity", "stars"],
    "description": ["description", "desc", "summary", "about"],
}

# City name aliases for fuzzy matching
CITY_ALIASES = {
    "bengaluru": "bangalore",
    "bangalore": "bangalore",
    "bombay": "mumbai",
    "mumbai": "mumbai",
    "new delhi": "delhi",
    "delhi": "delhi",
    "calcutta": "kolkata",
    "kolkata": "kolkata",
    "madras": "chennai",
    "chennai": "chennai",
    "hyderabad": "hyderabad",
    "goa": "goa",
    "jaipur": "jaipur",
    "bangaluru": "bangalore",
    "bengluru": "bangalore",
}

# Default budget assumptions (INR per day)
DEFAULT_LOCAL_TRANSPORT_PER_DAY = 800
DEFAULT_FOOD_PER_DAY = 1200

# Open-Meteo endpoints
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# LLM provider env keys
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_MODEL = "OPENAI_MODEL"
ENV_GOOGLE_API_KEY = "GOOGLE_API_KEY"
ENV_GEMINI_MODEL = "GEMINI_MODEL"
ENV_LLM_PROVIDER = "LLM_PROVIDER"  # openai | gemini

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

AGENT_MAX_ITERATIONS = 12
AGENT_VERBOSE = False
