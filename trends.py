"""
==============================================
  FRANKLIN STREET PANOPTICON v3
  Search Interpretation Engine (Live Only)
==============================================
All data fetched from Google Trends via pytrends.
No fallback data — if pytrends unavailable, returns None.
"""

import time

from config import (
    DEFAULT_GEO,
    DEFAULT_TIMEFRAME,
    TRENDS_TIMEZONE,
    SEED_KEYWORDS,
    TRIVIA_CATEGORIES,
    LOCAL_RELEVANCE_KEYWORDS,
)


# ---------------------------------------------------------------------------
# Core Trends Functions
# ---------------------------------------------------------------------------

def _get_pytrends():
    """Get a TrendReq instance or None if pytrends unavailable."""
    try:
        from pytrends.request import TrendReq
        return TrendReq(hl="en-US", tz=TRENDS_TIMEZONE)
    except ImportError:
        print("  [!] pytrends not installed. Run: pip install pytrends")
        return None


def fetch_trends(keywords=None, geo=DEFAULT_GEO, timeframe=DEFAULT_TIMEFRAME):
    """
    Fetch Google Trends interest-over-time for keywords.
    Returns dict of {keyword: avg_interest_score} or None.
    """
    if keywords is None:
        keywords = SEED_KEYWORDS

    pytrends = _get_pytrends()
    if pytrends is None:
        return None

    results = {}

    for i in range(0, len(keywords), 5):
        batch = keywords[i : i + 5]
        try:
            pytrends.build_payload(batch, cat=0, timeframe=timeframe, geo=geo)
            data = pytrends.interest_over_time()
            if not data.empty:
                for kw in batch:
                    if kw in data.columns:
                        results[kw] = int(data[kw].mean())
            time.sleep(2)
        except Exception as e:
            print(f"  [!] Trends API error for {batch}: {e}")
            time.sleep(5)
            continue

    return results if results else None


def fetch_related_queries(keyword, geo=DEFAULT_GEO, timeframe=DEFAULT_TIMEFRAME):
    """
    Fetch rising related queries for a keyword.
    Returns list of query strings or None.
    """
    pytrends = _get_pytrends()
    if pytrends is None:
        return None

    try:
        pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo)
        related = pytrends.related_queries()
        if keyword in related and related[keyword]["rising"] is not None:
            return related[keyword]["rising"]["query"].head(8).tolist()
        if keyword in related and related[keyword]["top"] is not None:
            return related[keyword]["top"]["query"].head(5).tolist()
    except Exception as e:
        print(f"  [!] Related queries error for '{keyword}': {e}")
        time.sleep(3)

    return None


def fetch_trending_searches(geo="united_states"):
    """
    Fetch today's top trending searches.
    Returns list of query strings or None.
    """
    pytrends = _get_pytrends()
    if pytrends is None:
        return None

    try:
        df = pytrends.trending_searches(pn=geo)
        if df is not None and not df.empty:
            return df[0].tolist()[:20]
    except Exception as e:
        print(f"  [!] Trending searches error: {e}")

    return None


def fetch_realtime_trending(cat="all", geo="US"):
    """
    Fetch real-time trending searches.
    Returns list of dicts or None.
    """
    pytrends = _get_pytrends()
    if pytrends is None:
        return None

    try:
        df = pytrends.realtime_trending_searches(pn=geo, cat=cat, count=20)
        if df is not None and not df.empty:
            results = []
            for _, row in df.head(15).iterrows():
                if "title" in row:
                    title = row["title"]
                elif "entityNames" in row:
                    title = row["entityNames"][0]
                else:
                    title = str(row.iloc[0])
                results.append({"title": str(title)})
            return results
    except Exception as e:
        print(f"  [!] Realtime trending error: {e}")

    return None


def _is_locally_relevant(query):
    """Check if a trending query has NC / UNC / Chapel Hill relevance."""
    query_lower = query.lower()
    return any(kw in query_lower for kw in LOCAL_RELEVANCE_KEYWORDS)


# ---------------------------------------------------------------------------
# Trends Report Builder
# ---------------------------------------------------------------------------

