"""
==============================================
  FRANKLIN STREET DATA - Configuration
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

CACHE_DIR = ".franklinst_cache"

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

DEFAULT_GEO = "US-NC-560"  # DMA 560 = Raleigh-Durham-Fayetteville (includes Chapel Hill)
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

# ---------------------------------------------------------------------------
# BTUT Mean-Field Game Engine Configuration
# ---------------------------------------------------------------------------

MFG_CONFIG = {
    "grid_size": 200,                  # Spatial discretization points along spine
    "kernel_bandwidth": 0.1,           # Gaussian RBF σ (interaction range)
    "diffusion": 0.02,                 # σ²/2 exploration noise coefficient
    "dt": 0.01,                        # Fokker-Planck time step
    "max_iterations": 150,             # Max steps per hour solve
    "convergence_threshold": 1e-5,     # Nash gap threshold
}

# Signal weights for the drift velocity v[ρ]
MFG_SIGNAL_WEIGHTS = {
    "venue_attraction": 1.0,           # Base Gaussian pull toward venues
    "anti_crowding": 0.3,              # Dispersal from density peaks
    "time_profile": 0.8,               # Hour-of-day venue type modulation
    "trends_boost": 0.15,              # Google Trends interest amplification
    "weather_damping": 0.2,            # Bad weather reduces drift magnitude
    "event_surge": 0.25,               # UNC event proximity boost
    "day_of_week": 0.4,                # Weekend vs weekday multiplier
}

# Typical hourly activity profiles by venue type (0-100, index = hour 0-23)
MFG_VENUE_PROFILES = {
    "bar":        [0,0,0,0,0,0,0,0,0,5,10,15,15,15,15,20,30,50,70,85,95,100,90,60],
    "restaurant": [0,0,0,0,0,0,5,10,15,20,40,70,85,80,50,30,40,70,90,85,70,50,30,10],
    "cafe":       [0,0,0,0,0,5,20,60,80,90,85,70,60,50,45,40,30,20,10,5,0,0,0,0],
    "nightclub":  [0,0,0,0,0,0,0,0,0,0,0,5,5,5,5,10,15,25,40,60,80,95,100,80],
    "pub":        [0,0,0,0,0,0,0,0,0,5,10,25,40,35,30,35,45,60,75,85,90,80,60,30],
    "fast_food":  [0,0,0,0,0,5,10,20,30,25,30,60,80,60,40,35,40,55,65,60,50,40,30,15],
}

# Day-of-week multipliers (Mon=0 through Sun=6)
MFG_DAY_MULTIPLIERS = [0.5, 0.5, 0.6, 0.7, 0.9, 1.0, 0.8]

# ---------------------------------------------------------------------------
# Local Relevance Filtering
# ---------------------------------------------------------------------------

# Keywords that indicate relevance to UNC / Chapel Hill / NC area
# Used to filter national trending searches for local relevance
LOCAL_RELEVANCE_KEYWORDS = [
    "unc", "tar heel", "chapel hill", "franklin street", "north carolina",
    "nc state", "duke", "acc", "raleigh", "durham", "charlotte",
    "carolina", "wolfpack", "blue devil", "wake forest", "ncaa",
    "triangle", "research triangle", "nc", "ncsu",
]
