# Franklin Street Data

Live foot traffic intelligence for Franklin Street, UNC Chapel Hill.

## How It Works

1. **OpenStreetMap Overpass API** discovers every bar, restaurant, cafe, nightclub on Franklin Street
2. **Google Places API** fetches hourly busyness (0-100%) for each venue — the only ranking signal
3. Busyness values become heat map weights, interpolated along the street into a convergent corridor
4. **Live feeds** (Reddit, DTH, UNC Calendar, Google Trends) extract keywords for trivia topic suggestions

## Quick Start

```bash
# Backend (Python)
pip install -r requirements.txt
python datastream.py

# Frontend (Next.js)
cd web && npm install && npm run dev
```

## Deploy

**Backend** → Fly.io:
```bash
fly launch --copy-config
fly secrets set GOOGLE_PLACES_API_KEY=your-key
fly deploy
```

**Frontend** → Vercel:
- Set Root Directory to `web` in Vercel dashboard
- Set `BACKEND_URL` env var to your Fly.io URL

## API Endpoints

```
GET /status          System health
GET /venues          All discovered venues + busyness
GET /heatmap         Heat map data points
GET /livefeed        Reddit + DTH + UNC Calendar + Trends
GET /trends          Google Trends + trivia suggestions
GET /intel           Census + weather + UNC events
GET /network         Street network topology
GET /report          Full text report
GET /export          Complete data dump
```

## Data Sources

| Source | Data | Key Needed |
|---|---|---|
| OpenStreetMap Overpass | Venue discovery | No |
| Reddit JSON API | r/UNC, r/chapelhill posts | No |
| Daily Tar Heel RSS | Campus news | No |
| UNC Calendar Localist | Campus events | No |
| Google Trends (pytrends) | Search interest | No |
| Chapel Hill ArcGIS | Crime data, GIS layers | No |
| NCDOT ArcGIS | Vehicle traffic counts | No |
| NC ABC Commission | Liquor licenses | No |
| Google Places API | Hourly busyness | Yes (free tier) |
| OpenWeatherMap | Weather | Yes (free tier) |
| US Census Bureau | Demographics | Yes (free) |

## Files

| File | Purpose |
|---|---|
| `config.py` | Constants, API keys, geography |
| `spots.py` | OSM venue discovery + busyness ranking |
| `traffic.py` | Google Places busyness, heat map builder |
| `trends.py` | Google Trends, rising queries |
| `intel.py` | Census, weather, UNC events |
| `osint.py` | Reddit, transit, crime, ABC licenses |
| `livefeed.py` | Live keyword feed aggregator |
| `forecast.py` | Live signal forecasting |
| `network.py` | Street network analysis |
| `spatial.py` | Isochrones, gravity model, placement |
| `buildings.py` | 3D building footprints, viewshed |
| `satellite.py` | Map tile sources |
| `main.py` | CLI report generator |
| `datastream.py` | REST API server |
| `web/` | Next.js frontend (Vercel) |
