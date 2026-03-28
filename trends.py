"""
==============================================
  FRANKLIN STREET DATA
  Hyper-Local Search Interpretation Engine
==============================================
Google Trends data at DMA level (Raleigh-Durham market,
which includes Chapel Hill). No state-level dilution.

DMA 560 = Raleigh-Durham-Fayetteville designated market area.
This is the most granular geo-targeting Google Trends supports.
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


def _get_pytrends():
    """Get a TrendReq instance or None if pytrends unavailable."""
    try:
        from pytrends.request import TrendReq
        return TrendReq(hl="en-US", tz=TRENDS_TIMEZONE)
    except ImportError:
        print("  [!] pytrends not installed. Run: pip install pytrends")
        return None


# ---------------------------------------------------------------------------
# Hyper-Local Interest (DMA 560: Raleigh-Durham-Chapel Hill)
# ---------------------------------------------------------------------------

def fetch_trends(keywords=None, geo=DEFAULT_GEO, timeframe=DEFAULT_TIMEFRAME):
    """
    Fetch Google Trends interest-over-time at DMA level.
    geo="US-NC-560" = Raleigh-Durham DMA (includes Chapel Hill).
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


def fetch_interest_by_city(keyword, geo="US-NC"):
    """
    Fetch interest breakdown by city within North Carolina.
    Shows which cities are searching for a term most —
    Chapel Hill vs Durham vs Raleigh vs Charlotte.
    Returns list of {city, interest} or None.
    """
    pytrends = _get_pytrends()
    if pytrends is None:
        return None

    try:
        pytrends.build_payload([keyword], timeframe="now 7-d", geo=geo)
        by_region = pytrends.interest_by_region(
            resolution="CITY",
            inc_low_vol=True,
            inc_geo_code=False,
        )
        if not by_region.empty:
            # Sort by interest descending
            by_region = by_region.sort_values(keyword, ascending=False)
            cities = []
            for city, row in by_region.head(15).iterrows():
                interest = int(row[keyword])
                if interest > 0:
                    cities.append({"city": city, "interest": interest})
            return cities
    except Exception as e:
        print(f"  [!] Interest by city error for '{keyword}': {e}")

    return None


# ---------------------------------------------------------------------------
# Related & Rising Queries (DMA Level)
# ---------------------------------------------------------------------------

def fetch_related_queries(keyword, geo=DEFAULT_GEO, timeframe=DEFAULT_TIMEFRAME):
    """
    Fetch rising related queries at DMA level.
    These are what people in the Raleigh-Durham area are ACTUALLY
    searching for related to this keyword right now.
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


def fetch_related_topics(keyword, geo=DEFAULT_GEO, timeframe=DEFAULT_TIMEFRAME):
    """
    Fetch rising related topics at DMA level.
    Topics are broader than queries — they group related searches together.
    """
    pytrends = _get_pytrends()
    if pytrends is None:
        return None

    try:
        pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo)
        related = pytrends.related_topics()
        if keyword in related and related[keyword]["rising"] is not None:
            df = related[keyword]["rising"]
            topics = []
            for _, row in df.head(8).iterrows():
                topics.append({
                    "title": row.get("topic_title", ""),
                    "type": row.get("topic_type", ""),
                    "value": int(row.get("value", 0)),
                })
            return topics
    except Exception as e:
        print(f"  [!] Related topics error for '{keyword}': {e}")

    return None


# ---------------------------------------------------------------------------
# Trending Searches (National, filtered for local relevance)
# ---------------------------------------------------------------------------

def fetch_trending_searches(geo="united_states"):
    """Fetch today's top trending searches nationally."""
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


def _is_locally_relevant(query):
    """Check if a trending query has NC / UNC / Chapel Hill relevance."""
    query_lower = query.lower()
    return any(kw in query_lower for kw in LOCAL_RELEVANCE_KEYWORDS)


# ---------------------------------------------------------------------------
# Real-Time Trending
# ---------------------------------------------------------------------------

def fetch_realtime_trending(cat="all", geo="US"):
    """Fetch real-time trending searches with context."""
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


# ---------------------------------------------------------------------------
# Full Trends Report (Hyper-Local)
# ---------------------------------------------------------------------------

