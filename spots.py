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

from traffic import fetch_nearby_places, get_current_busyness, fetch_popular_times


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


def get_venues_with_busyness(hour=None, radius_meters=500):
    """
    Discover all venues and fetch live busyness for each.

    Each venue gets:
      - busyness: 0-100 from Google Places API, or None if unavailable
      - hourly_profile: 24-hour busyness array, or None

    Ranked by busyness descending. Venues without busyness data
    appear at the end (they exist, we just can't rank them).
    """
    venues = discover_venues(radius_meters=radius_meters)
    if not venues:
        return []

    for venue in venues:
        # Try to get live busyness from Google Places
        hourly = fetch_popular_times(venue["name"], place_id=None)
        venue["hourly_profile"] = hourly
        venue["busyness"] = get_current_busyness(
            venue["name"], place_id=None, hour=hour,
        )

    # Sort: venues with busyness data first (by busyness desc),
    # then venues without data (alphabetical)
    with_data = [v for v in venues if v["busyness"] is not None]
    without_data = [v for v in venues if v["busyness"] is None]

    with_data.sort(key=lambda v: v["busyness"], reverse=True)
    without_data.sort(key=lambda v: v["name"])

    return with_data + without_data


# ---------------------------------------------------------------------------
# Backward-compatible aliases for existing consumers
# These wrap the new OSM-based discovery
# ---------------------------------------------------------------------------

def get_enriched_spots(time_of_day="evening", hour=None, top_n=50):
    """
    Get venues ranked by busyness.
    Replaces the old editorial-score-based ranking.
    """
    venues = get_venues_with_busyness(hour=hour)

    # Add composite_score for backward compatibility
    # It's just busyness normalized to 0-10, or 0 if no data
    for v in venues:
        if v["busyness"] is not None:
            v["composite_score"] = round(v["busyness"] / 10, 1)
        else:
            v["composite_score"] = 0
        v["live_busyness"] = v["busyness"]

    return venues[:top_n]


def get_ranked_spots(time_of_day="evening", top_n=50):
    """Alias for get_enriched_spots."""
    return get_enriched_spots(time_of_day=time_of_day, top_n=top_n)


# Backward compatibility — modules that import this constant
# get an empty list (the real data comes from discover_venues())
FRANKLIN_STREET_SPOTS = []
