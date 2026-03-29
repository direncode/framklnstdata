"""
==============================================
  FRANKLIN STREET DATA
  BTUT Mean-Field Game Engine
==============================================
Kernel-Weighted Mean-Field Game simulator using forward
Fokker-Planck PDE density evolution.

  ∂ρ/∂t = -∇·(v[ρ]ρ) + σ²/2 Δρ

The drift velocity v[ρ] fuses live signals (trends, weather,
events, time-of-day, venue type) into a single continuous
density field over the Franklin Street corridor.

Gaussian RBF kernel: K(x,y) = exp(-||x-y||² / 2σ²)
Complexity: O(N) per step — no pairwise interactions.

References:
  - BTUT Technical Report v3.0 (Kumaratilleke, 2026)
  - btut.ai
"""

import math
import threading
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config import (
    FRANKLIN_STREET_SPINE,
    FRANKLIN_STREET_CENTER,
    MFG_CONFIG,
    MFG_SIGNAL_WEIGHTS,
    MFG_VENUE_PROFILES,
    MFG_DAY_MULTIPLIERS,
    MFG_FALLBACK_HOURS,
    VENUE_SEARCH_KEYWORDS,
    CACHE_DIR,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class MFGConfig:
    grid_size: int = 200
    kernel_bandwidth: float = 0.1
    diffusion: float = 0.02
    dt: float = 0.01
    max_iterations: int = 150
    convergence_threshold: float = 1e-5

    @classmethod
    def from_dict(cls, d: dict) -> "MFGConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Spatial Grid
# ---------------------------------------------------------------------------

def _build_grid(spine_points: list[tuple], n: int):
    """Discretize the Franklin Street spine into a 1D grid of n points.

    Returns:
        grid_lat: np.ndarray of latitudes
        grid_lon: np.ndarray of longitudes
        grid_dist: np.ndarray of cumulative distance (meters) along spine
        dx: grid spacing in meters
    """
    # Compute cumulative arc-length along spine
    lats = [p[0] for p in spine_points]
    lons = [p[1] for p in spine_points]
    cum_dist = [0.0]
    for i in range(1, len(lats)):
        d = _haversine(lats[i - 1], lons[i - 1], lats[i], lons[i])
        cum_dist.append(cum_dist[-1] + d)

    total_length = cum_dist[-1]

    # Interpolate n evenly-spaced points along the spine
    target_dists = np.linspace(0, total_length, n)
    grid_lat = np.interp(target_dists, cum_dist, lats)
    grid_lon = np.interp(target_dists, cum_dist, lons)

    dx = total_length / (n - 1) if n > 1 else 1.0
    return grid_lat, grid_lon, target_dists, dx


def _haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Opening Hours Parser
# ---------------------------------------------------------------------------

# OSM day abbreviations → Python weekday (0=Mon)
_OSM_DAYS = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}


def parse_opening_hours(hours_str):
    """Parse OSM opening_hours into a lookup: (day, hour) -> open/closed.

    Handles common formats:
      "Mo-Fr 08:00-22:00"
      "Mo-Fr 08:00-22:00; Sa-Su 10:00-23:00"
      "Mo-Su 11:00-02:00"  (wraps past midnight)
      "24/7"

    Returns a function: is_open(day: int, hour: int) -> bool
    Returns None if the string can't be parsed (treat as always open).
    """
    if not hours_str or not isinstance(hours_str, str):
        return None

    hours_str = hours_str.strip()
    if hours_str == "24/7":
        return lambda day, hour: True

    schedule = {}  # (day, hour) -> True

    try:
        for rule in hours_str.split(";"):
            rule = rule.strip()
            if not rule:
                continue

            # Split "Mo-Fr 08:00-22:00" into day part and time part
            parts = rule.split()
            if len(parts) < 2:
                continue

            day_part = parts[0]
            time_part = parts[1]

            # Parse day range
            days = _parse_day_range(day_part)
            if not days:
                continue

            # Parse time range
            open_h, close_h = _parse_time_range(time_part)
            if open_h is None:
                continue

            # Mark hours as open
            for d in days:
                if close_h > open_h:
                    for h in range(open_h, close_h):
                        schedule[(d, h)] = True
                else:
                    # Wraps past midnight (e.g., 20:00-02:00)
                    for h in range(open_h, 24):
                        schedule[(d, h)] = True
                    next_day = (d + 1) % 7
                    for h in range(0, close_h):
                        schedule[(next_day, h)] = True

        if not schedule:
            return None

        return lambda day, hour: schedule.get((day % 7, hour % 24), False)

    except Exception:
        return None


