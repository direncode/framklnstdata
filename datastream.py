#!/usr/bin/env python3
"""
==============================================
  FRANKLIN STREET DATA
  Physical Data API (Datastream)
==============================================

A REST API that serves the entire Franklin Street Data intelligence
as consumable JSON endpoints. Designed for physical data
interpretation — decision-makers can query real-time
foot traffic, venue intelligence, trend signals, and
combined analysis programmatically.

Run:
  python datastream.py                  # Starts on port 8765
  python datastream.py --port 9000      # Custom port

Endpoints:
  GET /                                 # API overview + docs
  GET /status                           # System health + data freshness
  GET /spots                            # All ranked spots with live scores
  GET /spots/<id>                       # Single spot deep dive
  GET /traffic?hour=21&day=friday       # Traffic analysis at specific time
  GET /heatmap?hour=21&day=friday       # Heat map data points (GeoJSON)
  GET /venues                           # All discovered OSM venues
  GET /trends                           # Current trending topics + suggestions
  GET /intel                            # Full OSINT intelligence briefing
  GET /intel/demographics               # Census demographics
  GET /intel/weather                    # Current weather + impact
  GET /intel/events                     # Event context + multipliers
  GET /network                          # Street network analysis
  GET /network/intersections            # Key intersections
  GET /report                           # Full combined text report
  GET /export                           # Complete data export (all feeds)
"""

import json
import copy
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from config import FRANKLIN_STREET_CENTER, FRANKLIN_STREET_BOUNDS
from spots import get_enriched_spots, discover_venues
from traffic import (
    build_heatmap_data,
    fetch_nearby_places,
    get_ncdot_traffic,
    aggregate_busyness,
    get_current_busyness,
    fetch_popular_times,
)
from trends import (
    build_trends_report,
    generate_trivia_suggestions,
)
from intel import (
    build_intel_report,
    fetch_demographics,
    fetch_weather,
    fetch_unc_events,
)
from spatial import build_spatial_analysis
from buildings import fetch_building_footprints, compute_viewshed_for_spots
from osint import (
    build_deep_osint_report,
    fetch_crime_data,
    fetch_transit_stops,
    fetch_abc_licenses,
    fetch_all_reddit,
    estimate_pedestrian_flow,
)
from forecast import build_forecast_report
from livefeed import build_live_feed
from network import (
    fetch_street_network,
    find_intersections,
    compute_walk_scores,
    get_network_lines,
)
from main import generate_report

# Version
API_VERSION = "3.0.0"
API_NAME = "Franklin Street Data Datastream"


# ---------------------------------------------------------------------------
# Helper: Parse day name to weekday int
# ---------------------------------------------------------------------------

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}


def _parse_day(day_str):
    if day_str is None:
        return datetime.now().weekday()
    return DAY_MAP.get(day_str.lower(), datetime.now().weekday())


def _parse_hour(hour_str):
    if hour_str is None:
        return datetime.now().hour
    try:
        return max(0, min(23, int(hour_str)))
    except ValueError:
        return datetime.now().hour


# ---------------------------------------------------------------------------
# API Route Handlers
# ---------------------------------------------------------------------------

def handle_root():
    """API overview and documentation."""
    return {
        "name": API_NAME,
        "version": API_VERSION,
        "description": (
            "Surveillance-grade intelligence API for Franklin Street, "
            "UNC Chapel Hill. Provides real-time foot traffic analysis, "
            "venue intelligence, trend signals, demographic data, and "
            "combined actionable reports."
        ),
        "center": {
            "lat": FRANKLIN_STREET_CENTER[0],
            "lon": FRANKLIN_STREET_CENTER[1],
        },
        "bounds": FRANKLIN_STREET_BOUNDS,
        "endpoints": {
            "/status": "System health and data feed status",
            "/spots": "All ranked spots with live busyness scores",
            "/spots/<id>": "Single spot deep intelligence dive",
            "/traffic": "Traffic analysis (params: hour, day)",
            "/heatmap": "Heat map GeoJSON (params: hour, day)",
            "/venues": "All discovered OSM venues near Franklin St",
            "/trends": "Current trending topics and trivia suggestions",
            "/intel": "Full OSINT intelligence briefing",
            "/intel/demographics": "Census demographic data",
            "/intel/weather": "Current weather and flyering impact",
            "/intel/events": "Event context and traffic multipliers",
            "/network": "Street network topology analysis",
            "/network/intersections": "Key intersections with connectivity scores",
            "/report": "Full combined text report",
            "/export": "Complete data export (all feeds combined)",
        },
        "timestamp": datetime.now().isoformat(),
    }


