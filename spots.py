"""
==============================================
  FRANKLIN STREET DATA
  Venue Discovery & Ranking
==============================================
Every venue on Franklin Street, discovered live from OpenStreetMap
and enriched with Google Places data.

Ranking signal: Google Places popularity
  (rating × review volume = how much foot traffic a venue generates)

Google does NOT expose live "busyness" (the bar chart on Google Maps)
through any official API. The populartimes library that scraped it
was removed from PyPI. What we CAN get from the official API:
  - user_ratings_total: how many people reviewed (proxy for traffic volume)
  - rating: quality signal (higher rated = draws more people)

popularity = (rating / 5.0) × min(100, user_ratings_total / 5)

This is real Google data, not editorial guesswork. But it's popularity
(cumulative), not live busyness (real-time). Labeled as such.
"""

import math
from config import FRANKLIN_STREET_CENTER
from traffic import fetch_nearby_places, search_places_nearby


def discover_venues(radius_meters=500):
    """
    Discover all venues on/near Franklin Street via OpenStreetMap.
    Returns list of venue dicts with name, lat, lon, amenity_type.
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
    Discover venues via OSM, enrich with Google Places popularity.

    1. OSM Overpass → all venues with coordinates
    2. Google Places Nearby Search → rating + user_ratings_total
    3. Match by proximity (nearest Google Place within 50m)
    4. Compute popularity score:
       popularity = (rating / 5.0) × min(100, user_ratings_total / 5)

    This is POPULARITY (cumulative), not live BUSYNESS (real-time).
    Google does not expose live busyness through any official API.
    """
    venues = discover_venues(radius_meters=radius_meters)
    if not venues:
        return []

    # Get Google Places data
    lat, lon = FRANKLIN_STREET_CENTER
    google_places = search_places_nearby(lat, lon, radius=radius_meters)

    if google_places:
        gp_list = list(google_places.values())
        for venue in venues:
            best_match = None
            best_dist = 100

            for gp in gp_list:
                dist = _haversine(venue["lat"], venue["lon"], gp["lat"], gp["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_match = gp

            if best_match and best_dist < 50:
                venue["google_matched"] = True
                venue["rating"] = best_match.get("rating")
                venue["user_ratings_total"] = best_match.get("user_ratings_total", 0)
                venue["price_level"] = best_match.get("price_level")
                venue["place_id"] = best_match.get("place_id")

                # Popularity score: rating quality × review volume
                rating = best_match.get("rating") or 0
                reviews = best_match.get("user_ratings_total") or 0
                venue["busyness"] = round(
                    (rating / 5.0) * min(100, reviews / 5)
                )
                venue["busyness_source"] = "google_places_popularity"
            else:
                venue["google_matched"] = False
                venue["busyness"] = None
                venue["busyness_source"] = None

            venue["hourly_profile"] = None
    else:
        for venue in venues:
            venue["busyness"] = None
            venue["hourly_profile"] = None
            venue["busyness_source"] = None

    # Sort: highest popularity first
    with_data = [v for v in venues if v["busyness"] is not None]
    without_data = [v for v in venues if v["busyness"] is None]

    with_data.sort(key=lambda v: v["busyness"], reverse=True)
    without_data.sort(key=lambda v: v["name"])

    return with_data + without_data


def get_enriched_spots(time_of_day="evening", hour=None, top_n=50):
    """Get venues ranked by popularity."""
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
