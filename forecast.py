"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Live Signal Forecast
==============================================
Forecasting based on live data feeds only.
Uses Google Trends momentum + weather + UNC events + Reddit
to assess current conditions.

No hardcoded baselines. No event multipliers.
"""

from datetime import datetime


def forecast_from_live_data():
    """
    Build a forecast using whatever live data is actually available.
    Returns a structured report with clear provenance for each signal.
    """
    signals = {}

    # Signal 1: Google Trends momentum
    try:
        from trends import fetch_trends
        trends = fetch_trends(["Franklin Street bars", "Chapel Hill nightlife", "UNC events"])
        if trends:
            signals["trends"] = {
                "data": trends,
                "source": "Google Trends (live via pytrends)",
            }
    except Exception:
        pass

    # Signal 2: Weather conditions
    try:
        from intel import fetch_weather
        weather = fetch_weather()
        if weather:
            signals["weather"] = {
                "data": weather,
                "source": weather.get("source", "OpenWeatherMap"),
                "is_good_for_flyering": weather.get("is_good_flyering_weather"),
            }
    except Exception:
        pass

    # Signal 3: UNC Events
    try:
        from intel import fetch_unc_events
        events = fetch_unc_events()
        if events:
            signals["unc_events"] = {
                "count": len(events),
                "upcoming": events[:5],
                "source": "UNC Calendar API (live)",
            }
    except Exception:
        pass

    # Signal 4: Reddit activity
    try:
        from osint import fetch_reddit_posts
        posts = fetch_reddit_posts("UNC", limit=10)
        if posts:
            avg_score = sum(p["score"] for p in posts) / len(posts)
            signals["reddit"] = {
                "avg_post_score": round(avg_score, 1),
                "recent_topics": [p["title"][:80] for p in posts[:5]],
                "source": "Reddit JSON API (live)",
            }
    except Exception:
        pass

    # Signal 5: Transit stops
    try:
        from osint import fetch_transit_stops
        stops = fetch_transit_stops()
        if stops:
            signals["transit"] = {
                "stops_nearby": len(stops),
                "source": "Chapel Hill Transit GTFS (live)",
            }
    except Exception:
        pass

    recommendation = _build_recommendation(signals)

    return {
        "signals": signals,
        "signal_count": len(signals),
        "recommendation": recommendation,
        "generated_at": datetime.now().isoformat(),
    }


def _build_recommendation(signals):
    """Synthesize available signals into recommendations."""
    recs = []

    weather = signals.get("weather", {})
    if weather:
        if weather.get("is_good_for_flyering"):
            recs.append("Weather is favorable for outdoor flyering.")
        elif weather.get("is_good_for_flyering") is False:
            recs.append("Weather is unfavorable — focus on indoor placements.")

    events = signals.get("unc_events", {})
    if events:
        count = events.get("count", 0)
        if count > 5:
            recs.append(f"{count} UNC events this week — high campus activity.")
        elif count > 0:
            recs.append(f"{count} UNC events this week — moderate campus activity.")

    trends = signals.get("trends", {})
    if trends and trends.get("data"):
        data = trends["data"]
        nightlife_score = data.get("Chapel Hill nightlife", 0)
        if nightlife_score > 70:
            recs.append(f"'Chapel Hill nightlife' trending at {nightlife_score} — high interest.")
        elif nightlife_score > 40:
            recs.append(f"'Chapel Hill nightlife' at {nightlife_score} — moderate interest.")

    if not recs:
        recs.append("Insufficient live data. Set API keys for better forecasting.")

    return recs


def build_forecast_report():
    """Build forecast from live signals only."""
    return {
        "live_forecast": forecast_from_live_data(),
        "generated_at": datetime.now().isoformat(),
    }