def handle_status():
    """System health and data source status."""
    from config import GOOGLE_PLACES_API_KEY
    import os

    return {
        "status": "operational",
        "version": API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "data_feeds": {
            "google_places": "active" if GOOGLE_PLACES_API_KEY else "no_key",
            "openstreetmap": "active",
            "ncdot_aadt": "active",
            "census": "active",
            "weather": "active" if os.environ.get("OPENWEATHER_API_KEY") else "no_key",
            "google_trends": "available",
            "street_network": "active",
        },
        "surveillance_area": {
            "center": list(FRANKLIN_STREET_CENTER),
            "radius_meters": 400,
            "venue_source": "OpenStreetMap Overpass API",
        },
    }


def handle_spots(params):
    """All ranked spots with live busyness."""
    hour = _parse_hour(params.get("hour", [None])[0])
    day = params.get("day", [None])[0]
    tod = params.get("time", ["evening"])[0]
    n = int(params.get("n", ["10"])[0])

    spots = get_enriched_spots(time_of_day=tod, hour=hour, top_n=n)

    return {
        "query": {"hour": hour, "time_of_day": tod, "count": n},
        "spots": [
            {
                "rank": i + 1,
                "id": s["id"],
                "name": s["name"],
                "lat": s["lat"],
                "lon": s["lon"],
                "address": s["address"],
                "place_type": s.get("place_type"),
                "composite_score": s["composite_score"],
                "live_busyness": s.get("live_busyness", None),
                "hourly_profile": s.get("hourly_profile", None),
                "metrics": {
                    "foot_traffic": s["foot_traffic"],
                    "dwell_time": s["dwell_time"],
                    "visibility": s["visibility"],
                    "student_density": s["student_density"],
                },
                "best_times": s["best_times"],
                "rationale": s["rationale"],
                "placement_tip": s["placement_tip"],
            }
            for i, s in enumerate(spots)
        ],
        "timestamp": datetime.now().isoformat(),
    }


def handle_spot_detail(spot_id, params):
    """Single spot deep dive."""
    hour = _parse_hour(params.get("hour", [None])[0])

    spots = get_enriched_spots(hour=hour, top_n=100)
    spots = aggregate_busyness(spots, hour=hour)

    spot = next((s for s in spots if s["id"] == spot_id), None)
    if not spot:
        return {"error": f"Spot ID {spot_id} not found", "valid_ids": list(range(1, 11))}

    return {
        "spot": {
            "id": spot["id"],
            "name": spot["name"],
            "lat": spot["lat"],
            "lon": spot["lon"],
            "address": spot["address"],
            "place_type": spot.get("place_type"),
            "place_id": spot.get("place_id"),
            "live_busyness": spot.get("live_busyness"),
            "hourly_profile": spot.get("hourly_profile"),
            "metrics": {
                "foot_traffic": spot["foot_traffic"],
                "dwell_time": spot["dwell_time"],
                "visibility": spot["visibility"],
                "student_density": spot["student_density"],
            },
            "best_times": spot["best_times"],
            "rationale": spot["rationale"],
            "placement_tip": spot["placement_tip"],
        },
        "timestamp": datetime.now().isoformat(),
    }


def handle_traffic(params):
    """Traffic analysis for a specific time."""
    hour = _parse_hour(params.get("hour", [None])[0])
    day = _parse_day(params.get("day", [None])[0])

    spots = get_enriched_spots(hour=hour, top_n=100)
    spots = aggregate_busyness(spots, hour=hour)

    event = get_event_context()
    ncdot = get_ncdot_traffic()

    return {
        "query": {"hour": hour, "day_of_week": day},
        "venues": [
            {
                "name": s["name"],
                "busyness": s.get("live_busyness", 0),
                "hourly_profile": s.get("hourly_profile"),
                "lat": s["lat"],
                "lon": s["lon"],
            }
            for s in spots
        ],
        "event_context": {
            "type": event["event_type"],
            "traffic_multiplier": event["traffic_multiplier"],
        },
        "ncdot_aadt": ncdot,
        "timestamp": datetime.now().isoformat(),
    }


