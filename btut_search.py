"""
==============================================
  FRANKLIN STREET DATA
  BTUT Keyword-Space Search Algorithm
==============================================
Applies Fokker-Planck Mean-Field Game dynamics to keyword space.

Keywords are agents. Trending topics create drift. Diffusion
prevents monoculture. The converged density reveals what
Chapel Hill is searching for right now.

  ∂ρ/∂t = -∂(v[ρ]ρ)/∂k + D_k ∂²ρ/∂k²

This runs BEFORE the geographic Fokker-Planck solver — the
keyword convergence feeds venue-type scores into the
geographic drift function as search_convergence_by_type.

Two PDEs in cascade:
  1. Keyword-space PDE → what Chapel Hill searches for
  2. Geographic PDE → where foot traffic flows
"""

import math
import json
import os
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from config import (
    VENUE_SEARCH_KEYWORDS,
    MFG_VENUE_PROFILES,
    LOCAL_RELEVANCE_KEYWORDS,
    CACHE_DIR,
    KEYWORD_MFG_CONFIG,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class KeywordMFGConfig:
    kernel_bandwidth: float = 2.0
    diffusion: float = 0.05
    dt: float = 0.01
    max_iterations: int = 100
    convergence_threshold: float = 1e-4
    anti_crowding: float = 0.2

    @classmethod
    def from_dict(cls, d: dict) -> "KeywordMFGConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Keyword Grid Construction
# ---------------------------------------------------------------------------

@dataclass
class KeywordAgent:
    index: int
    keyword: str
    venue_type: str


def build_keyword_grid() -> list[KeywordAgent]:
    """Construct 1D keyword grid from VENUE_SEARCH_KEYWORDS.

    Keywords are ordered by venue type group so semantically
    related keywords are adjacent on the grid.
    """
    grid = []
    idx = 0
    for vtype, keywords in VENUE_SEARCH_KEYWORDS.items():
        for kw in keywords:
            grid.append(KeywordAgent(index=idx, keyword=kw, venue_type=vtype))
            idx += 1
    return grid


# Module-level cached grid
_keyword_grid: Optional[list[KeywordAgent]] = None


def _get_grid() -> list[KeywordAgent]:
    global _keyword_grid
    if _keyword_grid is None:
        _keyword_grid = build_keyword_grid()
    return _keyword_grid


# ---------------------------------------------------------------------------
# Signal Scoring
# ---------------------------------------------------------------------------

def compute_keyword_signals(
    grid: list[KeywordAgent],
    events: list[dict] | None,
    rss_titles: list[str] | None,
    autocomplete: list[str] | None,
    hour: int,
    weather: dict | None,
) -> np.ndarray:
    """Compute raw signal score S(j) for each keyword position.

    Fuses 5 signal sources:
      1. UNC Events text matching
      2. Google Trends RSS title matching
      3. Google Autocomplete local suggestions (KEY LOCAL SIGNAL)
      4. Time-of-day baseline from venue profiles
      5. Weather modulation
    """
    n = len(grid)
    scores = np.zeros(n)

    # Build corpora
    event_text = ""
    if events:
        event_text = " ".join(
            e.get("title", "") + " " + e.get("description", "")
            for e in events
        ).lower()

    rss_text = ""
    if rss_titles:
        rss_text = " ".join(rss_titles).lower()

    # Google Autocomplete — what people ACTUALLY search for Chapel Hill
    autocomplete_text = ""
    if autocomplete:
        autocomplete_text = " ".join(autocomplete).lower()

    # Weather modulation
    is_bad_weather = False
    if weather and isinstance(weather, dict):
        is_bad_weather = not weather.get("is_good_flyering_weather", True)

    indoor_types = {"cafe", "cinema", "library", "fitness_centre", "shop", "supermarket"}
    outdoor_types = {"bar", "nightclub", "pub", "fast_food"}

    for agent in grid:
        kw_lower = agent.keyword.lower()
        vtype = agent.venue_type
        score = 0.0

        # 1. Event signal (0-60)
        if event_text and kw_lower in event_text:
            hits = event_text.count(kw_lower)
            score += min(hits * 15, 60)

        # 2. RSS signal (0-40)
        if rss_text and kw_lower in rss_text:
            hits = rss_text.count(kw_lower)
            score += min(hits * 20, 40)

        # 3. Autocomplete signal (0-50) — THE KEY LOCAL SIGNAL
        # If people are actively typing "chapel hill [keyword]" into Google,
        # that keyword is genuinely trending locally RIGHT NOW
        if autocomplete_text and kw_lower in autocomplete_text:
            hits = autocomplete_text.count(kw_lower)
            score += min(hits * 25, 50)

        # 4. Time-of-day baseline (0-30)
        profile = MFG_VENUE_PROFILES.get(vtype)
        if profile and isinstance(profile, list) and len(profile) > hour:
            score += profile[hour % 24] * 0.3

        # 5. Weather modulation
        if is_bad_weather:
            if vtype in indoor_types:
                score *= 1.3
            elif vtype in outdoor_types:
                score *= 0.5

        scores[agent.index] = score

    return scores


# ---------------------------------------------------------------------------
# Keyword-Space Fokker-Planck Solver
# ---------------------------------------------------------------------------

def keyword_fokker_planck(
    signal_scores: np.ndarray,
    config: KeywordMFGConfig,
) -> tuple[np.ndarray, float, int]:
    """Evolve keyword attention density via Fokker-Planck PDE.

    ∂ρ/∂t = -∂(v[ρ]ρ)/∂k + D_k ∂²ρ/∂k²

    where v(k) = Σ_j S(j) · K(k,j) · sign(j-k) - α · ∂ρ/∂k

    Returns (density_field, nash_gap, iterations).
    """
    n = len(signal_scores)
    if n < 3:
        return np.ones(n) / n, 0.0, 0

    dt = config.dt
    D = config.diffusion
    sigma = config.kernel_bandwidth
    alpha = config.anti_crowding

    # Initial uniform density
    rho = np.ones(n) / n

    # Precompute kernel matrix K(i,j) = exp(-|i-j|²/2σ²)
    indices = np.arange(n)
    kernel = np.exp(-(indices[:, None] - indices[None, :]) ** 2 / (2 * sigma ** 2))

    # Direction matrix: sign(j - i)
    direction = np.sign(indices[None, :] - indices[:, None])

    nash_gap = float("inf")
    iterations = 0

    for step in range(config.max_iterations):
        # Drift velocity: v(k) = Σ_j S(j) · K(k,j) · sign(j-k)
        v_field = np.dot(kernel * direction, signal_scores)

        # Anti-crowding: -α · ∂ρ/∂k
        if alpha > 0 and n > 2:
            grad_rho = np.gradient(rho)
            v_field -= alpha * grad_rho / (rho.max() + 1e-8)

        # Fokker-Planck step (central finite differences, dx=1)
        rho_new = rho.copy()
        for i in range(1, n - 1):
            drift = (rho[i + 1] * v_field[i + 1] - rho[i - 1] * v_field[i - 1]) / 2
            diffusion = D * (rho[i + 1] - 2 * rho[i] + rho[i - 1])
            rho_new[i] = rho[i] + dt * (-drift + diffusion)

        # Boundary conditions
        rho_new[0] = rho_new[1]
        rho_new[n - 1] = rho_new[n - 2]

        # Non-negativity + normalize
        rho_new = np.maximum(rho_new, 0)
        total = rho_new.sum()
        if total > 0:
            rho_new /= total

        # Nash gap
        nash_gap = float(np.sqrt(np.sum((rho_new - rho) ** 2)))
        rho = rho_new
        iterations = step + 1

        if nash_gap < config.convergence_threshold:
            break

    return rho, nash_gap, iterations


# ---------------------------------------------------------------------------
# Score Extraction
# ---------------------------------------------------------------------------

def density_to_keyword_scores(
    density: np.ndarray,
    grid: list[KeywordAgent],
) -> dict[str, float]:
    """Convert converged density to per-keyword scores (0-100)."""
    if density.max() <= 0:
        return {}

    # Normalize to 0-100
    d_min = density.min()
    d_max = density.max()
    spread = d_max - d_min if d_max > d_min else 1e-8

    scores = {}
    for agent in grid:
        raw = (density[agent.index] - d_min) / spread
        scores[agent.keyword] = max(0, min(100, int(round(raw * 100))))

    return scores


def aggregate_venue_type_scores(
    keyword_scores: dict[str, float],
    grid: list[KeywordAgent],
) -> dict[str, float]:
    """Aggregate keyword scores to venue type level.

    Uses softmax weighting so higher-scoring keywords contribute more.
    """
    type_scores: dict[str, list[float]] = {}
    for agent in grid:
        score = keyword_scores.get(agent.keyword, 0)
        if agent.venue_type not in type_scores:
            type_scores[agent.venue_type] = []
        type_scores[agent.venue_type].append(score)

    result = {}
    for vtype, scores in type_scores.items():
        if not scores:
            continue
        # Softmax-weighted mean: higher scores count more
        arr = np.array(scores, dtype=float)
        if arr.max() > 0:
            weights = np.exp(arr / max(arr.max(), 1) * 3)  # Temperature=3
            result[vtype] = float(np.average(arr, weights=weights))
        else:
            result[vtype] = 0.0

    return result


def compute_trajectories(
    current: dict[str, float],
    previous: dict[str, float] | None,
) -> dict[str, str]:
    """Compare current vs previous scores → rising/stable/falling."""
    if not previous:
        return {k: "stable" for k in current}

    result = {}
    for kw, score in current.items():
        prev = previous.get(kw, score)
        if score > prev + 5:
            result[kw] = "rising"
        elif score < prev - 5:
            result[kw] = "falling"
        else:
            result[kw] = "stable"
    return result


# ---------------------------------------------------------------------------
# Google Trends RSS Fetch (cached)
# ---------------------------------------------------------------------------

def _fetch_rss_titles() -> list[str]:
    """Fetch Google Trends RSS and extract titles. Cached 30 min."""
    import requests
    from xml.etree import ElementTree

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "rss_titles.json")

    try:
        if os.path.exists(cache_file):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if (datetime.now() - mtime) < timedelta(minutes=30):
                with open(cache_file) as f:
                    return json.load(f)
    except Exception:
        pass

    titles = []
    try:
        resp = requests.get(
            "https://trends.google.com/trending/rss?geo=US",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; academic research)"},
        )
        if resp.status_code == 200:
            root = ElementTree.fromstring(resp.content)
            for item in root.iter("item"):
                title = item.findtext("title", "")
                if title:
                    titles.append(title)
    except Exception as e:
        print(f"  [!] RSS fetch error: {e}")

    if titles:
        try:
            with open(cache_file, "w") as f:
                json.dump(titles, f)
        except Exception:
            pass

    return titles


