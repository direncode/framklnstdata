#!/usr/bin/env python3
"""
==============================================
  FRANKLIN STREET PANOPTICON v1
  Trivia Night Optimization for Bandidos
  UNC Chapel Hill · Franklin Street
==============================================

Run standalone:   python panopticon.py
Run as web app:   streamlit run app.py

This script generates a combined report with:
  1. Top foot traffic spots for QR/flyer placement
  2. Trending trivia topic suggestions from Google Trends
  3. Actionable recommendations
"""

import time
import textwrap
from datetime import datetime

from spots import get_ranked_spots

# ---------------------------------------------------------------------------
# Google Trends - Search Interpretation Engine
# ---------------------------------------------------------------------------

# Default seed keywords for UNC Chapel Hill trivia relevance
SEED_KEYWORDS = [
    "UNC basketball",
    "UNC Chapel Hill",
    "Franklin Street bars",
    "Chapel Hill events",
    "March Madness",
    "Tar Heels",
    "UNC football",
    "North Carolina news",
    "Chapel Hill restaurants",
    "college trivia",
]

# Category-keyword mapping for trivia topic generation
TRIVIA_CATEGORIES = {
    "UNC Sports": ["UNC basketball", "Tar Heels", "UNC football", "March Madness", "ACC tournament"],
    "Campus Life": ["UNC Chapel Hill", "Chapel Hill events", "UNC classes", "UNC housing"],
    "Franklin Street": ["Franklin Street bars", "Chapel Hill restaurants", "Chapel Hill nightlife"],
    "Pop Culture": ["TikTok trends", "Netflix popular", "viral meme", "Grammy awards"],
    "NC News & Politics": ["North Carolina news", "NC governor", "Raleigh news", "NC weather"],
    "Science & Tech": ["AI news", "space news", "new technology 2024", "science discovery"],
    "Music": ["new music releases", "concert tour 2024", "Spotify top songs"],
    "Movies & TV": ["new movies", "box office", "TV show premiere", "streaming new releases"],
}


def fetch_trends(keywords=None, geo="US-NC", timeframe="now 7-d"):
    """
    Fetch Google Trends data for a list of keywords.
    Returns a dict of {keyword: interest_score} or None on failure.

    Uses pytrends with rate-limit awareness and graceful fallback.
    """
    if keywords is None:
        keywords = SEED_KEYWORDS

    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("  [!] pytrends not installed. Using fallback trend data.")
        return None

    pytrends = TrendReq(hl="en-US", tz=300)  # EST timezone
    results = {}

    # pytrends allows max 5 keywords per request
    for i in range(0, len(keywords), 5):
        batch = keywords[i : i + 5]
        try:
            pytrends.build_payload(batch, cat=0, timeframe=timeframe, geo=geo)
            data = pytrends.interest_over_time()
            if not data.empty:
                for kw in batch:
                    if kw in data.columns:
                        results[kw] = int(data[kw].mean())
            # Be nice to Google - rate limit
            time.sleep(2)
        except Exception as e:
            print(f"  [!] Trends API error for {batch}: {e}")
            time.sleep(5)  # Back off on errors
            continue

    return results if results else None