def handle_heatmap(params):
    """Heat map data as GeoJSON-compatible points."""
    hour = _parse_hour(params.get("hour", [None])[0])
    day = _parse_day(params.get("day", [None])[0])

    spots = get_enriched_spots(hour=hour, top_n=10)
    points = build_heatmap_data(spots, hour=hour, day_of_week=day)

    # Convert to GeoJSON FeatureCollection
    features = []
    for pt in points:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [pt[1], pt[0]],  # GeoJSON is [lon, lat]
            },
            "properties": {
                "weight": pt[2],
                "intensity": round(pt[2] * 100, 1),
            },
        })

    return {
        "type": "FeatureCollection",
        "query": {"hour": hour, "day_of_week": day},
        "features": features,
        "point_count": len(features),
        "timestamp": datetime.now().isoformat(),
    }


def handle_venues():
    """All discovered OSM venues."""
    places = fetch_nearby_places()
    return {
        "venue_count": len(places),
        "radius_meters": 400,
        "center": list(FRANKLIN_STREET_CENTER),
        "venues": places,
        "timestamp": datetime.now().isoformat(),
    }


def handle_trends(params):
    """Current trends and trivia suggestions."""
    live = params.get("live", ["false"])[0].lower() == "true"

    if live:
        trends_report = build_trends_report()
    else:
        trends_report = None

    suggestions, using_fallback = generate_trivia_suggestions(trends_report)

    return {
        "using_fallback": using_fallback,
        "suggestions": [
            {
                "category": s["category"],
                "keyword": s["keyword"],
                "score": s["score"],
                "strength": s["strength"],
                "suggestion": s["suggestion"],
                "rising_queries": s.get("related_rising", []),
            }
            for s in suggestions
        ],
        "trending_now": (
            trends_report.get("trending_now", []) if trends_report else []
        ),
        "locally_relevant": (
            trends_report.get("locally_relevant", []) if trends_report else []
        ),
        "timestamp": datetime.now().isoformat(),
    }


def handle_intel():
    """Full OSINT intelligence briefing."""
    return build_intel_report()


def handle_demographics():
    data = fetch_demographics()
    return data if data else {"error": "Set CENSUS_API_KEY env var"}


def handle_weather():
    data = fetch_weather()
    return data if data else {"error": "Set OPENWEATHER_API_KEY env var"}


def handle_events():
    data = fetch_unc_events()
    return data if data else {"error": "UNC Calendar unavailable"}


def handle_network():
    """Street network topology."""
    network = fetch_street_network()
    intersections = find_intersections(network)

    return {
        "node_count": network.get("node_count", 0),
        "edge_count": network.get("edge_count", 0),
        "intersection_count": len(intersections),
        "is_fallback": network.get("fallback", False),
        "intersections": intersections[:20],
        "timestamp": datetime.now().isoformat(),
    }


def handle_intersections():
    """Key intersections with connectivity scores."""
    intersections = find_intersections()
    return {
        "count": len(intersections),
        "intersections": intersections,
        "timestamp": datetime.now().isoformat(),
    }


def handle_report(params):
    """Full combined text report."""
    hour = _parse_hour(params.get("hour", [None])[0])
    tod = params.get("time", ["evening"])[0]

    report = generate_report(
        time_of_day=tod,
        num_spots=8,
        fetch_live_trends=False,
        fetch_live_traffic=True,
        hour=hour,
    )
    return {
        "report": report,
        "format": "text",
        "timestamp": datetime.now().isoformat(),
    }


def handle_spatial(params):
    """Advanced spatial analytics."""
    hour = _parse_hour(params.get("hour", [None])[0])
    spots = get_enriched_spots(hour=hour, top_n=10)
    return build_spatial_analysis(spots, hour=hour)


def handle_buildings():
    """3D building footprints."""
    buildings = fetch_building_footprints()
    return {
        "building_count": len(buildings),
        "buildings": buildings,
        "timestamp": datetime.now().isoformat(),
    }


