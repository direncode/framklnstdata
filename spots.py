"""
==============================================
  FRANKLIN STREET DATA
  Venue Discovery & Ranking
==============================================
Every venue on Franklin Street, discovered live from OpenStreetMap.
No hardcoded list. No editorial scores.

Ranking signal: Google Places busyness (0-100).
That's it. Busyness informs the decision.
"""

import math
from config import FRANKLIN_STREET_CENTER
from traffic import fetch_nearby_places, search_places_busyness


def discover_venues(radius_meters=500):
    """
    Discover all venues on/near Franklin Street via OpenStreetMap.
    Returns list of venue dicts with name, lat, lon, amenity_type.
    Returns empty list if OSM unavailable.
    """
    places = fetch_nearby_places(radius_meters=radius_meters)
    if not places:
        return []

    venues = []
    for i, place in enumerate(places):
        venues.append({
            "id": i + 1,
            "name": place["name"],
            "lat": place["lat"],
            "lon": place["lon"],
            "amenity_type": place.get("amenity_type", "unknown"),
            "osm_id": place.get("osm_id"),
            "cuisine": place.get("cuisine", ""),
            "opening_hours": place.get("opening_hours", ""),
        })

    return venues


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def get_venues_with_busyness(hour=None, radius_meters=500):
    """
    Discover all venues via OSM, then enrich with Google Places data.

    Strategy:
    1. OSM Overpass → all venues with coordinates
    2. Google Places Nearby Search → venues with ratings + user_ratings_total
    3. Match by proximity (closest Google Place to each OSM venue)
    4. Use user_ratings_total as a busyness proxy (more ratings = more traffic)
       until Google Places popular_times is available

    If no Google Places API key, venues still appear but with no busyness.
    """
    venues = discover_venues(radius_meters=radius_meters)
    if not venues:
        return []

    # Try to get Google Places data for the area
    lat, lon = FRANKLIN_STREET_CENTER
    google_places = search_places_busyness(lat, lon, radius=radius_meters)

    if google_places:
        # Match each OSM venue to nearest Google Place
        gp_list = list(google_places.values())
        for venue in venues:
            best_match = None
            best_dist = 100  # meters

            for gp in gp_list:
                dist = _haversine(venue["lat"], venue["lon"], gp["lat"], gp["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_match = gp

            if best_match and best_dist < 50:  # Within 50m = same venue
                venue["google_matched"] = True
                venue["rating"] = best_match.get("rating")
                venue["user_ratings_total"] = best_match.get("user_ratings_total", 0)
                venue["price_level"] = best_match.get("price_level")

                # Use user_ratings_total as busyness proxy:
                # More reviews = more popular = more foot traffic
                # Normalize: 0-1000+ ratings → 0-100 busyness
                ratings = best_match.get("user_ratings_total", 0)
                venue["busyness"] = min(100, int((ratings / 10)))
                venue["busyness_source"] = "google_places_ratings"
            else:
                venue["google_matched"] = False
                venue["busyness"] = None
                venue["busyness_source"] = None

            venue["hourly_profile"] = None  # Not available without populartimes
    else:
        # No Google data — venues exist but no busyness
        for venue in venues:
            venue["busyness"] = None
            venue["hourly_profile"] = None
            venue["busyness_source"] = None

    # Sort: venues with busyness first (desc), then without (alphabetical)
    with_data = [v for v in venues if v["busyness"] is not None]
    without_data = [v for v in venues if v["busyness"] is None]

    with_data.sort(key=lambda v: v["busyness"], reverse=True)
    without_data.sort(key=lambda v: v["name"])

    return with_data + without_data


def get_enriched_spots(time_of_day="evening", hour=None, top_n=50):
    """Get venues ranked by busyness."""
    venues = get_venues_with_busyness(hour=hour)

    for v in venues:
        if v["busyness"] is not None:
            v["composite_score"] = round(v["busyness"] / 10, 1)
        else:
            v["composite_score"] = 0
        v["live_busyness"] = v["busyness"]

    return venues[:top_n]


def get_ranked_spots(time_of_day="evening", top_n=50):
    return get_enriched_spots(time_of_day=time_of_day, top_n=top_n)


FRANKLIN_STREET_SPOTS = []
