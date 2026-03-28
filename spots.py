"""
==============================================
  FRANKLIN STREET DATA
  Venue Discovery & Ranking
==============================================
Every venue on Franklin Street, discovered live from OpenStreetMap
and enriched with real-time foot traffic from BestTime.app.

Ranking signal: BestTime.app live busyness (0-100%).
This is ACTUAL foot traffic data from anonymous phone signals,
not review counts or editorial guesses.
"""

import math
import os
import json
import time
from datetime import datetime, timedelta

import requests

from config import CACHE_DIR, FRANKLIN_STREET_CENTER
from traffic import fetch_nearby_places

BESTTIME_PRIVATE_KEY = os.environ.get("BESTTIME_API_KEY_PRIVATE", "")
BESTTIME_PUBLIC_KEY = os.environ.get("BESTTIME_API_KEY_PUBLIC", "")
BESTTIME_BASE = "https://besttime.app/api/v1"


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
# BestTime.app API — Real Foot Traffic
# ---------------------------------------------------------------------------

def besttime_forecast(venue_name, venue_address="Franklin Street, Chapel Hill, NC"):
    """
    Create a new foot traffic forecast for a venue via BestTime.app.
    Returns venue_id + full week forecast with hourly busyness (0-100%).
    Uses private key. Costs 1 forecast credit.
    Cache for 7 days (forecasts are based on weekly averages).
    """
    if not BESTTIME_PRIVATE_KEY:
        return None

    cache_key = f"besttime_forecast_{venue_name.replace(' ', '_')[:30]}"
    cached = _read_cache(cache_key, max_age_hours=168)  # 7 days
    if cached:
        return cached

    try:
        resp = requests.post(
            f"{BESTTIME_BASE}/forecasts",
            params={
                "api_key_private": BESTTIME_PRIVATE_KEY,
                "venue_name": venue_name,
                "venue_address": venue_address,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                result = {
                    "venue_id": data.get("venue_info", {}).get("venue_id"),
                    "venue_name": data.get("venue_info", {}).get("venue_name"),
                    "analysis": [],
                }

                # Extract day_raw (24 hourly values 0-100) for each day
                for day in data.get("analysis", []):
                    day_info = day.get("day_info", {})
                    result["analysis"].append({
                        "day_text": day_info.get("day_text", ""),
                        "day_int": day_info.get("day_int", 0),
                        "day_raw": day.get("day_raw", []),
                        "venue_open": day_info.get("venue_open", 0),
                        "venue_closed": day_info.get("venue_closed", 0),
                    })

                _write_cache(cache_key, result)
                print(f"  [+] BestTime forecast: {venue_name}")
                return result
            else:
                print(f"  [!] BestTime forecast failed for {venue_name}: {data.get('message', '')}")
        else:
            print(f"  [!] BestTime HTTP {resp.status_code} for {venue_name}")

        time.sleep(0.5)  # Rate limit: 300/min

    except Exception as e:
        print(f"  [!] BestTime error for {venue_name}: {e}")

    return None


def besttime_now(venue_name, venue_address="Franklin Street, Chapel Hill, NC"):
    """
    Get LIVE busyness for a venue right now via BestTime.app.
    Returns current busyness (0-100%) and forecasted busyness.
    Uses private key. Costs 1 live credit.
    Cache for 1 hour.
    """
    if not BESTTIME_PRIVATE_KEY:
        return None

    cache_key = f"besttime_now_{venue_name.replace(' ', '_')[:30]}"
    cached = _read_cache(cache_key, max_age_hours=1)
    if cached:
        return cached

    try:
        resp = requests.post(
            f"{BESTTIME_BASE}/forecasts/live",
            params={
                "api_key_private": BESTTIME_PRIVATE_KEY,
                "venue_name": venue_name,
                "venue_address": venue_address,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                analysis = data.get("analysis", {})
                result = {
                    "venue_name": data.get("venue_info", {}).get("venue_name"),
                    "venue_id": data.get("venue_info", {}).get("venue_id"),
                    "live_busyness": analysis.get("venue_live_busyness"),
                    "forecasted_busyness": analysis.get("venue_forecasted_busyness"),
                    "live_vs_forecast": analysis.get("venue_live_forecasted_delta"),
                    "hour": analysis.get("hour_start"),
                    "source": "besttime_live",
                }
                _write_cache(cache_key, result)
                print(f"  [+] BestTime live: {venue_name} = {result['live_busyness']}%")
                return result

        time.sleep(0.5)

    except Exception as e:
        print(f"  [!] BestTime live error for {venue_name}: {e}")

    return None


def besttime_get_busyness_for_hour(forecast, hour=None, day_of_week=None):
    """
    Extract busyness for a specific hour from a BestTime forecast.
    Returns 0-100 or None.
    """
    if not forecast or not forecast.get("analysis"):
        return None

    if hour is None:
        hour = datetime.now().hour
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    for day in forecast["analysis"]:
        if day.get("day_int") == day_of_week:
            raw = day.get("day_raw", [])
            # BestTime day_raw starts at 6am by default
            # Index 0 = 6am, index 1 = 7am, ... index 18 = midnight
            bt_index = (hour - 6) % 24
            if 0 <= bt_index < len(raw):
                return raw[bt_index]

    return None


# ---------------------------------------------------------------------------
# OSM Discovery
# ---------------------------------------------------------------------------

def discover_venues(radius_meters=500):
    """Discover all venues on/near Franklin Street via OpenStreetMap."""
    places = fetch_nearby_places(radius_meters=radius_meters)
    if not places:
        return []

    return [
        {
            "id": i + 1,
            "name": place["name"],
            "lat": place["lat"],
            "lon": place["lon"],
            "amenity_type": place.get("amenity_type", "unknown"),
            "osm_id": place.get("osm_id"),
        }
        for i, place in enumerate(places)
    ]


# ---------------------------------------------------------------------------
# Combined: OSM Discovery + BestTime Busyness
# ---------------------------------------------------------------------------

def get_venues_with_busyness(hour=None, radius_meters=500):
    """
    Discover venues via OSM, enrich with BestTime.app foot traffic.

    1. OSM Overpass → all venues with coordinates
    2. BestTime.app forecast → hourly busyness 0-100% for each venue
    3. Rank by busyness at the requested hour

    If no BestTime API key, venues appear but with no busyness data.
    """
    venues = discover_venues(radius_meters=radius_meters)
    if not venues:
        return []

    if not BESTTIME_PRIVATE_KEY:
        for venue in venues:
            venue["busyness"] = None
            venue["hourly_profile"] = None
            venue["busyness_source"] = None
        return venues

    if hour is None:
        hour = datetime.now().hour
    day_of_week = datetime.now().weekday()

    for venue in venues:
        # Get forecast for this venue
        forecast = besttime_forecast(
            venue["name"],
            f"{venue['name']}, Franklin Street, Chapel Hill, NC",
        )

        if forecast:
            # Extract busyness for the requested hour
            busyness = besttime_get_busyness_for_hour(
                forecast, hour=hour, day_of_week=day_of_week,
            )
            venue["busyness"] = busyness
            venue["venue_id"] = forecast.get("venue_id")
            venue["busyness_source"] = "besttime_forecast"

            # Extract today's full hourly profile
            for day in forecast.get("analysis", []):
                if day.get("day_int") == day_of_week:
                    venue["hourly_profile"] = day.get("day_raw")
                    break
            else:
                venue["hourly_profile"] = None
        else:
            venue["busyness"] = None
            venue["hourly_profile"] = None
            venue["busyness_source"] = None

    # Sort: highest busyness first
    with_data = [v for v in venues if v["busyness"] is not None]
    without_data = [v for v in venues if v["busyness"] is None]

    with_data.sort(key=lambda v: v["busyness"], reverse=True)
    without_data.sort(key=lambda v: v["name"])

    return with_data + without_data


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------

def get_enriched_spots(time_of_day="evening", hour=None, top_n=50):
    """Get venues ranked by foot traffic."""
    venues = get_venues_with_busyness(hour=hour)

    for v in venues:
        if v["busyness"] is not None:
            v["composite_score"] = round(v["busyness"] / 10, 1)
        else:
            v["composite_score"] = 0
        v["live_busyness"] = v["busyness"]

    return venues[:top_n]


def get_ranked_spots(time_of_day="evening", top_n=50):
    return get_enriched_spots(time_of_day=time_of_day, top_n=top_n)


FRANKLIN_STREET_SPOTS = []
