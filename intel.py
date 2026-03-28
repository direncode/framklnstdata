"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  OSINT Intelligence Aggregator
==============================================
Multi-source open intelligence: Census demographics,
weather conditions, UNC event calendar, and social
signal estimation for Chapel Hill / Franklin Street.
"""

import json
import os
from datetime import datetime, timedelta

import requests

from config import CACHE_DIR, FRANKLIN_STREET_CENTER

# ---------------------------------------------------------------------------
# Cache (shared with traffic.py)
# ---------------------------------------------------------------------------

def _cache_path():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _read_cache(key):
    try:
        fp = os.path.join(_cache_path(), f"{key}.json")
        with open(fp) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_cache(key, data):
    fp = os.path.join(_cache_path(), f"{key}.json")
    with open(fp, "w") as f:
        json.dump(data, f, indent=2)


def _cache_age_hours(key):
    fp = os.path.join(_cache_path(), f"{key}.json")
    if not os.path.exists(fp):
        return float("inf")
    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
    return (datetime.now() - mtime).total_seconds() / 3600


# ---------------------------------------------------------------------------
# Census Demographics (US Census Bureau API)
# ---------------------------------------------------------------------------

# Pre-computed Chapel Hill / Orange County demographics
# Source: US Census Bureau ACS 5-year estimates
# FIPS: North Carolina = 37, Orange County = 135
CHAPEL_HILL_DEMOGRAPHICS = {
    "total_population": 61960,
    "median_age": 25.8,
    "college_enrollment": 30011,
    "pct_18_24": 42.3,
    "pct_25_34": 14.7,
    "median_household_income": 57842,
    "pct_bachelors_or_higher": 72.1,
    "housing_units": 25841,
    "pct_renter_occupied": 58.3,
    "population_density_per_sq_mi": 2834,
    "source": "US Census Bureau ACS 2022 5-Year Estimates",
    "fips_state": "37",
    "fips_county": "135",
}

# Demographic insights relevant to trivia night marketing
DEMOGRAPHIC_INSIGHTS = [
    {
        "metric": "College-age population (18-24)",
        "value": "42.3%",
        "insight": (
            "Chapel Hill's population is 42% college-age — your primary "
            "trivia audience. Marketing should be campus-centric."
        ),
    },
    {
        "metric": "Renter-occupied housing",
        "value": "58.3%",
        "insight": (
            "Majority renters = high turnover = need constant re-marketing. "
            "New students every semester need to discover trivia night."
        ),
    },
    {
        "metric": "Median age",
        "value": "25.8 years",
        "insight": (
            "Very young median age driven by student population. "
            "Pop culture, memes, and social media topics will land best."
        ),
    },
    {
        "metric": "Education level",
        "value": "72.1% Bachelor's+",
        "insight": (
            "Highly educated population — don't dumb down the trivia. "
            "Academic and science questions will be appreciated."
        ),
    },
]


def get_demographics():
    """Return Chapel Hill demographic data and insights."""
    return {
        "data": CHAPEL_HILL_DEMOGRAPHICS,
        "insights": DEMOGRAPHIC_INSIGHTS,
    }


def fetch_live_census(api_key=None):
    """
    Fetch live Census data for Orange County, NC.
    Requires a Census API key (free at api.census.gov/data/key_signup.html).
    Falls back to static data if unavailable.
    """
    if not api_key:
        api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        return None

    cache_key = "census_live"
    if _cache_age_hours(cache_key) < 720:  # Cache for 30 days
        cached = _read_cache(cache_key)
        if cached:
            return cached

    url = (
        "https://api.census.gov/data/2022/acs/acs5"
        "?get=B01003_001E,B01002_001E,B14001_002E,"
        "B25001_001E,B19013_001E"
        "&for=county:135&in=state:37"
        f"&key={api_key}"
    )

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                values = data[1]
                result = {
                    "total_population": int(values[0]),
                    "median_age": float(values[1]),
                    "college_enrollment": int(values[2]),
                    "housing_units": int(values[3]),
                    "median_household_income": int(values[4]),
                    "source": "US Census Bureau ACS 2022 (Live API)",
                }
                _write_cache(cache_key, result)
                return result
    except Exception as e:
        print(f"  [!] Census API error: {e}")

    return None


# ---------------------------------------------------------------------------
# Weather Intelligence (OpenWeatherMap)
# ---------------------------------------------------------------------------

# Fallback weather for Chapel Hill (typical conditions)
FALLBACK_WEATHER = {
    "temp_f": 72,
    "feels_like_f": 73,
    "description": "partly cloudy",
    "humidity": 55,
    "wind_mph": 8,
    "is_good_flyering_weather": True,
    "weather_impact": (
        "Good conditions for outdoor flyering. "
        "Moderate temperature and low wind."
    ),
    "source": "fallback estimate",
}


def fetch_weather():
    """
    Fetch current weather for Chapel Hill from OpenWeatherMap.
    Requires OPENWEATHER_API_KEY env var (free tier: 1000 calls/day).
    Falls back to static data.
    """
    api_key = os.environ.get("OPENWEATHER_API_KEY")

    # Check cache first (weather cached for 30 min)
    cache_key = "weather_current"
    if _cache_age_hours(cache_key) < 0.5:
        cached = _read_cache(cache_key)
        if cached:
            return cached

    if not api_key:
        return FALLBACK_WEATHER

    lat, lon = FRANKLIN_STREET_CENTER
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=imperial"
    )

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]["speed"]
            desc = data["weather"][0]["description"]

            # Determine if weather is good for flyering
            is_good = (
                temp > 40 and temp < 95
                and wind < 20
                and "rain" not in desc.lower()
                and "storm" not in desc.lower()
                and "snow" not in desc.lower()
            )

            if not is_good:
                impact = _weather_impact(temp, wind, desc)
            else:
                impact = (
                    "Good conditions for outdoor flyering. "
                    f"{desc.title()}, {temp:.0f}°F."
                )

            result = {
                "temp_f": round(temp),
                "feels_like_f": round(feels_like),
                "description": desc,
                "humidity": humidity,
                "wind_mph": round(wind),
                "is_good_flyering_weather": is_good,
                "weather_impact": impact,
                "source": "OpenWeatherMap (live)",
            }
            _write_cache(cache_key, result)
            return result
    except Exception as e:
        print(f"  [!] Weather API error: {e}")

    return FALLBACK_WEATHER


def _weather_impact(temp, wind, desc):
    """Generate weather impact assessment for flyering."""
    issues = []
    if temp < 40:
        issues.append("cold temperatures reduce foot traffic")
    if temp > 95:
        issues.append("extreme heat reduces foot traffic")
    if wind > 15:
        issues.append("high wind may blow away flyers")
    if "rain" in desc.lower():
        issues.append("rain reduces outdoor foot traffic significantly")
    if "storm" in desc.lower():
        issues.append("storm conditions — postpone outdoor flyering")
    if "snow" in desc.lower():
        issues.append("snow reduces foot traffic — focus on indoor spots")

    if issues:
        return "Challenging conditions: " + "; ".join(issues) + "."
    return "Conditions acceptable for flyering."


# ---------------------------------------------------------------------------
# UNC Event Intelligence
# ---------------------------------------------------------------------------

# Curated high-impact UNC events that affect Franklin Street traffic
# These are the types of events that massively change foot traffic patterns
UNC_EVENT_TYPES = {
    "basketball_home": {
        "traffic_multiplier": 2.5,
        "best_flyering_window": "2-3 hours before game",
        "notes": "Franklin Street floods with fans. Peak opportunity.",
    },
    "football_home": {
        "traffic_multiplier": 3.0,
        "best_flyering_window": "Morning of game day",
        "notes": "Tailgating starts early. Massive foot traffic all day.",
    },
    "graduation": {
        "traffic_multiplier": 2.0,
        "best_flyering_window": "Not ideal — family-focused crowd",
        "notes": "High traffic but wrong demographic for trivia night.",
    },
    "first_week": {
        "traffic_multiplier": 1.8,
        "best_flyering_window": "All week, especially evenings",
        "notes": "New students exploring. Perfect for building audience.",
    },
    "home_game_win": {
        "traffic_multiplier": 4.0,
        "best_flyering_window": "Immediately after game",
        "notes": "Franklin Street rushes after wins. Euphoric crowd.",
    },
    "exam_week": {
        "traffic_multiplier": 0.4,
        "best_flyering_window": "Library areas only",
        "notes": "Students are studying. Low bar traffic. Skip flyering.",
    },
    "spring_break": {
        "traffic_multiplier": 0.2,
        "best_flyering_window": "Skip this week entirely",
        "notes": "Campus empty. Save your flyers.",
    },
    "normal_weekday": {
        "traffic_multiplier": 1.0,
        "best_flyering_window": "11am-1pm and 5pm-7pm",
        "notes": "Standard foot traffic patterns.",
    },
    "normal_weekend": {
        "traffic_multiplier": 1.3,
        "best_flyering_window": "Evening, 7pm-11pm",
        "notes": "Weekend bar traffic is higher.",
    },
}


def get_event_context():
    """
    Return current event context for Chapel Hill.
    In production, this would scrape the UNC events calendar.
    For now, returns day-of-week based context with event type database.
    """
    now = datetime.now()
    dow = now.weekday()
    month = now.month

    # Determine likely event context
    if month in (5, 12) and 1 <= now.day <= 15:
        event_type = "exam_week"
    elif month == 3 and 8 <= now.day <= 16:
        event_type = "spring_break"
    elif month in (8, 1) and 15 <= now.day <= 25:
        event_type = "first_week"
    elif dow < 5:
        event_type = "normal_weekday"
    else:
        event_type = "normal_weekend"

    event_info = UNC_EVENT_TYPES[event_type]

    return {
        "event_type": event_type,
        "traffic_multiplier": event_info["traffic_multiplier"],
        "best_flyering_window": event_info["best_flyering_window"],
        "notes": event_info["notes"],
        "day_of_week": now.strftime("%A"),
        "date": now.strftime("%Y-%m-%d"),
        "all_event_types": UNC_EVENT_TYPES,
    }


# ---------------------------------------------------------------------------
# Social Signal Estimation
# ---------------------------------------------------------------------------

# Estimated social media reach for Franklin Street venues
# Based on typical Instagram/TikTok posting patterns for college towns
SOCIAL_SIGNALS = {
    "franklin_street": {
        "avg_instagram_posts_per_day": 150,
        "avg_tiktok_mentions_per_week": 45,
        "peak_posting_hours": [19, 20, 21, 22, 23],
        "top_hashtags": [
            "#FranklinStreet", "#UNC", "#ChapelHill", "#TarHeels",
            "#GoHeels", "#UNCChapelHill", "#FranklinSt",
        ],
        "estimated_monthly_reach": 250000,
    },
    "bandidos": {
        "avg_instagram_posts_per_day": 8,
        "estimated_followers": 3200,
        "top_hashtags": ["#Bandidos", "#BandidosCH", "#FranklinStreet"],
    },
}


def get_social_signals():
    """Return social media signal estimates for Franklin Street."""
    return SOCIAL_SIGNALS


# ---------------------------------------------------------------------------
# Combined Intelligence Report
# ---------------------------------------------------------------------------

def build_intel_report():
    """
    Build a comprehensive OSINT intelligence report combining
    all available data sources.
    """
    return {
        "demographics": get_demographics(),
        "weather": fetch_weather(),
        "event_context": get_event_context(),
        "social_signals": get_social_signals(),
        "generated_at": datetime.now().isoformat(),
    }
