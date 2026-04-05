"""
==============================================
  FRANKLIN STREET DATA
  Satellite Orbit Tracking
==============================================
Tracks real satellite positions using Two-Line Element (TLE)
data from CelesTrak. Computes ground tracks, visibility,
and overhead passes for the surveillance dashboard.

Data sources:
  - CelesTrak (https://celestrak.org) - Free TLE data
  - Space-Track.org (NORAD catalog, requires account)

Implements simplified SGP4-like propagation for browser
display without requiring the full sgp4 library.
"""

import math
import time
import requests
from datetime import datetime, timezone

# Cache
_tle_cache = {}
_CACHE_TTL = 3600  # 1 hour (TLEs update every few hours)


# ---------------------------------------------------------------------------
# CelesTrak TLE Fetching
# ---------------------------------------------------------------------------

CELESTRAK_BASE = "https://celestrak.org/NORAD/elements/gp.php"

# Key satellite categories
TLE_CATEGORIES = {
    "stations": "stations",           # ISS, Tiangong
    "visual": "visual",               # Brightest satellites
    "starlink": "supplemental/starlink",  # SpaceX Starlink
    "gps": "gps-ops",                 # GPS constellation
    "weather": "weather",             # Weather satellites
    "earth_resources": "resource",    # Earth observation
    "geodetic": "geodetic",           # Geodetic satellites
    "military": "military",           # Military satellites (public TLEs)
    "reconnaissance": "tle-new",      # Recently launched (often recon)
}

# Notable satellites to always track
NOTABLE_SATELLITES = {
    "ISS": 25544,
    "TIANGONG": 48274,
    "HUBBLE": 20580,
    "TERRA": 25994,
    "LANDSAT 9": 49260,
    "SENTINEL-2A": 40697,
    "GOES-16": 41866,
    "NOAA-20": 43013,
}


def fetch_tle_data(category="stations", format="json"):
    """
    Fetch TLE data from CelesTrak.
    Returns list of satellite dicts with orbital elements.
    """
    cache_key = f"tle_{category}"
    if cache_key in _tle_cache:
        entry = _tle_cache[cache_key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    cat_path = TLE_CATEGORIES.get(category, category)

    try:
        url = f"{CELESTRAK_BASE}?GROUP={cat_path}&FORMAT=json"
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "FranklinStreetData/4.0"
        })
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _get_fallback_satellites(category)

    satellites = []
    for sat in data:
        satellites.append({
            "norad_id": sat.get("NORAD_CAT_ID"),
            "name": sat.get("OBJECT_NAME", "UNKNOWN"),
            "epoch": sat.get("EPOCH"),
            "mean_motion": sat.get("MEAN_MOTION"),
            "eccentricity": sat.get("ECCENTRICITY"),
            "inclination": sat.get("INCLINATION"),
            "ra_of_asc_node": sat.get("RA_OF_ASC_NODE"),
            "arg_of_pericenter": sat.get("ARG_OF_PERICENTER"),
            "mean_anomaly": sat.get("MEAN_ANOMALY"),
            "period_min": 1440.0 / sat.get("MEAN_MOTION", 14.0) if sat.get("MEAN_MOTION") else None,
            "apogee_km": sat.get("APOAPSIS"),
            "perigee_km": sat.get("PERIAPSIS"),
            "object_type": sat.get("OBJECT_TYPE", "PAYLOAD"),
            "country": sat.get("COUNTRY_CODE", ""),
            "launch_date": sat.get("LAUNCH_DATE"),
            "decay_date": sat.get("DECAY_DATE"),
            "category": category,
        })

    _tle_cache[cache_key] = {"data": satellites, "ts": time.time()}
    return satellites


