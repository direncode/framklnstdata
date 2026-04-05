"""
==============================================
  FRANKLIN STREET DATA
  Satellite & Aerial Imagery Layer System
==============================================
Provides multiple map tile sources including satellite,
aerial, terrain, and dark-mode base maps. Supports
toggling between views in the Streamlit dashboard.
"""

# ---------------------------------------------------------------------------
# Free Tile Server URLs (no API key required)
# ---------------------------------------------------------------------------

TILE_SOURCES = {
    # Satellite / Aerial Imagery
    "Esri Satellite": {
        "url": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": (
            "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, "
            "AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, "
            "and the GIS User Community"
        ),
        "name": "Esri World Imagery (Satellite)",
        "category": "satellite",
    },
    "Esri Satellite Labels": {
        "url": (
            "https://services.arcgisonline.com/ArcGIS/rest/services/"
            "Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": "Esri Reference Labels",
        "name": "Satellite Labels Overlay",
        "category": "overlay",
        "overlay": True,
    },
    # Dark Mode (Intelligence Dashboard Style)
    "CartoDB Dark": {
        "url": (
            "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        ),
        "attr": (
            "&copy; OpenStreetMap contributors &copy; CARTO"
        ),
        "name": "Dark Mode (Intelligence)",
        "category": "base",
    },
    # Terrain & Topographic
    "Esri Topo": {
        "url": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": (
            "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, "
            "Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, "
            "Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong)"
        ),
        "name": "Topographic",
        "category": "base",
    },
    # Street Map
    "OpenStreetMap": {
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "&copy; OpenStreetMap contributors",
        "name": "Street Map",
        "category": "base",
    },
    # Light Minimal (Good for overlays)
    "CartoDB Light": {
        "url": (
            "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        ),
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
        "name": "Light Minimal",
        "category": "base",
    },
    # Stamen Terrain (Watercolor-like terrain)
    "Stadia Terrain": {
        "url": (
            "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png"
        ),
        "attr": (
            "&copy; Stadia Maps &copy; Stamen Design "
            "&copy; OpenStreetMap contributors"
        ),
        "name": "Terrain (Stamen)",
        "category": "base",
    },

    # --- Global Expansion: NASA GIBS Layers ---
    "NASA GIBS Terra True Color": {
        "url": (
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
            "MODIS_Terra_CorrectedReflectance_TrueColor/default/"
            "{time}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
        ),
        "attr": "NASA EOSDIS GIBS",
        "name": "NASA Terra True Color (Daily)",
        "category": "satellite",
        "temporal": True,
    },
    "NASA VIIRS Night Lights": {
        "url": (
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
            "VIIRS_SNPP_DayNightBand_At_Sensor_Radiance/default/"
            "{time}/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png"
        ),
        "attr": "NASA EOSDIS GIBS",
        "name": "VIIRS Nighttime Lights",
        "category": "nighttime",
        "temporal": True,
    },
    "NASA Blue Marble": {
        "url": (
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
            "BlueMarble_NextGeneration/default/"
            "GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg"
        ),
        "attr": "NASA Blue Marble",
        "name": "Blue Marble (NASA)",
        "category": "satellite",
    },
    "NASA Black Marble": {
        "url": (
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
            "VIIRS_Black_Marble/default/"
            "GoogleMapsCompatible_Level8/{z}/{y}/{x}.png"
        ),
        "attr": "NASA Black Marble / VIIRS",
        "name": "Earth at Night (Black Marble)",
        "category": "nighttime",
    },
    "NASA Active Fires": {
        "url": (
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
            "MODIS_Terra_Thermal_Anomalies_Day/default/"
            "{time}/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png"
        ),
        "attr": "NASA EOSDIS GIBS - MODIS Fire",
        "name": "Active Fires (MODIS)",
        "category": "overlay",
        "overlay": True,
        "temporal": True,
    },
    "NASA NDVI": {
        "url": (
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
            "MODIS_Terra_NDVI_8Day/default/"
            "{time}/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png"
        ),
        "attr": "NASA EOSDIS GIBS - MODIS NDVI",
        "name": "Vegetation Index (NDVI)",
        "category": "overlay",
        "overlay": True,
        "temporal": True,
    },
    "NASA Aerosol": {
        "url": (
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
            "MODIS_Terra_Aerosol_Optical_Depth/default/"
            "{time}/GoogleMapsCompatible_Level7/{z}/{y}/{x}.png"
        ),
        "attr": "NASA EOSDIS GIBS - MODIS AOD",
        "name": "Aerosol Optical Depth",
        "category": "overlay",
        "overlay": True,
        "temporal": True,
    },

    # --- Sentinel Hub (free limited access) ---
    "Sentinel-2 True Color": {
        "url": (
            "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/"
            "GoogleMapsCompatible/{z}/{y}/{x}.jpg"
        ),
        "attr": "&copy; Sentinel-2 cloudless - EOX &amp; EU/ESA/Copernicus",
        "name": "Sentinel-2 Cloudless (2021)",
        "category": "satellite",
    },
}


# ---------------------------------------------------------------------------
# pydeck View State Presets for Franklin Street
# ---------------------------------------------------------------------------

PYDECK_VIEWS = {
    "street_level": {
        "latitude": 35.9132,
        "longitude": -79.0555,
        "zoom": 16,
        "pitch": 45,
        "bearing": -20,
    },
    "overhead": {
        "latitude": 35.9132,
        "longitude": -79.0555,
        "zoom": 16,
        "pitch": 0,
        "bearing": 0,
    },
    "campus_wide": {
        "latitude": 35.9120,
        "longitude": -79.0500,
        "zoom": 14.5,
        "pitch": 30,
        "bearing": 0,
    },
    "satellite_high": {
        "latitude": 35.9132,
        "longitude": -79.0555,
        "zoom": 17,
        "pitch": 0,
        "bearing": 0,
    },
}


def get_tile_url(source_name):
    """Get tile URL for a named source."""
    source = TILE_SOURCES.get(source_name)
    if source:
        return source["url"]
    return TILE_SOURCES["Esri Satellite"]["url"]


def get_tile_attr(source_name):
    """Get attribution for a named source."""
    source = TILE_SOURCES.get(source_name)
    if source:
        return source["attr"]
    return ""


def get_folium_tile_layers():
    """
    Return a list of (name, url, attr) tuples for folium TileLayer.
    Excludes overlays.
    """
    layers = []
    for key, source in TILE_SOURCES.items():
        if not source.get("overlay", False):
            layers.append((source["name"], source["url"], source["attr"]))
    return layers


def build_pydeck_map_style(source_name="CartoDB Dark"):
    """
    Return a pydeck-compatible map style string.
    pydeck uses Mapbox/MapLibre style URLs or built-in styles.
    """
    style_map = {
        "CartoDB Dark": "dark",
        "CartoDB Light": "light",
        "OpenStreetMap": "road",
        "Esri Satellite": "satellite",
        "Esri Topo": "road",
    }
    return style_map.get(source_name, "dark")
