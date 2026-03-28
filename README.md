# Franklin Street Panopticon v3

Surveillance-grade intelligence platform for trivia night optimization at Bandidos on Franklin Street, UNC Chapel Hill.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    PANOPTICON v3                              │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ traffic  │ trends   │ intel    │ network  │ satellite       │
│  .py     │  .py     │  .py     │  .py     │  .py            │
│          │          │          │          │                 │
│ OSM      │ Google   │ Census   │ Street   │ Esri Imagery    │
│ Popular  │ Trends   │ Weather  │ Network  │ Tile Layers     │
│ Times    │ Rising   │ Events   │ Central- │ View Presets    │
│ GIS      │ Queries  │ Social   │ ity      │                 │
│ NCDOT    │ Realtime │ Signals  │ Walk     │                 │
│ Heatmap  │          │          │ Score    │                 │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                       spots.py                               │
│              (Hybrid static + live scoring)                   │
├──────────────────────────────────────────────────────────────┤
│                       config.py                              │
├──────────┬──────────────────────┬────────────────────────────┤
│ CLI      │ Streamlit Dashboard  │ REST API                   │
│ panop-   │ app.py               │ datastream.py              │
│ ticon.py │ (Palantir-grade UI)  │ (JSON endpoints)           │
└──────────┴──────────────────────┴────────────────────────────┘
```

## Quick Start

```bash
pip install -r requirements.txt

# 1. CLI Report (works immediately, no API keys needed)
python panopticon.py --no-live

# 2. Streamlit Dashboard (satellite map, heat map, intelligence tabs)
streamlit run app.py

# 3. REST API (JSON data endpoints for integration)
python datastream.py
```

## Three Interfaces

### CLI (`panopticon.py`)
```bash
python panopticon.py                    # Full report with live data
python panopticon.py --hour 21          # Simulate 9pm busyness
python panopticon.py --no-live          # Static data only
python panopticon.py --save report.txt  # Save to file
```

### Dashboard (`app.py`)
```bash
streamlit run app.py
```
7 tabs: Satellite, Heat Map, Traffic, Network, Intel, Trends, Report

### Data API (`datastream.py`)
```bash
python datastream.py --port 8765
```
Endpoints:
- `GET /spots` — Ranked venues with live busyness
- `GET /traffic?hour=21&day=friday` — Traffic at specific time
- `GET /heatmap?hour=21` — GeoJSON heat map data
- `GET /venues` — OSM venue discovery
- `GET /trends?live=true` — Trending search intelligence
- `GET /intel` — Full OSINT briefing (demographics, weather, events)
- `GET /network` — Street network topology
- `GET /export` — Complete data export

## Data Sources

| Source | Data | Cost |
|---|---|---|
| OpenStreetMap Overpass API | Venue discovery, street network | Free |
| Esri World Imagery | Satellite/aerial tiles | Free |
| Google Places Popular Times | Hourly busyness | Free w/ key |
| NCDOT AADT | Vehicle traffic counts | Free (public record) |
| US Census Bureau | Demographics, population | Free |
| OpenWeatherMap | Weather conditions | Free tier |
| Google Trends (pytrends) | Search interest, rising queries | Free |
| Chapel Hill ArcGIS | GIS layers, pedestrian infra | Free |

## Optional API Keys

```bash
# For real popular times data (vs curated fallback)
export GOOGLE_PLACES_API_KEY="your-key"

# For live weather data (vs fallback estimate)
export OPENWEATHER_API_KEY="your-key"

# For live Census data (vs pre-computed)
export CENSUS_API_KEY="your-key"
```

## Files

| File | Lines | Purpose |
|---|---|---|
| `config.py` | Config | Constants, API keys, cache TTLs, geography |
| `spots.py` | Data | 10 curated locations + hybrid scoring |
| `traffic.py` | Engine | OSM, popular times, GIS, heat map builder |
| `trends.py` | Engine | Google Trends, rising queries, realtime |
| `intel.py` | Engine | Census, weather, events, social signals |
| `network.py` | Engine | Street network, centrality, walk scores |
| `satellite.py` | Engine | Tile sources, imagery layers, view presets |
| `panopticon.py` | CLI | Report generator with ASCII visualizations |
| `app.py` | UI | Streamlit Palantir-grade dashboard |
| `datastream.py` | API | REST JSON endpoints for data consumption |
