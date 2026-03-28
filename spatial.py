"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Spatial Analysis
==============================================
Geometric analyses on real venue positions:
  - Isochrones: walk-time rings from venue coordinates
  - Gravity model: destination probability from real distances + busyness
  - Optimal placement: greedy facility location with distance constraints
"""

import math
from datetime import datetime


# ---------------------------------------------------------------------------
# Haversine Distance
# ---------------------------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2):
    """Distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Isochrone Analysis (Walk-Time Polygons)
# ---------------------------------------------------------------------------

def compute_isochrones(center_lat, center_lon, times_min=None):
    """Walk-time rings at 4.5 km/h. Geometric approximation."""
    if times_min is None:
        times_min = [3, 5, 10]

    speed_kmh = 4.5
    isochrones = []

    for t in times_min:
        radius_km = (speed_kmh * t) / 60.0
        points = []
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            dlat = radius_km / 111.32
            dlon = radius_km / (111.32 * math.cos(math.radians(center_lat)))
            new_lat = center_lat + dlat * math.sin(rad)
            new_lon = center_lon + dlon * math.cos(rad)
            points.append([new_lat, new_lon])
        points.append(points[0])

        colors = {3: "#ff0000", 5: "#ff6600", 10: "#ffcc00", 15: "#00cc00"}
        isochrones.append({
            "minutes": t,
            "radius_m": round(radius_km * 1000),
            "polygon": points,
            "color": colors.get(t, "#0066ff"),
        })

    return isochrones


def compute_isochrones_for_spots(spots, times_min=None):
    """Compute isochrones for a list of spots."""
    if times_min is None:
        times_min = [3, 5]

    results = []
    for spot in spots:
        iso = compute_isochrones(spot["lat"], spot["lon"], times_min=times_min)
        results.append({
            "spot_name": spot["name"],
            "spot_id": spot.get("id"),
            "lat": spot["lat"],
            "lon": spot["lon"],
            "isochrones": iso,
        })
    return results


# ---------------------------------------------------------------------------
# Gravity Model (Real Distances + Busyness)
# ---------------------------------------------------------------------------

def gravity_model(spots, origin_lat, origin_lon):
    """
    Huff/Gravity model: predict visit probability from an origin point.
    Uses busyness as attractiveness. If no busyness, venue is excluded.
    """
    scores = []
    for spot in spots:
        dist = haversine(origin_lat, origin_lon, spot["lat"], spot["lon"])
        dist = max(dist, 0.01)

        busyness = spot.get("busyness") or spot.get("live_busyness")
        if busyness is None:
            continue

        gravity = busyness / (dist ** 2)
        scores.append((spot, gravity, dist))

    total = sum(g for _, g, _ in scores)
    if total == 0:
        return []

    result = []
    for spot, gravity, dist in scores:
        prob = gravity / total
        result.append({
            "spot_name": spot["name"],
            "probability_pct": round(prob * 100, 1),
            "distance_m": round(dist * 1000),
            "busyness": spot.get("busyness") or spot.get("live_busyness"),
        })

    result.sort(key=lambda r: r["probability_pct"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Optimal Placement (Greedy, by Busyness + Spacing)
# ---------------------------------------------------------------------------

def optimize_placement(spots, k=5, min_distance_km=0.05):
    """
    Select k venues maximizing busyness coverage with minimum spacing.
    Only considers venues with busyness data.
    """
    # Filter to venues with busyness
    ranked = [
        s for s in spots
        if (s.get("busyness") or s.get("composite_score", 0)) > 0
    ]
    ranked.sort(
        key=lambda s: s.get("busyness") or s.get("composite_score", 0),
        reverse=True,
    )

    selected = []
    for candidate in ranked:
        if len(selected) >= k:
            break
        too_close = any(
            haversine(candidate["lat"], candidate["lon"], sel["lat"], sel["lon"]) < min_distance_km
            for sel in selected
        )
        if not too_close:
            selected.append(candidate)

    return [
        {
            "rank": i + 1,
            "spot_name": s["name"],
            "busyness": s.get("busyness") or s.get("composite_score", 0),
            "lat": s["lat"],
            "lon": s["lon"],
        }
        for i, s in enumerate(selected)
    ]


# ---------------------------------------------------------------------------
# Combined Analysis
# ---------------------------------------------------------------------------

def build_spatial_analysis(spots, hour=None):
    """Run spatial analyses. Only uses real data (positions + busyness)."""
    optimal = optimize_placement(spots, k=5)
    top3 = sorted(
        [s for s in spots if s.get("busyness") is not None],
        key=lambda s: s.get("busyness", 0),
        reverse=True,
    )[:3]

    # Only compute isochrones if we have venues
    isochrones = compute_isochrones_for_spots(top3, times_min=[3, 5]) if top3 else []

    return {
        "optimal_placement": optimal,
        "isochrones": isochrones,
        "venue_count": len(spots),
        "venues_with_busyness": sum(1 for s in spots if s.get("busyness") is not None),
        "timestamp": datetime.now().isoformat(),
    }
