#!/usr/bin/env python3
"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Surveillance-Grade Intelligence Platform
  UNC Chapel Hill · Franklin Street
==============================================

Run standalone:   python panopticon.py
Run as web app:   streamlit run app.py
Run as API:       python datastream.py

Generates a combined surveillance report with:
  1. Live foot traffic analysis + heat map data
  2. Ranked placement spots for QR codes & flyers
  3. Trending trivia topic suggestions (Google Trends)
  4. Actionable recommendations
"""

import textwrap
from datetime import datetime

from spots import get_enriched_spots, get_ranked_spots
from trends import build_trends_report, generate_trivia_suggestions, FALLBACK_TRENDS
from traffic import (
    aggregate_busyness,
    fetch_nearby_places,
    get_ncdot_traffic,
)


# ---------------------------------------------------------------------------
# ASCII Visualization Helpers
# ---------------------------------------------------------------------------

def _bar(value, max_val=100, width=30):
    """Render a simple ASCII bar chart bar."""
    filled = int((value / max_val) * width)
    return "█" * filled + "░" * (width - filled)


def _sparkline_24h(hourly):
    """Render a 24-hour sparkline from hourly busyness values."""
    if not hourly or len(hourly) != 24:
        return "  (no hourly data)"
    blocks = " ▁▂▃▄▅▆▇█"
    max_v = max(hourly) if max(hourly) > 0 else 1
    chars = []
    for v in hourly:
        idx = int((v / max_v) * 8)
        idx = min(idx, 8)
        chars.append(blocks[idx])
    return "".join(chars)


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

def generate_report(
    time_of_day="evening",
    num_spots=8,
    fetch_live_trends=True,
    fetch_live_traffic=True,
    hour=None,
):
    """
    Generate the complete Franklin Street Panopticon v2 report.
    Returns the report as a string.
    """
    lines = []
    now = datetime.now()
    if hour is None:
        hour = now.hour
    day_name = now.strftime("%A")

    lines.append("")
    lines.append("=" * 62)
    lines.append("   ███ FRANKLIN STREET PANOPTICON v3 ███")
    lines.append("   Trivia Night Surveillance Report")
    lines.append(f"   Generated: {now.strftime('%B %d, %Y at %I:%M %p')}")
    lines.append(f"   Day: {day_name} | Analysis hour: {hour}:00")
    lines.append("=" * 62)
    lines.append("")

    # ---------------------------------------------------------------
    # Section 1: Live Foot Traffic Analysis
    # ---------------------------------------------------------------
    lines.append("─" * 62)
    lines.append("  ◉ SECTION 1: LIVE FOOT TRAFFIC ANALYSIS")
    lines.append("─" * 62)
    lines.append("")

    if fetch_live_traffic:
        spots = get_enriched_spots(
            time_of_day=time_of_day, hour=hour, top_n=num_spots
        )
    else:
        spots = get_ranked_spots(time_of_day=time_of_day, top_n=num_spots)

    # Show busyness bar chart
    lines.append(f"  Current busyness at {hour}:00 ({time_of_day} mode):")
    lines.append("")

    for spot in spots:
        busyness = spot.get("live_busyness", spot["foot_traffic"] * 10)
        name = spot["name"][:35].ljust(35)
        bar = _bar(busyness, 100, 20)
        lines.append(f"  {name} {bar} {busyness:3d}%")

    lines.append("")

    # 24-hour sparklines
    has_hourly = any("hourly_profile" in s for s in spots)
    if has_hourly:
        lines.append("  24-hour profiles (midnight → midnight):")
        lines.append("  " + "0   4   8   12  16  20  24")
        for spot in spots[:5]:
            hourly = spot.get("hourly_profile", [0] * 24)
            spark = _sparkline_24h(hourly)
            name = spot["name"][:28].ljust(28)
            lines.append(f"  {name} {spark}")
        lines.append("")

    # OSM venue discovery summary
    if fetch_live_traffic:
        try:
            osm_places = fetch_nearby_places()
            if osm_places:
                lines.append(
                    f"  OpenStreetMap scan: {len(osm_places)} venues detected "
                    f"within 400m of Franklin St"
                )
                by_type = {}
                for p in osm_places:
                    t = p.get("amenity_type", "other")
                    by_type[t] = by_type.get(t, 0) + 1
                type_str = ", ".join(
                    f"{v} {k}s" for k, v in sorted(
                        by_type.items(), key=lambda x: x[1], reverse=True
                    )
                )
                lines.append(f"  Breakdown: {type_str}")
                lines.append("")
        except Exception:
            pass

    # NCDOT traffic context
    ncdot = get_ncdot_traffic()
    if ncdot:
        lines.append("  NCDOT Vehicle Traffic (AADT, context data):")
        for road, data in ncdot.items():
            lines.append(f"    {road}: {data['aadt']:,} vehicles/day ({data['year']})")
        lines.append("")

    # ---------------------------------------------------------------
    # Section 2: Top Placement Spots
    # ---------------------------------------------------------------
    lines.append("─" * 62)
    lines.append("  ◉ SECTION 2: TOP SPOTS FOR QR CODES & FLYERS")
    lines.append(f"  (Ranked for {time_of_day} | {day_name})")
    lines.append("─" * 62)
    lines.append("")

    for i, spot in enumerate(spots, 1):
        busyness = spot.get("live_busyness", "N/A")
        lines.append(f"  #{i} ─ {spot['name']}")
        lines.append(f"      Score: {spot['composite_score']}/10 | "
                     f"Live busyness: {busyness}%")
        lines.append(f"      Address: {spot['address']}")
        lines.append(f"      Best times: {', '.join(spot['best_times'])}")
        lines.append(f"      Coords: {spot['lat']}, {spot['lon']}")
        lines.append("")
        # Wrap rationale
        for line in textwrap.wrap(f"Why: {spot['rationale']}", width=56):
            lines.append(f"      {line}")
        lines.append("")
        lines.append(f"      → TIP: {spot['placement_tip']}")
        lines.append("")
        lines.append("      " + "· " * 25)
        lines.append("")

    # ---------------------------------------------------------------
    # Section 3: Trending Trivia Topics
    # ---------------------------------------------------------------
    lines.append("─" * 62)
    lines.append("  ◉ SECTION 3: TRENDING TRIVIA TOPICS")
    lines.append("  (Google Trends · NC / Chapel Hill focus)")
    lines.append("─" * 62)
    lines.append("")

    trends_report = None
    if fetch_live_trends:
        lines.append("  Scanning Google Trends...")
        trends_report = build_trends_report()

    suggestions, using_fallback = generate_trivia_suggestions(trends_report)

    if using_fallback:
        lines.append("  (Using curated fallback data — "
                     "install pytrends for live data)")
    lines.append("")

    for s in suggestions:
        lines.append(
            f"  {s['marker']} [{s['strength']}] {s['category']} "
            f"(score: {s['score']})"
        )
        for line in textwrap.wrap(s["suggestion"], width=55):
            lines.append(f"      {line}")

        # Show rising queries if available
        if s.get("related_rising"):
            rising_str = ", ".join(s["related_rising"][:4])
            lines.append(f"      ↗ Rising searches: {rising_str}")

        lines.append("")

    # ---------------------------------------------------------------
    # Section 4: Action Plan
    # ---------------------------------------------------------------
    lines.append("─" * 62)
    lines.append("  ◉ SECTION 4: YOUR ACTION PLAN")
    lines.append("─" * 62)
    lines.append("")

    top3 = spots[:3]
    lines.append("  🎯 Quick Wins (do these today):")
    lines.append("")
    for i, spot in enumerate(top3, 1):
        busyness = spot.get("live_busyness", "")
        busyness_note = f" (currently {busyness}% busy)" if busyness else ""
        lines.append(f"  {i}. Place QR codes at {spot['name']}{busyness_note}")
        lines.append(f"     → {spot['placement_tip']}")
        lines.append("")

    lines.append("  📋 Trivia Night Prep:")
    lines.append("")
    hot_topics = [s for s in suggestions if s["strength"] == "HOT"]
    warm_topics = [s for s in suggestions if s["strength"] == "Warm"]

    if hot_topics:
        topic_names = ", ".join(t["category"] for t in hot_topics[:3])
        lines.append(f"  → Must-include categories: {topic_names}")
    if warm_topics:
        topic_names = ", ".join(t["category"] for t in warm_topics[:3])
        lines.append(f"  → Good backup categories: {topic_names}")
    lines.append("")

    lines.append("  ⏰ Timing:")
    lines.append("  → Post daytime flyers by 11am (catch the lunch crowd)")
    lines.append("  → Post evening flyers by 6pm (dinner-to-bar transition)")
    lines.append("  → Best nights: Tue, Wed, or Thu (less weekend competition)")
    lines.append("")

    lines.append("  📊 Data Sources Used:")
    data_sources = ["Static spot database (10 curated locations)"]
    if fetch_live_traffic:
        data_sources.append("OpenStreetMap Overpass API (venue discovery)")
        data_sources.append("Popular times estimation (hourly busyness)")
        data_sources.append("NCDOT AADT vehicle counts")
    if fetch_live_trends and not using_fallback:
        data_sources.append("Google Trends (live interest + rising queries)")
    else:
        data_sources.append("Curated trend fallback data")
    for ds in data_sources:
        lines.append(f"  • {ds}")
    lines.append("")

    lines.append("=" * 62)
    lines.append("   ███ End of Panopticon Report — Go crush trivia night! ███")
    lines.append("=" * 62)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Franklin Street Panopticon v2 — Trivia Night Optimizer"
    )
    parser.add_argument(
        "--time",
        choices=["morning", "daytime", "evening"],
        default="evening",
        help="Optimize for this time of day (default: evening)",
    )
    parser.add_argument(
        "--spots",
        type=int,
        default=8,
        help="Number of top spots to show (default: 8)",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=None,
        help="Simulate a specific hour (0-23) for busyness analysis",
    )
    parser.add_argument(
        "--no-trends",
        action="store_true",
        help="Skip live Google Trends fetch (use fallback data)",
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="Skip all live data (traffic + trends), use static only",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Save report to a file (e.g., --save report.txt)",
    )

    args = parser.parse_args()

    print()
    print("  ███ Starting Franklin Street Panopticon v2...")
    print()

    report = generate_report(
        time_of_day=args.time,
        num_spots=args.spots,
        fetch_live_trends=not (args.no_trends or args.no_live),
        fetch_live_traffic=not args.no_live,
        hour=args.hour,
    )

    print(report)

    if args.save:
        with open(args.save, "w") as f:
            f.write(report)
        print(f"\n  Report saved to {args.save}")
