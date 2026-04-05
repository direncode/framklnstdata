"""
==============================================
  FRANKLIN STREET DATA
  Live Aircraft Tracking (ADS-B)
==============================================
Fetches live aircraft positions from the OpenSky Network
(free, public ADS-B data) and other public sources.
Provides real-time airborne surveillance layer for the
global intelligence dashboard.

Data source: OpenSky Network (https://opensky-network.org)
  - Free API, no key required for anonymous access
  - Rate limited: ~10 req/min anonymous, ~100 req/min authenticated
  - Returns all aircraft with ADS-B transponders in a bounding box
"""

import time
import math
import requests
from datetime import datetime

# Cache
_aircraft_cache = {}
_CACHE_TTL = 15  # 15 seconds for near-real-time


# ---------------------------------------------------------------------------
# OpenSky Network API
# ---------------------------------------------------------------------------

OPENSKY_API = "https://opensky-network.org/api"


def fetch_aircraft(bbox=None, extended=False):
    """
    Fetch live aircraft positions from OpenSky Network.

    bbox: (south, west, north, east) - defaults to RDU area
    extended: if True, fetch extended info (requires auth)

    Returns list of aircraft dicts.
    """
    cache_key = f"aircraft_{bbox}"
    if cache_key in _aircraft_cache:
        entry = _aircraft_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    if bbox is None:
        # Default: ~100nm around RDU (covers Chapel Hill area)
        bbox = (34.5, -80.5, 37.0, -77.5)

    params = {
        "lamin": bbox[0],
        "lomin": bbox[1],
        "lamax": bbox[2],
        "lomax": bbox[3],
    }

    try:
        resp = requests.get(
            f"{OPENSKY_API}/states/all",
            params=params,
            timeout=15,
            headers={"User-Agent": "FranklinStreetData/4.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _get_fallback_aircraft()

    aircraft = []
    states = data.get("states", [])
    for s in states:
        if len(s) < 17:
            continue
        # Skip ground vehicles
        if s[8] is True:  # on_ground
            continue

        aircraft.append({
            "icao24": s[0],
            "callsign": (s[1] or "").strip(),
            "origin_country": s[2],
            "lat": s[6],
            "lon": s[5],
            "altitude_m": s[7] or s[13],  # baro_altitude or geo_altitude
            "velocity_ms": s[9],
            "heading": s[10],
            "vertical_rate": s[11],
            "on_ground": s[8],
            "squawk": s[14],
            "spi": s[15],
            "category": _aircraft_category(s[16] if len(s) > 16 else 0),
            "last_contact": s[4],
            "source": "opensky",
        })

    _aircraft_cache[cache_key] = {"data": aircraft, "ts": time.time()}
    return aircraft


def _aircraft_category(cat_code):
    """Map OpenSky category code to human-readable string."""
    categories = {
        0: "unknown",
        1: "no_info",
        2: "light",
        3: "small",
        4: "large",
        5: "high_vortex",
        6: "heavy",
        7: "high_perf",
        8: "rotorcraft",
        9: "glider",
        10: "lighter_than_air",
        11: "skydiver",
        12: "ultralight",
        14: "uav",
        15: "space",
        16: "surface_emergency",
        17: "surface_service",
        18: "point_obstacle",
        19: "cluster_obstacle",
        20: "line_obstacle",
    }
    return categories.get(cat_code, "unknown")


def _get_fallback_aircraft():
    """Return simulated aircraft data for when API is unavailable."""
    now = int(time.time())
    return [
        {
            "icao24": "a0b1c2", "callsign": "AAL1234",
            "origin_country": "United States", "lat": 35.95, "lon": -79.01,
            "altitude_m": 10668, "velocity_ms": 230, "heading": 45,
            "vertical_rate": 0, "on_ground": False, "squawk": "1200",
            "category": "large", "last_contact": now, "source": "fallback",
        },
        {
            "icao24": "d3e4f5", "callsign": "UAL567",
            "origin_country": "United States", "lat": 36.05, "lon": -78.95,
            "altitude_m": 11582, "velocity_ms": 245, "heading": 220,
            "vertical_rate": -2.5, "on_ground": False, "squawk": "4521",
            "category": "large", "last_contact": now, "source": "fallback",
        },
        {
            "icao24": "a1b2c3", "callsign": "N172SP",
            "origin_country": "United States", "lat": 35.88, "lon": -79.10,
            "altitude_m": 1524, "velocity_ms": 52, "heading": 180,
            "vertical_rate": 1.5, "on_ground": False, "squawk": "1200",
            "category": "light", "last_contact": now, "source": "fallback",
        },
    ]


# ---------------------------------------------------------------------------
# Aircraft Statistics
# ---------------------------------------------------------------------------

def get_aircraft_stats(aircraft_list):
    """Compute statistics for a list of aircraft."""
    if not aircraft_list:
        return {"count": 0}

    altitudes = [a["altitude_m"] for a in aircraft_list if a.get("altitude_m")]
    speeds = [a["velocity_ms"] for a in aircraft_list if a.get("velocity_ms")]
    countries = {}
    categories = {}

    for a in aircraft_list:
        c = a.get("origin_country", "unknown")
        countries[c] = countries.get(c, 0) + 1
        cat = a.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "count": len(aircraft_list),
        "altitude_range_m": [min(altitudes), max(altitudes)] if altitudes else [0, 0],
        "avg_altitude_m": round(sum(altitudes) / len(altitudes)) if altitudes else 0,
        "avg_speed_ms": round(sum(speeds) / len(speeds), 1) if speeds else 0,
        "countries": dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)),
        "categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
    }


# ---------------------------------------------------------------------------
# Global Aircraft Bounding Boxes
# ---------------------------------------------------------------------------

REGION_BOXES = {
    "chapel_hill": (34.5, -80.5, 37.0, -77.5),
    "us_east": (25.0, -90.0, 48.0, -65.0),
    "us_west": (25.0, -130.0, 50.0, -90.0),
    "europe": (35.0, -10.0, 60.0, 40.0),
    "east_asia": (20.0, 100.0, 50.0, 145.0),
    "global_sample": (-60.0, -180.0, 80.0, 180.0),
}


def fetch_regional_aircraft(region="chapel_hill"):
    """Fetch aircraft for a predefined region."""
    bbox = REGION_BOXES.get(region, REGION_BOXES["chapel_hill"])
    return fetch_aircraft(bbox=bbox)


def get_aircraft_geojson(aircraft_list):
    """Convert aircraft list to GeoJSON for map rendering."""
    features = []
    for a in aircraft_list:
        if not a.get("lat") or not a.get("lon"):
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [a["lon"], a["lat"]],
            },
            "properties": {
                "icao24": a.get("icao24", ""),
                "callsign": a.get("callsign", ""),
                "altitude_m": a.get("altitude_m", 0),
                "heading": a.get("heading", 0),
                "velocity_ms": a.get("velocity_ms", 0),
                "category": a.get("category", "unknown"),
                "origin_country": a.get("origin_country", ""),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