def _get_fallback_satellites(category):
    """Return hardcoded satellite data when CelesTrak is unreachable."""
    now = datetime.now(timezone.utc)
    return [
        {
            "norad_id": 25544, "name": "ISS (ZARYA)",
            "epoch": now.isoformat(),
            "mean_motion": 15.49, "eccentricity": 0.0002,
            "inclination": 51.64, "ra_of_asc_node": 180.0,
            "arg_of_pericenter": 90.0, "mean_anomaly": 270.0,
            "period_min": 92.9, "apogee_km": 422, "perigee_km": 420,
            "object_type": "PAYLOAD", "country": "ISS",
            "launch_date": "1998-11-20", "category": category,
        },
        {
            "norad_id": 48274, "name": "CSS (TIANHE)",
            "epoch": now.isoformat(),
            "mean_motion": 15.60, "eccentricity": 0.0003,
            "inclination": 41.47, "ra_of_asc_node": 200.0,
            "arg_of_pericenter": 85.0, "mean_anomaly": 275.0,
            "period_min": 92.3, "apogee_km": 390, "perigee_km": 385,
            "object_type": "PAYLOAD", "country": "PRC",
            "launch_date": "2021-04-29", "category": category,
        },
    ]


# ---------------------------------------------------------------------------
# Simplified Satellite Position Propagation
# ---------------------------------------------------------------------------

def propagate_satellite(sat, time_offset_min=0):
    """
    Simplified satellite position computation from TLE orbital elements.
    Returns approximate (lat, lon, alt_km) at current time + offset.

    This is a simplified circular orbit approximation, not full SGP4.
    Good enough for visualization purposes.
    """
    try:
        mean_motion = sat.get("mean_motion", 15.0)  # rev/day
        inclination = math.radians(sat.get("inclination", 51.6))
        raan = math.radians(sat.get("ra_of_asc_node", 0))
        mean_anomaly = math.radians(sat.get("mean_anomaly", 0))
        arg_peri = math.radians(sat.get("arg_of_pericenter", 0))

        # Orbital period in minutes
        period_min = 1440.0 / mean_motion if mean_motion > 0 else 90.0

        # Semi-major axis (km) from period
        mu = 398600.4418  # Earth GM (km³/s²)
        period_sec = period_min * 60
        a = (mu * (period_sec / (2 * math.pi)) ** 2) ** (1 / 3)

        # Current mean anomaly
        elapsed_min = time_offset_min
        n = 2 * math.pi / period_min  # rad/min
        M = mean_anomaly + n * elapsed_min

        # Approximate true anomaly (for near-circular orbits, M ≈ ν)
        E = M  # Eccentric anomaly ≈ mean anomaly for low e
        nu = E  # True anomaly

        # Position in orbital plane
        r = a  # Circular approximation
        u = arg_peri + nu  # Argument of latitude

        # Transform to Earth-fixed coordinates
        # Account for Earth rotation
        earth_rotation_rate = 2 * math.pi / (23 * 60 + 56)  # rad/min (sidereal)
        gmst = earth_rotation_rate * elapsed_min

        x = r * (math.cos(raan - gmst) * math.cos(u) - math.sin(raan - gmst) * math.sin(u) * math.cos(inclination))
        y = r * (math.sin(raan - gmst) * math.cos(u) + math.cos(raan - gmst) * math.sin(u) * math.cos(inclination))
        z = r * math.sin(u) * math.sin(inclination)

        # Convert to lat/lon
        lon = math.degrees(math.atan2(y, x))
        lat = math.degrees(math.asin(z / r))
        alt_km = a - 6371.0  # Approximate altitude

        return {
            "lat": round(lat, 4),
            "lon": round(lon % 360 - 180, 4),  # Normalize to -180..180
            "alt_km": round(max(0, alt_km), 1),
        }
    except Exception:
        return {"lat": 0, "lon": 0, "alt_km": 400}


def compute_ground_track(sat, duration_min=90, step_min=1):
    """
    Compute the ground track of a satellite over a time period.
    Returns list of {lat, lon, alt_km, time_offset_min}.
    """
    track = []
    for t in range(0, int(duration_min), int(step_min)):
        pos = propagate_satellite(sat, time_offset_min=t)
        pos["time_offset_min"] = t
        track.append(pos)
    return track


