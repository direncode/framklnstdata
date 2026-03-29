"""
==============================================
  FRANKLIN STREET DATA
  Live OSINT Module
==============================================
All data is API-fetched. No hardcoded fake data.

Sources:
  - Chapel Hill Transit GTFS (public, free)
  - Chapel Hill Open Data / ArcGIS (public, free)
  - NC ABC Commission (public records, scraped)
  - Reddit API (public, free via JSON endpoint)
"""

import json
import os
import math
import csv
import io
from datetime import datetime, timedelta
from collections import defaultdict

import requests

from config import (
    CACHE_DIR,
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
# Chapel Hill Transit GTFS (Live)
# ---------------------------------------------------------------------------

def fetch_transit_stops():
    """
    Fetch bus/transit stops in Chapel Hill via OpenStreetMap Overpass API.
    No API key needed, no GTFS ZIP download.
    Returns list of stop dicts or None.
    """
    cached = _read_cache("transit_stops", max_age_hours=720)
    if cached:
        return cached

    # Use Overpass API to get bus stops in Chapel Hill area
    query = """
    [out:json][timeout:30];
    (
      node["highway"="bus_stop"](35.880,-79.110,35.960,-79.010);
      node["public_transport"="stop_position"](35.880,-79.110,35.960,-79.010);
      node["public_transport"="platform"](35.880,-79.110,35.960,-79.010);
    );
    out;
    """

    try:
        from config import OVERPASS_API_URL
        resp = requests.post(OVERPASS_API_URL, data={"data": query}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        stops = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            stops.append({
                "stop_id": str(element.get("id", "")),
                "stop_name": tags.get("name", tags.get("ref", f"Stop {element.get('id', '')}")),
                "lat": element.get("lat"),
                "lon": element.get("lon"),
            })

        if stops:
            _write_cache("transit_stops", stops)
            print(f"  [+] Transit: {len(stops)} bus stops via OSM")
        return stops if stops else None

    except Exception as e:
        print(f"  [!] Transit stops error: {e}")
        return None


# ---------------------------------------------------------------------------
# Chapel Hill Open Data - Crime/Incidents (Live)
# ---------------------------------------------------------------------------

def fetch_crime_data():
    """
    Fetch crime/incident data from Chapel Hill's ArcGIS open data portal.
    Returns list of incident dicts or None.
    """
    cached = _read_cache("crime_incidents", max_age_hours=24)
    if cached:
        return cached

    # Chapel Hill publishes incident data via ArcGIS (full Chapel Hill area)
    url = (
        "https://services1.arcgis.com/jOyGkcqHAywMxJEv/arcgis/rest/services"
        "/Police_Incidents/FeatureServer/0/query"
        "?where=1%3D1&outFields=*"
        "&geometry=-79.110,35.880,-79.010,35.960"
        "&geometryType=esriGeometryEnvelope&inSR=4326&outSR=4326&spatialRel=esriSpatialRelIntersects"
        "&resultRecordCount=200&f=json"
    )

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        incidents = []
        for feature in data.get("features", []):
            attrs = feature.get("attributes", {})
            geom = feature.get("geometry", {})
            incidents.append({
                "type": attrs.get("OFFENSE_DESCRIPTION", attrs.get("offense_description", "")),
                "date": attrs.get("DATE_REPORTED", attrs.get("date_reported", "")),
                "location": attrs.get("LOCATION", attrs.get("location", "")),
                "lat": geom.get("y"),
                "lon": geom.get("x"),
            })

        if incidents:
            _write_cache("crime_incidents", incidents)
            print(f"  [+] Crime data: {len(incidents)} incidents")
        return incidents if incidents else None

    except Exception as e:
        print(f"  [!] Crime data error: {e}")
        return None


# ---------------------------------------------------------------------------
# Reddit - UNC/Chapel Hill Live Feed
# ---------------------------------------------------------------------------

def fetch_reddit_posts(subreddit="UNC", limit=25):
    """
    Fetch recent posts from r/UNC and r/chapelhill via Reddit JSON API.
    No API key needed — uses public .json endpoint.
    Returns list of post dicts or None.
    """
    cache_key = f"reddit_{subreddit}"
    cached = _read_cache(cache_key, max_age_hours=0.5)
    if cached:
        return cached

    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "FranklinStDataBot/1.0 (academic research tool)",
        })
        resp.raise_for_status()
        data = resp.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            posts.append({
                "title": post.get("title", ""),
                "subreddit": post.get("subreddit", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "created_utc": post.get("created_utc", 0),
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "flair": post.get("link_flair_text", ""),
                "selftext": (post.get("selftext", "") or "")[:300],
            })

        if posts:
            _write_cache(cache_key, posts)
            print(f"  [+] Reddit r/{subreddit}: {len(posts)} posts")
        return posts if posts else None

    except Exception as e:
        print(f"  [!] Reddit r/{subreddit} error: {e}")
        return None


def fetch_all_reddit():
    """Fetch from multiple UNC/Chapel Hill subreddits."""
    results = {}
    for sub in ["UNC", "chapelhill", "NorthCarolina"]:
        posts = fetch_reddit_posts(sub)
        if posts:
            results[sub] = posts
    return results if results else None


# ---------------------------------------------------------------------------
# NC ABC License Lookup (Live)
# ---------------------------------------------------------------------------

def fetch_abc_licenses():
    """
    Search NC ABC Commission permit database for Franklin Street venues.
    The NC ABC publishes permit data that can be queried.
    Returns list of license dicts or None.
    """
    cached = _read_cache("abc_licenses", max_age_hours=720)
    if cached:
        return cached

    # NC ABC permit search API
    url = (
        "https://abc.nc.gov/Permits/SearchResults"
        "?City=Chapel+Hill&County=ORANGE&PermitType=&Status=Active"
    )

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "FranklinStDataBot/1.0 (academic research tool)",
        })
        if resp.status_code != 200:
            return None

        # Parse HTML table (simple extraction)
        text = resp.text
        licenses = []

        # Look for table rows with permit data
        import re
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.DOTALL)
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 4:
                name = re.sub(r'<[^>]+>', '', cells[0]).strip()
                address = re.sub(r'<[^>]+>', '', cells[1]).strip()
                permit_type = re.sub(r'<[^>]+>', '', cells[2]).strip()
                status = re.sub(r'<[^>]+>', '', cells[3]).strip()

                if name and "franklin" in address.lower():
                    licenses.append({
                        "name": name,
                        "address": address,
                        "permit_type": permit_type,
                        "status": status,
                    })

        if licenses:
            _write_cache("abc_licenses", licenses)
            print(f"  [+] ABC Licenses: {len(licenses)} on Franklin St")
        return licenses if licenses else None

    except Exception as e:
        print(f"  [!] ABC license lookup error: {e}")
        return None


