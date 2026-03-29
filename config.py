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

# Full Chapel Hill bounding box — covers the entire town
CHAPEL_HILL_BOUNDS = {
    "south": 35.8800,
    "north": 35.9600,
    "west": -79.1100,
    "east": -79.0100,
}

# Waypoints along the full Franklin Street → Carrboro corridor
# Extends from campus edge east through West Franklin into Carrboro
FRANKLIN_STREET_SPINE = [
    (35.9136, -79.0510),  # East end — near campus edge
    (35.9135, -79.0520),  # Approaching campus
    (35.9134, -79.0530),  # East Franklin
    (35.9133, -79.0540),  # Columbia St intersection
    (35.9132, -79.0548),  # He's Not Here area
    (35.9131, -79.0555),  # Bandidos area
    (35.9130, -79.0562),  # TOPO area
    (35.9128, -79.0575),  # Near Linda's / West Franklin
    (35.9126, -79.0590),  # Merritt Mill intersection
    (35.9124, -79.0610),  # West Franklin corridor
    (35.9122, -79.0630),  # Approaching Carrboro
    (35.9120, -79.0650),  # Carrboro town line
    (35.9118, -79.0670),  # Main St Carrboro area
    (35.9115, -79.0695),  # Weaver St Market area
    (35.9112, -79.0720),  # West Carrboro
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

# Modular trend areas — Chapel Hill default, expandable to Triangle
TREND_AREAS = {
    "chapel_hill": {"geo": "US-NC-560", "label": "Chapel Hill / Triangle NC"},
    "raleigh":     {"geo": "US-NC-560", "label": "Raleigh-Durham DMA"},
    "charlotte":   {"geo": "US-NC-517", "label": "Charlotte DMA"},
    "national":    {"geo": "US",        "label": "United States"},
}
DEFAULT_TREND_AREA = "chapel_hill"

# Search keyword → venue type mapping for convergence analysis
# Maps trending search terms to venue categories they predict traffic for
VENUE_SEARCH_KEYWORDS = {
    "bar":        ["bars", "nightlife", "drinks", "cocktails", "happy hour", "beer",
                   "wine bar", "brewery", "craft beer", "karaoke", "pub crawl"],
    "restaurant": ["restaurants", "dining", "food", "eat", "dinner", "lunch",
                   "brunch", "sushi", "mexican food", "italian", "thai",
                   "indian food", "ramen", "steakhouse", "seafood"],
    "cafe":       ["coffee", "cafe", "espresso", "latte", "study spot", "wifi",
                   "bakery", "pastry", "tea", "matcha"],
    "nightclub":  ["clubs", "dancing", "DJ", "nightlife", "party", "rave",
                   "EDM", "hip hop night", "ladies night"],
    "pub":        ["pub", "bar", "beer", "wings", "trivia night", "sports bar",
                   "game day", "watch party"],
    "fast_food":  ["fast food", "takeout", "burgers", "pizza", "delivery",
                   "drive through", "late night food", "cheap eats"],
    "ice_cream":  ["ice cream", "frozen yogurt", "dessert", "gelato", "sweets"],
    "supermarket": ["grocery", "supermarket", "food store", "organic"],
    "fitness_centre": ["gym", "fitness", "workout", "yoga", "crossfit", "pilates"],
    "cinema":     ["movies", "cinema", "film", "theater", "IMAX", "new movies"],
    "hotel":      ["hotel", "lodging", "stay", "accommodation", "Airbnb"],
    "pharmacy":   ["pharmacy", "drugstore", "medicine", "prescription"],
    "bookstore":  ["books", "bookstore", "reading", "Barnes Noble"],
    "shopping":   ["shopping", "clothes", "retail", "sale", "outlet", "mall"],
}

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
    "search_convergence": 0.25,        # Search trajectory → venue convergence
    "transit_access": 0.15,            # Transit stop proximity boost
    "crime_damping": 0.1,              # Crime incident safety suppression
    "social_buzz": 0.1,                # Reddit social activity amplifier
    "news_boost": 0.1,                 # Daily Tar Heel headline boost
    "demographics": 0.1,               # College-age population multiplier
}

# Typical hourly activity profiles by venue type (0-100, index = hour 0-23)
MFG_VENUE_PROFILES = {
    "bar":        [0,0,0,0,0,0,0,0,0,5,10,15,15,15,15,20,30,50,70,85,95,100,90,60],
    "restaurant": [0,0,0,0,0,0,5,10,15,20,40,70,85,80,50,30,40,70,90,85,70,50,30,10],
    "cafe":       [0,0,0,0,0,5,20,60,80,90,85,70,60,50,45,40,30,20,10,5,0,0,0,0],
    "nightclub":  [0,0,0,0,0,0,0,0,0,0,0,5,5,5,5,10,15,25,40,60,80,95,100,80],
    "pub":        [0,0,0,0,0,0,0,0,0,5,10,25,40,35,30,35,45,60,75,85,90,80,60,30],
    "fast_food":  [0,0,0,0,0,5,10,20,30,25,30,60,80,60,40,35,40,55,65,60,50,40,30,15],
    # Non-food venues
    "pharmacy":   [0,0,0,0,0,0,0,0,15,40,50,50,45,40,45,50,50,40,30,15,5,0,0,0],
    "bank":       [0,0,0,0,0,0,0,0,10,40,60,65,60,55,55,50,40,15,0,0,0,0,0,0],
    "supermarket":[0,0,0,0,0,0,5,15,30,45,55,60,55,45,40,45,55,65,60,45,30,15,5,0],
    "cinema":     [0,0,0,0,0,0,0,0,0,5,15,25,40,50,55,50,55,65,75,80,75,60,40,15],
    "fitness_centre":[0,0,0,0,0,10,30,60,70,55,45,50,55,45,40,45,55,65,60,40,25,10,0,0],
    "hotel":      [20,15,10,10,10,10,15,30,50,60,55,45,40,40,45,55,60,55,50,45,40,35,30,25],
    "library":    [0,0,0,0,0,0,0,0,15,40,55,60,55,50,50,55,60,55,45,30,15,5,0,0],
    "shop":       [0,0,0,0,0,0,0,0,5,20,50,65,70,60,55,55,60,55,40,20,5,0,0,0],
}

# Day-of-week multipliers (Mon=0 through Sun=6)
MFG_DAY_MULTIPLIERS = [0.5, 0.5, 0.6, 0.7, 0.9, 1.0, 0.8]

# Fallback operating hours when OSM opening_hours is missing
# Format: (open_hour, close_hour) — used to zero out busyness for closed venues
MFG_FALLBACK_HOURS = {
    "bar":          (16, 2),   # 4pm - 2am
    "nightclub":    (21, 3),   # 9pm - 3am
    "pub":          (11, 2),   # 11am - 2am
    "restaurant":   (7, 23),   # 7am - 11pm
    "cafe":         (6, 20),   # 6am - 8pm
    "fast_food":    (6, 24),   # 6am - midnight
    "pharmacy":     (8, 21),   # 8am - 9pm
    "bank":         (9, 17),   # 9am - 5pm
    "supermarket":  (7, 22),   # 7am - 10pm
    "cinema":       (10, 24),  # 10am - midnight
    "fitness_centre": (5, 22), # 5am - 10pm
    "hotel":        (0, 24),   # 24/7
    "library":      (8, 22),   # 8am - 10pm
    "shop":         (9, 21),   # 9am - 9pm
}

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