def get_overhead_satellites(observer_lat=35.9132, observer_lon=-79.0555, max_elevation=90):
    """
    Find satellites currently overhead (or near overhead) for a given location.
    Returns list of satellites with approximate elevation angles.
    """
    # Fetch stations + visual satellites
    sats = fetch_tle_data("stations") + fetch_tle_data("visual")

    overhead = []
    for sat in sats:
        pos = propagate_satellite(sat)
        if pos["lat"] == 0 and pos["lon"] == 0:
            continue

        # Approximate elevation angle
        dlat = math.radians(pos["lat"] - observer_lat)
        dlon = math.radians(pos["lon"] - observer_lon)
        dist_deg = math.sqrt(dlat**2 + (dlon * math.cos(math.radians(observer_lat)))**2)
        dist_km = dist_deg * 111.32

        if dist_km < 2000:  # Within ~2000km ground range
            # Simplified elevation angle
            alt_km = pos.get("alt_km", 400)
            elev = math.degrees(math.atan2(alt_km, dist_km))

            overhead.append({
                "name": sat["name"],
                "norad_id": sat["norad_id"],
                "lat": pos["lat"],
                "lon": pos["lon"],
                "alt_km": pos["alt_km"],
                "elevation_deg": round(elev, 1),
                "distance_km": round(dist_km, 1),
                "category": sat.get("category", ""),
            })

    return sorted(overhead, key=lambda x: x["elevation_deg"], reverse=True)


# ---------------------------------------------------------------------------
# Satellite Constellation Data
# ---------------------------------------------------------------------------

def get_constellation_stats():
    """Get stats for major satellite constellations."""
    return {
        "constellations": [
            {"name": "Starlink", "operator": "SpaceX", "count": 6000, "orbit_km": 550,
             "purpose": "Internet", "country": "US"},
            {"name": "GPS", "operator": "US Space Force", "count": 31, "orbit_km": 20200,
             "purpose": "Navigation", "country": "US"},
            {"name": "GLONASS", "operator": "Roscosmos", "count": 24, "orbit_km": 19100,
             "purpose": "Navigation", "country": "RU"},
            {"name": "Galileo", "operator": "ESA", "count": 28, "orbit_km": 23222,
             "purpose": "Navigation", "country": "EU"},
            {"name": "BeiDou", "operator": "CNSA", "count": 35, "orbit_km": 21528,
             "purpose": "Navigation", "country": "CN"},
            {"name": "Iridium NEXT", "operator": "Iridium", "count": 66, "orbit_km": 780,
             "purpose": "Communications", "country": "US"},
            {"name": "OneWeb", "operator": "OneWeb", "count": 634, "orbit_km": 1200,
             "purpose": "Internet", "country": "UK"},
            {"name": "Planet Labs", "operator": "Planet", "count": 200, "orbit_km": 475,
             "purpose": "Earth Imaging", "country": "US"},
            {"name": "WorldView Legion", "operator": "Maxar", "count": 6, "orbit_km": 500,
             "purpose": "High-Res Imaging", "country": "US"},
        ],
        "total_active": 10500,
        "total_tracked": 30000,
        "debris_tracked": 36500,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_satellite_geojson(satellites):
    """Convert satellite list to GeoJSON for map rendering."""
    features = []
    for sat in satellites:
        pos = propagate_satellite(sat)
        if pos["lat"] == 0 and pos["lon"] == 0:
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [pos["lon"], pos["lat"]],
            },
            "properties": {
                "name": sat["name"],
                "norad_id": sat.get("norad_id"),
                "alt_km": pos["alt_km"],
                "inclination": sat.get("inclination"),
                "period_min": sat.get("period_min"),
                "category": sat.get("category", ""),
                "country": sat.get("country", ""),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
