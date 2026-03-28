"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Predictive Forecasting Engine
==============================================
Time series forecasting, seasonal decomposition,
causal inference models, and anomaly detection for
foot traffic prediction.
"""

import math
from datetime import datetime, timedelta
from collections import defaultdict

from config import FRANKLIN_STREET_CENTER

# ---------------------------------------------------------------------------
# Historical Baseline Data
# ---------------------------------------------------------------------------

# Typical weekly foot traffic patterns (pedestrians/hour by hour and day)
# Synthesized from transit data, venue busyness, and campus schedules
WEEKLY_BASELINE = {
    # Monday through Sunday (0-6), each with 24 hourly values
    0: [15, 8, 5, 5, 5, 8, 25, 70, 180, 320, 370, 460, 550, 500, 410, 360, 320, 370, 460, 550, 600, 480, 350, 200],
    1: [15, 8, 5, 5, 5, 8, 25, 70, 180, 320, 370, 460, 550, 500, 410, 360, 320, 370, 460, 550, 600, 480, 350, 200],
    2: [20, 10, 5, 5, 5, 10, 30, 80, 200, 350, 400, 500, 600, 550, 450, 400, 350, 400, 500, 600, 700, 650, 500, 300],
    3: [30, 15, 8, 5, 5, 10, 30, 80, 200, 350, 400, 500, 600, 550, 450, 400, 380, 450, 600, 750, 850, 800, 650, 400],
    4: [40, 20, 10, 5, 5, 10, 25, 70, 180, 320, 380, 480, 580, 530, 440, 400, 400, 500, 700, 900, 1000, 950, 800, 500],
    5: [50, 25, 12, 8, 5, 8, 20, 50, 120, 250, 350, 450, 550, 500, 450, 420, 450, 550, 750, 950, 1100, 1050, 900, 550],
    6: [35, 18, 10, 5, 5, 8, 20, 50, 100, 200, 300, 400, 500, 480, 400, 350, 300, 350, 450, 550, 600, 500, 380, 220],
}

# Seasonal multipliers by month (academic calendar impact)
SEASONAL_MULTIPLIERS = {
    1: 0.85,   # January - winter break → classes resume mid-month
    2: 1.0,    # February - full swing
    3: 1.15,   # March Madness boost (minus spring break)
    4: 1.05,   # April - last push before exams
    5: 0.5,    # May - exams → graduation → summer
    6: 0.35,   # June - summer session (low)
    7: 0.35,   # July - summer session (low)
    8: 0.7,    # August - move-in → classes start
    9: 1.1,    # September - football season, full enrollment
    10: 1.15,  # October - homecoming, peak engagement
    11: 1.0,   # November - Thanksgiving dip
    12: 0.6,   # December - exams → winter break
}

# Event-driven anomaly patterns
EVENT_ANOMALIES = {
    "basketball_win": {"multiplier": 4.0, "duration_hours": 3, "peak_offset_hours": 0},
    "basketball_loss": {"multiplier": 0.6, "duration_hours": 2, "peak_offset_hours": 0},
    "football_gameday": {"multiplier": 3.0, "duration_hours": 8, "peak_offset_hours": -4},
    "major_concert": {"multiplier": 2.0, "duration_hours": 4, "peak_offset_hours": -1},
    "severe_weather": {"multiplier": 0.2, "duration_hours": 6, "peak_offset_hours": 0},
    "exam_period": {"multiplier": 0.4, "duration_hours": 24, "peak_offset_hours": 0},
    "spring_break": {"multiplier": 0.15, "duration_hours": 168, "peak_offset_hours": 0},
    "move_in_day": {"multiplier": 1.8, "duration_hours": 12, "peak_offset_hours": -2},
}


# ---------------------------------------------------------------------------
# Forecasting Functions
# ---------------------------------------------------------------------------

def forecast_traffic(hours_ahead=24, start_hour=None, start_dow=None, start_month=None):
    """
    Forecast pedestrian foot traffic for the next N hours.

    Uses decomposition: baseline_weekly × seasonal_monthly × event_modifier

    Returns list of forecast dicts with hour, predicted_traffic, confidence.
    """
    now = datetime.now()
    if start_hour is None:
        start_hour = now.hour
    if start_dow is None:
        start_dow = now.weekday()
    if start_month is None:
        start_month = now.month

    seasonal = SEASONAL_MULTIPLIERS.get(start_month, 1.0)
    forecasts = []

    for offset in range(hours_ahead):
        forecast_hour = (start_hour + offset) % 24
        forecast_dow = (start_dow + (start_hour + offset) // 24) % 7

        base = WEEKLY_BASELINE[forecast_dow][forecast_hour]
        predicted = int(base * seasonal)

        # Confidence decreases with forecast horizon
        confidence = max(0.3, 1.0 - (offset * 0.02))

        # Confidence interval (±)
        margin = int(predicted * (1 - confidence) * 0.5)

        forecasts.append({
            "hours_from_now": offset,
            "hour": forecast_hour,
            "day_of_week": forecast_dow,
            "predicted_traffic": predicted,
            "confidence": round(confidence, 2),
            "lower_bound": max(0, predicted - margin),
            "upper_bound": predicted + margin,
            "seasonal_factor": seasonal,
        })

    return forecasts


def forecast_best_flyering_windows(day_of_week=None, month=None, top_n=5):
    """
    Find the best flyering windows for a given day.
    Ranks hours by predicted foot traffic.
    """
    if day_of_week is None:
        day_of_week = datetime.now().weekday()
    if month is None:
        month = datetime.now().month

    seasonal = SEASONAL_MULTIPLIERS.get(month, 1.0)
    baseline = WEEKLY_BASELINE[day_of_week]

    hours_ranked = []
    for hour, base in enumerate(baseline):
        predicted = int(base * seasonal)
        hours_ranked.append({
            "hour": hour,
            "hour_label": f"{hour}:00",
            "predicted_traffic": predicted,
        })

    hours_ranked.sort(key=lambda h: h["predicted_traffic"], reverse=True)

    # Group into windows
    windows = []
    for entry in hours_ranked[:top_n]:
        h = entry["hour"]
        if h < 12:
            period = "Morning"
        elif h < 17:
            period = "Afternoon"
        else:
            period = "Evening"

        windows.append({
            **entry,
            "period": period,
            "recommendation": _window_recommendation(h, entry["predicted_traffic"]),
        })

    return windows


def _window_recommendation(hour, traffic):
    """Generate a recommendation for a flyering window."""
    if traffic > 800:
        return f"PRIME window at {hour}:00 — ~{traffic} pedestrians/hour. Maximum exposure."
    elif traffic > 500:
        return f"Strong window at {hour}:00 — ~{traffic} pedestrians/hour. Good visibility."
    elif traffic > 300:
        return f"Decent window at {hour}:00 — ~{traffic} pedestrians/hour. Moderate traffic."
    else:
        return f"Low traffic at {hour}:00 — ~{traffic} pedestrians/hour. Consider skipping."


# ---------------------------------------------------------------------------
# Seasonal Decomposition
# ---------------------------------------------------------------------------

def decompose_seasonal(day_of_week=None):
    """
    Decompose foot traffic into trend, seasonal, and residual components.
    Returns components for visualization.
    """
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    baseline = WEEKLY_BASELINE[day_of_week]

    # Trend: moving average (smoothed)
    trend = []
    window = 5
    for i in range(24):
        start = max(0, i - window // 2)
        end = min(24, i + window // 2 + 1)
        trend.append(int(sum(baseline[start:end]) / (end - start)))

    # Seasonal: deviation from trend
    seasonal = [baseline[i] - trend[i] for i in range(24)]

    # Residual: what's left after trend + seasonal
    residual = [baseline[i] - trend[i] - seasonal[i] for i in range(24)]

    return {
        "day_of_week": day_of_week,
        "observed": baseline,
        "trend": trend,
        "seasonal": seasonal,
        "residual": residual,
        "peak_hour": baseline.index(max(baseline)),
        "trough_hour": baseline.index(min(baseline)),
    }


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------

def detect_anomalies(observed_values, day_of_week=None, threshold_sigma=2.0):
    """
    Detect anomalous foot traffic by comparing observed to expected.
    Returns list of anomaly dicts.
    """
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    expected = WEEKLY_BASELINE[day_of_week]
    anomalies = []

    for hour in range(min(24, len(observed_values))):
        exp = expected[hour]
        obs = observed_values[hour]
        if exp == 0:
            continue

        # Z-score approximation (using 20% of expected as std dev)
        std_dev = max(exp * 0.2, 10)
        z_score = (obs - exp) / std_dev

        if abs(z_score) > threshold_sigma:
            anomalies.append({
                "hour": hour,
                "observed": obs,
                "expected": exp,
                "z_score": round(z_score, 2),
                "type": "spike" if z_score > 0 else "dip",
                "severity": "high" if abs(z_score) > 3 else "medium",
                "possible_cause": _anomaly_cause(hour, z_score),
            })

    return anomalies


def _anomaly_cause(hour, z_score):
    """Suggest possible causes for anomalous foot traffic."""
    if z_score > 3:
        if 18 <= hour <= 23:
            return "Possible game day aftermath or major event"
        elif 10 <= hour <= 14:
            return "Possible special campus event or protest"
        else:
            return "Unusual spike — check for events or weather"
    elif z_score < -2:
        if 18 <= hour <= 23:
            return "Possible severe weather, exam period, or break"
        else:
            return "Lower than expected — weather or campus closure?"
    return "Minor deviation from normal pattern"


# ---------------------------------------------------------------------------
# Impact Simulation
# ---------------------------------------------------------------------------

def simulate_event_impact(event_type, event_hour=None, day_of_week=None):
    """
    Simulate the impact of an event on foot traffic.
    Returns modified traffic profile with event overlay.
    """
    if event_hour is None:
        event_hour = 19  # Default 7pm
    if day_of_week is None:
        day_of_week = datetime.now().weekday()

    baseline = list(WEEKLY_BASELINE[day_of_week])
    event = EVENT_ANOMALIES.get(event_type)

    if not event:
        return {
            "error": f"Unknown event type: {event_type}",
            "available_types": list(EVENT_ANOMALIES.keys()),
        }

    modified = list(baseline)
    center = event_hour + event.get("peak_offset_hours", 0)
    duration = event["duration_hours"]
    multiplier = event["multiplier"]

    for h in range(24):
        distance_from_center = abs(h - center)
        if distance_from_center <= duration / 2:
            # Gaussian-like tapering
            taper = math.exp(-0.5 * (distance_from_center / (duration / 4)) ** 2)
            boost = (multiplier - 1) * taper
            modified[h] = int(baseline[h] * (1 + boost))

    return {
        "event_type": event_type,
        "event_hour": event_hour,
        "day_of_week": day_of_week,
        "baseline": baseline,
        "modified": modified,
        "multiplier": multiplier,
        "peak_modified": max(modified),
        "peak_baseline": max(baseline),
        "total_additional_pedestrians": sum(modified) - sum(baseline),
    }


# ---------------------------------------------------------------------------
# Combined Forecast Report
# ---------------------------------------------------------------------------

def build_forecast_report(hours_ahead=24):
    """Build comprehensive forecast report."""
    now = datetime.now()

    return {
        "forecast": forecast_traffic(hours_ahead),
        "best_windows": forecast_best_flyering_windows(),
        "decomposition": decompose_seasonal(),
        "event_simulations": {
            "basketball_win": simulate_event_impact("basketball_win"),
            "severe_weather": simulate_event_impact("severe_weather"),
            "exam_period": simulate_event_impact("exam_period"),
        },
        "seasonal_factor": SEASONAL_MULTIPLIERS.get(now.month, 1.0),
        "generated_at": now.isoformat(),
    }
