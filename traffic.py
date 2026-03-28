"""
==============================================
  FRANKLIN STREET DATA
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
    Build heat map from venue busyness data.

    Simple and honest:
    1. Each venue with live busyness (Google Places) → point with real weight
    2. Each OSM-discovered venue → point (we know it exists, weight = existence)
    3. Linear interpolation between venues along the street spine
       so the heat map shows a corridor, not isolated blobs

    When Google Places API is unavailable, the heat map only shows
    venue locations (existence) not busyness intensity.

    Returns list of [lat, lon, weight] for folium.plugins.HeatMap.
    """
    if hour is None:
        hour = datetime.now().hour

    heatmap_points = []
    venue_weights = {}  # {(lat, lon): weight} for interpolation

    # 1. Curated spots — use live busyness if available, else just mark location
    for spot in spots:
        busyness = get_current_busyness(
            spot["name"], spot.get("place_id"), hour=hour,
        )
        if busyness is not None:
            # Real data from Google Places API
            weight = busyness / 100.0
        else:
            # No busyness data — just mark that a venue exists here
            weight = 0.3
        venue_weights[(spot["lat"], spot["lon"])] = weight
        heatmap_points.append([spot["lat"], spot["lon"], weight])

    # 2. OSM-discovered venues — existence signal only
    try:
        osm_places = fetch_nearby_places()
        for place in osm_places:
            # We know a venue is here. That's all we know.
            venue_weights[(place["lat"], place["lon"])] = 0.2
            heatmap_points.append([place["lat"], place["lon"], 0.2])
    except Exception:
        pass

    # 3. Interpolate along the Franklin Street spine
    #    Linear blend between nearest venue weights on each side.
    #    This creates a continuous corridor instead of isolated dots.
    for i in range(len(FRANKLIN_STREET_SPINE) - 1):
        lat1, lon1 = FRANKLIN_STREET_SPINE[i]
        lat2, lon2 = FRANKLIN_STREET_SPINE[i + 1]

        w1 = _nearest_weight(lat1, lon1, venue_weights)
        w2 = _nearest_weight(lat2, lon2, venue_weights)

        # 4 intermediate points per segment, linearly blended
        for j in range(1, 5):
            t = j / 5.0
            lat_mid = lat1 + t * (lat2 - lat1)
            lon_mid = lon1 + t * (lon2 - lon1)
            weight_mid = w1 + t * (w2 - w1)
            if weight_mid > 0.05:
                heatmap_points.append([lat_mid, lon_mid, weight_mid * 0.6])

    return heatmap_points


def _nearest_weight(lat, lon, venue_weights):
    """Find the weight of the nearest venue to a point."""
    best_dist = float("inf")
    best_weight = 0
    for (vlat, vlon), weight in venue_weights.items():
        dist = abs(vlat - lat) + abs(vlon - lon)
        if dist < best_dist:
            best_dist = dist
            best_weight = weight
    return best_weight


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
