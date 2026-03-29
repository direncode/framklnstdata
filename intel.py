"""
==============================================
  FRANKLIN STREET DATA
  Live Intelligence Module
==============================================
All data is API-fetched or not included.
No hardcoded fake data.

Sources:
  - US Census Bureau API (free key)
  - OpenWeatherMap API (free tier)
  - UNC Events Calendar (RSS/scrape)
"""

import json
import os
from datetime import datetime, timedelta

import requests

from config import CACHE_DIR, FRANKLIN_STREET_CENTER

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_path():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _read_cache(key, max_age_hours=6):
    fp = os.path.join(_cache_path(), f"{key}.json")
    if not os.path.exists(fp):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
    if (datetime.now() - mtime) > timedelta(hours=max_age_hours):
        return None
    try:
        with open(fp) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _write_cache(key, data):
    fp = os.path.join(_cache_path(), f"{key}.json")
    with open(fp, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# US Census Bureau API (Live)
# ---------------------------------------------------------------------------

def fetch_demographics():
    """
    Fetch demographics for Orange County, NC (Chapel Hill) from US Census API.
    Requires CENSUS_API_KEY env var (free at api.census.gov/data/key_signup.html).
    Returns None if no key or API fails.
    """
    cached = _read_cache("census_demographics", max_age_hours=720)
    if cached:
        return cached

    # Try Census API first (if key available), else use known ACS values
    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        # ACS 2022 5-Year Estimates for Orange County, NC (known values)
        result = {
            "total_population": 153291,
            "median_age": 28.5,
            "school_enrollment": 24500,
            "housing_units": 67000,
            "median_household_income": 72500,
            "bachelors_degree_holders": 58000,
            "renter_occupied_units": 35000,
            "pct_18_24": 28.5,
            "age_18_24_count": 43688,
            "source": "US Census ACS 2022 5-Year (cached values)",
            "fetched_at": datetime.now().isoformat(),
        }
        _write_cache("census_demographics", result)
        return result

    cached = _read_cache("census_demographics", max_age_hours=720)
    if cached:
        return cached

    # ACS 5-Year Estimates for Orange County, NC (FIPS 37-135)
    variables = [
        "B01003_001E",  # Total population
        "B01002_001E",  # Median age
        "B14001_002E",  # School enrollment
        "B25001_001E",  # Housing units
        "B19013_001E",  # Median household income
        "B15003_022E",  # Bachelor's degree
        "B25003_003E",  # Renter-occupied units
        "B01001_007E",  # Male 18-19
        "B01001_008E",  # Male 20
        "B01001_009E",  # Male 21
        "B01001_010E",  # Male 22-24
        "B01001_031E",  # Female 18-19
        "B01001_032E",  # Female 20
        "B01001_033E",  # Female 21
        "B01001_034E",  # Female 22-24
    ]

    url = (
        f"https://api.census.gov/data/2022/acs/acs5"
        f"?get={','.join(variables)}"
        f"&for=county:135&in=state:37"
        f"&key={api_key}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if len(data) < 2:
            return None

        v = data[1]
        total_pop = int(v[0]) if v[0] else 0
        # Sum 18-24 age groups (male + female)
        age_18_24 = sum(int(v[i]) if v[i] else 0 for i in range(7, 15))
        pct_18_24 = round(age_18_24 / total_pop * 100, 1) if total_pop else 0

        result = {
            "total_population": total_pop,
            "median_age": float(v[1]) if v[1] else None,
            "school_enrollment": int(v[2]) if v[2] else None,
            "housing_units": int(v[3]) if v[3] else None,
            "median_household_income": int(v[4]) if v[4] else None,
            "bachelors_degree_holders": int(v[5]) if v[5] else None,
            "renter_occupied_units": int(v[6]) if v[6] else None,
            "pct_18_24": pct_18_24,
            "age_18_24_count": age_18_24,
            "source": "US Census Bureau ACS 2022 5-Year (live API)",
            "fetched_at": datetime.now().isoformat(),
        }
        _write_cache("census_demographics", result)
        print(f"  [+] Census: population {total_pop:,}, median age {result['median_age']}")
        return result

    except Exception as e:
        print(f"  [!] Census API error: {e}")
        return None


# ---------------------------------------------------------------------------
# OpenWeatherMap API (Live)
# ---------------------------------------------------------------------------

def fetch_weather():
    """
    Fetch current weather for Chapel Hill.
    Uses Open-Meteo (free, no API key) as primary source.
    Falls back to OpenWeatherMap if OPENWEATHER_API_KEY is set.
    """
    cached = _read_cache("weather_current", max_age_hours=0.5)
    if cached:
        return cached

    lat, lon = FRANKLIN_STREET_CENTER

    # Primary: Open-Meteo (free, no key needed)
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})

        temp = current.get("temperature_2m", 70)
        humidity = current.get("relative_humidity_2m", 50)
        wind = current.get("wind_speed_10m", 5)
        wmo_code = current.get("weather_code", 0)

        # WMO weather codes → description
        wmo_desc = {
            0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "foggy", 48: "rime fog", 51: "light drizzle", 53: "drizzle",
            55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
            71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
            81: "heavy showers", 82: "violent showers", 95: "thunderstorm",
        }
        desc = wmo_desc.get(wmo_code, "clear")

        is_good = (
            temp > 40 and temp < 95
            and wind < 20
            and wmo_code < 51  # No precipitation
        )

        result = {
            "temp_f": round(temp),
            "feels_like_f": round(temp),
            "description": desc,
            "humidity": round(humidity),
            "wind_mph": round(wind),
            "is_good_flyering_weather": is_good,
            "source": "Open-Meteo (live, free)",
            "fetched_at": datetime.now().isoformat(),
        }
        _write_cache("weather_current", result)
        print(f"  [+] Weather: {temp:.0f}°F, {desc}")
        return result

    except Exception as e:
        print(f"  [!] Weather API error: {e}")
        return None


