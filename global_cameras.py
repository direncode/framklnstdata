"""
==============================================
  FRANKLIN STREET DATA
  Global Surveillance Camera Intelligence
==============================================
Aggregates surveillance camera data from OpenStreetMap
(man_made=surveillance tags), public traffic camera feeds,
and FLOCK/ALPR databases. Computes fields of view,
coverage areas, and inter-agency sharing networks.

Inspired by:
  - Ringmast4r/FLOCK (336K+ cameras, Leaflet + OSM)
  - babastienne/PanoptiCity (CCTV FOV + OSM contribution)
  - peekdistrict (collaborative camera tracking)
"""

import json
import math
import time
import requests
from datetime import datetime

# Cache
_camera_cache = {}
_CACHE_TTL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# OpenStreetMap Camera Discovery (Global)
# ---------------------------------------------------------------------------

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_cameras_osm(bbox=None, limit=5000):
    """
    Fetch surveillance cameras from OpenStreetMap Overpass API.
    bbox: (south, west, north, east) or None for Franklin Street area.
    Returns list of camera dicts with lat, lon, type, operator, etc.
    """
    cache_key = f"osm_cameras_{bbox}"
    if cache_key in _camera_cache:
        entry = _camera_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    if bbox is None:
        bbox = (35.90, -79.07, 35.93, -79.04)  # Franklin Street area

    query = f"""
    [out:json][timeout:30];
    (
      node["man_made"="surveillance"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      node["amenity"="surveillance"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out body {limit};
    """

    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=35)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    cameras = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        cameras.append({
            "id": el["id"],
            "lat": el["lat"],
            "lon": el["lon"],
            "type": tags.get("surveillance:type", tags.get("surveillance", "unknown")),
            "zone": tags.get("surveillance:zone", "unknown"),
            "operator": tags.get("operator", "unknown"),
            "mount": tags.get("camera:mount", ""),
            "direction": _parse_direction(tags.get("camera:direction", "")),
            "brand": tags.get("brand", ""),
            "description": tags.get("description", ""),
            "indoor": tags.get("indoor", "no") == "yes",
            "source": "osm",
        })

    _camera_cache[cache_key] = {"data": cameras, "ts": time.time()}
    return cameras


def _parse_direction(direction_str):
    """Parse camera direction from OSM tag to degrees."""
    if not direction_str:
        return None
    try:
        return float(direction_str)
    except ValueError:
        compass = {
            "N": 0, "NE": 45, "E": 90, "SE": 135,
            "S": 180, "SW": 225, "W": 270, "NW": 315,
        }
        return compass.get(direction_str.upper())


# ---------------------------------------------------------------------------
# Public Traffic Camera Feeds
# ---------------------------------------------------------------------------

# Known public traffic camera endpoints (DOT feeds, etc.)
PUBLIC_TRAFFIC_CAMS = {
    "ncdot": {
        "name": "NC DOT Traffic Cameras",
        "url": "https://tims.ncdot.gov/tims/api/incidents/cameras",
        "region": "North Carolina",
        "type": "traffic",
    },
    "nycdot": {
        "name": "NYC DOT Traffic Cameras",
        "url": "https://webcams.nyctmc.org/api/cameras",
        "region": "New York City",
        "type": "traffic",
    },
}


def fetch_traffic_cameras(region="ncdot"):
    """Fetch public DOT traffic camera feeds."""
    cache_key = f"traffic_cams_{region}"
    if cache_key in _camera_cache:
        entry = _camera_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    config = PUBLIC_TRAFFIC_CAMS.get(region, {})
    if not config:
        return []

    try:
        resp = requests.get(config["url"], timeout=15, headers={
            "User-Agent": "FranklinStreetData/4.0"
        })
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _get_fallback_traffic_cams(region)

    cameras = []
    if isinstance(data, list):
        for cam in data[:500]:
            cameras.append({
                "id": cam.get("id", cam.get("cameraId", "")),
                "lat": cam.get("latitude", cam.get("lat", 0)),
                "lon": cam.get("longitude", cam.get("lon", cam.get("lng", 0))),
                "name": cam.get("name", cam.get("title", "Traffic Camera")),
                "feed_url": cam.get("imageUrl", cam.get("url", "")),
                "type": "traffic",
                "operator": config["name"],
                "region": config["region"],
                "source": "dot_feed",
            })

    _camera_cache[cache_key] = {"data": cameras, "ts": time.time()}
    return cameras