def build_trends_report(seed_keywords=None, geo=DEFAULT_GEO):
    """
    Comprehensive trends report at DMA level.
    Everything scoped to Raleigh-Durham market (Chapel Hill).
    """
    if seed_keywords is None:
        all_kw = []
        for kws in TRIVIA_CATEGORIES.values():
            all_kw.extend(kws)
        seed_keywords = list(dict.fromkeys(all_kw))

    report = {
        "geo": geo,
        "geo_description": "Raleigh-Durham-Fayetteville DMA (includes Chapel Hill)",
        "interest_scores": None,
        "rising_queries": {},
        "rising_topics": {},
        "interest_by_city": {},
        "trending_now": None,
        "realtime": None,
        "locally_relevant": [],
    }

    # 1. Interest over time (DMA level)
    print(f"  [*] Fetching interest scores (geo={geo})...")
    report["interest_scores"] = fetch_trends(seed_keywords, geo=geo)

    if report["interest_scores"] is None:
        print("  [!] No trends data available")
        return report

    # 2. Rising queries for top keyword per category (DMA level)
    print("  [*] Fetching rising queries (DMA level)...")
    for category, keywords in TRIVIA_CATEGORIES.items():
        best_kw = max(keywords, key=lambda kw: report["interest_scores"].get(kw, 0))
        if report["interest_scores"].get(best_kw, 0) > 0:
            rising = fetch_related_queries(best_kw, geo=geo)
            if rising:
                report["rising_queries"][best_kw] = rising

            # Also get rising topics for top categories
            topics = fetch_related_topics(best_kw, geo=geo)
            if topics:
                report["rising_topics"][best_kw] = topics

            time.sleep(1)

    # 3. Interest by city for top keywords (where in NC is searching most)
    print("  [*] Fetching interest by city...")
    top_keywords = sorted(
        report["interest_scores"].items(), key=lambda x: x[1], reverse=True
    )[:3]
    for kw, _ in top_keywords:
        cities = fetch_interest_by_city(kw)
        if cities:
            report["interest_by_city"][kw] = cities
        time.sleep(1)

    # 4. Trending searches (national, filtered for local)
    print("  [*] Fetching trending searches...")
    report["trending_now"] = fetch_trending_searches()

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
    Generate trivia topic suggestions from hyper-local trends data.
    Returns (list of suggestions, has_data bool).
    """
    if trends_report is None or trends_report.get("interest_scores") is None:
        return [], False

    trends_data = trends_report["interest_scores"]
    rising_queries = trends_report.get("rising_queries", {})
    rising_topics = trends_report.get("rising_topics", {})
    locally_relevant = trends_report.get("locally_relevant", [])
    interest_by_city = trends_report.get("interest_by_city", {})

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
            topics = rising_topics.get(best_kw, [])
            cities = interest_by_city.get(best_kw, [])

            # Build city context if available
            city_note = ""
            if cities:
                top_cities = [c["city"] for c in cities[:3]]
                city_note = f" (trending most in: {', '.join(top_cities)})"

            suggestion = {
                "category": category,
                "keyword": best_kw,
                "score": best_score,
                "strength": strength,
                "marker": marker,
                "suggestion": _make_suggestion(category, best_kw, strength) + city_note,
                "related_rising": related or [],
                "rising_topics": [t["title"] for t in topics] if topics else [],
                "top_cities": cities[:5] if cities else [],
            }
            suggestions.append(suggestion)

    suggestions.sort(key=lambda s: s["score"], reverse=True)

    # Add locally relevant trending as bonus
    if locally_relevant:
        suggestions.insert(0, {
            "category": "Trending Locally (Triangle NC)",
            "keyword": ", ".join(locally_relevant[:3]),
            "score": 99,
            "strength": "HOT",
            "marker": ">>>",
            "suggestion": (
                f"Trending RIGHT NOW in the Triangle: {', '.join(locally_relevant[:5])}. "
                "Perfect for a 'what's happening right now' lightning round."
            ),
            "related_rising": locally_relevant[:8],
            "rising_topics": [],
            "top_cities": [],
        })

    return suggestions, True


def _make_suggestion(category, keyword, strength):
    """Generate a natural language trivia suggestion."""
    templates = {
        "UNC Sports": (
            f'"{keyword}" is trending {strength.lower()} in the Triangle. '
            "Great time for a round on Tar Heel athletes, recent game scores, "
            "or rivalry history."
        ),
        "Campus Life": (
            f'"{keyword}" is getting search interest locally. '
            "Try questions about campus traditions, famous alumni, or UNC history."
        ),
        "Franklin Street": (
            f'"{keyword}" is popular in local searches. '
            "Do a local round: name-the-bar-from-the-photo, Franklin Street "
            "history, or 'which restaurant has this menu item?'"
        ),
        "Pop Culture": (
            f'"{keyword}" is trending {strength.lower()}. '
            "Perfect for a pop culture lightning round."
        ),
        "NC News & Politics": (
            f'"{keyword}" is in the news locally. '
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
