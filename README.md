# Franklin Street Panopticon v2

Surveillance-grade trivia night optimization for Bandidos on Franklin Street, UNC Chapel Hill.

## What It Does

1. **Live Foot Traffic Engine** - Discovers venues via OpenStreetMap, fetches hourly busyness via Google Places popular times, pulls Chapel Hill GIS layers, and renders convergent heat maps of Franklin Street foot traffic.
2. **Search Interpretation Engine** - Pulls Google Trends interest scores, rising queries, and real-time trending searches. Generates trivia category suggestions with NC/Chapel Hill geo-awareness.
3. **Ranked Spot Placement** - Hybrid static + live scoring of 10 curated locations for QR code and flyer placement.
4. **Interactive Streamlit App** - Dark-themed heat map with hour/day controls, live traffic charts, 24-hour timelines, trending trivia topics, and downloadable reports.

## Quick Start

```bash
pip install -r requirements.txt

# CLI (uses fallback data, works immediately)
python panopticon.py --no-live

# CLI with live data
python panopticon.py

# Web app (interactive heat map + dashboard)
streamlit run app.py
```

## CLI Options

```
python panopticon.py [OPTIONS]

  --time {morning,daytime,evening}   Optimize for time of day (default: evening)
  --spots N                          Number of spots to show (default: 8)
  --hour H                           Simulate hour 0-23 for busyness analysis
  --no-trends                        Skip live Google Trends
  --no-live                          Skip all live data (static only)
  --save FILE                        Save report to file
```

## Optional: Google Places API Key

For real popular times data (instead of curated fallback patterns):

```bash
export GOOGLE_PLACES_API_KEY="your-key-here"
```

Free tier gives $200/month credit which covers thousands of requests.

## Files

| File | Purpose |
|---|---|
| `panopticon.py` | CLI report generator |
| `app.py` | Streamlit web dashboard |
| `spots.py` | Location database + hybrid ranking |
| `traffic.py` | Live foot traffic engine (OSM, popular times, GIS, heat map) |
| `trends.py` | Google Trends engine (interest, rising queries, realtime) |
| `config.py` | Centralized configuration and constants |

## Data Sources

- **OpenStreetMap Overpass API** - Free venue discovery (no key needed)
- **Google Places Popular Times** - Hourly busyness (optional API key)
- **Chapel Hill ArcGIS Open Data** - Pedestrian infrastructure layers
- **NCDOT AADT** - Annual vehicle traffic counts
- **Google Trends (pytrends)** - Search interest, rising queries, trending now