def build_trends_report(seed_keywords=None, geo=DEFAULT_GEO):
    """
    Orchestrate all trend fetching into a structured report.
    Returns None values for any feed that fails — no fake data.
    """
    if seed_keywords is None:
        all_kw = []
        for kws in TRIVIA_CATEGORIES.values():
            all_kw.extend(kws)
        seed_keywords = list(dict.fromkeys(all_kw))

    report = {
        "interest_scores": None,
        "rising_queries": {},
        "trending_now": None,
        "realtime": None,
        "locally_relevant": [],
    }

    # 1. Interest over time
    print("  [*] Fetching interest scores...")
    report["interest_scores"] = fetch_trends(seed_keywords, geo=geo)

    if report["interest_scores"] is None:
        print("  [!] No trends data available (pytrends required)")
        return report

    # 2. Rising queries for top keywords per category
    print("  [*] Fetching rising queries...")
    for category, keywords in TRIVIA_CATEGORIES.items():
        best_kw = None
        best_score = 0
        for kw in keywords:
            score = report["interest_scores"].get(kw, 0)
            if score > best_score:
                best_score = score
                best_kw = kw
        if best_kw:
            rising = fetch_related_queries(best_kw, geo=geo)
            if rising:
                report["rising_queries"][best_kw] = rising
            time.sleep(1)

    # 3. Today's trending searches
    print("  [*] Fetching today's trending searches...")
    report["trending_now"] = fetch_trending_searches()

    # 4. Filter for local relevance
    if report["trending_now"]:
        report["locally_relevant"] = [
            q for q in report["trending_now"] if _is_locally_relevant(q)
        ]

    # 5. Realtime trending
    print("  [*] Fetching realtime trends...")
    report["realtime"] = fetch_realtime_trending()

    return report


# ---------------------------------------------------------------------------
# Trivia Suggestion Generator
# ---------------------------------------------------------------------------

def generate_trivia_suggestions(trends_report=None):
    """
    Generate trivia topic suggestions from live trends data.
    Returns (list of suggestions, has_data bool).
    If no data available, returns empty list.
    """
    if trends_report is None or trends_report.get("interest_scores") is None:
        return [], False

    trends_data = trends_report["interest_scores"]
    rising_queries = trends_report.get("rising_queries", {})
    locally_relevant = trends_report.get("locally_relevant", [])

    suggestions = []

    for category, keywords in TRIVIA_CATEGORIES.items():
        best_kw = None
        best_score = 0
        for kw in keywords:
            score = trends_data.get(kw, 0)
            if score > best_score:
                best_score = score
                best_kw = kw

        if best_kw and best_score > 0:
            if best_score >= 75:
                strength = "HOT"
                marker = ">>>"
            elif best_score >= 50:
                strength = "Warm"
                marker = ">>"
            else:
                strength = "Mild"
                marker = ">"

            related = rising_queries.get(best_kw, [])

            suggestion = {
                "category": category,
                "keyword": best_kw,
                "score": best_score,
                "strength": strength,
                "marker": marker,
                "suggestion": _make_suggestion(category, best_kw, strength),
                "related_rising": related or [],
            }
            suggestions.append(suggestion)

    suggestions.sort(key=lambda s: s["score"], reverse=True)

    # Add locally relevant trending as bonus
    if locally_relevant:
        suggestions.insert(0, {
            "category": "Trending Locally (NC/UNC)",
            "keyword": ", ".join(locally_relevant[:3]),
            "score": 99,
            "strength": "HOT",
            "marker": ">>>",
            "suggestion": (
                f"Trending RIGHT NOW in NC: {', '.join(locally_relevant[:5])}. "
                "Perfect for a 'what's happening right now' lightning round."
            ),
            "related_rising": locally_relevant[:8],
        })

    return suggestions, True


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
            "UNC history."
        ),
        "Franklin Street": (
            f'"{keyword}" is popular in searches. '
            "Do a local round: name-the-bar-from-the-photo, Franklin Street "
            "history, or 'which restaurant has this menu item?'"
        ),
        "Pop Culture": (
            f'"{keyword}" is trending {strength.lower()}. '
            "Perfect for a pop culture lightning round — memes, viral moments, "
            "or 'name that TikTok sound.'"
        ),
        "NC News & Politics": (
            f'"{keyword}" is in the news. '
            "Add a current events round focused on North Carolina."
        ),
        "Science & Tech": (
            f'"{keyword}" is generating buzz. '
            "Tech-savvy students will love a science/tech round."
        ),
        "Music": (
            f'"{keyword}" is trending. '
            "Music rounds are crowd favorites — try name-that-tune."
        ),
        "Movies & TV": (
            f'"{keyword}" is getting attention. '
            "Movie/TV rounds work great — try screenshot identification."
        ),
    }
    return templates.get(
        category, f'"{keyword}" is trending — consider questions in this area.'
    )
