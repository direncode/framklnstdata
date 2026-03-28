"""
==============================================
  FRANKLIN STREET PANOPTICON v3
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
    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        return None

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
    Fetch current weather for Chapel Hill from OpenWeatherMap.
    Requires OPENWEATHER_API_KEY env var (free: 1000 calls/day).
    Returns None if no key or API fails.
    """
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return None

    cached = _read_cache("weather_current", max_age_hours=0.5)
    if cached:
        return cached

    lat, lon = FRANKLIN_STREET_CENTER
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]
        desc = data["weather"][0]["description"]

        is_good = (
            temp > 40 and temp < 95
            and wind < 20
            and "rain" not in desc.lower()
            and "storm" not in desc.lower()
            and "snow" not in desc.lower()
        )

        result = {
            "temp_f": round(temp),
            "feels_like_f": round(feels_like),
            "description": desc,
            "humidity": humidity,
            "wind_mph": round(wind),
            "is_good_flyering_weather": is_good,
            "source": "OpenWeatherMap (live)",
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
            "User-Agent": "PanopticonBot/1.0 (academic research tool)",
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