# ---------------------------------------------------------------------------
# Pedestrian Count from Live Sources
# ---------------------------------------------------------------------------

def estimate_pedestrian_flow(hour=None, day_of_week=None):
    """
    Estimate pedestrian flow using live transit data as a base signal.
    If no transit data available, returns None instead of fake numbers.
    """
    if hour is None:
        hour = datetime.now().hour
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    stops = fetch_transit_stops()
    if not stops:
        return None

    # Use number of nearby stops as a proxy for transit accessibility
    stop_count = len(stops)

    return {
        "hour": hour,
        "day_of_week": day_of_week,
        "nearby_transit_stops": stop_count,
        "data_source": "Chapel Hill Transit GTFS (live)",
        "note": "Transit stop density used as pedestrian flow proxy",
        "fetched_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Combined Deep OSINT Report
# ---------------------------------------------------------------------------

def build_deep_osint_report():
    """Build OSINT report from live sources only. None = data unavailable."""
    return {
        "reddit": fetch_all_reddit(),
        "transit_stops": fetch_transit_stops(),
        "crime_data": fetch_crime_data(),
        "abc_licenses": fetch_abc_licenses(),
        "pedestrian_estimate": estimate_pedestrian_flow(),
        "data_sources": {
            "reddit": "live (no key needed)",
            "transit": "live GTFS (no key needed)",
            "crime": "live ArcGIS (no key needed)",
            "abc_licenses": "live NC ABC (no key needed)",
        },
        "generated_at": datetime.now().isoformat(),
    }
