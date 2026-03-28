"""
==============================================
  FRANKLIN STREET PANOPTICON v3 - Configuration
==============================================
Centralized constants, API keys, and cache settings.
"""

import os

# ---------------------------------------------------------------------------
# Franklin Street Geography
# ---------------------------------------------------------------------------

FRANKLIN_STREET_CENTER = (35.9132, -79.0555)

# Bounding box for the Franklin Street corridor (SW corner, NE corner)
FRANKLIN_STREET_BOUNDS = {
    "south": 35.9100,
    "north": 35.9230,
    "west": -79.0620,
    "east": -79.0430,
}

# Waypoints along Franklin Street for heat map interpolation
# These define the "spine" of the street for continuous heat mapping
FRANKLIN_STREET_SPINE = [
    (35.9126, -79.0590),  # West end near Merritt Mill
    (35.9128, -79.0575),  # Near Linda's / West Franklin
    (35.9130, -79.0562),  # TOPO area
    (35.9131, -79.0555),  # Bandidos area
    (35.9132, -79.0548),  # He's Not Here area
    (35.9133, -79.0540),  # Columbia St intersection
    (35.9134, -79.0530),  # East Franklin
    (35.9135, -79.0520),  # Approaching campus
    (35.9136, -79.0510),  # Near campus edge
]

# ---------------------------------------------------------------------------
# API Keys (from environment variables)
# ---------------------------------------------------------------------------

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", None)

# ---------------------------------------------------------------------------
# External API Endpoints
# ---------------------------------------------------------------------------

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Chapel Hill ArcGIS Open Data
CHAPEL_HILL_GIS_BASE = (
    "https://services1.arcgis.com/jOyGkcqHAywMxJEv/arcgis/rest/services"
)

# ---------------------------------------------------------------------------
# Cache Configuration
# ---------------------------------------------------------------------------

CACHE_DIR = ".panopticon_cache"

# Cache time-to-live in hours
CACHE_TTL = {
    "popular_times": 6,       # Busyness patterns refresh every 6 hours
    "overpass": 720,           # OSM data: 30 days (buildings don't move)
    "gis": 168,                # Chapel Hill GIS: 7 days
    "trends_interest": 1,      # Google Trends interest scores: 1 hour
    "trends_rising": 1,        # Rising queries: 1 hour
    "trends_realtime": 0.5,    # Realtime trending: 30 minutes
}

# ---------------------------------------------------------------------------
# Google Trends Configuration
# ---------------------------------------------------------------------------

DEFAULT_GEO = "US-NC"
DEFAULT_TIMEFRAME = "now 7-d"
TRENDS_TIMEZONE = 300  # EST

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

TRIVIA_CATEGORIES = {
    "UNC Sports": [
        "UNC basketball", "Tar Heels", "UNC football",
        "March Madness", "ACC tournament", "UNC lacrosse",
    ],
    "Campus Life": [
        "UNC Chapel Hill", "Chapel Hill events", "UNC classes",
        "UNC housing", "UNC Greek life", "UNC dining",
    ],
    "Franklin Street": [
        "Franklin Street bars", "Chapel Hill restaurants",
        "Chapel Hill nightlife", "Franklin Street Chapel Hill",
    ],
    "Pop Culture": [
        "TikTok trends", "Netflix popular", "viral meme",
        "Grammy awards", "celebrity news", "SNL",
    ],
    "NC News & Politics": [
        "North Carolina news", "NC governor", "Raleigh news",
        "NC weather", "Triangle NC", "Durham news",
    ],
    "Science & Tech": [
        "AI news", "space news", "new technology",
        "science discovery", "ChatGPT", "Apple",
    ],
    "Music": [
        "new music releases", "concert tour", "Spotify top songs",
        "album release", "music festival", "rap album",
    ],
    "Movies & TV": [
        "new movies", "box office", "TV show premiere",
        "streaming new releases", "Marvel", "anime",
    ],
}

# Keywords that indicate relevance to UNC / Chapel Hill / NC area
# Used to filter national trending searches for local relevance
LOCAL_RELEVANCE_KEYWORDS = [
    "unc", "tar heel", "chapel hill", "franklin street", "north carolina",
    "nc state", "duke", "acc", "raleigh", "durham", "charlotte",
    "carolina", "wolfpack", "blue devil", "wake forest", "ncaa",
    "triangle", "research triangle", "nc", "ncsu",
]