def _fetch_local_autocomplete() -> list[str]:
    """Fetch Google Autocomplete suggestions for Chapel Hill queries.

    This is the key LOCAL signal — it returns what people ACTUALLY
    type into Google right now when searching for Chapel Hill venues.
    Free, no auth, no rate limits, ~200ms response time.
    Cached 30 minutes.
    """
    import requests

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "autocomplete_local.json")

    try:
        if os.path.exists(cache_file):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if (datetime.now() - mtime) < timedelta(minutes=30):
                with open(cache_file) as f:
                    return json.load(f)
    except Exception:
        pass

    suggestions = []
    # Query Google Autocomplete for Chapel Hill venue-related searches
    queries = [
        "chapel hill",
        "chapel hill restaurants",
        "chapel hill bars",
        "chapel hill things to do",
        "franklin street chapel hill",
        "best food chapel hill",
        "unc chapel hill events",
        "carrboro",
    ]

    for q in queries:
        try:
            url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={q}"
            resp = requests.get(url, timeout=5, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            })
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 1:
                    for s in data[1]:
                        if s and s != q:
                            suggestions.append(s)
        except Exception:
            continue

    # Deduplicate
    suggestions = list(dict.fromkeys(suggestions))

    if suggestions:
        try:
            with open(cache_file, "w") as f:
                json.dump(suggestions, f)
        except Exception:
            pass
        print(f"  [+] Autocomplete: {len(suggestions)} local suggestions")

    return suggestions