def _get_fallback_traffic_cams(region):
    """Fallback hardcoded traffic cameras near Chapel Hill."""
    if region == "ncdot":
        return [
            {"id": "nc-i40-ch1", "lat": 35.9265, "lon": -79.0395, "name": "I-40 at US 15-501",
             "type": "traffic", "operator": "NCDOT", "source": "fallback", "feed_url": ""},
            {"id": "nc-i40-ch2", "lat": 35.9186, "lon": -79.0075, "name": "I-40 at NC 86",
             "type": "traffic", "operator": "NCDOT", "source": "fallback", "feed_url": ""},
            {"id": "nc-us15-ch", "lat": 35.9052, "lon": -79.0478, "name": "US 15-501 at Fordham Blvd",
             "type": "traffic", "operator": "NCDOT", "source": "fallback", "feed_url": ""},
        ]
    return []


# ---------------------------------------------------------------------------
# FLOCK/ALPR Camera Database (Public Data)
# ---------------------------------------------------------------------------

# Known ALPR camera concentrations from public reporting
ALPR_NETWORKS = {
    "flock_safety": {
        "name": "Flock Safety ALPR Network",
        "description": "Automated License Plate Recognition cameras used by law enforcement",
        "estimated_count": 336000,
        "coverage": "United States",
        "data_sharing": True,
    },
}


def fetch_alpr_cameras_osm(bbox=None, limit=2000):
    """
    Fetch ALPR-tagged cameras from OSM.
    These are tagged as surveillance:type=ALPR or similar.
    """
    cache_key = f"alpr_cameras_{bbox}"
    if cache_key in _camera_cache:
        entry = _camera_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    if bbox is None:
        bbox = (35.85, -79.12, 35.97, -78.98)

    query = f"""
    [out:json][timeout:30];
    (
      node["man_made"="surveillance"]["surveillance:type"="ALPR"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      node["man_made"="surveillance"]["surveillance:type"="camera"]["surveillance"~"ALPR|LPR"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out body {limit};
    """

    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=35)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    cameras = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        cameras.append({
            "id": el["id"],
            "lat": el["lat"],
            "lon": el["lon"],
            "type": "ALPR",
            "operator": tags.get("operator", "unknown"),
            "network": tags.get("network", ""),
            "brand": tags.get("brand", ""),
            "source": "osm_alpr",
        })

    _camera_cache[cache_key] = {"data": cameras, "ts": time.time()}
    return cameras


# ---------------------------------------------------------------------------
# Field of View Computation (PanoptiCity-inspired)
# ---------------------------------------------------------------------------

def compute_camera_fov(camera, fov_angle=90, range_meters=50):
    """
    Compute the field of view polygon for a camera.
    Returns a list of [lon, lat] points forming the FOV triangle.

    camera: dict with lat, lon, direction (degrees from north)
    fov_angle: total FOV angle in degrees
    range_meters: how far the camera can see
    """
    direction = camera.get("direction")
    if direction is None:
        return None

    lat = camera["lat"]
    lon = camera["lon"]
    half_fov = fov_angle / 2

    # Convert range to approximate degrees
    lat_per_meter = 1.0 / 111320
    lon_per_meter = 1.0 / (111320 * math.cos(math.radians(lat)))

    points = [[lon, lat]]  # Camera position

    for angle_offset in range(-int(half_fov), int(half_fov) + 1, 5):
        angle_rad = math.radians(direction + angle_offset)
        dx = range_meters * math.sin(angle_rad) * lon_per_meter
        dy = range_meters * math.cos(angle_rad) * lat_per_meter
        points.append([lon + dx, lat + dy])

    points.append([lon, lat])  # Close polygon
    return points


