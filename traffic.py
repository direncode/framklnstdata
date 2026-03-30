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

def fetch_nearby_places(radius_meters=None):
    """
    Query OpenStreetMap Overpass API to discover ALL venues across
    Chapel Hill — bars, restaurants, cafes, shops, entertainment,
    services, and more. Completely free, no API key.

    Covers the full Chapel Hill bounding box (~16 km²).
    Extracts comprehensive metadata per venue.

    Returns list of dicts with rich metadata per venue.
    """
    from config import CHAPEL_HILL_BOUNDS

    cache_key = _cache_key("overpass_chapel_hill_full")
    if _is_cache_valid(cache_key, CACHE_TTL["overpass"]):
        cached = _read_cache(cache_key)
        if cached:
            return cached

    bbox = CHAPEL_HILL_BOUNDS
    s, n, w, e = bbox["south"], bbox["north"], bbox["west"], bbox["east"]

    # Comprehensive Overpass query covering all venue categories
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"~"bar|restaurant|cafe|pub|fast_food|nightclub|food_court|ice_cream|biergarten|brewery|wine_bar"]({s},{w},{n},{e});
      way["amenity"~"bar|restaurant|cafe|pub|fast_food|nightclub|food_court|ice_cream|biergarten|brewery|wine_bar"]({s},{w},{n},{e});
      node["amenity"~"cinema|theatre|arts_centre|community_centre|events_venue|music_venue|nightclub|casino|bowling_alley"]({s},{w},{n},{e});
      way["amenity"~"cinema|theatre|arts_centre|community_centre|events_venue|music_venue|nightclub|casino|bowling_alley"]({s},{w},{n},{e});
      node["amenity"~"pharmacy|bank|atm|post_office|library|marketplace|fuel|car_wash|dentist|doctors|clinic|hospital|veterinary"]({s},{w},{n},{e});
      way["amenity"~"pharmacy|bank|atm|post_office|library|marketplace|fuel|car_wash|dentist|doctors|clinic|hospital|veterinary"]({s},{w},{n},{e});
      node["shop"~"supermarket|convenience|clothes|books|electronics|hardware|florist|bakery|butcher|deli|greengrocer|beauty|hairdresser|tattoo|bicycle|sports|outdoor|gift|jewelry|optician|department_store|mall|music|alcohol|tobacco|coffee|tea|pastry|chocolate|cheese"]({s},{w},{n},{e});
      way["shop"~"supermarket|convenience|clothes|books|electronics|hardware|florist|bakery|butcher|deli|greengrocer|beauty|hairdresser|tattoo|bicycle|sports|outdoor|gift|jewelry|optician|department_store|mall|music|alcohol|tobacco|coffee|tea|pastry|chocolate|cheese"]({s},{w},{n},{e});
      node["leisure"~"fitness_centre|sports_centre|swimming_pool|bowling_alley|escape_game|amusement_arcade|dance|park|garden"]({s},{w},{n},{e});
      way["leisure"~"fitness_centre|sports_centre|swimming_pool|bowling_alley|escape_game|amusement_arcade|dance|park|garden"]({s},{w},{n},{e});
      node["tourism"~"hotel|motel|guest_house|hostel|museum|gallery|attraction|viewpoint|information"]({s},{w},{n},{e});
      way["tourism"~"hotel|motel|guest_house|hostel|museum|gallery|attraction|viewpoint|information"]({s},{w},{n},{e});
    );
    out center tags;
    """

    try:
        resp = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [!] Overpass API error: {e}")
        # Fall back to cached data even if expired
        cached = _read_cache(cache_key)
        if cached:
            print(f"  [+] Using stale cache ({len(cached)} venues)")
            return cached
        return []

    places = []
    seen_ids = set()
    for element in data.get("elements", []):
        osm_id = element.get("id")
        if osm_id in seen_ids:
            continue
        seen_ids.add(osm_id)

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

        if not lat_e or not lon_e:
            continue

        # Determine primary category
        amenity = tags.get("amenity", "")
        shop = tags.get("shop", "")
        leisure = tags.get("leisure", "")
        tourism = tags.get("tourism", "")
        primary_type = amenity or shop or leisure or tourism or "unknown"

        # Build comprehensive address
        addr_parts = []
        if tags.get("addr:housenumber"):
            addr_parts.append(tags["addr:housenumber"])
        if tags.get("addr:street"):
            addr_parts.append(tags["addr:street"])
        address = " ".join(addr_parts) if addr_parts else ""
        if tags.get("addr:city"):
            address += f", {tags['addr:city']}" if address else tags["addr:city"]

        places.append({
            "name": name,
            "lat": lat_e,
            "lon": lon_e,
            "amenity_type": primary_type,
            "osm_id": osm_id,
            # Contact & web
            "phone": tags.get("phone", tags.get("contact:phone", "")),
            "website": tags.get("website", tags.get("contact:website", "")),
            "email": tags.get("email", tags.get("contact:email", "")),
            # Address
            "address": address,
            "addr_street": tags.get("addr:street", ""),
            "addr_housenumber": tags.get("addr:housenumber", ""),
            "addr_postcode": tags.get("addr:postcode", ""),
            # Food & drink specifics
            "cuisine": tags.get("cuisine", ""),
            "diet_vegan": tags.get("diet:vegan", ""),
            "diet_vegetarian": tags.get("diet:vegetarian", ""),
            "takeaway": tags.get("takeaway", ""),
            "delivery": tags.get("delivery", ""),
            "outdoor_seating": tags.get("outdoor_seating", ""),
            # Hours & access
            "opening_hours": tags.get("opening_hours", ""),
            "wheelchair": tags.get("wheelchair", ""),
            "internet_access": tags.get("internet_access", ""),
            # Brand & chain
            "brand": tags.get("brand", ""),
            "operator": tags.get("operator", ""),
            # Descriptive
            "description": tags.get("description", ""),
            "wikipedia": tags.get("wikipedia", ""),
            "wikidata": tags.get("wikidata", ""),
            # Category tags
            "category": _classify_venue(primary_type),
        })

    _write_cache(cache_key, places)
    print(f"  [+] Discovered {len(places)} venues across Chapel Hill via OpenStreetMap")
    return places


def _classify_venue(amenity_type):
    """Classify venue into broad category for filtering and display."""
    food_drink = {"bar", "restaurant", "cafe", "pub", "fast_food", "nightclub",
                  "food_court", "ice_cream", "biergarten", "brewery", "wine_bar",
                  "bakery", "butcher", "deli", "greengrocer", "pastry",
                  "chocolate", "cheese", "coffee", "tea", "alcohol"}
    entertainment = {"cinema", "theatre", "arts_centre", "community_centre",
                     "events_venue", "music_venue", "casino", "bowling_alley",
                     "escape_game", "amusement_arcade", "dance", "museum",
                     "gallery", "attraction"}
    shopping = {"supermarket", "convenience", "clothes", "books", "electronics",
                "hardware", "florist", "beauty", "hairdresser", "tattoo",
                "bicycle", "sports", "outdoor", "gift", "jewelry", "optician",
                "department_store", "mall", "music", "tobacco"}
    fitness = {"fitness_centre", "sports_centre", "swimming_pool", "park", "garden"}
    lodging = {"hotel", "motel", "guest_house", "hostel"}
    services = {"pharmacy", "bank", "atm", "post_office", "library",
                "marketplace", "fuel", "car_wash", "dentist", "doctors",
                "clinic", "hospital", "veterinary"}

    t = amenity_type.lower()
    if t in food_drink:
        return "food_drink"
    if t in entertainment:
        return "entertainment"
    if t in shopping:
        return "shopping"
    if t in fitness:
        return "fitness"
    if t in lodging:
        return "lodging"
    if t in services:
        return "services"
    return "other"


# ---------------------------------------------------------------------------
# Google Places — Venue Search + Live Busyness
# ---------------------------------------------------------------------------

def search_places_nearby(lat, lon, radius=500):
    """
    Search for places near a location via Google Places Nearby Search.
    Returns dict of {place_id: {name, lat, lon, rating, ...}} or None.
    """
    if not GOOGLE_PLACES_API_KEY:
        return None

    cache_key = _cache_key("places_search", f"{lat}_{lon}_{radius}")
    if _is_cache_valid(cache_key, CACHE_TTL["popular_times"]):
        cached = _read_cache(cache_key)
        if cached:
            return cached

    all_results = {}

    # Search multiple types to get broader coverage
    for place_type in ["bar", "restaurant", "cafe", "night_club"]:
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lon}&radius={radius}"
            f"&type={place_type}"
            f"&key={GOOGLE_PLACES_API_KEY}"
        )

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for place in data.get("results", []):
                pid = place.get("place_id")
                if pid and pid not in all_results:
                    all_results[pid] = {
                        "place_id": pid,
                        "name": place.get("name", ""),
                        "lat": place["geometry"]["location"]["lat"],
                        "lon": place["geometry"]["location"]["lng"],
                        "types": place.get("types", []),
                        "rating": place.get("rating"),
                        "user_ratings_total": place.get("user_ratings_total", 0),
                        "price_level": place.get("price_level"),
                        "business_status": place.get("business_status", ""),
                    }
        except Exception as e:
            print(f"  [!] Places Search error ({place_type}): {e}")

    if all_results:
        _write_cache(cache_key, all_results)
        print(f"  [+] Google Places: {len(all_results)} venues found")

    return all_results if all_results else None


# Backward compat alias
search_places_busyness = search_places_nearby


def fetch_place_busyness(place_id):
    """
    Fetch live busyness for a specific place via Google Places API v1 (New).
    The new API returns populartimes data when available.
    Returns dict with current_busyness (0-100) and hourly_profile, or None.
    """
    if not GOOGLE_PLACES_API_KEY or not place_id:
        return None

    cache_key = _cache_key("busyness", place_id)
    if _is_cache_valid(cache_key, 1):  # 1 hour cache
        cached = _read_cache(cache_key)
        if cached:
            return cached

    # Try Places API v1 (New) which can return popularity data
    url = "https://places.googleapis.com/v1/places/" + place_id
    headers = {
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "displayName,currentOpeningHours,regularOpeningHours",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # The v1 API doesn't reliably return busyness either,
            # but we confirm the place exists and is operational
            result = {
                "place_id": place_id,
                "name": data.get("displayName", {}).get("text", ""),
                "verified": True,
            }
            _write_cache(cache_key, result)
            return result
    except Exception as e:
        print(f"  [!] Places v1 error for {place_id}: {e}")

    return None


def get_current_busyness(place_name, place_id=None, hour=None):
    """Legacy stub — busyness now comes from BTUT MFG engine."""
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
    Build heat map from BTUT density field or venue busyness data.

    Primary: Uses the Fokker-Planck density field ρ(x,t) from the BTUT
    Mean-Field Game engine for a continuous traffic corridor.

    Fallback: Per-venue interpolation along the street spine.

    Returns list of [lat, lon, weight] for folium.plugins.HeatMap.
    """
    if hour is None:
        hour = datetime.now().hour

    # Heatmap = venue busyness at venue locations
    # Only show venues with meaningful busyness (>15%) to avoid visual noise
    # Square the weight to make the heatmap more punishing — 50% shows as 25% heat
    heatmap_points = []

    for spot in spots:
        busyness = spot.get("busyness")
        if busyness is not None and busyness > 15:
            weight = (busyness / 100.0) ** 1.5  # Exponential curve punishes low scores
            heatmap_points.append([spot["lat"], spot["lon"], weight])

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
    """Legacy stub — busyness now comes from BTUT MFG engine."""
    return spots
