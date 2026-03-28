"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Spatial Analysis (Honest)
==============================================
Only analyses that work on real inputs:
  - Isochrones: geometric walk-time rings (real coordinates)
  - Gravity model: destination probability (real distances)
  - Optimal placement: greedy facility location (real positions)
  - Pareto frontier: dominance on real metric dimensions

Removed: KDE, DBSCAN, Voronoi, hexbins — these require
real observed point data, not 10 guessed scores.
"""

import math
from datetime import datetime

from config import FRANKLIN_STREET_CENTER


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
    """
    Compute walk-time isochrone rings from a center point.
    Uses radial approximation at 4.5 km/h walking speed.

    These are geometric — for network-aware isochrones,
    use OSRM or Valhalla API.
    """
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
    """Compute isochrones for all spots."""
    if times_min is None:
        times_min = [3, 5]

    results = []
    for spot in spots:
        iso = compute_isochrones(spot["lat"], spot["lon"], times_min=times_min)
        results.append({
            "spot_name": spot["name"],
            "spot_id": spot["id"],
            "lat": spot["lat"],
            "lon": spot["lon"],
            "isochrones": iso,
        })
    return results


# ---------------------------------------------------------------------------
# Gravity Model (Real Distances)
# ---------------------------------------------------------------------------

def gravity_model(spots, origin_lat, origin_lon):
    """
    Huff/Gravity model: predict probability of visiting each spot
    from a given origin point.

    P(visit i) = (A_i / d_i^2) / sum(A_j / d_j^2)

    Uses composite_score as attractiveness. If live_busyness is available,
    uses that instead (actual data > editorial estimate).
    """
    scores = []
    for spot in spots:
        dist = haversine(origin_lat, origin_lon, spot["lat"], spot["lon"])
        dist = max(dist, 0.01)

        # Prefer live data over editorial estimates
        if spot.get("live_busyness") is not None:
            attractiveness = spot["live_busyness"] / 10.0
        else:
            attractiveness = spot.get("composite_score", 5)

        gravity = attractiveness / (dist ** 2)
        scores.append((spot, gravity, dist))

    total = sum(g for _, g, _ in scores)
    if total == 0:
        return []

    result = []
    for spot, gravity, dist in scores:
        prob = gravity / total
        result.append({
            "spot_name": spot["name"],
            "spot_id": spot["id"],
            "probability_pct": round(prob * 100, 1),
            "distance_m": round(dist * 1000),
            "data_source": "live_busyness" if spot.get("live_busyness") is not None else "editorial_estimate",
        })

    result.sort(key=lambda r: r["probability_pct"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Pareto Frontier
# ---------------------------------------------------------------------------

def pareto_frontier(spots):
    """
    Identify Pareto-optimal spots — spots where no other spot
    beats them on ALL metrics simultaneously.

    NOTE: Uses editorial estimates (foot_traffic, dwell_time, etc.)
    These are not measured data.
    """
    objectives = ["foot_traffic", "dwell_time", "visibility", "student_density"]
    n = len(spots)
    is_pareto = [True] * n

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dominates_all = all(
                spots[j].get(obj, 0) >= spots[i].get(obj, 0)
                for obj in objectives
            )
            dominates_one = any(
                spots[j].get(obj, 0) > spots[i].get(obj, 0)
                for obj in objectives
            )
            if dominates_all and dominates_one:
                is_pareto[i] = False
                break

    result = []
    for i, spot in enumerate(spots):
        result.append({
            "spot_name": spot["name"],
            "spot_id": spot["id"],
            "is_pareto": is_pareto[i],
            "scores": {obj: spot.get(obj, 0) for obj in objectives},
            "data_source": "editorial_estimates",
        })

    result.sort(key=lambda r: (not r["is_pareto"], -sum(r["scores"].values())))
    return result


# ---------------------------------------------------------------------------
# Optimal Placement (Greedy Facility Location)
# ---------------------------------------------------------------------------

def optimize_placement(spots, k=5, min_distance_km=0.05):
    """
    Select k spots maximizing coverage with minimum spacing.
    Greedy approximation to the maximal coverage problem.
    """
    selected = []
    remaining = list(range(len(spots)))
    remaining.sort(key=lambda i: spots[i].get("composite_score", 0), reverse=True)

    while len(selected) < k and remaining:
        candidate = remaining.pop(0)
        too_close = False
        for sel_idx in selected:
            dist = haversine(
                spots[candidate]["lat"], spots[candidate]["lon"],
                spots[sel_idx]["lat"], spots[sel_idx]["lon"],
            )
            if dist < min_distance_km:
                too_close = True
                break
        if not too_close:
            selected.append(candidate)

    return [
        {
            "rank": i + 1,
            "spot_name": spots[idx]["name"],
            "spot_id": spots[idx]["id"],
            "composite_score": spots[idx].get("composite_score", 0),
            "lat": spots[idx]["lat"],
            "lon": spots[idx]["lon"],
        }
        for i, idx in enumerate(selected)
    ]


# ---------------------------------------------------------------------------
# Combined Analysis
# ---------------------------------------------------------------------------

def build_spatial_analysis(spots, hour=None):
    """Run spatial analyses on spots. Labels data provenance clearly."""
    pareto = pareto_frontier(spots)
    optimal = optimize_placement(spots, k=5)
    top3 = sorted(spots, key=lambda s: s.get("composite_score", 0), reverse=True)[:3]
    isochrones = compute_isochrones_for_spots(top3, times_min=[3, 5])

    return {
        "pareto_frontier": pareto,
        "pareto_optimal_count": sum(1 for p in pareto if p["is_pareto"]),
        "optimal_placement": optimal,
        "isochrones": isochrones,
        "note": (
            "Pareto and placement use editorial estimates from spots.py. "
            "Gravity model uses live_busyness when available from Google Places API."
        ),
        "timestamp": datetime.now().isoformat(),
    }
