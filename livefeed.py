"""
==============================================
  FRANKLIN STREET DATA
  Live Keyword Feed
==============================================
Real-time monitoring of UNC / Chapel Hill keywords
from multiple live sources.

Sources (all free, no API key needed):
  - Reddit r/UNC, r/chapelhill, r/NorthCarolina (JSON API)
  - Google Trends rising queries (pytrends)
  - UNC Events Calendar (Localist JSON API)
  - The Daily Tar Heel RSS feed

All data is fetched live. Nothing hardcoded.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from xml.etree import ElementTree

import requests

from config import (
    CACHE_DIR,
    LOCAL_RELEVANCE_KEYWORDS,
    TRIVIA_CATEGORIES,
)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_path():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _read_cache(key, max_age_hours=0.5):
    fp = os.path.join(_cache_path(), f"{key}.json")
    if not os.path.exists(fp):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(fp))
    if (datetime.now() - mtime) > timedelta(hours=max_age_hours):
        return None
    try:
        with open(fp) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _write_cache(key, data):
    fp = os.path.join(_cache_path(), f"{key}.json")
    with open(fp, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Reddit Live Feed
# ---------------------------------------------------------------------------

def fetch_reddit_feed(subreddits=None, limit=15):
    """
    Fetch recent posts from UNC/Chapel Hill subreddits.
    Uses Reddit's public JSON endpoint (no API key needed).
    """
    if subreddits is None:
        subreddits = ["UNC", "chapelhill", "NorthCarolina"]

    cache_key = "livefeed_reddit"
    cached = _read_cache(cache_key, max_age_hours=0.25)
    if cached:
        return cached

    all_posts = []
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit}"
        try:
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; FranklinStData/4.0; academic research)",
            })
            if resp.status_code == 200:
                data = resp.json()
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    all_posts.append({
                        "source": f"r/{sub}",
                        "title": post.get("title", ""),
                        "score": post.get("score", 0),
                        "comments": post.get("num_comments", 0),
                        "created": datetime.fromtimestamp(
                            post.get("created_utc", 0)
                        ).isoformat(),
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "flair": post.get("link_flair_text", ""),
                    })
            time.sleep(1)  # Rate limit between subreddits
        except Exception as e:
            print(f"  [!] Reddit r/{sub} error: {e}")

    if all_posts:
        # Sort by recency
        all_posts.sort(key=lambda p: p["created"], reverse=True)
        _write_cache(cache_key, all_posts)

    return all_posts if all_posts else None


# ---------------------------------------------------------------------------
# Daily Tar Heel RSS Feed
# ---------------------------------------------------------------------------

def fetch_dth_feed():
    """
    Fetch recent articles from The Daily Tar Heel via RSS.
    The DTH is UNC's student newspaper — real-time campus news.
    """
    cache_key = "livefeed_dth"
    cached = _read_cache(cache_key, max_age_hours=1)
    if cached:
        return cached

    # Try multiple DTH feed URLs (site blocks some)
    urls = [
        "https://www.dailytarheel.com/feed",
        "https://www.dailytarheel.com/rss.xml",
        "https://www.dailytarheel.com/feed.xml",
    ]

    resp = None
    for url in urls:
        try:
            resp = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            })
            if resp.status_code == 200:
                break
            resp = None
        except Exception:
            continue

    if not resp:
        print("  [!] DTH: all feed URLs returned non-200")
        return None

    try:
        root = ElementTree.fromstring(resp.content)
        articles = []

        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            description = item.findtext("description", "")
            # Strip HTML from description
            description = re.sub(r'<[^>]+>', '', description)[:200]

            articles.append({
                "source": "Daily Tar Heel",
                "title": title,
                "url": link,
                "published": pub_date,
                "summary": description,
            })

        if articles:
            _write_cache(cache_key, articles)
            print(f"  [+] DTH: {len(articles)} articles")

        return articles if articles else None

    except Exception as e:
        print(f"  [!] DTH RSS error: {e}")
        return None


# ---------------------------------------------------------------------------
# Google Trends Live Keywords
# ---------------------------------------------------------------------------

def fetch_live_trending_keywords(geo="US-NC"):
    """
    Fetch currently trending searches and filter for UNC/Chapel Hill relevance.
    Uses pytrends (no API key needed).
    """
    cache_key = "livefeed_trending"
    cached = _read_cache(cache_key, max_age_hours=0.5)
    if cached:
        return cached

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=300)

        # Get today's trending searches
        trending = pytrends.trending_searches(pn="united_states")
        all_trending = trending[0].tolist()[:30] if trending is not None else []

        # Filter for local relevance
        local = [
            q for q in all_trending
            if any(kw in q.lower() for kw in LOCAL_RELEVANCE_KEYWORDS)
        ]

        # Also get real-time interest for our core keywords
        core_kws = ["UNC basketball", "Chapel Hill", "Franklin Street"]
        pytrends.build_payload(core_kws, timeframe="now 1-d", geo=geo)
        interest = pytrends.interest_over_time()

        current_interest = {}
        if not interest.empty:
            for kw in core_kws:
                if kw in interest.columns:
                    current_interest[kw] = int(interest[kw].iloc[-1])

        result = {
            "nationally_trending": all_trending[:15],
            "locally_relevant": local,
            "core_keyword_interest": current_interest,
            "source": "Google Trends (live via pytrends)",
            "fetched_at": datetime.now().isoformat(),
        }

        _write_cache(cache_key, result)
        return result

    except ImportError:
        print("  [!] pytrends not installed")
        return None
    except Exception as e:
        print(f"  [!] Trends feed error: {e}")
        return None


# ---------------------------------------------------------------------------
# UNC Events Feed
# ---------------------------------------------------------------------------

def fetch_unc_events_feed():
    """
    Fetch upcoming UNC events from the Localist calendar API.
    Returns list of events or None.
    """
    cache_key = "livefeed_unc_events"
    cached = _read_cache(cache_key, max_age_hours=2)
    if cached:
        return cached

    url = "https://calendar.unc.edu/api/2/events?days=7&pp=25"

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "FranklinStDataBot/1.0 (UNC academic tool)",
        })
        resp.raise_for_status()
        data = resp.json()

        events = []
        for item in data.get("events", []):
            ev = item.get("event", {})
            events.append({
                "source": "UNC Calendar",
                "title": ev.get("title", ""),
                "location": ev.get("location_name", ""),
                "date": ev.get("first_date", ""),
                "url": ev.get("localist_url", ""),
                "type": [
                    f.get("name", "")
                    for f in ev.get("filters", {}).get("event_types", [])
                ],
            })

        if events:
            _write_cache(cache_key, events)
            print(f"  [+] UNC Events: {len(events)} upcoming")

        return events if events else None

    except Exception as e:
        print(f"  [!] UNC Events feed error: {e}")
        return None


# ---------------------------------------------------------------------------
# Keyword Extraction
# ---------------------------------------------------------------------------

def extract_keywords(feed_data):
    """
    Extract trending keywords/topics from all feed sources.
    Returns ranked list of keywords with frequency counts.
    """
    keyword_counts = {}

    # Process Reddit titles
    reddit = feed_data.get("reddit") or []
    for post in reddit:
        words = re.findall(r'\b[A-Za-z]{4,}\b', post.get("title", ""))
        for word in words:
            w = word.lower()
            if w not in {"this", "that", "with", "from", "have", "been",
                         "what", "when", "where", "which", "there", "their",
                         "about", "would", "could", "should", "just", "like",
                         "does", "going", "anyone", "know", "think", "they",
                         "some", "more", "than", "very", "also", "here"}:
                keyword_counts[w] = keyword_counts.get(w, 0) + 1

    # Process DTH headlines
    dth = feed_data.get("dth") or []
    for article in dth:
        words = re.findall(r'\b[A-Za-z]{4,}\b', article.get("title", ""))
        for word in words:
            w = word.lower()
            keyword_counts[w] = keyword_counts.get(w, 0) + 2  # News weighted higher

    # Sort by frequency
    sorted_kw = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"keyword": kw, "frequency": count} for kw, count in sorted_kw[:30]]


# ---------------------------------------------------------------------------
# Combined Live Feed
# ---------------------------------------------------------------------------

def build_live_feed():
    """
    Aggregate all live keyword feeds into a single intelligence stream.
    Every piece of data has a clear source. Nothing fabricated.
    """
    feed = {
        "reddit": fetch_reddit_feed(),
        "dth": fetch_dth_feed(),
        "trends": fetch_live_trending_keywords(),
        "unc_events": fetch_unc_events_feed(),
    }

    # Extract keywords from all sources
    feed["extracted_keywords"] = extract_keywords(feed)

    # Build trivia topic suggestions from live keywords
    feed["trivia_suggestions"] = _keywords_to_trivia(feed)

    feed["sources"] = {
        "reddit": "Reddit JSON API (no key)",
        "dth": "Daily Tar Heel RSS (no key)",
        "trends": "Google Trends (pytrends, no key)",
        "unc_events": "UNC Localist Calendar API (no key)",
    }
    feed["generated_at"] = datetime.now().isoformat()

    return feed


def _keywords_to_trivia(feed):
    """Convert live keyword data into trivia topic suggestions."""
    suggestions = []

    # From Reddit
    reddit = feed.get("reddit") or []
    hot_posts = [p for p in reddit if p.get("score", 0) > 20]
    for post in hot_posts[:5]:
        suggestions.append({
            "source": post["source"],
            "topic": post["title"][:100],
            "signal": f"score {post['score']}, {post['comments']} comments",
            "suggestion": f"Hot on {post['source']}: '{post['title'][:60]}' — could inspire a trivia question.",
        })

    # From DTH
    dth = feed.get("dth") or []
    for article in dth[:3]:
        suggestions.append({
            "source": "Daily Tar Heel",
            "topic": article["title"][:100],
            "signal": "campus news",
            "suggestion": f"DTH headline: '{article['title'][:60]}' — good for a current events round.",
        })

    # From trends
    trends = feed.get("trends")
    if trends and trends.get("locally_relevant"):
        for query in trends["locally_relevant"][:3]:
            suggestions.append({
                "source": "Google Trends",
                "topic": query,
                "signal": "trending locally in NC",
                "suggestion": f"'{query}' is trending in NC right now — perfect trivia material.",
            })

    # From UNC events
    events = feed.get("unc_events") or []
    for ev in events[:3]:
        suggestions.append({
            "source": "UNC Calendar",
            "topic": ev["title"][:100],
            "signal": f"upcoming event at {ev.get('location', 'campus')}",
            "suggestion": f"UNC event: '{ev['title'][:60]}' — ask about it at trivia.",
        })

    return suggestions
