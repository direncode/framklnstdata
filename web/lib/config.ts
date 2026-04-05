export const FRANKLIN_STREET = {
  center: { lat: 35.9132, lng: -79.0555 },
  zoom: 16,
  bounds: {
    south: 35.91,
    north: 35.923,
    west: -79.062,
    east: -79.043,
  },
};

export const MAP_STYLES = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  satellite:
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
};

// Global surveillance configuration
export const GLOBAL_CONFIG = {
  // CesiumJS 3D Globe
  cesium: {
    defaultView: { lat: 35.9132, lon: -79.0555, height: 50000 },
    imagery: {
      esri: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      esriLabels: "https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      sentinel2: "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg",
    },
  },

  // NASA GIBS tile URL builder
  gibs: {
    baseUrl: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best",
    defaultLayer: "MODIS_Terra_CorrectedReflectance_TrueColor",
    defaultFormat: "jpg",
    matrixSet: "GoogleMapsCompatible_Level9",
  },

  // Aircraft tracking regions
  aircraftRegions: {
    chapel_hill: { label: "Chapel Hill", bbox: [34.5, -80.5, 37.0, -77.5] },
    us_east: { label: "US East Coast", bbox: [25.0, -90.0, 48.0, -65.0] },
    us_west: { label: "US West Coast", bbox: [25.0, -130.0, 50.0, -90.0] },
    europe: { label: "Europe", bbox: [35.0, -10.0, 60.0, 40.0] },
    east_asia: { label: "East Asia", bbox: [20.0, 100.0, 50.0, 145.0] },
  },

  // Satellite tracking categories
  satelliteCategories: [
    "stations", "visual", "gps", "weather",
    "earth_resources", "military", "starlink",
  ],

  // Display modes
  displayModes: ["normal", "night_vision", "flir", "crt"] as const,

  // Data refresh intervals (ms)
  refreshIntervals: {
    aircraft: 15000,
    satellites: 60000,
    cameras: 300000,
    venues: 120000,
  },
};
