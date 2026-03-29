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
    TREND_AREAS,
    DEFAULT_TREND_AREA,
    VENUE_SEARCH_KEYWORDS,
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
    Hyper-local Chapel Hill trend engine.

    Fuses multiple local data sources into venue-type interest scores:
    1. UNC Events Calendar — what's happening on campus NOW
    2. Reddit r/UNC + r/chapelhill — what students are talking about
    3. Google Trends RSS — national trends filtered for local relevance
    4. Time-of-day patterns — what Chapel Hill searches for at this hour

    Returns dict of {keyword_or_type: interest_score (0-100)}.
    All sources are free, no API keys, no rate limits.
    Cached for 30 minutes.
    """
    import json, os
    from xml.etree import ElementTree
    from datetime import datetime, timedelta
    import requests

    if keywords is None:
        keywords = SEED_KEYWORDS

    # File-based cache (30 min TTL for fresher local data)
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".franklinst_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "trends_local.json")

    try:
        if os.path.exists(cache_file):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if (datetime.now() - mtime) < timedelta(minutes=30):
                with open(cache_file) as f:
                    cached = json.load(f)
                if cached:
                    return cached
    except Exception:
        pass

    results = {}
    local_topics = []  # Raw trending topics for the Command panel
    hour = datetime.now().hour

    # --- Source 1: UNC Events (most reliable local signal) ---
    try:
        from intel import fetch_unc_events
        events = fetch_unc_events()
        if events:
            event_text = " ".join(e.get("title", "") + " " + e.get("description", "")
                                  for e in events).lower()
            # Score venue types by event keyword matches
            for vtype, vkws in VENUE_SEARCH_KEYWORDS.items():
                hits = sum(1 for kw in vkws if kw.lower() in event_text)
                if hits > 0:
                    results[vtype] = results.get(vtype, 0) + min(hits * 15, 60)

            # Extract top event topics
            for e in events[:10]:
                title = e.get("title", "")
                if title:
                    local_topics.append({"source": "UNC Events", "topic": title, "score": 70})

            print(f"  [+] Local trends: {len(events)} UNC events analyzed")
    except Exception as e:
        print(f"  [!] Local trends (events): {e}")

    # --- Source 2: Reddit — removed (rate limited on Fly.io servers) ---

    # --- Source 3: Google Trends RSS (national, filtered for local) ---
    try:
        rss_url = "https://trends.google.com/trending/rss?geo=US"
        resp = requests.get(rss_url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (compatible; academic research)",
        })
        if resp.status_code == 200:
            root = ElementTree.fromstring(resp.content)
            for item in root.iter("item"):
                title = item.findtext("title", "")
                if not title:
                    continue
                title_lower = title.lower()

                # Filter for local relevance
                if any(kw in title_lower for kw in LOCAL_RELEVANCE_KEYWORDS):
                    local_topics.append({
                        "source": "Google Trends",
                        "topic": title,
                        "score": 90,
                    })

                # Score venue types from national trends
                for vtype, vkws in VENUE_SEARCH_KEYWORDS.items():
                    if any(kw.lower() in title_lower for kw in vkws[:3]):
                        results[vtype] = results.get(vtype, 0) + 20
    except Exception as e:
        print(f"  [!] Local trends (RSS): {e}")

    # --- Source 4: Time-of-day baseline (Chapel Hill patterns) ---
    # What Chapel Hill searches for at this hour based on venue profiles
    from config import MFG_VENUE_PROFILES
    for vtype, profile in MFG_VENUE_PROFILES.items():
        if isinstance(profile, list) and len(profile) > hour:
            time_score = profile[hour]  # 0-100 from venue profile
            results[vtype] = results.get(vtype, 0) + int(time_score * 0.3)

    # Normalize all scores to 0-100
    if results:
        max_score = max(results.values()) if results.values() else 1
        for k in results:
            results[k] = min(100, int(results[k] * 100 / max(max_score, 1)))

    # Sort local topics by score
    local_topics.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Store topics alongside scores for the Command panel
    final = {
        **results,
        "_local_topics": local_topics[:20],
        "_source_count": sum(1 for s in ["events", "reddit", "rss"] if any(
            t.get("source", "").lower().startswith(s[:3]) for t in local_topics
        )),
    }

    # Cache
    try:
        with open(cache_file, "w") as f:
            json.dump(final, f)
    except Exception:
        pass

    print(f"  [+] Local trends: {len(results)} venue types, {len(local_topics)} topics")
    return final if results else None


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

def build_trends_report(seed_keywords=None, geo=DEFAULT_GEO, area=None):
    """
    Comprehensive trends report scoped to a specific area.
    Default: Chapel Hill / Triangle NC (DMA 560).
    Areas: chapel_hill, raleigh, charlotte, national.
    """
    if area and area in TREND_AREAS:
        geo = TREND_AREAS[area]["geo"]
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


# ---------------------------------------------------------------------------
# Search-to-Venue Convergence Engine
# ---------------------------------------------------------------------------

def compute_search_convergence(venues, hour=None, area=None):
    """
    Compute search trajectory → venue convergence scores.

    Maps Google Trends interest for venue-related keywords onto specific
    venues by type affinity, time modulation, and cuisine matching.

    This creates a "search convergence field" that predicts WHERE
    foot traffic will flow based on what people are searching for NOW.

    Returns:
        {
            "venue_scores": {venue_name: convergence_score (0-100)},
            "top_searches": [{keyword, score, venue_type, matching_count}],
            "heatmap": [[lat, lon, weight], ...],
        }
    """
    from datetime import datetime
    from config import MFG_VENUE_PROFILES

    if hour is None:
        hour = datetime.now().hour

    geo = DEFAULT_GEO
    if area and area in TREND_AREAS:
        geo = TREND_AREAS[area]["geo"]

    # Step 1: Build search keywords from venue type mappings
    all_search_kw = []
    kw_to_types = {}  # keyword -> set of venue types it maps to
    for vtype, keywords in VENUE_SEARCH_KEYWORDS.items():
        for kw in keywords:
            if kw not in kw_to_types:
                kw_to_types[kw] = set()
                all_search_kw.append(kw)
            kw_to_types[kw].add(vtype)

    # Step 2: Fetch interest scores for venue-related search terms
    # Use a subset to avoid API rate limits (top keywords per type)
    search_kw_subset = []
    for vtype, keywords in VENUE_SEARCH_KEYWORDS.items():
        search_kw_subset.extend(keywords[:3])  # Top 3 per type
    search_kw_subset = list(dict.fromkeys(search_kw_subset))[:25]

    interest = fetch_trends(keywords=search_kw_subset, geo=geo)
    if not interest:
        return {"venue_scores": {}, "top_searches": [], "heatmap": []}

    # Step 3: Compute per-venue-type aggregate interest
    type_interest = {}
    for kw, score in interest.items():
        for vtype in kw_to_types.get(kw, set()):
            if vtype not in type_interest:
                type_interest[vtype] = []
            type_interest[vtype].append(score)

    type_avg = {}
    for vtype, scores in type_interest.items():
        type_avg[vtype] = sum(scores) / len(scores) if scores else 0

    # Step 4: Time-modulate — searches for "bars" at 9pm matter more than at 9am
    for vtype in type_avg:
        profile = MFG_VENUE_PROFILES.get(vtype, MFG_VENUE_PROFILES.get("restaurant"))
        if profile:
            time_factor = profile[hour % 24] / 100.0
            # Blend: 60% raw interest + 40% time-weighted
            type_avg[vtype] = type_avg[vtype] * (0.6 + 0.4 * time_factor)

    # Step 5: Score each venue
    venue_scores = {}
    for v in venues:
        name = v.get("name", "")
        vtype = v.get("amenity_type", "unknown").lower()

        # Direct type match
        score = type_avg.get(vtype, 0)

        # Cuisine-based bonus: if venue cuisine matches a trending keyword
        cuisine = v.get("cuisine", "").lower()
        if cuisine:
            for kw, kw_score in interest.items():
                if kw.lower() in cuisine or cuisine in kw.lower():
                    score = max(score, kw_score * 0.8)

        venue_scores[name] = min(100, max(0, int(round(score))))

    # Step 6: Build top searches report
    top_searches = []
    for kw, score in sorted(interest.items(), key=lambda x: x[1], reverse=True)[:10]:
        matching_types = list(kw_to_types.get(kw, set()))
        matching_count = sum(1 for v in venues
                            if v.get("amenity_type", "").lower() in matching_types)
        top_searches.append({
            "keyword": kw,
            "score": score,
            "venue_types": matching_types,
            "matching_venues": matching_count,
        })

    # Step 7: Spatial convergence heatmap
    heatmap = []
    max_score = max(venue_scores.values()) if venue_scores else 1
    for v in venues:
        s = venue_scores.get(v.get("name", ""), 0)
        if s > 5 and max_score > 0:
            weight = s / max_score
            heatmap.append([v["lat"], v["lon"], weight])

    return {
        "venue_scores": venue_scores,
        "top_searches": top_searches,
        "heatmap": heatmap,
    }
