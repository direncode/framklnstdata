"""
==============================================
  FRANKLIN STREET DATA
  Venue Discovery & BTUT Foot Traffic
==============================================
Uses the BTUT Mean-Field Game engine (Fokker-Planck PDE)
to compute foot traffic density from live signals:
  - Google Trends interest scores
  - Weather conditions
  - UNC events calendar
  - Time-of-day venue type profiles
  - Day-of-week multipliers

Replaces BestTime API with proprietary O(N) density solver.
"""

import os
import json
import math
from datetime import datetime, timedelta

from config import CACHE_DIR, FRANKLIN_STREET_CENTER, FRANKLIN_STREET_BOUNDS
from traffic import fetch_nearby_places


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
# Haversine
# ---------------------------------------------------------------------------

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# BTUT Mean-Field Game Busyness
# ---------------------------------------------------------------------------

def get_venues_with_busyness(hour=None, radius_meters=500):
    """
    Get all Franklin Street venues with BTUT-computed foot traffic.

    Strategy:
    1. Discover venues via OpenStreetMap (free, cached 30 days)
    2. Collect live signals (trends, weather, events)
    3. Run Fokker-Planck density solver to convergence
    4. Sample density at venue positions → busyness (0-100)

    The MFG engine fuses all signals into a continuous density
    field ρ(x,t) over the Franklin Street corridor.
    """
    if hour is None:
        hour = datetime.now().hour
    day_of_week = datetime.now().weekday()

    # Check cache first (MFG results cached 1 hour per day/hour)
    cache_key = f"mfg_busyness_{day_of_week}_{hour}"
    cached = _read_cache(cache_key, max_age_hours=1)
    if cached:
        print(f"  [+] BTUT: using cached density ({len(cached)} venues, hour={hour})")
        return cached

    # Step 1: Discover venues via OSM (always available, free)
    osm_venues = fetch_nearby_places(radius_meters=radius_meters)
    if not osm_venues:
        osm_venues = []

    # Step 2: Run BTUT Mean-Field Game engine
    try:
        from mfg import get_mfg_engine, collect_signals

        print(f"  [*] BTUT: solving density field (hour={hour}, day={day_of_week})...")
        signals = collect_signals()
        engine = get_mfg_engine(osm_venues)

        # Solve for this hour
        result = engine.solve_hour(hour, day_of_week, signals)
        nash_gap = result["nash_gap"]
        iterations = result["iterations"]
        converged = nash_gap < 1e-4

        print(f"  [+] BTUT: converged={'yes' if converged else 'approx'} "
              f"(gap={nash_gap:.2e}, {iterations} steps)")

        # Also generate 24-hour profiles
        profiles_24h = {}
        try:
            result_24h = engine.solve_24h(day_of_week, signals)
            profiles_24h = result_24h.get("hourly_profiles", {})
        except Exception:
            pass

        # Build venue list with MFG busyness
        venues = []
        venue_busyness = result["venue_busyness"]
        for i, place in enumerate(osm_venues):
            name = place["name"]
            vb = venue_busyness.get(name, {})
            busyness = vb.get("busyness")
            hourly_profile = profiles_24h.get(name)

            venues.append({
                "id": i + 1,
                "name": name,
                "lat": place["lat"],
                "lon": place["lon"],
                "amenity_type": place.get("amenity_type", "unknown"),
                "osm_id": place.get("osm_id"),
                "busyness": busyness,
                "hourly_profile": hourly_profile,
                "busyness_source": "btut_mfg",
                "nash_gap": nash_gap,
            })

    except ImportError:
        # numpy not installed — fall back to no busyness
        print("  [!] BTUT engine unavailable (numpy not installed)")
        venues = []
        for i, place in enumerate(osm_venues):
            venues.append({
                "id": i + 1,
                "name": place["name"],
                "lat": place["lat"],
                "lon": place["lon"],
                "amenity_type": place.get("amenity_type", "unknown"),
                "osm_id": place.get("osm_id"),
                "busyness": None,
                "hourly_profile": None,
                "busyness_source": None,
            })
    except Exception as e:
        print(f"  [!] BTUT engine error: {e}")
        venues = []
        for i, place in enumerate(osm_venues):
            venues.append({
                "id": i + 1,
                "name": place["name"],
                "lat": place["lat"],
                "lon": place["lon"],
                "amenity_type": place.get("amenity_type", "unknown"),
                "osm_id": place.get("osm_id"),
                "busyness": None,
                "hourly_profile": None,
                "busyness_source": None,
            })

    # Sort: busyness desc, then alphabetical
    with_data = [v for v in venues if v.get("busyness") is not None and v["busyness"] > 0]
    without_data = [v for v in venues if not (v.get("busyness") is not None and v["busyness"] > 0)]

    with_data.sort(key=lambda v: v["busyness"], reverse=True)
    without_data.sort(key=lambda v: v["name"])

    result_list = with_data + without_data

    # Cache the result
    _write_cache(cache_key, result_list)

    return result_list


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
