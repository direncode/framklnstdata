"""
==============================================
  FRANKLIN STREET DATA
  Street-Level Imagery Intelligence
==============================================
Integrates with open street-level imagery sources:
  - Mapillary (Meta) — crowdsourced street-level photos
  - KartaView (OpenStreetCam) — crowdsourced driving imagery
  - OpenStreetMap photo links

Inspired by:
  - tjhorner/streetlens (self-hosted panorama viewer)
  - sparkyniner/Netryx (street-level geolocation)

Provides panoramic photo links, coverage maps, and
image-based venue intelligence for the dashboard.
"""

import time
import math
import requests
from datetime import datetime

# Cache
_imagery_cache = {}
_CACHE_TTL = 1800  # 30 minutes


# ---------------------------------------------------------------------------
# Mapillary API (v4)
# ---------------------------------------------------------------------------

MAPILLARY_API = "https://graph.mapillary.com"
MAPILLARY_TILES = "https://tiles.mapillary.com"


def fetch_mapillary_images(bbox=None, limit=100, access_token=None):
    """
    Fetch street-level images from Mapillary within a bounding box.
    Requires a Mapillary access token (free to obtain).

    Returns list of image metadata dicts.
    """
    cache_key = f"mapillary_{bbox}_{limit}"
    if cache_key in _imagery_cache:
        entry = _imagery_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    if bbox is None:
        bbox = (-79.065, 35.908, -79.043, 35.923)  # Franklin Street

    if not access_token:
        # Return coverage estimate without actual images
        return _get_mapillary_coverage_estimate(bbox)

    try:
        resp = requests.get(
            f"{MAPILLARY_API}/images",
            params={
                "access_token": access_token,
                "fields": "id,captured_at,compass_angle,geometry,is_pano,thumb_1024_url,sequence",
                "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
                "limit": limit,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _get_mapillary_coverage_estimate(bbox)

    images = []
    for img in data.get("data", []):
        geom = img.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        images.append({
            "id": img["id"],
            "lat": coords[1],
            "lon": coords[0],
            "captured_at": img.get("captured_at"),
            "compass_angle": img.get("compass_angle"),
            "is_panorama": img.get("is_pano", False),
            "thumb_url": img.get("thumb_1024_url", ""),
            "viewer_url": f"https://www.mapillary.com/app/?pKey={img['id']}",
            "sequence_id": img.get("sequence"),
            "source": "mapillary",
        })

    _imagery_cache[cache_key] = {"data": images, "ts": time.time()}
    return images


def _get_mapillary_coverage_estimate(bbox):
    """Estimate Mapillary coverage for an area without API key."""
    # Mapillary has good coverage in most US college towns
    return [{
        "id": "coverage_estimate",
        "coverage": "high",
        "estimated_images": 5000,
        "note": "Set MAPILLARY_ACCESS_TOKEN for actual image data",
        "viewer_url": f"https://www.mapillary.com/app/?lat={35.9132}&lng={-79.0555}&z=16",
        "source": "mapillary_estimate",
        "bbox": list(bbox) if bbox else [],
    }]


# ---------------------------------------------------------------------------
# Mapillary Vector Tiles (Coverage Visualization)
# ---------------------------------------------------------------------------

def get_mapillary_tile_sources():
    """
    Get Mapillary vector tile source URLs for MapLibre.
    These show coverage lines/points on the map without needing an API key.
    """
    return {
        "mapillary_sequences": {
            "type": "vector",
            "tiles": [
                "https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=MLY|0000000000000000|0000000000000000000000000000000000"
            ],
            "minzoom": 6,
            "maxzoom": 14,
            "description": "Mapillary sequence coverage lines",
        },
        "mapillary_images": {
            "type": "vector",
            "tiles": [
                "https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=MLY|0000000000000000|0000000000000000000000000000000000"
            ],
            "minzoom": 14,
            "maxzoom": 17,
            "description": "Mapillary image point locations",
        },
    }


# ---------------------------------------------------------------------------
# KartaView (OpenStreetCam)
# ---------------------------------------------------------------------------

KARTAVIEW_API = "https://api.openstreetcam.org/2.0"


def fetch_kartaview_images(bbox=None, limit=100):
    """
    Fetch street-level photos from KartaView/OpenStreetCam.
    No API key required.
    """
    cache_key = f"kartaview_{bbox}_{limit}"
    if cache_key in _imagery_cache:
        entry = _imagery_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    if bbox is None:
        bbox = (-79.065, 35.908, -79.043, 35.923)

    try:
        resp = requests.post(
            f"{KARTAVIEW_API}/photo/",
            data={
                "bbTopLeft": f"{bbox[3]},{bbox[0]}",
                "bbBottomRight": f"{bbox[1]},{bbox[2]}",
                "page": 1,
                "itemsPerPage": limit,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    images = []
    for photo in data.get("result", {}).get("data", []):
        images.append({
            "id": photo.get("id"),
            "lat": float(photo.get("lat", 0)),
            "lon": float(photo.get("lng", 0)),
            "captured_at": photo.get("shot_date"),
            "compass_angle": float(photo.get("heading", 0)),
            "sequence_id": photo.get("sequence_id"),
            "thumb_url": photo.get("lth_name", ""),
            "source": "kartaview",
        })

    _imagery_cache[cache_key] = {"data": images, "ts": time.time()}
    return images


# ---------------------------------------------------------------------------
# OSM Photo-Linked Features
# ---------------------------------------------------------------------------

def fetch_osm_photos(bbox=None, limit=200):
    """
    Fetch OSM features with photo/image/panorama tags.
    """
    cache_key = f"osm_photos_{bbox}"
    if cache_key in _imagery_cache:
        entry = _imagery_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    if bbox is None:
        bbox = (35.908, -79.065, 35.923, -79.043)

    query = f"""
    [out:json][timeout:25];
    (
      node["image"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      node["wikimedia_commons"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["image"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out body {limit};
    """

    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    photos = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if not lat or not lon:
            continue

        photos.append({
            "id": el["id"],
            "lat": lat,
            "lon": lon,
            "name": tags.get("name", ""),
            "image_url": tags.get("image", ""),
            "wikimedia": tags.get("wikimedia_commons", ""),
            "source": "osm_photo",
        })

    _imagery_cache[cache_key] = {"data": photos, "ts": time.time()}
    return photos


# ---------------------------------------------------------------------------
# Street Imagery Coverage Analysis
# ---------------------------------------------------------------------------

def get_street_imagery_coverage(bbox=None):
    """
    Analyze street-level imagery coverage for an area.
    Combines all sources and returns coverage statistics.
    """
    if bbox is None:
        bbox = (-79.065, 35.908, -79.043, 35.923)

    mapillary = fetch_mapillary_images(bbox=bbox)
    kartaview = fetch_kartaview_images(bbox=bbox)
    osm_photos = fetch_osm_photos(bbox=(bbox[1], bbox[0], bbox[3], bbox[2]))

    return {
        "sources": {
            "mapillary": {
                "count": len(mapillary),
                "viewer_url": f"https://www.mapillary.com/app/?lat={35.9132}&lng={-79.0555}&z=16",
            },
            "kartaview": {
                "count": len(kartaview),
                "viewer_url": "https://kartaview.org/map/",
            },
            "osm_photos": {
                "count": len(osm_photos),
            },
        },
        "total_images": len(mapillary) + len(kartaview) + len(osm_photos),
        "bbox": list(bbox),
        "recommendation": "Use Mapillary viewer for best street-level panoramic experience",
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Panorama Viewer URLs
# ---------------------------------------------------------------------------

def get_panorama_url(lat, lon, source="mapillary"):
    """Get a URL to view street-level imagery at a given location."""
    if source == "mapillary":
        return f"https://www.mapillary.com/app/?lat={lat}&lng={lon}&z=17"
    elif source == "kartaview":
        return f"https://kartaview.org/map/@{lat},{lon},17z"
    elif source == "google":
        return f"https://www.google.com/maps/@{lat},{lon},3a,75y,0h,90t/data=!3m6!1e1!3m4!1s!2e0!7i!8i"
    return None