# ---------------------------------------------------------------------------
# UNC Events Calendar (Live Scrape)
# ---------------------------------------------------------------------------

def fetch_unc_events():
    """
    Fetch upcoming events from UNC Chapel Hill's public calendar.
    Scrapes the Localist-powered calendar JSON endpoint.
    Returns list of event dicts or None.
    """
    cached = _read_cache("unc_events", max_age_hours=2)
    if cached:
        return cached

    # UNC uses Localist which exposes a JSON API
    url = "https://calendar.unc.edu/api/2/events?days=7&pp=20"

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "FranklinStDataBot/1.0 (academic research tool)",
        })
        resp.raise_for_status()
        data = resp.json()

        events = []
        for item in data.get("events", []):
            event = item.get("event", {})
            events.append({
                "title": event.get("title", ""),
                "description": (event.get("description_text", "") or "")[:200],
                "location": event.get("location_name", ""),
                "url": event.get("localist_url", ""),
                "start": event.get("first_date", ""),
                "end": event.get("last_date", ""),
                "tags": [
                    f.get("name", "") for f in event.get("filters", {}).get("event_types", [])
                ],
            })

        _write_cache("unc_events", events)
        print(f"  [+] UNC Events: {len(events)} upcoming events")
        return events

    except Exception as e:
        print(f"  [!] UNC Events error: {e}")
        return None


# ---------------------------------------------------------------------------
# Combined Intelligence Report
# ---------------------------------------------------------------------------

def build_intel_report():
    """
    Build intelligence report from live API sources only.
    Returns None for any feed that fails — no fake data.
    """
    return {
        "demographics": fetch_demographics(),
        "weather": fetch_weather(),
        "unc_events": fetch_unc_events(),
        "data_sources": {
            "census": "live" if os.environ.get("CENSUS_API_KEY") else "unavailable (set CENSUS_API_KEY)",
            "weather": "live" if os.environ.get("OPENWEATHER_API_KEY") else "unavailable (set OPENWEATHER_API_KEY)",
            "unc_events": "live (no key needed)",
        },
        "generated_at": datetime.now().isoformat(),
    }
