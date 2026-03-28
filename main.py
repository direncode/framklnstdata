#!/usr/bin/env python3
"""
==============================================
  FRANKLIN STREET DATA
  Surveillance-Grade Intelligence Platform
  UNC Chapel Hill · Franklin Street
==============================================

Run standalone:   python franklinst.py
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

from spots import get_enriched_spots
from trends import build_trends_report, generate_trivia_suggestions
from traffic import get_ncdot_traffic


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
    Generate the complete Franklin Street Data report.
    Returns the report as a string.
    """
    lines = []
    now = datetime.now()
    if hour is None:
        hour = now.hour
    day_name = now.strftime("%A")

    lines.append("")
    lines.append("=" * 62)
    lines.append("   ███ FRANKLIN STREET DATA ███")
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

    spots = get_enriched_spots(hour=hour, top_n=num_spots)

    if not spots:
        lines.append("  No venues discovered (need network access for OSM)")
        lines.append("")
    else:
        lines.append(f"  {len(spots)} venues discovered via OpenStreetMap")
        lines.append("")

        # Venue type breakdown
        by_type = {}
        for s in spots:
            t = s.get("amenity_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        type_str = ", ".join(
            f"{v} {k}s" for k, v in sorted(
                by_type.items(), key=lambda x: x[1], reverse=True
            )
        )
        lines.append(f"  Types: {type_str}")
        lines.append("")

        # Busyness bar chart (only venues with live data)
        has_live = any(s.get("busyness") is not None for s in spots)
        if has_live:
            lines.append(f"  Live busyness at {hour}:00 (Google Places API):")
            lines.append("")
            for spot in spots:
                busyness = spot.get("busyness")
                if busyness is not None:
                    name = spot["name"][:35].ljust(35)
                    bar = _bar(busyness, 100, 20)
                    lines.append(f"  {name} {bar} {busyness:3d}%")
            lines.append("")
        else:
            lines.append("  Live busyness: unavailable (set GOOGLE_PLACES_API_KEY)")
            lines.append("  Venues are listed but cannot be ranked by activity.")
            lines.append("")

        # 24-hour sparklines
        has_hourly = any(s.get("hourly_profile") is not None for s in spots)
        if has_hourly:
            lines.append("  24-hour profiles (midnight → midnight):")
            lines.append("  " + "0   4   8   12  16  20  24")
            for spot in spots[:8]:
                hourly = spot.get("hourly_profile")
                if hourly:
                    spark = _sparkline_24h(hourly)
                    name = spot["name"][:28].ljust(28)
                    lines.append(f"  {name} {spark}")
            lines.append("")

    # NCDOT traffic context
    ncdot = get_ncdot_traffic()
    if ncdot:
        lines.append("  NCDOT Vehicle Traffic (AADT):")
        for road, data in ncdot.items():
            lines.append(f"    {road}: {data['aadt']:,} vehicles/day ({data['year']})")
        lines.append("")

    # ---------------------------------------------------------------
    # Section 2: Venues Ranked by Busyness
    # ---------------------------------------------------------------
    lines.append("─" * 62)
    lines.append("  ◉ SECTION 2: VENUES RANKED BY BUSYNESS")
    lines.append(f"  ({day_name} at {hour}:00)")
    lines.append("─" * 62)
    lines.append("")

    for i, spot in enumerate(spots[:num_spots], 1):
        busyness = spot.get("busyness")
        busyness_str = f"{busyness}%" if busyness is not None else "no data"
        vtype = spot.get("amenity_type", "")
        lines.append(f"  #{i} ─ {spot['name']} ({vtype})")
        lines.append(f"      Busyness: {busyness_str}")
        lines.append(f"      Coords: {spot['lat']:.5f}, {spot['lon']:.5f}")
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

    suggestions, has_data = generate_trivia_suggestions(trends_report)

    if not has_data:
        lines.append("  (No trends data — install pytrends for live data)")
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

    top5 = [s for s in spots[:5] if s.get("busyness") is not None]
    if top5:
        lines.append("  Busiest venues right now — go where the people are:")
        lines.append("")
        for i, spot in enumerate(top5, 1):
            lines.append(f"  {i}. {spot['name']} — {spot['busyness']}% busy")
        lines.append("")
    elif spots:
        lines.append("  Venues discovered but busyness unknown.")
        lines.append("  Set GOOGLE_PLACES_API_KEY to see which are busiest.")
        lines.append("")

    lines.append("  📊 Data Sources:")
    lines.append("  • OpenStreetMap Overpass API (venue discovery)")
    if any(s.get("busyness") is not None for s in spots):
        lines.append("  • Google Places API (live busyness)")
    if ncdot:
        lines.append("  • NCDOT ArcGIS (vehicle traffic counts)")
    if has_data:
        lines.append("  • Google Trends (live search interest)")
    lines.append("")

    lines.append("=" * 62)
    lines.append("   ███ End of Report — Go crush trivia night! ███")
    lines.append("=" * 62)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Franklin Street Data — Trivia Night Optimizer"
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
    print("  ███ Starting Franklin Street Data...")
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
