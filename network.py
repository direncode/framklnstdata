"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Street Network Analysis Engine
==============================================
Analyzes the Franklin Street pedestrian network using
OpenStreetMap data. Computes betweenness centrality,
intersection density, and walk-score-like metrics to
identify optimal placement positions.
"""

import json
import os
import math
from datetime import datetime

from config import (
    CACHE_DIR,
    FRANKLIN_STREET_CENTER,
    FRANKLIN_STREET_BOUNDS,
    OVERPASS_API_URL,
)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_path():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _cache_age_hours(key):
    fp = os.path.join(_cache_path(), f"{key}.json")
    if not os.path.exists(fp):
        return float("inf")
    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
    return (datetime.now() - mtime).total_seconds() / 3600


def _read_cache(key):
    try:
        fp = os.path.join(_cache_path(), f"{key}.json")
        with open(fp) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_cache(key, data):
    fp = os.path.join(_cache_path(), f"{key}.json")
    with open(fp, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Street Network Data (Overpass API)
# ---------------------------------------------------------------------------

def fetch_street_network():
    """
    Fetch the walking/pedestrian street network for the Franklin Street
    area from OpenStreetMap via Overpass API.

    Returns a dict with 'nodes' and 'edges' lists.
    """
    cache_key = "street_network"
    if _cache_age_hours(cache_key) < 720:  # 30 day cache
        cached = _read_cache(cache_key)
        if cached:
            return cached

    bounds = FRANKLIN_STREET_BOUNDS
    bbox = f"{bounds['south']},{bounds['west']},{bounds['north']},{bounds['east']}"

    query = f"""
    [out:json][timeout:30];
    (
      way["highway"~"footway|pedestrian|residential|tertiary|secondary|primary|path|steps|service|living_street|cycleway"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """

    try:
        import requests
        resp = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [!] Street network fetch error: {e}")
        return _fallback_network()

    # Parse nodes and ways
    nodes = {}
    edges = []

    for element in data.get("elements", []):
        if element["type"] == "node":
            nodes[element["id"]] = {
                "id": element["id"],
                "lat": element["lat"],
                "lon": element["lon"],
            }
        elif element["type"] == "way":
            way_nodes = element.get("nodes", [])
            tags = element.get("tags", {})
            highway_type = tags.get("highway", "unknown")
            name = tags.get("name", "")

            for i in range(len(way_nodes) - 1):
                edges.append({
                    "from": way_nodes[i],
                    "to": way_nodes[i + 1],
                    "highway": highway_type,
                    "name": name,
                })

    result = {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }

    _write_cache(cache_key, result)
    print(f"  [+] Street network: {len(nodes)} nodes, {len(edges)} edges")
    return result


def _fallback_network():
    """Fallback street network data when Overpass is unavailable."""
    return {
        "nodes": {},
        "edges": [],
        "node_count": 0,
        "edge_count": 0,
        "fallback": True,
    }


# ---------------------------------------------------------------------------
# Intersection Analysis
# ---------------------------------------------------------------------------

def find_intersections(network=None):
    """
    Find intersections (nodes where 3+ edges meet) in the street network.
    Returns list of intersection dicts with lat, lon, degree.
    """
    if network is None:
        network = fetch_street_network()

    if network.get("fallback"):
        return []  # No fake data — need live network

    # Count degree of each node
    degree = {}
    for edge in network["edges"]:
        degree[edge["from"]] = degree.get(edge["from"], 0) + 1
        degree[edge["to"]] = degree.get(edge["to"], 0) + 1

    # Intersections are nodes with degree >= 3
    intersections = []
    for node_id, deg in degree.items():
        if deg >= 3 and node_id in network["nodes"]:
            node = network["nodes"][node_id]
            intersections.append({
                "id": node_id,
                "lat": node["lat"],
                "lon": node["lon"],
                "degree": deg,
                "connectivity_score": min(10, deg * 2),
            })

    # Sort by degree (most connected first)
    intersections.sort(key=lambda x: x["degree"], reverse=True)
    return intersections




# ---------------------------------------------------------------------------
# Betweenness Centrality (Simplified)
# ---------------------------------------------------------------------------

def compute_centrality(network=None, sample_size=50):
    """
    Compute approximate betweenness centrality for network nodes.
    Uses sampling for performance (full computation is O(V*E)).

    Returns dict of {node_id: centrality_score}.
    Higher scores = more paths pass through this node = better placement.
    """
    if network is None:
        network = fetch_street_network()

    if network.get("fallback") or not network["edges"]:
        return {}

    # Build adjacency list
    adj = {}
    for edge in network["edges"]:
        adj.setdefault(edge["from"], []).append(edge["to"])
        adj.setdefault(edge["to"], []).append(edge["from"])

    node_ids = list(adj.keys())
    if len(node_ids) < 3:
        return {}

    # Sample source nodes for approximate centrality
    import random
    random.seed(42)  # Reproducible
    sources = random.sample(node_ids, min(sample_size, len(node_ids)))

    centrality = {n: 0.0 for n in node_ids}

    for source in sources:
        # BFS from source
        visited = {source}
        queue = [source]
        predecessors = {source: []}
        distance = {source: 0}
        order = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    distance[neighbor] = distance[current] + 1
                    predecessors[neighbor] = [current]
                elif distance[neighbor] == distance[current] + 1:
                    predecessors[neighbor].append(current)

        # Accumulate centrality (simplified Brandes algorithm)
        delta = {n: 0.0 for n in order}
        while order:
            w = order.pop()
            for v in predecessors.get(w, []):
                delta[v] += (1 + delta[w]) / max(1, len(predecessors.get(w, [])))
            if w != source:
                centrality[w] += delta[w]

    # Normalize
    max_c = max(centrality.values()) if centrality else 1
    if max_c > 0:
        for n in centrality:
            centrality[n] = round(centrality[n] / max_c * 10, 2)

    return centrality


# ---------------------------------------------------------------------------
# Walk Score Estimation
# ---------------------------------------------------------------------------

def compute_walk_scores(spots, network=None):
    """
    Compute a walk-score-like metric for each spot based on:
    - Nearby intersection density
    - Street connectivity
    - Proximity to high-centrality nodes

    Adds 'walk_score' (0-100) to each spot dict.
    """
    intersections = find_intersections(network)

    for spot in spots:
        # Count intersections within ~100m
        nearby_intersections = 0
        total_connectivity = 0
        for ix in intersections:
            dist = _haversine(
                spot["lat"], spot["lon"],
                ix["lat"], ix["lon"],
            )
            if dist < 0.15:  # ~150 meters
                nearby_intersections += 1
                total_connectivity += ix.get("connectivity_score", 0)

        # Walk score formula
        intersection_factor = min(40, nearby_intersections * 8)
        connectivity_factor = min(30, total_connectivity * 3)
        base_walkability = 30  # Franklin Street baseline

        spot["walk_score"] = min(
            100, base_walkability + intersection_factor + connectivity_factor
        )
        spot["nearby_intersections"] = nearby_intersections

    return spots


def _haversine(lat1, lon1, lat2, lon2):
    """Haversine distance in km between two lat/lon points."""
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
# Network Visualization Data
# ---------------------------------------------------------------------------

def get_network_lines(network=None):
    """
    Convert street network edges to line segments for map visualization.
    Returns list of [[from_lon, from_lat], [to_lon, to_lat]] pairs
    with color based on road type.
    """
    if network is None:
        network = fetch_street_network()

    if network.get("fallback"):
        return []

    lines = []
    color_map = {
        "primary": [255, 100, 100, 200],
        "secondary": [255, 165, 0, 180],
        "tertiary": [255, 255, 100, 160],
        "residential": [100, 200, 255, 140],
        "footway": [0, 255, 100, 120],
        "pedestrian": [0, 255, 150, 140],
        "path": [0, 200, 100, 100],
        "cycleway": [200, 100, 255, 120],
        "steps": [255, 200, 0, 120],
    }

    nodes = network["nodes"]
    for edge in network["edges"]:
        from_node = nodes.get(str(edge["from"])) or nodes.get(edge["from"])
        to_node = nodes.get(str(edge["to"])) or nodes.get(edge["to"])

        if from_node and to_node:
            color = color_map.get(edge.get("highway", ""), [150, 150, 150, 100])
            lines.append({
                "from": [from_node["lon"], from_node["lat"]],
                "to": [to_node["lon"], to_node["lat"]],
                "color": color,
                "highway": edge.get("highway", "unknown"),
                "name": edge.get("name", ""),
            })

    return lines