def _parse_day_range(day_str):
    """Parse 'Mo-Fr' or 'Sa,Su' or 'Mo' into list of day ints."""
    days = []
    for part in day_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start_i = _OSM_DAYS.get(start.strip()[:2])
            end_i = _OSM_DAYS.get(end.strip()[:2])
            if start_i is not None and end_i is not None:
                if end_i >= start_i:
                    days.extend(range(start_i, end_i + 1))
                else:
                    days.extend(range(start_i, 7))
                    days.extend(range(0, end_i + 1))
        else:
            d = _OSM_DAYS.get(part.strip()[:2])
            if d is not None:
                days.append(d)
    return days


def _parse_time_range(time_str):
    """Parse '08:00-22:00' into (8, 22)."""
    try:
        if "-" not in time_str:
            return None, None
        start, end = time_str.split("-", 1)
        open_h = int(start.split(":")[0])
        close_h = int(end.split(":")[0])
        return open_h, close_h
    except (ValueError, IndexError):
        return None, None


# ---------------------------------------------------------------------------
# BTUT Fokker-Planck Engine
# ---------------------------------------------------------------------------

class FranklinStreetMFG:
    """Fokker-Planck density solver for the Franklin Street corridor.

    Models foot traffic as a population density ρ(x,t) evolving on
    a 1D spatial grid under drift (venue attraction, signals) and
    diffusion (exploration noise).
    """

    def __init__(self, config: MFGConfig, venues: list[dict]):
        self.config = config
        self.venues = venues
        self.weights = MFG_SIGNAL_WEIGHTS

        # Build spatial grid
        n = config.grid_size
        self.grid_lat, self.grid_lon, self.grid_dist, self.dx = _build_grid(
            FRANKLIN_STREET_SPINE, n
        )
        self.n = n

        # Map each venue to its nearest grid index
        # Venues far from the spine (>200m) get time-profile-only busyness
        self.venue_indices = {}      # name -> grid index (on-spine venues)
        self.venue_types = {}        # name -> normalized type (all venues)
        self.off_spine_venues = {}   # name -> True (too far from spine)
        self.venue_hours = {}        # name -> is_open(day, hour) function or None

        for v in venues:
            name = v["name"]
            raw_type = v.get("amenity_type", "restaurant")
            self.venue_types[name] = self._normalize_type(raw_type)
            parsed = parse_opening_hours(v.get("opening_hours", ""))
            if parsed is None:
                # Fallback: use typical hours for this venue type
                ntype = self._normalize_type(raw_type)
                fallback = MFG_FALLBACK_HOURS.get(ntype)
                if fallback:
                    open_h, close_h = fallback
                    if close_h > open_h:
                        parsed = lambda day, hour, o=open_h, c=close_h: o <= hour < c
                    else:
                        parsed = lambda day, hour, o=open_h, c=close_h: hour >= o or hour < c
            self.venue_hours[name] = parsed

            idx = self._nearest_grid_index(v["lat"], v["lon"])
            dist = _haversine(v["lat"], v["lon"],
                              float(self.grid_lat[idx]), float(self.grid_lon[idx]))
            if dist <= 200:  # Within 200m of spine
                self.venue_indices[name] = idx
            else:
                self.off_spine_venues[name] = True

    def _nearest_grid_index(self, lat: float, lon: float) -> int:
        dists = np.sqrt(
            (self.grid_lat - lat) ** 2 + (self.grid_lon - lon) ** 2
        )
        return int(np.argmin(dists))

    @staticmethod
    def _normalize_type(amenity_type: str) -> str:
        t = amenity_type.lower()
        if t in ("bar", "biergarten", "brewery", "wine_bar"):
            return "bar"
        if "night" in t or "club" in t:
            return "nightclub"
        if t == "pub":
            return "pub"
        if t in ("cafe", "coffee", "tea"):
            return "cafe"
        if t in ("fast_food", "food_court"):
            return "fast_food"
        if t in ("ice_cream",):
            return "cafe"
        if t in ("pharmacy", "dentist", "doctors", "clinic", "hospital", "veterinary"):
            return "pharmacy"
        if t in ("bank", "atm", "post_office"):
            return "bank"
        if t in ("supermarket", "convenience", "marketplace"):
            return "supermarket"
        if t in ("cinema", "theatre", "arts_centre", "museum", "gallery"):
            return "cinema"
        if t in ("fitness_centre", "sports_centre", "swimming_pool"):
            return "fitness_centre"
        if t in ("hotel", "motel", "guest_house", "hostel"):
            return "hotel"
        if t in ("library",):
            return "library"
        if t in ("clothes", "books", "electronics", "hardware", "florist",
                 "beauty", "hairdresser", "tattoo", "bicycle", "sports",
                 "outdoor", "gift", "jewelry", "optician", "department_store",
                 "mall", "music", "bakery", "butcher", "deli", "greengrocer",
                 "alcohol", "tobacco"):
            return "shop"
        if t == "restaurant":
            return "restaurant"
        return "restaurant"

    # ----- Drift Velocity -----

    def compute_drift(self, rho: np.ndarray, hour: int, day: int,
                      signals: dict) -> np.ndarray:
        """Build drift velocity v[ρ](x) from multi-signal fusion.

        Components:
          1. Venue attraction — Gaussian pull toward venue positions
          2. Anti-crowding — negative gradient of density
          3. Time-of-day modulation — venue type hourly profiles
          4. Trends boost — amplify venues matching trending keywords
          5. Weather damping — reduce overall drift in bad weather
          6. Event surge — boost near event-proximate venues
          7. Day-of-week — weekend/weekday multiplier
        """
        w = self.weights
        n = self.n
        v = np.zeros(n)
        sigma = self.config.kernel_bandwidth
        dx = self.dx

        # Day-of-week multiplier
        day_mult = MFG_DAY_MULTIPLIERS[day % 7] if day is not None else 0.7

        # Weather damping factor (1.0 = good weather, reduced otherwise)
        weather_factor = 1.0
        weather = signals.get("weather")
        if weather and isinstance(weather, dict):
            if not weather.get("is_good_flyering_weather", True):
                weather_factor = 0.5

        # Trends interest map (keyword -> score 0-100)
        trends_interest = signals.get("trends_interest") or {}

        # Event count → surge multiplier
        events = signals.get("events")
        event_count = len(events) if isinstance(events, list) else 0
        event_surge = min(1.0 + event_count * 0.05, 2.0)  # Cap at 2x

        # Reddit social buzz — which venue types are being talked about
        reddit = signals.get("reddit_activity") or {}
        buzz_types = set(reddit.get("buzz_types", []))
        reddit_score = min(reddit.get("avg_score", 0) / 100.0, 1.0)

        # Transit stop positions → accessibility boost per grid cell
        transit_boost = np.zeros(n)
        transit_stops = signals.get("transit_stops")
        if transit_stops and isinstance(transit_stops, list):
            for stop in transit_stops:
                slat = stop.get("lat") or stop.get("stop_lat")
                slon = stop.get("lon") or stop.get("stop_lon")
                if slat and slon:
                    sidx = self._nearest_grid_index(float(slat), float(slon))
                    lo = max(0, sidx - 5)
                    hi = min(n, sidx + 6)
                    transit_boost[lo:hi] += 0.1
            transit_boost = np.minimum(transit_boost, 1.0)

        # Crime data → safety damping per grid cell
        crime_damping = np.ones(n)
        crime_data = signals.get("crime_data")
        if crime_data and isinstance(crime_data, list):
            for incident in crime_data:
                clat = incident.get("lat")
                clon = incident.get("lon")
                if clat and clon:
                    cidx = self._nearest_grid_index(float(clat), float(clon))
                    lo = max(0, cidx - 3)
                    hi = min(n, cidx + 4)
                    crime_damping[lo:hi] *= 0.95  # Each incident reduces by 5%
            crime_damping = np.maximum(crime_damping, 0.5)  # Floor at 50%

        # News keyword boost by venue type
        news_kw = signals.get("news_keywords") or {}

        # Demographics college multiplier
        demo = signals.get("demographics") or {}
        college_mult = demo.get("college_multiplier", 1.0)

        # --- Component 1: Venue attraction + time profile + all signals ---
        for name, idx in self.venue_indices.items():
            # Skip venues that are closed at this hour/day
            is_open_fn = self.venue_hours.get(name)
            if is_open_fn and not is_open_fn(day if day is not None else 0, hour):
                continue

            vtype = self.venue_types.get(name, "restaurant")
            profile = MFG_VENUE_PROFILES.get(vtype, MFG_VENUE_PROFILES["restaurant"])
            time_weight = profile[hour % 24] / 100.0

            # Base attraction strength
            attraction = w["venue_attraction"] * time_weight * w["time_profile"]

            # Trends boost
            trends_boost = 0.0
            for kw, score in trends_interest.items():
                kw_lower = kw.lower()
                if (vtype in kw_lower or
                    ("bar" in kw_lower and vtype in ("bar", "pub", "nightclub")) or
                    ("restaurant" in kw_lower and vtype == "restaurant") or
                    ("coffee" in kw_lower and vtype == "cafe") or
                    ("nightlife" in kw_lower and vtype in ("bar", "nightclub", "pub"))):
                    trends_boost = max(trends_boost, score / 100.0)
            attraction += trends_boost * w["trends_boost"]

            # Search convergence
            conv_by_type = signals.get("search_convergence_by_type") or {}
            conv_score = conv_by_type.get(vtype, 0) / 100.0
            if conv_score > 0:
                attraction += conv_score * w.get("search_convergence", 0.25)

            # Social buzz — Reddit mentions boost matching venue types
            if vtype in buzz_types:
                attraction += reddit_score * w.get("social_buzz", 0.1)

            # News boost — DTH headlines mentioning this venue type
            if vtype in news_kw:
                attraction += (news_kw[vtype] / 100.0) * w.get("news_boost", 0.1)

            # Transit accessibility boost at this grid position
            attraction += transit_boost[idx] * w.get("transit_access", 0.15)

            # Apply day and weather modulation
            attraction *= day_mult * w["day_of_week"]
            attraction *= weather_factor * (1.0 + (1.0 - weather_factor) * w["weather_damping"])
            attraction *= event_surge * w["event_surge"] if event_count > 0 else 1.0

            # Crime safety factor at this grid position
            attraction *= crime_damping[idx] ** w.get("crime_damping", 0.1)

            # Demographics college crowd boost (evening hours)
            if hour >= 17 or hour <= 2:
                attraction *= college_mult * w.get("demographics", 0.1)

            # Gaussian kernel pull toward this venue position
            grid_dists = (self.grid_dist - self.grid_dist[idx]) / (dx * 10 + 1e-8)
            kernel = np.exp(-grid_dists ** 2 / (2 * sigma ** 2))
            direction = -(self.grid_dist - self.grid_dist[idx])  # toward venue
            direction /= (np.abs(direction) + 1e-8)

            v += attraction * kernel * direction

        # --- Component 2: Anti-crowding (negative density gradient) ---
        if w["anti_crowding"] > 0:
            grad_rho = np.gradient(rho, dx)
            v -= w["anti_crowding"] * grad_rho / (rho.max() + 1e-8)

        return v

    # ----- Fokker-Planck Evolution -----

    def evolve_density(self, rho: np.ndarray, v_field: np.ndarray) -> np.ndarray:
        """One Fokker-Planck time step via finite differences.

        ∂ρ/∂t = -∂(ρv)/∂x + D ∂²ρ/∂x²
        """
        dt = self.config.dt
        dx = self.dx
        D = self.config.diffusion
        n = self.n

        rho_new = rho.copy()

        # Interior points (central differences)
        for i in range(1, n - 1):
            # Drift term: -∂(ρv)/∂x via central difference
            drift = (rho[i + 1] * v_field[i + 1] - rho[i - 1] * v_field[i - 1]) / (2 * dx)

            # Diffusion term: D ∂²ρ/∂x²
            diffusion = D * (rho[i + 1] - 2 * rho[i] + rho[i - 1]) / (dx ** 2)

            rho_new[i] = rho[i] + dt * (-drift + diffusion)

        # Reflective boundary conditions (no flux at ends)
        rho_new[0] = rho_new[1]
        rho_new[n - 1] = rho_new[n - 2]

        # Ensure non-negativity and normalize
        rho_new = np.maximum(rho_new, 0)
        total = np.sum(rho_new) * dx
        if total > 0:
            rho_new /= total

        return rho_new

    # ----- Solver -----

    def solve_hour(self, hour: int, day: int, signals: dict) -> dict:
        """Run Fokker-Planck to convergence for a single hour.

        Returns dict with:
          density_field: np.ndarray — final density ρ(x)
          venue_busyness: dict — {name: {busyness: 0-100, hourly_profile: [24]}}
          nash_gap: float — convergence metric
          iterations: int — steps taken
        """
        n = self.n
        dx = self.dx

        # Initial condition: uniform density
        rho = np.ones(n) / (n * dx)

        nash_gap = float("inf")
        iterations = 0

        for step in range(self.config.max_iterations):
            v_field = self.compute_drift(rho, hour, day, signals)
            rho_new = self.evolve_density(rho, v_field)

            # Nash gap: L2 norm of density change
            nash_gap = float(np.sqrt(np.sum((rho_new - rho) ** 2) * dx))
            rho = rho_new
            iterations = step + 1

            if nash_gap < self.config.convergence_threshold:
                break

        # Extract venue busyness from density
        venue_busyness = self._density_to_venue_busyness(rho, hour, day, signals)

        # Build signal breakdown per venue (for frontend transparency)
        signal_breakdown = self._compute_signal_breakdown(hour, day, signals)
        for name in venue_busyness:
            venue_busyness[name]["signals"] = signal_breakdown.get(name, {})

        return {
            "density_field": rho,
            "venue_busyness": venue_busyness,
            "nash_gap": nash_gap,
            "iterations": iterations,
        }

    def solve_24h(self, day: int, signals: dict) -> dict:
        """Generate full 24-hour density profiles for all venues.

        Returns dict with hourly_profiles per venue and convergence info.
        """
        all_names = list(self.venue_indices.keys()) + list(self.off_spine_venues.keys())
        hourly_profiles = {name: [] for name in all_names}
        convergence = {}
        density_fields = []

        for hour in range(24):
            result = self.solve_hour(hour, day, signals)
            density_fields.append(result["density_field"])
            convergence[hour] = result["nash_gap"]

            for name in all_names:
                vb = result["venue_busyness"].get(name, {})
                hourly_profiles[name].append(vb.get("busyness", 0))

        # Build venue_busyness with full profiles
        venue_busyness = {}
        for name in all_names:
            venue_busyness[name] = {
                "hourly_profile": hourly_profiles[name],
            }

        return {
            "hourly_profiles": hourly_profiles,
            "density_fields": density_fields,
            "convergence": convergence,
            "venue_busyness": venue_busyness,
        }

    # ----- Output Conversion -----

    def _density_to_venue_busyness(self, rho: np.ndarray, hour: int = 0,
                                    day: int = 0, signals: dict = None) -> dict:
        """Sample density at venue positions, normalize to 0-100.

        On-spine venues get density-based busyness.
        Off-spine venues get time-profile-based busyness.
        """
        result = {}

        # --- On-spine venues: sample from density field ---
        raw_values = {}
        for name, idx in self.venue_indices.items():
            # Check if venue is open
            is_open_fn = self.venue_hours.get(name)
            if is_open_fn and not is_open_fn(day, hour):
                result[name] = {"busyness": 0, "closed": True}
                continue

            lo = max(0, idx - 2)
            hi = min(self.n, idx + 3)
            raw_values[name] = float(np.mean(rho[lo:hi]))

        if raw_values:
            max_val = max(raw_values.values())
            min_val = min(raw_values.values())
            spread = max_val - min_val if max_val > min_val else 1e-8

            for name, raw in raw_values.items():
                busyness = int(round(((raw - min_val) / spread) * 100))
                busyness = max(0, min(100, busyness))
                result[name] = {"busyness": busyness}

        # --- Off-spine venues: time-profile based busyness ---
        day_mult = MFG_DAY_MULTIPLIERS[day % 7] if day is not None else 0.7
        weather_factor = 1.0
        if signals:
            weather = signals.get("weather")
            if weather and isinstance(weather, dict):
                if not weather.get("is_good_flyering_weather", True):
                    weather_factor = 0.6

        conv_by_type = (signals or {}).get("search_convergence_by_type") or {}
        news_kw = (signals or {}).get("news_keywords") or {}
        reddit = (signals or {}).get("reddit_activity") or {}
        buzz_types = set(reddit.get("buzz_types", []))
        reddit_score = min(reddit.get("avg_score", 0) / 100.0, 1.0)
        demo = (signals or {}).get("demographics") or {}
        college_mult = demo.get("college_multiplier", 1.0)

        for name in self.off_spine_venues:
            # Check if venue is open
            is_open_fn = self.venue_hours.get(name)
            if is_open_fn and not is_open_fn(day, hour):
                result[name] = {"busyness": 0, "closed": True}
                continue

            vtype = self.venue_types.get(name, "restaurant")
            profile = MFG_VENUE_PROFILES.get(vtype, MFG_VENUE_PROFILES["restaurant"])
            base = profile[hour % 24] / 100.0

            # Signal boosts for off-spine venues
            conv_boost = 1.0 + (conv_by_type.get(vtype, 0) / 100.0) * 0.3
            buzz_boost = 1.0 + (0.15 if vtype in buzz_types else 0) * reddit_score
            news_boost = 1.0 + (news_kw.get(vtype, 0) / 100.0) * 0.15
            evening_mult = college_mult if (hour >= 17 or hour <= 2) else 1.0

            busyness = int(round(
                base * day_mult * weather_factor * conv_boost
                * buzz_boost * news_boost * evening_mult * 100
            ))
            busyness = max(0, min(100, busyness))
            result[name] = {"busyness": busyness}

        return result

    def _compute_signal_breakdown(self, hour, day, signals):
        """Compute human-readable signal breakdown per venue.

        Returns {venue_name: {signal_name: description}} for transparency.
        """
        if not signals:
            return {}

        result = {}
        conv_by_type = signals.get("search_convergence_by_type") or {}
        news_kw = signals.get("news_keywords") or {}
        reddit = signals.get("reddit_activity") or {}
        buzz_types = set(reddit.get("buzz_types", []))
        weather = signals.get("weather") or {}
        events = signals.get("events")
        event_count = len(events) if isinstance(events, list) else 0
        day_mult = MFG_DAY_MULTIPLIERS[day % 7] if day is not None else 0.7

        all_names = list(self.venue_indices.keys()) + list(self.off_spine_venues.keys())
        for name in all_names:
            reasons = {}
            vtype = self.venue_types.get(name, "restaurant")
            profile = MFG_VENUE_PROFILES.get(vtype, MFG_VENUE_PROFILES.get("restaurant", [50]*24))
            time_val = profile[hour % 24]

            reasons["time_profile"] = f"{vtype} at {hour}:00 → {time_val}% typical"

            if day_mult < 0.7:
                reasons["day_of_week"] = f"Weekday dampening ({int(day_mult*100)}%)"
            elif day_mult >= 0.9:
                reasons["day_of_week"] = f"Weekend boost ({int(day_mult*100)}%)"

            if weather.get("is_good_flyering_weather") is False:
                desc = weather.get("description", "bad weather")
                reasons["weather"] = f"Bad weather: {desc} → reduced traffic"
            elif weather.get("description"):
                reasons["weather"] = f"{weather['description']}, {weather.get('temp_f', '?')}°F"

            if event_count > 0:
                reasons["events"] = f"{event_count} UNC events → {min(event_count*5, 100)}% surge"

            conv = conv_by_type.get(vtype, 0)
            if conv > 10:
                reasons["search_convergence"] = f"'{vtype}' trending at {int(conv)}% interest"

            if vtype in buzz_types:
                reasons["reddit"] = f"Active Reddit discussion about {vtype} venues"

            if vtype in news_kw:
                reasons["news"] = f"Daily Tar Heel mentions {vtype} ({news_kw[vtype]}% match)"

            # Check if closed
            is_open_fn = self.venue_hours.get(name)
            if is_open_fn and not is_open_fn(day if day is not None else 0, hour):
                reasons["status"] = "CLOSED at this hour"
            else:
                reasons["status"] = "OPEN"

            result[name] = reasons

        return result

    def density_to_heatmap(self, density_field: np.ndarray) -> list:
        """Convert density field to [[lat, lon, weight], ...] for heatmap.

        Samples every few grid points for a continuous corridor.
        """
        rho = density_field
        if rho.max() <= 0:
            return []

        # Normalize to 0-1 for heatmap weights
        rho_norm = rho / (rho.max() + 1e-12)

        points = []
        step = max(1, self.n // 100)  # ~100 heatmap points
        for i in range(0, self.n, step):
            w = float(rho_norm[i])
            if w > 0.02:
                points.append([float(self.grid_lat[i]), float(self.grid_lon[i]), w])

        return points


# ---------------------------------------------------------------------------
# Signal Collection
# ---------------------------------------------------------------------------

def collect_signals() -> dict:
    """Gather all live signal inputs for the MFG drift function.

    Calls existing modules. Each signal is optional — if an API
    fails, that signal is simply None and the drift function
    proceeds without it.
    """
    signals = {
        "trends_interest": None,
        "weather": None,
        "events": None,
        "reddit_activity": None,
        "search_convergence_by_type": None,
        "transit_stops": None,
        "crime_data": None,
        "news_keywords": None,
        "demographics": None,
    }

    # --- 1. Google Trends (writes to file cache — instant on subsequent calls) ---
    trends_scores = None
    try:
        from trends import fetch_trends
        from config import SEED_KEYWORDS
        # fetch_trends has 1-hour file cache — first call is slow, rest instant
        all_kw = list(SEED_KEYWORDS[:3])
        for vtype_kws in VENUE_SEARCH_KEYWORDS.values():
            all_kw.append(vtype_kws[0])
        all_kw = list(dict.fromkeys(all_kw))[:10]
        trends_scores = fetch_trends(keywords=all_kw)
        if trends_scores:
            signals["trends_interest"] = trends_scores
            print(f"    [sig] trends: {len(trends_scores)} keywords")
    except Exception as e:
        print(f"    [sig] trends: {e}")

    # --- 2. Search convergence by venue type (from trends, no extra API) ---
    if trends_scores:
        try:
            venue_type_scores = {}
            for vtype, kws in VENUE_SEARCH_KEYWORDS.items():
                matching = [trends_scores.get(kw, 0) for kw in kws if kw in trends_scores]
                if matching:
                    venue_type_scores[vtype] = sum(matching) / len(matching)
            if venue_type_scores:
                signals["search_convergence_by_type"] = venue_type_scores
                print(f"    [sig] convergence: {len(venue_type_scores)} types")
        except Exception:
            pass

    # --- 3. Weather ---
    try:
        from intel import fetch_weather
        weather = fetch_weather()
        if weather:
            signals["weather"] = weather
            print("    [sig] weather: OK")
    except Exception as e:
        print(f"    [sig] weather: {e}")

    # --- 4. UNC Events ---
    try:
        from intel import fetch_unc_events
        events = fetch_unc_events()
        if events:
            signals["events"] = events
            print(f"    [sig] events: {len(events)} found")
    except Exception as e:
        print(f"    [sig] events: {e}")

    # --- 5. Reddit social buzz ---
    try:
        from livefeed import fetch_reddit_feed
        posts = fetch_reddit_feed(limit=10)
        if posts:
            avg_score = sum(p.get("score", 0) for p in posts) / len(posts)
            titles = " ".join(p.get("title", "") for p in posts).lower()
            buzz_types = set()
            for vtype, kws in VENUE_SEARCH_KEYWORDS.items():
                if any(kw.lower() in titles for kw in kws[:3]):
                    buzz_types.add(vtype)
            signals["reddit_activity"] = {
                "avg_score": avg_score,
                "post_count": len(posts),
                "buzz_types": list(buzz_types),
            }
            print(f"    [sig] reddit: {len(posts)} posts, avg={avg_score:.0f}")
    except Exception as e:
        print(f"    [sig] reddit: {e}")

    # --- 6. Transit stop density ---
    try:
        from osint import fetch_transit_stops
        stops = fetch_transit_stops()
        if stops:
            signals["transit_stops"] = stops
            print(f"    [sig] transit: {len(stops)} stops")
    except Exception as e:
        print(f"    [sig] transit: {e}")

    # --- 7. Crime/incident data ---
    try:
        from osint import fetch_crime_data
        crimes = fetch_crime_data()
        if crimes:
            signals["crime_data"] = crimes
            print(f"    [sig] crime: {len(crimes)} incidents")
    except Exception as e:
        print(f"    [sig] crime: {e}")

    # --- 8. Daily Tar Heel headlines ---
    try:
        from livefeed import fetch_dth_feed
        articles = fetch_dth_feed()
        if articles:
            all_titles = " ".join(a.get("title", "") for a in articles).lower()
            news_kw = {}
            for vtype, kws in VENUE_SEARCH_KEYWORDS.items():
                hits = sum(1 for kw in kws if kw.lower() in all_titles)
                if hits > 0:
                    news_kw[vtype] = min(hits * 20, 100)
            if news_kw:
                signals["news_keywords"] = news_kw
            print(f"    [sig] news: {len(articles)} articles")
    except Exception as e:
        print(f"    [sig] news: {e}")

    # --- 9. Census demographics ---
    try:
        from intel import fetch_demographics
        demo = fetch_demographics()
        if demo:
            pct_18_24 = demo.get("pct_18_24", 0)
            signals["demographics"] = {
                "pct_college_age": pct_18_24,
                "college_multiplier": 1.0 + (pct_18_24 / 100.0) * 0.5,
            }
            print(f"    [sig] demographics: {pct_18_24:.1f}% college age")
    except Exception as e:
        print(f"    [sig] demographics: {e}")

    return signals


# ---------------------------------------------------------------------------
# Engine Singleton (cached per venue set)
# ---------------------------------------------------------------------------

_engine_cache: Optional[FranklinStreetMFG] = None
_engine_venue_count: int = 0

# Signals cache — populated by background thread, read by fast path
_signals_cache: dict = {}
_signals_lock = threading.Lock()
_signals_collecting: bool = False


def get_mfg_engine(venues: list[dict]) -> FranklinStreetMFG:
    """Get or create the MFG engine (cached singleton)."""
    global _engine_cache, _engine_venue_count

    if _engine_cache is not None and _engine_venue_count == len(venues):
        return _engine_cache

    config = MFGConfig.from_dict(MFG_CONFIG)
    _engine_cache = FranklinStreetMFG(config, venues)
    _engine_venue_count = len(venues)
    return _engine_cache