def handle_viewshed(params):
    """Viewshed analysis for spots."""
    spots = get_enriched_spots(top_n=10)
    return {
        "viewshed": compute_viewshed_for_spots(spots),
        "timestamp": datetime.now().isoformat(),
    }


def handle_osint():
    """Deep OSINT intelligence."""
    return build_deep_osint_report()


def handle_reddit():
    """Live Reddit feed."""
    data = fetch_all_reddit()
    return data if data else {"error": "Reddit unavailable"}


def handle_crime():
    """Crime data from Chapel Hill ArcGIS."""
    data = fetch_crime_data()
    return data if data else {"error": "Crime data unavailable"}


def handle_transit():
    """Transit stops from GTFS."""
    data = fetch_transit_stops()
    return data if data else {"error": "Transit data unavailable"}


def handle_livefeed():
    """Live keyword feed from all sources."""
    return build_live_feed()


def handle_forecast(params):
    """Live signal forecast."""
    return build_forecast_report()


def handle_export(params):
    """Complete data export — all feeds combined."""
    hour = _parse_hour(params.get("hour", [None])[0])

    return {
        "api": API_NAME,
        "version": API_VERSION,
        "exported_at": datetime.now().isoformat(),
        "spots": handle_spots(params),
        "traffic": handle_traffic(params),
        "venues": handle_venues(),
        "intel": handle_intel(),
        "network": handle_network(),
        "trends": handle_trends(params),
        "spatial": handle_spatial(params),
        "osint": handle_osint(),
        "forecast": handle_forecast(params),
    }


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class DataHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Franklin Street Data API API."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        routes = {
            "": handle_root,
            "/status": handle_status,
            "/spots": lambda: handle_spots(params),
            "/traffic": lambda: handle_traffic(params),
            "/heatmap": lambda: handle_heatmap(params),
            "/venues": handle_venues,
            "/trends": lambda: handle_trends(params),
            "/intel": handle_intel,
            "/intel/demographics": handle_demographics,
            "/intel/weather": handle_weather,
            "/intel/events": handle_events,
            "/network": handle_network,
            "/network/intersections": handle_intersections,
            "/spatial": lambda: handle_spatial(params),
            "/buildings": handle_buildings,
            "/viewshed": lambda: handle_viewshed(params),
            "/osint": handle_osint,
            "/osint/reddit": handle_reddit,
            "/osint/crime": handle_crime,
            "/osint/transit": handle_transit,
            "/livefeed": handle_livefeed,
            "/forecast": lambda: handle_forecast(params),
            "/report": lambda: handle_report(params),
            "/export": lambda: handle_export(params),
        }

        # Check for /spots/<id> pattern
        if path.startswith("/spots/"):
            try:
                spot_id = int(path.split("/")[2])
                result = handle_spot_detail(spot_id, params)
            except (ValueError, IndexError):
                result = {"error": "Invalid spot ID"}
        elif path in routes:
            handler = routes[path]
            try:
                result = handler() if callable(handler) and not params else handler()
            except TypeError:
                result = handler()
        else:
            result = {
                "error": "Not found",
                "available_endpoints": list(routes.keys()),
            }
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, indent=2, default=str).encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2, default=str).encode())

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"  [API] {args[0]}")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Franklin Street Data Datastream API"
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Port to serve on (default: 8765)",
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    print()
    print("  ███ FRANKLIN STREET DATA ███")
    print("  ═══ Datastream API ═══")
    print()
    print(f"  Serving on http://{args.host}:{args.port}")
    print(f"  Docs:      http://localhost:{args.port}/")
    print()
    print("  Endpoints:")
    print("    /status          System health")
    print("    /spots           Ranked surveillance points")
    print("    /traffic         Live foot traffic analysis")
    print("    /heatmap         GeoJSON heat map data")
    print("    /venues          OSM venue discovery")
    print("    /trends          Trending search intelligence")
    print("    /intel           Full OSINT briefing")
    print("    /network         Street network topology")
    print("    /report          Text surveillance report")
    print("    /export          Complete data export")
    print()

    server = HTTPServer((args.host, args.port), DataHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Datastream shutdown.")
        server.server_close()
