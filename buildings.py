"""
==============================================
  FRANKLIN STREET DATA
  3D Building Footprints & Structure Layer
==============================================
Fetches building footprints from OpenStreetMap,
computes viewshed-like visibility analysis, and
provides 3D extrusion data for pydeck visualization.
"""

import json
import os
import math
from datetime import datetime

import requests

from config import (
    CACHE_DIR,
    OVERPASS_API_URL,
    FRANKLIN_STREET_CENTER,
    FRANKLIN_STREET_BOUNDS,
)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_path():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _cache_age_hours(key):
    fp = os.path.join(_cache_path(), f"{key}.json")
    if not os.path.exists(fp):
        return float("inf")
    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
    return (datetime.now() - mtime).total_seconds() / 3600


def _read_cache(key):
    try:
        with open(os.path.join(_cache_path(), f"{key}.json")) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_cache(key, data):
    with open(os.path.join(_cache_path(), f"{key}.json"), "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# Building Footprint Fetch (OpenStreetMap)
# ---------------------------------------------------------------------------

def fetch_building_footprints(radius_meters=500):
    """
    Fetch building footprints from OpenStreetMap Overpass API.
    Returns list of building dicts with polygon coordinates,
    height, name, and type.
    """
    cache_key = "buildings_osm"
    if _cache_age_hours(cache_key) < 720:  # 30 day cache
        cached = _read_cache(cache_key)
        if cached:
            return cached

    lat, lon = FRANKLIN_STREET_CENTER
    query = f"""
    [out:json][timeout:30];
    (
      way["building"]
        (around:{radius_meters},{lat},{lon});
    );
    out body;
    >;
    out skel qt;
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
        print(f"  [!] Building footprints error: {e}")
        return _fallback_buildings()

    # Collect all nodes first
    nodes = {}
    for el in data.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = (el["lat"], el["lon"])

    # Build polygons from ways
    buildings = []
    for el in data.get("elements", []):
        if el["type"] != "way":
            continue
        tags = el.get("tags", {})
        if "building" not in tags:
            continue

        way_nodes = el.get("nodes", [])
        polygon = []
        for nid in way_nodes:
            if nid in nodes:
                polygon.append(list(nodes[nid]))

        if len(polygon) < 3:
            continue

        # Parse height (OSM uses meters, defaults vary)
        height = _parse_height(tags)
        levels = _parse_levels(tags)

        buildings.append({
            "id": el["id"],
            "name": tags.get("name", ""),
            "building_type": tags.get("building", "yes"),
            "amenity": tags.get("amenity", ""),
            "height_m": height,
            "levels": levels,
            "polygon": polygon,
            "centroid": _centroid(polygon),
        })

    _write_cache(cache_key, buildings)
    print(f"  [+] Building footprints: {len(buildings)} buildings")
    return buildings


def _parse_height(tags):
    """Parse building height from OSM tags."""
    if "height" in tags:
        try:
            h = tags["height"].replace("m", "").replace(" ", "")
            return float(h)
        except ValueError:
            pass
    if "building:levels" in tags:
        try:
            return int(tags["building:levels"]) * 3.5
        except ValueError:
            pass
    # Defaults by type
    defaults = {
        "commercial": 12, "retail": 8, "apartments": 15,
        "residential": 9, "university": 14, "church": 18,
        "parking": 10, "industrial": 8,
    }
    btype = tags.get("building", "yes")
    return defaults.get(btype, 10)


def _parse_levels(tags):
    """Parse building levels from OSM tags."""
    if "building:levels" in tags:
        try:
            return int(tags["building:levels"])
        except ValueError:
            pass
    return 3


def _centroid(polygon):
    """Compute centroid of a polygon."""
    if not polygon:
        return [0, 0]
    avg_lat = sum(p[0] for p in polygon) / len(polygon)
    avg_lon = sum(p[1] for p in polygon) / len(polygon)
    return [avg_lat, avg_lon]


def _fallback_buildings():
    """No fallback — return empty if OSM fetch fails."""
    return []


# ---------------------------------------------------------------------------
# pydeck 3D Building Data
# ---------------------------------------------------------------------------

def buildings_to_pydeck(buildings=None, busyness_map=None):
    """
    Convert building footprints to pydeck PolygonLayer format.
    Optionally color/extrude by nearby venue busyness.

    Returns list of dicts with 'polygon', 'height', 'color' for pydeck.
    """
    if buildings is None:
        buildings = fetch_building_footprints()

    pydeck_data = []
    for bldg in buildings:
        polygon = bldg.get("polygon", [])
        if len(polygon) < 3:
            continue

        height = bldg.get("height_m", 10)
        name = bldg.get("name", "")

        # Color by busyness if available
        if busyness_map and name:
            busyness = busyness_map.get(name, 0)
            color = _busyness_color(busyness)
        else:
            btype = bldg.get("building_type", "yes")
            color = _building_color(btype)

        # Convert polygon to [lon, lat] format for pydeck
        pydeck_polygon = [[p[1], p[0]] for p in polygon]

        pydeck_data.append({
            "polygon": pydeck_polygon,
            "height": height,
            "color": color,
            "name": name,
            "building_type": bldg.get("building_type", ""),
            "levels": bldg.get("levels", 0),
        })

    return pydeck_data


def _building_color(btype):
    """Color buildings by type."""
    colors = {
        "commercial": [100, 150, 255, 180],
        "retail": [100, 200, 150, 180],
        "residential": [180, 180, 200, 140],
        "apartments": [160, 160, 200, 150],
        "university": [255, 200, 100, 180],
        "church": [200, 150, 255, 180],
        "parking": [120, 120, 120, 120],
    }
    return colors.get(btype, [150, 150, 180, 140])


def _busyness_color(busyness):
    """Color buildings by busyness level (0-100)."""
    if busyness >= 80:
        return [255, 50, 50, 220]
    elif busyness >= 60:
        return [255, 150, 0, 200]
    elif busyness >= 40:
        return [255, 255, 0, 180]
    elif busyness >= 20:
        return [100, 200, 100, 160]
    else:
        return [100, 100, 200, 140]


# ---------------------------------------------------------------------------
# Viewshed Analysis (Simplified)
# ---------------------------------------------------------------------------

def compute_viewshed(observer_lat, observer_lon, buildings=None, max_range_m=200):
    """
    Simplified viewshed analysis: from an observer point, determine
    which directions have clear sight lines vs. blocked by buildings.

    Returns 360 boolean values (one per degree) indicating visibility.
    True = visible (can see a flyer from this direction).
    """
    if buildings is None:
        buildings = fetch_building_footprints()

    visibility = [True] * 360

    for bldg in buildings:
        centroid = bldg.get("centroid", [0, 0])
        # Distance to building
        dist = _haversine_m(observer_lat, observer_lon, centroid[0], centroid[1])

        if dist > max_range_m or dist < 5:
            continue

        # Bearing to building
        bearing = _bearing(observer_lat, observer_lon, centroid[0], centroid[1])

        # Angular width of building (approximate from polygon extent)
        polygon = bldg.get("polygon", [])
        if len(polygon) < 3:
            continue

        angular_width = _angular_width(
            observer_lat, observer_lon, polygon, dist
        )

        # Block visibility in that arc
        half_width = int(angular_width / 2) + 1
        for offset in range(-half_width, half_width + 1):
            angle = (bearing + offset) % 360
            visibility[angle] = False

    visible_degrees = sum(1 for v in visibility if v)
    return {
        "visibility_map": visibility,
        "visible_degrees": visible_degrees,
        "blocked_degrees": 360 - visible_degrees,
        "visibility_pct": round(visible_degrees / 360 * 100, 1),
        "observer": [observer_lat, observer_lon],
    }


def _haversine_m(lat1, lon1, lat2, lon2):
    """Haversine distance in meters."""
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _bearing(lat1, lon1, lat2, lon2):
    """Bearing in degrees from point 1 to point 2."""
    dlon = math.radians(lon2 - lon1)
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon)
    return int(math.degrees(math.atan2(x, y))) % 360


def _angular_width(obs_lat, obs_lon, polygon, dist):
    """Approximate angular width of a polygon from observer."""
    bearings = []
    for p in polygon:
        b = _bearing(obs_lat, obs_lon, p[0], p[1])
        bearings.append(b)
    if not bearings:
        return 0
    # Handle wrap-around
    bearings.sort()
    max_gap = 0
    for i in range(len(bearings) - 1):
        gap = bearings[i + 1] - bearings[i]
        max_gap = max(max_gap, gap)
    wrap_gap = 360 - bearings[-1] + bearings[0]
    max_gap = max(max_gap, wrap_gap)
    return 360 - max_gap


def compute_viewshed_for_spots(spots, buildings=None):
    """Compute viewshed for all spots. Returns visibility percentages."""
    if buildings is None:
        buildings = fetch_building_footprints()

    results = []
    for spot in spots:
        vs = compute_viewshed(spot["lat"], spot["lon"], buildings)
        results.append({
            "spot_name": spot["name"],
            "spot_id": spot["id"],
            "visibility_pct": vs["visibility_pct"],
            "visible_degrees": vs["visible_degrees"],
        })

    results.sort(key=lambda r: r["visibility_pct"], reverse=True)
    return results
