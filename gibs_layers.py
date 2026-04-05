"""
==============================================
  FRANKLIN STREET DATA
  NASA GIBS Satellite Imagery Layers
==============================================
Configuration for NASA Global Imagery Browse Services (GIBS)
tile layers. Provides hundreds of satellite imagery products
including true-color composites, thermal, vegetation indices,
nighttime lights, and more.

Source: https://nasa-gibs.github.io/gibs-api-docs/
Tile format: WMTS (Web Map Tile Service)
"""

from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# GIBS WMTS Tile URL Template
# ---------------------------------------------------------------------------

GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

def gibs_tile_url(layer, date=None, format="png", matrix_set="GoogleMapsCompatible_Level9"):
    """
    Build GIBS WMTS tile URL template for MapLibre/Leaflet.
    Returns URL with {z}/{y}/{x} placeholders.
    """
    if date is None:
        date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    return (
        f"{GIBS_BASE}/{layer}/default/{date}/"
        f"{matrix_set}/{{z}}/{{y}}/{{x}}.{format}"
    )


# ---------------------------------------------------------------------------
# Curated GIBS Layer Catalog
# ---------------------------------------------------------------------------

GIBS_LAYERS = {
    # True Color Imagery
    "modis_terra_truecolor": {
        "id": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "name": "MODIS Terra True Color",
        "description": "Daily true-color satellite imagery from NASA Terra/MODIS",
        "format": "jpg",
        "max_zoom": 9,
        "category": "visible",
        "resolution": "250m",
        "temporal": True,
    },
    "modis_aqua_truecolor": {
        "id": "MODIS_Aqua_CorrectedReflectance_TrueColor",
        "name": "MODIS Aqua True Color",
        "description": "Daily true-color from NASA Aqua/MODIS (afternoon pass)",
        "format": "jpg",
        "max_zoom": 9,
        "category": "visible",
        "resolution": "250m",
        "temporal": True,
    },
    "viirs_snpp_truecolor": {
        "id": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
        "name": "VIIRS True Color",
        "description": "Daily true-color from Suomi NPP/VIIRS (higher resolution)",
        "format": "jpg",
        "max_zoom": 9,
        "category": "visible",
        "resolution": "375m",
        "temporal": True,
    },

    # Nighttime / Thermal
    "viirs_night_lights": {
        "id": "VIIRS_SNPP_DayNightBand_At_Sensor_Radiance",
        "name": "VIIRS Nighttime Lights",
        "description": "Nighttime visible/near-IR lights from space",
        "format": "png",
        "max_zoom": 8,
        "category": "nighttime",
        "resolution": "500m",
        "temporal": True,
    },
    "modis_lst_day": {
        "id": "MODIS_Terra_Land_Surface_Temp_Day",
        "name": "Land Surface Temperature (Day)",
        "description": "Daytime land surface temperature from MODIS",
        "format": "png",
        "max_zoom": 7,
        "category": "thermal",
        "resolution": "1km",
        "temporal": True,
    },
    "modis_lst_night": {
        "id": "MODIS_Terra_Land_Surface_Temp_Night",
        "name": "Land Surface Temperature (Night)",
        "description": "Nighttime land surface temperature",
        "format": "png",
        "max_zoom": 7,
        "category": "thermal",
        "resolution": "1km",
        "temporal": True,
    },

    # Fires & Thermal Anomalies
    "modis_fire": {
        "id": "MODIS_Terra_Thermal_Anomalies_Day",
        "name": "Active Fires (MODIS)",
        "description": "Active fire/thermal hotspots detected by MODIS",
        "format": "png",
        "max_zoom": 8,
        "category": "fire",
        "resolution": "1km",
        "temporal": True,
    },
    "viirs_fire": {
        "id": "VIIRS_SNPP_Thermal_Anomalies_375m_Day",
        "name": "Active Fires (VIIRS)",
        "description": "High-resolution fire detection from VIIRS",
        "format": "png",
        "max_zoom": 9,
        "category": "fire",
        "resolution": "375m",
        "temporal": True,
    },

    # Vegetation & Land
    "modis_ndvi": {
        "id": "MODIS_Terra_NDVI_8Day",
        "name": "Vegetation Index (NDVI)",
        "description": "8-day NDVI vegetation greenness composite",
        "format": "png",
        "max_zoom": 8,
        "category": "vegetation",
        "resolution": "250m",
        "temporal": True,
    },
    "modis_snow": {
        "id": "MODIS_Terra_Snow_Cover",
        "name": "Snow Cover",
        "description": "Daily snow cover extent from MODIS",
        "format": "png",
        "max_zoom": 8,
        "category": "weather",
        "resolution": "500m",
        "temporal": True,
    },

    # Atmospheric
    "modis_aod": {
        "id": "MODIS_Terra_Aerosol_Optical_Depth",
        "name": "Aerosol Optical Depth",
        "description": "Atmospheric aerosol/haze concentration",
        "format": "png",
        "max_zoom": 7,
        "category": "atmosphere",
        "resolution": "1km",
        "temporal": True,
    },
    "modis_cloud": {
        "id": "MODIS_Terra_Cloud_Top_Temp_Day",
        "name": "Cloud Top Temperature",
        "description": "Cloud-top temperature for weather analysis",
        "format": "png",
        "max_zoom": 7,
        "category": "weather",
        "resolution": "1km",
        "temporal": True,
    },

    # Reference / Base Layers
    "blue_marble": {
        "id": "BlueMarble_NextGeneration",
        "name": "Blue Marble (Monthly)",
        "description": "NASA Blue Marble composite imagery",
        "format": "jpg",
        "max_zoom": 8,
        "category": "reference",
        "resolution": "500m",
        "temporal": False,
    },
    "earth_at_night": {
        "id": "VIIRS_Black_Marble",
        "name": "Earth at Night (Black Marble)",
        "description": "Annual composite of nighttime lights",
        "format": "png",
        "max_zoom": 8,
        "category": "nighttime",
        "resolution": "500m",
        "temporal": False,
    },

    # Sentinel (via GIBS)
    "sentinel_truecolor": {
        "id": "HLS_S30_Nadir_BRDF_Adjusted_Reflectance",
        "name": "Sentinel-2 True Color (HLS)",
        "description": "Harmonized Landsat-Sentinel true color (30m)",
        "format": "png",
        "max_zoom": 13,
        "category": "visible",
        "resolution": "30m",
        "temporal": True,
    },
}


