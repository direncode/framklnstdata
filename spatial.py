"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Advanced Spatial Analytics Engine
==============================================
Isochrone analysis, kernel density estimation,
DBSCAN clustering, Voronoi tessellation, hexbin
aggregation, gravity/Huff models, and multi-criteria
Pareto optimization.
"""

import math
import json
import os
from datetime import datetime
from collections import defaultdict

from config import (
    CACHE_DIR,
    FRANKLIN_STREET_CENTER,
    FRANKLIN_STREET_BOUNDS,
    FRANKLIN_STREET_SPINE,
)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_path():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _read_cache(key):
    try:
        with open(os.path.join(_cache_path(), f"{key}.json")) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_cache(key, data):
    with open(os.path.join(_cache_path(), f"{key}.json"), "w") as f:
        json.dump(data, f)


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

def compute_isochrones(center_lat, center_lon, walk_speeds_kmh=None, times_min=None):
    """
    Compute walk-time isochrone polygons from a center point.
    Uses simple radial approximation (circle-based).

    For production, use OSRM or Valhalla for network-aware isochrones.

    Returns list of isochrone dicts with polygon coordinates.
    """
    if walk_speeds_kmh is None:
        walk_speeds_kmh = [4.5]  # Average walking speed
    if times_min is None:
        times_min = [3, 5, 10, 15]

    speed = walk_speeds_kmh[0]
    isochrones = []

    for t in times_min:
        radius_km = (speed * t) / 60.0
        # Generate polygon points (circle approximation)
        points = []
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            # Approximate lat/lon offset
            dlat = radius_km / 111.32
            dlon = radius_km / (111.32 * math.cos(math.radians(center_lat)))
            new_lat = center_lat + dlat * math.sin(rad)
            new_lon = center_lon + dlon * math.cos(rad)
            points.append([new_lat, new_lon])
        points.append(points[0])  # Close polygon

        isochrones.append({
            "minutes": t,
            "radius_km": round(radius_km, 3),
            "radius_m": round(radius_km * 1000),
            "polygon": points,
            "color": _isochrone_color(t),
        })

    return isochrones


def _isochrone_color(minutes):
    """Color gradient for isochrone rings."""
    colors = {3: "#ff0000", 5: "#ff6600", 10: "#ffcc00", 15: "#00cc00"}
    return colors.get(minutes, "#0066ff")


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
# Kernel Density Estimation (KDE)
# ---------------------------------------------------------------------------

def compute_kde(points, grid_resolution=50, bandwidth_km=0.05):
    """
    Compute kernel density estimation on a grid over the Franklin Street area.
    Uses Gaussian kernel.

    Args:
        points: list of (lat, lon, weight) tuples
        grid_resolution: number of grid cells per axis
        bandwidth_km: kernel bandwidth in km

    Returns dict with 'grid' (2D array), 'lat_range', 'lon_range'.
    """
    bounds = FRANKLIN_STREET_BOUNDS
    lat_range = (bounds["south"], bounds["north"])
    lon_range = (bounds["west"], bounds["east"])

    lat_step = (lat_range[1] - lat_range[0]) / grid_resolution
    lon_step = (lon_range[1] - lon_range[0]) / grid_resolution

    grid = [[0.0] * grid_resolution for _ in range(grid_resolution)]

    for i in range(grid_resolution):
        for j in range(grid_resolution):
            grid_lat = lat_range[0] + (i + 0.5) * lat_step
            grid_lon = lon_range[0] + (j + 0.5) * lon_step

            density = 0.0
            for plat, plon, weight in points:
                dist = haversine(grid_lat, grid_lon, plat, plon)
                # Gaussian kernel
                kernel = math.exp(-0.5 * (dist / bandwidth_km) ** 2)
                density += weight * kernel

            grid[i][j] = round(density, 4)

    return {
        "grid": grid,
        "lat_range": lat_range,
        "lon_range": lon_range,
        "resolution": grid_resolution,
        "bandwidth_km": bandwidth_km,
        "max_density": max(max(row) for row in grid),
    }


def kde_to_heatmap_points(kde_result, threshold=0.01):
    """Convert KDE grid to heat map points for folium visualization."""
    points = []
    lat_range = kde_result["lat_range"]
    lon_range = kde_result["lon_range"]
    res = kde_result["resolution"]
    max_d = kde_result["max_density"]

    if max_d == 0:
        return points

    lat_step = (lat_range[1] - lat_range[0]) / res
    lon_step = (lon_range[1] - lon_range[0]) / res

    for i in range(res):
        for j in range(res):
            val = kde_result["grid"][i][j]
            normalized = val / max_d
            if normalized > threshold:
                lat = lat_range[0] + (i + 0.5) * lat_step
                lon = lon_range[0] + (j + 0.5) * lon_step
                points.append([lat, lon, normalized])

    return points


# ---------------------------------------------------------------------------
# DBSCAN Clustering
# ---------------------------------------------------------------------------

def dbscan_cluster(points, eps_km=0.05, min_samples=3):
    """
    DBSCAN clustering of geographic points.
    Pure Python implementation (no sklearn dependency).

    Args:
        points: list of (lat, lon, weight) tuples
        eps_km: maximum distance between points in same cluster
        min_samples: minimum points to form a cluster

    Returns list of cluster dicts with center, members, density.
    """
    n = len(points)
    if n < min_samples:
        return []

    # Build distance matrix
    labels = [-1] * n  # -1 = unvisited
    cluster_id = 0

    def region_query(idx):
        neighbors = []
        for j in range(n):
            if j != idx:
                dist = haversine(
                    points[idx][0], points[idx][1],
                    points[j][0], points[j][1],
                )
                if dist <= eps_km:
                    neighbors.append(j)
        return neighbors

    for i in range(n):
        if labels[i] != -1:
            continue

        neighbors = region_query(i)
        if len(neighbors) < min_samples:
            labels[i] = 0  # Noise
            continue

        cluster_id += 1
        labels[i] = cluster_id

        seed_set = list(neighbors)
        while seed_set:
            q = seed_set.pop(0)
            if labels[q] == 0:  # Was noise, now border
                labels[q] = cluster_id
            if labels[q] != -1:
                continue
            labels[q] = cluster_id
            q_neighbors = region_query(q)
            if len(q_neighbors) >= min_samples:
                seed_set.extend(q_neighbors)

    # Build cluster summaries
    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        if label > 0:
            clusters[label].append(i)

    result = []
    for cid, members in clusters.items():
        member_points = [points[m] for m in members]
        avg_lat = sum(p[0] for p in member_points) / len(member_points)
        avg_lon = sum(p[1] for p in member_points) / len(member_points)
        total_weight = sum(p[2] for p in member_points)

        result.append({
            "cluster_id": cid,
            "center": [avg_lat, avg_lon],
            "member_count": len(members),
            "total_weight": round(total_weight, 2),
            "avg_weight": round(total_weight / len(members), 2),
            "members": member_points,
        })

    result.sort(key=lambda c: c["total_weight"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Voronoi Tessellation
# ---------------------------------------------------------------------------

def compute_voronoi(spots):
    """
    Compute Voronoi tessellation — assign every grid point to its
    nearest spot. Returns a grid of spot assignments showing which
    venue 'owns' each area.
    """
    bounds = FRANKLIN_STREET_BOUNDS
    resolution = 40

    lat_step = (bounds["north"] - bounds["south"]) / resolution
    lon_step = (bounds["east"] - bounds["west"]) / resolution

    cells = defaultdict(list)

    for i in range(resolution):
        for j in range(resolution):
            lat = bounds["south"] + (i + 0.5) * lat_step
            lon = bounds["west"] + (j + 0.5) * lon_step

            # Find nearest spot
            best_dist = float("inf")
            best_spot = None
            for spot in spots:
                dist = haversine(lat, lon, spot["lat"], spot["lon"])
                if dist < best_dist:
                    best_dist = dist
                    best_spot = spot["name"]

            cells[best_spot].append([lat, lon])

    result = []
    for spot_name, points in cells.items():
        spot = next((s for s in spots if s["name"] == spot_name), None)
        result.append({
            "spot_name": spot_name,
            "spot_id": spot["id"] if spot else None,
            "cell_count": len(points),
            "coverage_area_pct": round(len(points) / (resolution ** 2) * 100, 1),
            "boundary_points": points,
        })

    result.sort(key=lambda c: c["cell_count"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Hexbin Aggregation (H3-like)
# ---------------------------------------------------------------------------

def compute_hexbins(points, hex_size_km=0.03):
    """
    Aggregate points into hexagonal bins.
    Pure Python approximation of H3 hexagonal indexing.

    Returns list of hexbin dicts with center, count, total_weight.
    """
    # Approximate hex grid using offset coordinates
    hex_height = hex_size_km / 111.32  # km to degrees lat
    hex_width = hex_size_km / (111.32 * math.cos(math.radians(FRANKLIN_STREET_CENTER[0])))

    bins = defaultdict(lambda: {"count": 0, "total_weight": 0, "lats": [], "lons": []})

    for lat, lon, weight in points:
        # Quantize to hex grid
        row = int((lat - FRANKLIN_STREET_BOUNDS["south"]) / hex_height)
        col = int((lon - FRANKLIN_STREET_BOUNDS["west"]) / hex_width)
        # Offset every other row
        if row % 2 == 1:
            col_offset = col + 0.5
        else:
            col_offset = col

        key = (row, int(col_offset))
        bins[key]["count"] += 1
        bins[key]["total_weight"] += weight
        bins[key]["lats"].append(lat)
        bins[key]["lons"].append(lon)

    result = []
    for (row, col), data in bins.items():
        center_lat = FRANKLIN_STREET_BOUNDS["south"] + (row + 0.5) * hex_height
        center_lon = FRANKLIN_STREET_BOUNDS["west"] + (col + 0.5) * hex_width

        # Generate hexagon vertices
        vertices = []
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            vlat = center_lat + (hex_height / 2) * math.sin(rad)
            vlon = center_lon + (hex_width / 2) * math.cos(rad)
            vertices.append([vlat, vlon])
        vertices.append(vertices[0])

        result.append({
            "center": [center_lat, center_lon],
            "vertices": vertices,
            "count": data["count"],
            "total_weight": round(data["total_weight"], 2),
            "avg_weight": round(data["total_weight"] / data["count"], 2),
        })

    result.sort(key=lambda h: h["total_weight"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Gravity Model
# ---------------------------------------------------------------------------

def gravity_model(spots, origin_lat, origin_lon, attractiveness_key="composite_score"):
    """
    Huff/Gravity model: predict probability of visiting each spot
    from a given origin point.

    P(visit spot_i) = (A_i / d_i^2) / sum(A_j / d_j^2)

    Where A = attractiveness score, d = distance.
    Returns list of (spot_name, probability, distance) sorted by probability.
    """
    scores = []
    for spot in spots:
        dist = haversine(origin_lat, origin_lon, spot["lat"], spot["lon"])
        dist = max(dist, 0.01)  # Avoid division by zero
        attractiveness = spot.get(attractiveness_key, spot.get("composite_score", 5))
        gravity = attractiveness / (dist ** 2)
        scores.append((spot, gravity, dist))

    total_gravity = sum(g for _, g, _ in scores)
    if total_gravity == 0:
        return []

    result = []
    for spot, gravity, dist in scores:
        prob = gravity / total_gravity
        result.append({
            "spot_name": spot["name"],
            "spot_id": spot["id"],
            "probability": round(prob, 4),
            "probability_pct": round(prob * 100, 1),
            "distance_km": round(dist, 3),
            "distance_m": round(dist * 1000),
            "attractiveness": spot.get(attractiveness_key, spot.get("composite_score", 5)),
        })

    result.sort(key=lambda r: r["probability"], reverse=True)
    return result


def gravity_model_grid(spots, grid_resolution=30):
    """
    Compute gravity model probabilities across a grid.
    For each grid cell, show which spot has highest attraction.

    Returns grid data suitable for choropleth visualization.
    """
    bounds = FRANKLIN_STREET_BOUNDS
    lat_step = (bounds["north"] - bounds["south"]) / grid_resolution
    lon_step = (bounds["east"] - bounds["west"]) / grid_resolution

    grid_cells = []
    for i in range(grid_resolution):
        for j in range(grid_resolution):
            lat = bounds["south"] + (i + 0.5) * lat_step
            lon = bounds["west"] + (j + 0.5) * lon_step

            probs = gravity_model(spots, lat, lon)
            if probs:
                top = probs[0]
                grid_cells.append({
                    "lat": lat,
                    "lon": lon,
                    "dominant_spot": top["spot_name"],
                    "probability": top["probability"],
                    "distance_m": top["distance_m"],
                })

    return grid_cells


# ---------------------------------------------------------------------------
# Pareto Frontier (Multi-Criteria Optimization)
# ---------------------------------------------------------------------------

def pareto_frontier(spots, objectives=None):
    """
    Identify Pareto-optimal spots (no single spot dominates on all metrics).

    Returns list of (spot, is_pareto) indicating frontier membership.
    """
    if objectives is None:
        objectives = ["foot_traffic", "dwell_time", "visibility", "student_density"]

    n = len(spots)
    is_pareto = [True] * n

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # Check if j dominates i (j >= i on all objectives, j > i on at least one)
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
        })

    # Sort: Pareto-optimal first, then by sum of scores
    result.sort(
        key=lambda r: (not r["is_pareto"], -sum(r["scores"].values()))
    )
    return result


# ---------------------------------------------------------------------------
# Optimal Placement (Integer Optimization)
# ---------------------------------------------------------------------------

def optimize_placement(spots, k=5, min_distance_km=0.05):
    """
    Select k optimal spots that maximize total coverage while
    maintaining minimum distance between placements.

    Uses greedy algorithm (approximation to facility location problem).
    """
    selected = []
    remaining = list(range(len(spots)))

    # Sort by composite score descending
    remaining.sort(key=lambda i: spots[i].get("composite_score", 0), reverse=True)

    while len(selected) < k and remaining:
        candidate = remaining.pop(0)

        # Check minimum distance constraint
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
# Spatial Summary
# ---------------------------------------------------------------------------

def build_spatial_analysis(spots, hour=None):
    """
    Run all spatial analyses and return a combined summary.
    """
    # Build point data from spots
    points = []
    for spot in spots:
        busyness = spot.get("live_busyness", spot["foot_traffic"] * 10)
        points.append((spot["lat"], spot["lon"], busyness / 100.0))

    # Run analyses
    clusters = dbscan_cluster(points, eps_km=0.08, min_samples=2)
    hexbins = compute_hexbins(points)
    voronoi = compute_voronoi(spots)
    pareto = pareto_frontier(spots)
    optimal = optimize_placement(spots, k=5)

    # Isochrones for top 3 spots
    top3 = sorted(spots, key=lambda s: s.get("composite_score", 0), reverse=True)[:3]
    isochrones = compute_isochrones_for_spots(top3, times_min=[3, 5])

    return {
        "clusters": clusters,
        "cluster_count": len(clusters),
        "hexbins": hexbins,
        "hexbin_count": len(hexbins),
        "voronoi_cells": voronoi,
        "pareto_frontier": pareto,
        "pareto_optimal_count": sum(1 for p in pareto if p["is_pareto"]),
        "optimal_placement": optimal,
        "isochrones": isochrones,
        "timestamp": datetime.now().isoformat(),
    }
