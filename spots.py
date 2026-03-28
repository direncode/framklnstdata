"""
==============================================
  FRANKLIN STREET DATA
  Venue Discovery & Live Foot Traffic
==============================================
Step 1: BestTime Venue Search — discovers and forecasts all venues
        in the Franklin Street area in ONE API call.
Step 2: BestTime Venue Filter — queries the forecasted venues for
        busyness at a specific day/hour.

This replaces the old approach of forecasting 53 venues individually
(which burned 53 API credits per page load).
"""

import os
import json
import math
import time as time_module
from datetime import datetime, timedelta

import requests

from config import CACHE_DIR, FRANKLIN_STREET_CENTER, FRANKLIN_STREET_BOUNDS
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
# Step 1: BestTime Venue Search (one call, discovers + forecasts area)
# ---------------------------------------------------------------------------

def besttime_venue_search():
    """
    Search for all venues near Franklin Street via BestTime.
    This triggers forecasts for all found venues in one batch.
    Results are cached for 7 days (forecasts represent weekly averages).

    Returns the search job URL or cached venue data.
    """
    if not BESTTIME_PRIVATE_KEY:
        return None

    cached = _read_cache("besttime_search", max_age_hours=168)
    if cached:
        print(f"  [+] BestTime: using cached search ({len(cached)} venues)")
        return cached

    lat, lon = FRANKLIN_STREET_CENTER

    # Initiate venue search for the Franklin Street area
    try:
        resp = requests.post(
            f"{BESTTIME_BASE}/venues/search",
            params={
                "api_key_private": BESTTIME_PRIVATE_KEY,
                "q": "bars restaurants cafes Chapel Hill Franklin Street NC",
                "num": 50,
                "lat": lat,
                "lng": lon,
                "radius": 500,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            job_id = data.get("job_id")
            if job_id:
                print(f"  [+] BestTime search started, job_id={job_id}")
                # Poll for completion
                return _poll_search_job(job_id)
            elif data.get("venues"):
                # Sometimes returns venues directly
                venues = data["venues"]
                _write_cache("besttime_search", venues)
                return venues
        else:
            print(f"  [!] BestTime search HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [!] BestTime search error: {e}")

    return None


def _poll_search_job(job_id, max_wait=60):
    """Poll BestTime search job until complete."""
    start = time_module.time()
    while time_module.time() - start < max_wait:
        try:
            resp = requests.get(
                f"{BESTTIME_BASE}/venues/progress",
                params={
                    "api_key_private": BESTTIME_PRIVATE_KEY,
                    "job_id": job_id,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                if status == "OK":
                    venues = data.get("venues", [])
                    if venues:
                        _write_cache("besttime_search", venues)
                        print(f"  [+] BestTime search complete: {len(venues)} venues")
                        return venues
                elif status == "error":
                    print(f"  [!] BestTime search failed: {data.get('message')}")
                    return None
                # Still processing
        except Exception:
            pass
        time_module.sleep(3)

    print("  [!] BestTime search timed out")
    return None


# ---------------------------------------------------------------------------
# Step 2: BestTime Venue Filter (query busyness for day/hour)
# ---------------------------------------------------------------------------

def besttime_venue_filter(hour=None, day_of_week=None):
    """
    Filter all forecasted venues for busyness at a specific day/hour.
    Uses the public key (no credit cost for filtering).

    Returns list of venues with busyness data.
    """
    if not BESTTIME_PUBLIC_KEY:
        return None

    if hour is None:
        hour = datetime.now().hour
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    cache_key = f"besttime_filter_{day_of_week}_{hour}"
    cached = _read_cache(cache_key, max_age_hours=1)
    if cached:
        return cached

    lat, lon = FRANKLIN_STREET_CENTER
    bounds = FRANKLIN_STREET_BOUNDS

    try:
        resp = requests.get(
            f"{BESTTIME_BASE}/venues/filter",
            params={
                "api_key_public": BESTTIME_PUBLIC_KEY,
                "lat": lat,
                "lng": lon,
                "radius": 500,
                "day_int": day_of_week,
                "hour": hour,
                "types": "BAR,RESTAURANT,CAFE,CLUB,PUB,NIGHT_CLUB",
                "order_by": "day_rank_max",
                "order": "desc",
                "foot_traffic": "true",
                "limit": 100,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            venues = data.get("venues", [])
            if venues:
                result = []
                for v in venues:
                    info = v.get("venue_info", {})
                    forecast = v.get("venue_foot_traffic_forecast", {})

                    # Get busyness for this hour from day_raw
                    busyness = None
                    day_raw = forecast.get("day_raw")
                    if day_raw and isinstance(day_raw, list):
                        # BestTime day_raw: index 0 = 6am, wraps at 24
                        bt_index = (hour - 6) % 24
                        if 0 <= bt_index < len(day_raw):
                            busyness = day_raw[bt_index]

                    result.append({
                        "name": info.get("venue_name", ""),
                        "lat": info.get("venue_lat"),
                        "lon": info.get("venue_lng"),
                        "venue_id": info.get("venue_id"),
                        "venue_type": info.get("venue_type", ""),
                        "busyness": busyness,
                        "hourly_profile": day_raw,
                        "busyness_source": "besttime_forecast",
                    })

                _write_cache(cache_key, result)
                print(f"  [+] BestTime filter: {len(result)} venues at hour {hour}")
                return result
            else:
                print(f"  [!] BestTime filter: no venues returned")
        else:
            print(f"  [!] BestTime filter HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  [!] BestTime filter error: {e}")

    return None


# ---------------------------------------------------------------------------
# Combined: OSM Discovery + BestTime Busyness
# ---------------------------------------------------------------------------

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def get_venues_with_busyness(hour=None, radius_meters=500):
    """
    Get all Franklin Street venues with real foot traffic data.

    Strategy:
    1. Trigger BestTime venue search (once, cached 7 days)
    2. Query BestTime venue filter for busyness at requested hour
    3. Also discover OSM venues and merge (OSM has more coverage)
    4. Match BestTime venues to OSM venues by proximity

    If no BestTime keys, falls back to OSM-only (no busyness).
    """
    if hour is None:
        hour = datetime.now().hour
    day_of_week = datetime.now().weekday()

    # Get OSM venues (always available, no API key needed)
    osm_venues = fetch_nearby_places(radius_meters=radius_meters)
    if not osm_venues:
        osm_venues = []

    venues = []
    for i, place in enumerate(osm_venues):
        venues.append({
            "id": i + 1,
            "name": place["name"],
            "lat": place["lat"],
            "lon": place["lon"],
            "amenity_type": place.get("amenity_type", "unknown"),
            "busyness": None,
            "hourly_profile": None,
            "busyness_source": None,
        })

    if not BESTTIME_PRIVATE_KEY and not BESTTIME_PUBLIC_KEY:
        return venues

    # Step 1: Ensure venues are forecasted (one-time, cached 7 days)
    besttime_venue_search()

    # Step 2: Filter for busyness at requested hour
    bt_venues = besttime_venue_filter(hour=hour, day_of_week=day_of_week)

    if bt_venues:
        # Match BestTime venues to OSM venues by proximity
        for venue in venues:
            best_match = None
            best_dist = 80  # meters threshold

            for bt in bt_venues:
                if bt.get("lat") and bt.get("lon"):
                    dist = _haversine(
                        venue["lat"], venue["lon"],
                        bt["lat"], bt["lon"],
                    )
                    if dist < best_dist:
                        best_dist = dist
                        best_match = bt

            if best_match:
                venue["busyness"] = best_match.get("busyness")
                venue["hourly_profile"] = best_match.get("hourly_profile")
                venue["busyness_source"] = "besttime_forecast"
                venue["venue_id"] = best_match.get("venue_id")

        # Also add BestTime venues that weren't in OSM
        osm_coords = set((v["lat"], v["lon"]) for v in venues)
        for bt in bt_venues:
            if bt.get("lat") and bt.get("lon"):
                is_new = all(
                    _haversine(bt["lat"], bt["lon"], lat, lon) > 80
                    for lat, lon in osm_coords
                )
                if is_new:
                    venues.append({
                        "id": len(venues) + 1,
                        "name": bt["name"],
                        "lat": bt["lat"],
                        "lon": bt["lon"],
                        "amenity_type": bt.get("venue_type", "unknown"),
                        "busyness": bt.get("busyness"),
                        "hourly_profile": bt.get("hourly_profile"),
                        "busyness_source": "besttime_forecast",
                    })

    # Sort: busyness desc, then alphabetical
    with_data = [v for v in venues if v.get("busyness") is not None and v["busyness"] > 0]
    without_data = [v for v in venues if not (v.get("busyness") is not None and v["busyness"] > 0)]

    with_data.sort(key=lambda v: v["busyness"], reverse=True)
    without_data.sort(key=lambda v: v["name"])

    return with_data + without_data


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------

def get_enriched_spots(time_of_day="evening", hour=None, top_n=50):
    venues = get_venues_with_busyness(hour=hour)
    for v in venues:
        if v.get("busyness") is not None and v["busyness"] > 0:
            v["composite_score"] = round(v["busyness"] / 10, 1)
        else:
            v["composite_score"] = 0
        v["live_busyness"] = v.get("busyness")
    return venues[:top_n]


def get_ranked_spots(time_of_day="evening", top_n=50):
    return get_enriched_spots(time_of_day=time_of_day, top_n=top_n)


FRANKLIN_STREET_SPOTS = []
