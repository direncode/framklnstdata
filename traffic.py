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

def fetch_popular_times(place_name, place_id=None):
    """
    Get hourly busyness data for a venue via Google Places API.
    Requires GOOGLE_PLACES_API_KEY env var and populartimes library.
    Returns a list of 24 busyness values (0-100) or None.
    """
    if not GOOGLE_PLACES_API_KEY or not place_id:
        return None

    cache_key = _cache_key("popular_times", place_id)
    if _is_cache_valid(cache_key, CACHE_TTL["popular_times"]):
        cached = _read_cache(cache_key)
        if cached:
            return cached

    try:
        import populartimes
        result = populartimes.get_id(GOOGLE_PLACES_API_KEY, place_id)
        if result and "populartimes" in result:
            today = datetime.now().weekday()
            day_names = [
                "monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday",
            ]
            for day_data in result["populartimes"]:
                if day_data["name"].lower() == day_names[today]:
                    hourly = day_data["data"]
                    _write_cache(cache_key, hourly)
                    return hourly
    except ImportError:
        print("  [!] populartimes not installed. Run: pip install populartimes")
    except Exception as e:
        print(f"  [!] Popular times API error for {place_name}: {e}")

    return None


def get_current_busyness(place_name, place_id=None, hour=None):
    """
    Get the busyness score (0-100) for a venue at a specific hour.
    Returns None if no live data available.
    """
    if hour is None:
        hour = datetime.now().hour

    hourly = fetch_popular_times(place_name, place_id)
    if hourly and 0 <= hour < 24:
        return hourly[hour]
    return None


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

def get_ncdot_traffic():
    """
    Fetch NCDOT AADT data from their ArcGIS REST service.
    Returns dict of road segments with traffic counts, or None.
    """
    cache_key = _cache_key("ncdot_aadt")
    if _is_cache_valid(cache_key, 720):  # 30 day cache
        cached = _read_cache(cache_key)
        if cached:
            return cached

    bounds = FRANKLIN_STREET_BOUNDS
    bbox = f"{bounds['west']},{bounds['south']},{bounds['east']},{bounds['north']}"

    url = (
        "https://services.ncdot.gov/arcgis/rest/services/"
        "NCDOT_AADT/MapServer/0/query"
        f"?geometry={bbox}"
        f"&geometryType=esriGeometryEnvelope&inSR=4326&outSR=4326"
        f"&outFields=ROUTE,AADT,AADT_YEAR,ROAD_NAME"
        f"&where=1%3D1&f=json"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = {}
        for feature in data.get("features", []):
            attrs = feature.get("attributes", {})
            name = attrs.get("ROAD_NAME", attrs.get("ROUTE", "Unknown"))
            aadt = attrs.get("AADT")
            year = attrs.get("AADT_YEAR")
            if name and aadt:
                results[name] = {"aadt": int(aadt), "year": int(year) if year else None}

        if results:
            _write_cache(cache_key, results)
            print(f"  [+] NCDOT: {len(results)} road segments with AADT data")
            return results
    except Exception as e:
        print(f"  [!] NCDOT AADT error: {e}")

    return None


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

    # 1. Add venue points with live busyness (if available)
    spot_busyness = {}
    has_live_data = False
    for spot in spots:
        busyness = get_current_busyness(
            spot["name"],
            spot.get("place_id"),
            hour=hour,
        )
        if busyness is not None:
            has_live_data = True
            spot_busyness[spot["name"]] = busyness
            weight = busyness / 100.0
            if weight > 0:
                heatmap_points.append([spot["lat"], spot["lon"], weight])
        else:
            # Use static foot_traffic score as weight proxy (from spots.py)
            ft = spot.get("foot_traffic", 5)
            spot_busyness[spot["name"]] = ft * 10
            heatmap_points.append([spot["lat"], spot["lon"], ft / 10.0])

    # 2. Add discovered OSM venues as points (uniform weight — no fake busyness)
    try:
        osm_places = fetch_nearby_places()
        for place in osm_places:
            # OSM venues get a base weight — we know they exist, not how busy
            heatmap_points.append([place["lat"], place["lon"], 0.3])
    except Exception:
        pass

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
    best_busyness = 0

    for spot in spots:
        dist = abs(spot["lat"] - lat) + abs(spot["lon"] - lon)
        if dist < best_dist:
            best_dist = dist
            best_busyness = spot_busyness.get(spot["name"], 0)

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
        # Get full 24-hour profile (None if no API key)
        hourly = fetch_popular_times(spot["name"], spot.get("place_id"))
        spot["hourly_profile"] = hourly  # None if unavailable

        # Get current busyness (None if no API key)
        spot["live_busyness"] = get_current_busyness(
            spot["name"], spot.get("place_id"), hour=hour
        )

    return spots