# ---------------------------------------------------------------------------
# Layer Access Functions
# ---------------------------------------------------------------------------

def get_gibs_layer_config(layer_key, date=None):
    """
    Get full tile configuration for a GIBS layer.
    Returns dict compatible with MapLibre raster source config.
    """
    layer = GIBS_LAYERS.get(layer_key)
    if not layer:
        return None

    if date is None and layer.get("temporal"):
        date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif date is None:
        date = "default"

    tile_url = gibs_tile_url(
        layer["id"],
        date=date if layer.get("temporal") else None,
        format=layer.get("format", "png"),
    )

    return {
        "key": layer_key,
        "name": layer["name"],
        "description": layer["description"],
        "category": layer["category"],
        "resolution": layer["resolution"],
        "date": date,
        "tile_url": tile_url,
        "max_zoom": layer.get("max_zoom", 9),
        "format": layer.get("format", "png"),
        "temporal": layer.get("temporal", False),
    }


def get_gibs_catalog():
    """Return the full catalog of available GIBS layers."""
    catalog = {}
    for key, layer in GIBS_LAYERS.items():
        catalog[key] = {
            "name": layer["name"],
            "description": layer["description"],
            "category": layer["category"],
            "resolution": layer["resolution"],
            "temporal": layer.get("temporal", False),
        }
    return catalog


def get_gibs_layers_by_category(category):
    """Get all GIBS layers in a given category."""
    return {
        k: v for k, v in GIBS_LAYERS.items()
        if v.get("category") == category
    }


def get_available_dates(layer_key, count=30):
    """
    Get available dates for a temporal GIBS layer.
    Returns last N days (GIBS typically has data 1-2 days behind).
    """
    layer = GIBS_LAYERS.get(layer_key)
    if not layer or not layer.get("temporal"):
        return []

    dates = []
    for i in range(1, count + 1):
        d = datetime.utcnow() - timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates
