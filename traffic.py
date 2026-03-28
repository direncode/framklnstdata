"""
==============================================
  FRANKLIN STREET PANOPTICON v2
  Live Foot Traffic Engine
==============================================
Fetches real-time busyness data from Google Places,
discovers venues via OpenStreetMap Overpass API,
pulls Chapel Hill GIS layers, and builds heat map data
for convergent foot traffic visualization.
"""

import json
import os
import time
import hashlib
from datetime import datetime, timedelta

import requests

from config import (
    CACHE_DIR,
    CACHE_TTL,
    GOOGLE_PLACES_API_KEY,
    OVERPASS_API_URL,
    CHAPEL_HILL_GIS_BASE,
    FRANKLIN_STREET_BOUNDS,
    FRANKLIN_STREET_SPINE,
    FRANKLIN_STREET_CENTER,
)

# ---------------------------------------------------------------------------
# Cache Layer
# ---------------------------------------------------------------------------

def _get_cache_path():
    """Ensure cache directory exists and return its path."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _cache_key(prefix, params=""):
    """Generate a cache filename from a prefix and optional params."""
    if params:
        h = hashlib.md5(params.encode()).hexdigest()[:8]
        return f"{prefix}_{h}.json"
    return f"{prefix}.json"


def _is_cache_valid(key, max_age_hours):
    """Check if a cached file exists and is fresh enough."""
    filepath = os.path.join(_get_cache_path(), key)
    if not os.path.exists(filepath):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    return (datetime.now() - mtime) < timedelta(hours=max_age_hours)


def _read_cache(key):
    """Read data from a cache file. Returns None if missing."""
    filepath = os.path.join(_get_cache_path(), key)
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_cache(key, data):
    """Write data to a cache file."""
    filepath = os.path.join(_get_cache_path(), key)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# OpenStreetMap Overpass API - Venue Discovery
# ---------------------------------------------------------------------------

def fetch_nearby_places(radius_meters=400):
    """
    Query OpenStreetMap Overpass API to discover bars, restaurants, cafes,
    and other amenities near Franklin Street. Completely free, no API key.

    Returns list of dicts: [{name, lat, lon, amenity_type}, ...]
    """
    cache_key = _cache_key("overpass_places")
    if _is_cache_valid(cache_key, CACHE_TTL["overpass"]):
        cached = _read_cache(cache_key)
        if cached:
            return cached

    lat, lon = FRANKLIN_STREET_CENTER
    query = f"""
    [out:json][timeout:30];
    (
      node["amenity"~"bar|restaurant|cafe|pub|fast_food|nightclub"]
        (around:{radius_meters},{lat},{lon});
      way["amenity"~"bar|restaurant|cafe|pub|fast_food|nightclub"]
        (around:{radius_meters},{lat},{lon});
    );
    out center;
    """

    try:
        resp = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [!] Overpass API error: {e}")
        return []

    places = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        # Get coordinates (nodes have lat/lon directly, ways have center)
        if element["type"] == "node":
            lat_e = element.get("lat")
            lon_e = element.get("lon")
        else:
            center = element.get("center", {})
            lat_e = center.get("lat")
            lon_e = center.get("lon")

        if lat_e and lon_e:
            places.append({
                "name": name,
                "lat": lat_e,
                "lon": lon_e,
                "amenity_type": tags.get("amenity", "unknown"),
                "osm_id": element.get("id"),
                "cuisine": tags.get("cuisine", ""),
                "opening_hours": tags.get("opening_hours", ""),
            })

    _write_cache(cache_key, places)
    print(f"  [+] Discovered {len(places)} venues via OpenStreetMap")
    return places


# ---------------------------------------------------------------------------
# Google Places Popular Times
# ---------------------------------------------------------------------------

# Curated fallback popular times for key Franklin Street venues
# Format: {venue_name_fragment: {day_index: [24 hourly busyness values 0-100]}}
# day_index: 0=Monday, 6=Sunday
# These represent typical patterns for college-town bars/restaurants

_EVENING_PEAK = [0, 0, 0, 0, 0, 0, 0, 5, 10, 15, 20, 30, 40, 35, 30, 25,
                 30, 45, 60, 75, 85, 90, 70, 40]
_LUNCH_PEAK = [0, 0, 0, 0, 0, 0, 0, 10, 25, 35, 40, 60, 75, 65, 45, 30,
               25, 30, 40, 50, 55, 45, 30, 15]
_BAR_LATE = [0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, 15, 20, 20, 15, 15,
             20, 30, 50, 70, 85, 95, 90, 60]
_COFFEE_MORNING = [0, 0, 0, 0, 0, 0, 10, 40, 70, 80, 65, 50, 55, 50, 40,
                   30, 25, 20, 15, 10, 5, 0, 0, 0]
_INTERSECTION = [0, 0, 0, 0, 0, 0, 5, 15, 35, 50, 55, 60, 65, 60, 55, 50,
                 55, 60, 55, 45, 35, 25, 15, 5]

# Weekend modifier: bars are busier on Thu-Sat
_WEEKEND_BOOST = 1.3
_WEEKDAY_NORMAL = 1.0

FALLBACK_POPULAR_TIMES = {
    "bandidos": {"pattern": _EVENING_PEAK, "type": "restaurant"},
    "topo": {"pattern": _EVENING_PEAK, "type": "bar"},
    "top of the hill": {"pattern": _EVENING_PEAK, "type": "bar"},
    "he's not here": {"pattern": _BAR_LATE, "type": "bar"},
    "linda's": {"pattern": _BAR_LATE, "type": "bar"},
    "carolina coffee": {"pattern": _COFFEE_MORNING, "type": "cafe"},
    "sutton": {"pattern": _LUNCH_PEAK, "type": "restaurant"},
    "alpine": {"pattern": _COFFEE_MORNING, "type": "cafe"},
    "varsity": {"pattern": _EVENING_PEAK, "type": "entertainment"},
    "target": {"pattern": _LUNCH_PEAK, "type": "retail"},
}


def _match_fallback_pattern(name):
    """Find the best matching fallback pattern for a venue name."""
    name_lower = name.lower()
    for key, data in FALLBACK_POPULAR_TIMES.items():
        if key in name_lower:
            return data["pattern"]
    # Default pattern based on common amenity type
    return _EVENING_PEAK


def _get_day_modifier(day_of_week):
    """Get busyness modifier based on day of week (0=Mon, 6=Sun)."""
    # Thu=3, Fri=4, Sat=5 are busier
    if day_of_week in (3, 4, 5):
        return _WEEKEND_BOOST
    return _WEEKDAY_NORMAL


def fetch_popular_times(place_name, place_id=None):
    """
    Get hourly busyness data for a venue.

    If GOOGLE_PLACES_API_KEY is set and populartimes is installed,
    fetches real data. Otherwise uses curated fallback patterns.

    Returns a list of 24 busyness values (0-100) for today,
    or None on complete failure.
    """
    # Try live data first
    if GOOGLE_PLACES_API_KEY and place_id:
        cache_key = _cache_key("popular_times", place_id)
        if _is_cache_valid(cache_key, CACHE_TTL["popular_times"]):
            cached = _read_cache(cache_key)
            if cached:
                return cached

        try:
            import populartimes
            result = populartimes.get_id(GOOGLE_PLACES_API_KEY, place_id)
            if result and "populartimes" in result:
                # populartimes returns data per day-of-week
                today = datetime.now().weekday()
                for day_data in result["populartimes"]:
                    if day_data["name"].lower() == [
                        "monday", "tuesday", "wednesday", "thursday",
                        "friday", "saturday", "sunday"
                    ][today].lower():
                        hourly = day_data["data"]
                        _write_cache(cache_key, hourly)
                        return hourly
        except ImportError:
            pass
        except Exception as e:
            print(f"  [!] Popular times API error for {place_name}: {e}")

    # Fallback to curated patterns
    pattern = _match_fallback_pattern(place_name)
    today = datetime.now().weekday()
    modifier = _get_day_modifier(today)
    return [min(100, int(v * modifier)) for v in pattern]


def get_current_busyness(place_name, place_id=None, hour=None):
    """
    Get the busyness score (0-100) for a venue at a specific hour.
    If hour is None, uses the current hour.
    """
    if hour is None:
        hour = datetime.now().hour

    hourly = fetch_popular_times(place_name, place_id)
    if hourly and 0 <= hour < 24:
        return hourly[hour]
    return 0


# ---------------------------------------------------------------------------
# Chapel Hill GIS Data
# ---------------------------------------------------------------------------

def fetch_chapel_hill_gis():
    """
    Pull pedestrian infrastructure data from Chapel Hill's ArcGIS open data.
    Returns GeoJSON features for sidewalks and pedestrian areas, or empty
    list on failure. This is supplementary context data.
    """
    cache_key = _cache_key("chapel_hill_gis")
    if _is_cache_valid(cache_key, CACHE_TTL["gis"]):
        cached = _read_cache(cache_key)
        if cached:
            return cached

    # Try the Chapel Hill sidewalks layer
    bounds = FRANKLIN_STREET_BOUNDS
    bbox = f"{bounds['west']},{bounds['south']},{bounds['east']},{bounds['north']}"

    endpoints = [
        # Sidewalks layer
        f"{CHAPEL_HILL_GIS_BASE}/Sidewalks/FeatureServer/0/query"
        f"?where=1%3D1&outFields=*&geometry={bbox}"
        f"&geometryType=esriGeometryEnvelope&inSR=4326&outSR=4326&f=geojson",
        # Pedestrian infrastructure
        f"{CHAPEL_HILL_GIS_BASE}/Pedestrian_Network/FeatureServer/0/query"
        f"?where=1%3D1&outFields=*&geometry={bbox}"
        f"&geometryType=esriGeometryEnvelope&inSR=4326&outSR=4326&f=geojson",
    ]

    features = []
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "features" in data:
                    features.extend(data["features"])
                    print(f"  [+] Got {len(data['features'])} GIS features")
        except Exception as e:
            print(f"  [!] Chapel Hill GIS error: {e}")
            continue

    if features:
        _write_cache(cache_key, features)

    return features


# ---------------------------------------------------------------------------
# NCDOT Traffic Data
# ---------------------------------------------------------------------------

# NCDOT AADT (Annual Average Daily Traffic) for roads near Franklin Street
# Source: NCDOT Traffic Volume Maps - these are public record
NCDOT_AADT_DATA = {
    "Franklin St (E of Columbia)": {"aadt": 12500, "year": 2023},
    "Franklin St (W of Columbia)": {"aadt": 14200, "year": 2023},
    "Columbia St (N of Franklin)": {"aadt": 8900, "year": 2023},
    "Columbia St (S of Franklin)": {"aadt": 10100, "year": 2023},
    "S Estes Dr (near University Place)": {"aadt": 15800, "year": 2023},
}


def get_ncdot_traffic():
    """Return NCDOT AADT data for roads near Franklin Street."""
    return NCDOT_AADT_DATA


# ---------------------------------------------------------------------------
# Heat Map Builder
# ---------------------------------------------------------------------------

def build_heatmap_data(spots, hour=None, day_of_week=None):
    """
    Build heat map data points for folium HeatMap visualization.

    Takes the spots list, gets busyness for each, then interpolates
    additional points along the Franklin Street spine to create a
    continuous heat corridor effect.

    Returns list of [lat, lon, weight] for folium.plugins.HeatMap.
    """
    if hour is None:
        hour = datetime.now().hour
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    heatmap_points = []

    # 1. Add actual venue points with their busyness
    spot_busyness = {}
    for spot in spots:
        busyness = get_current_busyness(
            spot["name"],
            spot.get("place_id"),
            hour=hour,
        )
        # Apply day-of-week modifier
        modifier = _get_day_modifier(day_of_week)
        busyness = min(100, int(busyness * modifier))

        spot_busyness[spot["name"]] = busyness

        # Add the spot itself
        weight = busyness / 100.0
        if weight > 0:
            heatmap_points.append([spot["lat"], spot["lon"], weight])

    # 2. Add discovered OSM venues with estimated busyness
    try:
        osm_places = fetch_nearby_places()
        for place in osm_places:
            busyness = get_current_busyness(place["name"], hour=hour)
            modifier = _get_day_modifier(day_of_week)
            busyness = min(100, int(busyness * modifier))
            weight = busyness / 100.0
            if weight > 0.05:  # Skip nearly-zero points
                heatmap_points.append([place["lat"], place["lon"], weight * 0.7])
    except Exception:
        pass  # OSM data is supplementary

    # 3. Interpolate along the Franklin Street spine for continuity
    if len(heatmap_points) >= 2:
        _interpolate_spine(heatmap_points, spots, spot_busyness)

    return heatmap_points


def _interpolate_spine(heatmap_points, spots, spot_busyness):
    """
    Add interpolated points along the Franklin Street spine
    between known venues for a continuous heat corridor.
    """
    for i in range(len(FRANKLIN_STREET_SPINE) - 1):
        lat1, lon1 = FRANKLIN_STREET_SPINE[i]
        lat2, lon2 = FRANKLIN_STREET_SPINE[i + 1]

        # Find nearest known spots to this segment for weight interpolation
        w1 = _nearest_spot_busyness(lat1, lon1, spots, spot_busyness)
        w2 = _nearest_spot_busyness(lat2, lon2, spots, spot_busyness)

        # Generate 5 intermediate points per segment
        for j in range(1, 6):
            t = j / 6.0
            lat_interp = lat1 + t * (lat2 - lat1)
            lon_interp = lon1 + t * (lon2 - lon1)
            weight_interp = (w1 + t * (w2 - w1)) / 100.0

            if weight_interp > 0.02:
                # Slight random-ish offset to avoid a perfect line
                lat_offset = ((j * 7) % 5 - 2) * 0.00003
                lon_offset = ((j * 11) % 5 - 2) * 0.00003
                heatmap_points.append([
                    lat_interp + lat_offset,
                    lon_interp + lon_offset,
                    weight_interp * 0.5,  # Interpolated points are fainter
                ])


def _nearest_spot_busyness(lat, lon, spots, spot_busyness):
    """Find the busyness of the nearest known spot to a given point."""
    best_dist = float("inf")
    best_busyness = 30  # Default ambient foot traffic

    for spot in spots:
        dist = abs(spot["lat"] - lat) + abs(spot["lon"] - lon)
        if dist < best_dist:
            best_dist = dist
            best_busyness = spot_busyness.get(spot["name"], 30)

    return best_busyness


# ---------------------------------------------------------------------------
# Aggregate Busyness for Spot Enrichment
# ---------------------------------------------------------------------------

def aggregate_busyness(spots, hour=None):
    """
    Enrich spots list with live busyness data.
    Adds 'live_busyness' (0-100) and 'hourly_profile' (24-element list)
    to each spot dict. Returns the enriched list.
    """
    if hour is None:
        hour = datetime.now().hour

    for spot in spots:
        # Get full 24-hour profile
        hourly = fetch_popular_times(spot["name"], spot.get("place_id"))
        spot["hourly_profile"] = hourly or [0] * 24

        # Get current busyness
        spot["live_busyness"] = get_current_busyness(
            spot["name"], spot.get("place_id"), hour=hour
        )

    return spots