def compute_coverage_area(cameras, grid_resolution=0.001):
    """
    Compute overall surveillance coverage percentage for an area.
    Returns coverage stats.
    """
    if not cameras:
        return {"coverage_pct": 0, "camera_count": 0, "types": {}}

    type_counts = {}
    for cam in cameras:
        ctype = cam.get("type", "unknown")
        type_counts[ctype] = type_counts.get(ctype, 0) + 1

    # Estimate coverage based on camera density
    lats = [c["lat"] for c in cameras if c.get("lat")]
    lons = [c["lon"] for c in cameras if c.get("lon")]

    if not lats or not lons:
        return {"coverage_pct": 0, "camera_count": len(cameras), "types": type_counts}

    area_km2 = (
        (max(lats) - min(lats)) * 111.32 *
        (max(lons) - min(lons)) * 111.32 * math.cos(math.radians(sum(lats) / len(lats)))
    )

    # Rough estimate: each camera covers ~2500 sq meters
    covered_km2 = len(cameras) * 0.0025
    coverage_pct = min(100, (covered_km2 / max(area_km2, 0.001)) * 100)

    return {
        "coverage_pct": round(coverage_pct, 1),
        "camera_count": len(cameras),
        "area_km2": round(area_km2, 3),
        "types": type_counts,
        "operators": list(set(c.get("operator", "unknown") for c in cameras)),
    }


# ---------------------------------------------------------------------------
# Combined Camera Intelligence
# ---------------------------------------------------------------------------

def get_all_cameras(bbox=None, include_traffic=True, include_alpr=True):
    """
    Aggregate all camera sources for a given area.
    Returns combined list + coverage stats.
    """
    all_cameras = []

    # OSM surveillance cameras
    osm_cams = fetch_cameras_osm(bbox=bbox)
    all_cameras.extend(osm_cams)

    # Traffic cameras
    if include_traffic:
        traffic_cams = fetch_traffic_cameras("ncdot")
        all_cameras.extend(traffic_cams)

    # ALPR cameras
    if include_alpr:
        alpr_cams = fetch_alpr_cameras_osm(bbox=bbox)
        all_cameras.extend(alpr_cams)

    # Compute FOV for cameras with direction data
    for cam in all_cameras:
        if cam.get("direction") is not None:
            cam["fov_polygon"] = compute_camera_fov(cam)

    coverage = compute_coverage_area(all_cameras)

    return {
        "cameras": all_cameras,
        "total_count": len(all_cameras),
        "coverage": coverage,
        "sources": {
            "osm": len(osm_cams),
            "traffic": len(all_cameras) - len(osm_cams) - len(alpr_cams) if include_traffic else 0,
            "alpr": len(alpr_cams) if include_alpr else 0,
        },
        "networks": ALPR_NETWORKS,
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Global Camera Hotspots (Major Metro Areas)
# ---------------------------------------------------------------------------

GLOBAL_CAMERA_HOTSPOTS = [
    {"city": "London", "lat": 51.5074, "lon": -0.1278, "estimated_cameras": 691000, "country": "UK"},
    {"city": "Beijing", "lat": 39.9042, "lon": 116.4074, "estimated_cameras": 1150000, "country": "CN"},
    {"city": "Shanghai", "lat": 31.2304, "lon": 121.4737, "estimated_cameras": 408000, "country": "CN"},
    {"city": "New York", "lat": 40.7128, "lon": -74.0060, "estimated_cameras": 70882, "country": "US"},
    {"city": "Delhi", "lat": 28.6139, "lon": 77.2090, "estimated_cameras": 179000, "country": "IN"},
    {"city": "Moscow", "lat": 55.7558, "lon": 37.6173, "estimated_cameras": 213000, "country": "RU"},
    {"city": "Singapore", "lat": 1.3521, "lon": 103.8198, "estimated_cameras": 108981, "country": "SG"},
    {"city": "Seoul", "lat": 37.5665, "lon": 126.9780, "estimated_cameras": 1169000, "country": "KR"},
    {"city": "Los Angeles", "lat": 34.0522, "lon": -118.2437, "estimated_cameras": 34959, "country": "US"},
    {"city": "Chicago", "lat": 41.8781, "lon": -87.6298, "estimated_cameras": 35000, "country": "US"},
    {"city": "Chapel Hill", "lat": 35.9132, "lon": -79.0555, "estimated_cameras": 450, "country": "US"},
]


def get_global_camera_stats():
    """Return global surveillance camera statistics and hotspot data."""
    return {
        "hotspots": GLOBAL_CAMERA_HOTSPOTS,
        "global_estimate": 770000000,
        "cameras_per_person_leaders": [
            {"country": "China", "ratio": "1:2.1"},
            {"country": "UK", "ratio": "1:6.5"},
            {"country": "US", "ratio": "1:4.6"},
            {"country": "South Korea", "ratio": "1:4.3"},
        ],
        "alpr_networks": ALPR_NETWORKS,
        "timestamp": datetime.now().isoformat(),
    }