def fetch_related_queries(keyword, geo="US-NC"):
    """Fetch rising related queries for a keyword from Google Trends."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []

    try:
        pytrends = TrendReq(hl="en-US", tz=300)
        pytrends.build_payload([keyword], cat=0, timeframe="now 7-d", geo=geo)
        related = pytrends.related_queries()
        if keyword in related and related[keyword]["rising"] is not None:
            rising = related[keyword]["rising"]
            return rising["query"].head(5).tolist()
    except Exception:
        pass
    return []


# Fallback trends when API is unavailable - manually curated for UNC relevance
FALLBACK_TRENDS = {
    "UNC basketball": 85,
    "Tar Heels": 72,
    "March Madness": 90,
    "Franklin Street bars": 55,
    "Chapel Hill events": 45,
    "UNC Chapel Hill": 65,
    "TikTok trends": 78,
    "Netflix popular": 60,
    "North Carolina news": 50,
    "AI news": 70,
}


def generate_trivia_suggestions(trends_data=None):
    """
    Generate trivia topic suggestions based on trends data.
    Returns a list of suggestion dicts with category, topic, score, and reasoning.
    """
    if trends_data is None:
        trends_data = FALLBACK_TRENDS
        using_fallback = True
    else:
        using_fallback = False

    suggestions = []

    for category, keywords in TRIVIA_CATEGORIES.items():
        # Find the highest-scoring keyword in this category
        best_kw = None
        best_score = 0
        for kw in keywords:
            score = trends_data.get(kw, 0)
            if score > best_score:
                best_score = score
                best_kw = kw

        if best_kw and best_score > 0:
            # Determine trend strength
            if best_score >= 75:
                strength = "HOT"
                emoji = ">>>"
            elif best_score >= 50:
                strength = "Warm"
                emoji = ">>"
            else:
                strength = "Mild"
                emoji = ">"

            suggestion = {
                "category": category,
                "keyword": best_kw,
                "score": best_score,
                "strength": strength,
                "emoji": emoji,
                "suggestion": _make_suggestion(category, best_kw, strength),
            }
            suggestions.append(suggestion)

    # Sort by score descending
    suggestions.sort(key=lambda s: s["score"], reverse=True)

    return suggestions, using_fallback


def _make_suggestion(category, keyword, strength):
    """Generate a natural language trivia suggestion."""
    templates = {
        "UNC Sports": (
            f'"{keyword}" is trending {strength.lower()} in NC. '
            "Great time for a round on Tar Heel athletes, recent game scores, "
            "or rivalry history (Duke vs UNC never gets old)."
        ),
        "Campus Life": (
            f'"{keyword}" is getting search interest. '
            "Try questions about campus traditions, famous alumni, or "
            "UNC history - students love showing off school knowledge."
        ),
        "Franklin Street": (
            f'"{keyword}" is popular in searches. '
            "Do a local round: name-the-bar-from-the-photo, Franklin Street "
            "history, or 'which restaurant has this menu item?'"
        ),
        "Pop Culture": (
            f'"{keyword}" is trending {strength.lower()}. '
            "Perfect for a pop culture lightning round - memes, viral moments, "
            "or 'name that TikTok sound.'"
        ),
        "NC News & Politics": (
            f'"{keyword}" is in the news. '
            "Add a current events round focused on North Carolina - "
            "local news, state politics, or weather events."
        ),
        "Science & Tech": (
            f'"{keyword}" is generating buzz. '
            "Tech-savvy students will love a science/tech round. Try "
            "AI trivia, space facts, or 'real or fake headline?'"
        ),
        "Music": (
            f'"{keyword}" is trending. '
            "Music rounds are crowd favorites - try name-that-tune, "
            "lyrics completion, or 'which artist said this?'"
        ),
        "Movies & TV": (
            f'"{keyword}" is getting attention. '
            "Movie/TV rounds work great - try screenshot identification, "
            "quote attribution, or 'which show is this plot twist from?'"
        ),
    }
    return templates.get(category, f'"{keyword}" is trending - consider questions in this area.')


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

def generate_report(time_of_day="evening", num_spots=8, fetch_live_trends=True):
    """
    Generate the complete Franklin Street Panopticon report.
    Returns the report as a string.
    """
    lines = []
    now = datetime.now()

    lines.append("=" * 60)
    lines.append("  FRANKLIN STREET PANOPTICON v1")
    lines.append("  Trivia Night Optimization Report")
    lines.append(f"  Generated: {now.strftime('%B %d, %Y at %I:%M %p')}")
    lines.append("=" * 60)
    lines.append("")

    # --- Section 1: Foot Traffic Spots ---
    lines.append("-" * 60)
    lines.append("  SECTION 1: TOP SPOTS FOR QR CODES & FLYERS")
    lines.append(f"  (Optimized for {time_of_day} placement)")
    lines.append("-" * 60)
    lines.append("")

    spots = get_ranked_spots(time_of_day=time_of_day, top_n=num_spots)

    for i, spot in enumerate(spots, 1):
        lines.append(f"  #{i} - {spot['name']}")
        lines.append(f"      Score: {spot['composite_score']}/10")
        lines.append(f"      Address: {spot['address']}")
        lines.append(f"      Best times: {', '.join(spot['best_times'])}")
        lines.append(f"      Coords: {spot['lat']}, {spot['lon']}")
        lines.append("")
        lines.append(f"      Why here: {spot['rationale']}")
        lines.append("")
        lines.append(f"      Tip: {spot['placement_tip']}")
        lines.append("")
        lines.append("      " + "- " * 25)
        lines.append("")

    # --- Section 2: Trending Trivia Topics ---
    lines.append("-" * 60)
    lines.append("  SECTION 2: TRENDING TRIVIA TOPICS")
    lines.append("  (Based on Google Trends for NC / Chapel Hill)")
    lines.append("-" * 60)
    lines.append("")

    trends_data = None
    if fetch_live_trends:
        lines.append("  Fetching live trends from Google...")
        all_keywords = []
        for kws in TRIVIA_CATEGORIES.values():
            all_keywords.extend(kws)
        # Deduplicate
        all_keywords = list(dict.fromkeys(all_keywords))
        trends_data = fetch_trends(all_keywords)

    suggestions, using_fallback = generate_trivia_suggestions(trends_data)

    if using_fallback:
        lines.append("  (Using curated fallback data - install pytrends for live data)")
        lines.append("")

    for s in suggestions:
        lines.append(f"  {s['emoji']} [{s['strength']}] {s['category']} (score: {s['score']})")
        wrapped = textwrap.wrap(s["suggestion"], width=55)
        for line in wrapped:
            lines.append(f"      {line}")
        lines.append("")

    # --- Section 3: Action Plan ---
    lines.append("-" * 60)
    lines.append("  SECTION 3: YOUR ACTION PLAN")
    lines.append("-" * 60)
    lines.append("")

    top3 = spots[:3]
    lines.append("  Quick Wins (do these today):")
    lines.append("")
    for i, spot in enumerate(top3, 1):
        lines.append(f"  {i}. Place QR codes at {spot['name']}")
        lines.append(f"     -> {spot['placement_tip']}")
        lines.append("")

    lines.append("  Trivia Night Prep:")
    lines.append("")
    hot_topics = [s for s in suggestions if s["strength"] == "HOT"]
    warm_topics = [s for s in suggestions if s["strength"] == "Warm"]

    if hot_topics:
        topic_names = ", ".join(t["category"] for t in hot_topics[:3])
        lines.append(f"  -> Must-include categories: {topic_names}")
    if warm_topics:
        topic_names = ", ".join(t["category"] for t in warm_topics[:3])
        lines.append(f"  -> Good backup categories: {topic_names}")
    lines.append("")

    lines.append("  Timing:")
    lines.append("  -> Post daytime flyers by 11am (catch the lunch crowd)")
    lines.append("  -> Post evening flyers by 6pm (catch the dinner-to-bar transition)")
    lines.append("  -> Best night for trivia: Tuesday, Wednesday, or Thursday")
    lines.append("     (less competition from weekend events)")
    lines.append("")

    lines.append("=" * 60)
    lines.append("  End of Report - Go crush trivia night!")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Franklin Street Panopticon - Trivia Night Optimizer"
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
        "--no-trends",
        action="store_true",
        help="Skip live Google Trends fetch (use fallback data)",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Save report to a file (e.g., --save report.txt)",
    )

    args = parser.parse_args()

    print()
    print("  Starting Franklin Street Panopticon...")
    print()

    report = generate_report(
        time_of_day=args.time,
        num_spots=args.spots,
        fetch_live_trends=not args.no_trends,
    )

    print(report)

    if args.save:
        with open(args.save, "w") as f:
            f.write(report)
        print(f"\n  Report saved to {args.save}")