# ---------------------------------------------------------------------------
# Top-Level Solver
# ---------------------------------------------------------------------------

# Cache for trajectory comparison
_previous_keyword_scores: dict[str, float] = {}


def solve_keyword_mfg(
    hour: int,
    events: list[dict] | None = None,
    weather: dict | None = None,
) -> dict:
    """Run the full keyword-space Fokker-Planck solver.

    Returns dict with:
      keyword_scores: {keyword: 0-100}
      venue_type_scores: {vtype: 0-100}
      local_topics: [{keyword, score, venue_type, trajectory}]
      hot_keywords: [keywords with score >= 60]
      nash_gap: float
      iterations: int
    """
    global _previous_keyword_scores

    grid = _get_grid()
    config = KeywordMFGConfig.from_dict(KEYWORD_MFG_CONFIG)

    # Fetch both signal sources (cached 30 min each)
    rss_titles = _fetch_rss_titles()
    autocomplete = _fetch_local_autocomplete()

    # Filter RSS for local relevance
    local_rss = [t for t in rss_titles
                 if any(kw in t.lower() for kw in LOCAL_RELEVANCE_KEYWORDS)]

    # Compute raw signals (5 sources now)
    signals = compute_keyword_signals(
        grid, events, rss_titles, autocomplete, hour, weather,
    )

    # Run Fokker-Planck
    density, nash_gap, iterations = keyword_fokker_planck(signals, config)

    # Extract scores
    keyword_scores = density_to_keyword_scores(density, grid)
    venue_type_scores = aggregate_venue_type_scores(keyword_scores, grid)

    # Trajectories
    trajectories = compute_trajectories(keyword_scores, _previous_keyword_scores)
    _previous_keyword_scores = keyword_scores.copy()

    # Build local topics
    hot_keywords = [kw for kw, s in keyword_scores.items() if s >= 60]
    local_topics = []

    # Add hot keywords as topics
    for kw, score in sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)[:15]:
        if score > 10:
            # Find venue type for this keyword
            vtype = next((a.venue_type for a in grid if a.keyword == kw), "unknown")
            local_topics.append({
                "keyword": kw,
                "score": score,
                "venue_type": vtype,
                "trajectory": trajectories.get(kw, "stable"),
                "source": "BTUT Keyword MFG",
            })

    # Add Google Autocomplete discoveries (REAL local search data)
    if autocomplete:
        for suggestion in autocomplete[:8]:
            # Match suggestion to venue type
            s_lower = suggestion.lower()
            matched_type = "local"
            for vtype, kws in VENUE_SEARCH_KEYWORDS.items():
                if any(kw.lower() in s_lower for kw in kws[:5]):
                    matched_type = vtype
                    break
            local_topics.append({
                "keyword": suggestion,
                "score": 75,
                "venue_type": matched_type,
                "trajectory": "stable",
                "source": "Google Autocomplete",
            })

    # Add locally-relevant RSS topics
    for title in local_rss[:5]:
        local_topics.append({
            "keyword": title,
            "score": 80,
            "venue_type": "trending",
            "trajectory": "rising",
            "source": "Google Trends",
        })

    # Add UNC event titles
    if events:
        for e in events[:5]:
            title = e.get("title", "")
            if title:
                local_topics.append({
                    "keyword": title[:60],
                    "score": 70,
                    "venue_type": "event",
                    "trajectory": "stable",
                    "source": "UNC Events",
                })

    print(f"  [+] Keyword MFG: {len(hot_keywords)} hot keywords, "
          f"gap={nash_gap:.2e}, {iterations} steps")

    return {
        "keyword_scores": keyword_scores,
        "venue_type_scores": venue_type_scores,
        "local_topics": local_topics,
        "hot_keywords": hot_keywords,
        "nash_gap": nash_gap,
        "iterations": iterations,
    }
