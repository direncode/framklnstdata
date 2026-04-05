"use client";

import { useState, useEffect } from "react";

/**
 * Global OSINT Intelligence Dashboard
 *
 * Aggregated intelligence view showing all global data sources:
 * cameras, aircraft, satellites, GIBS layers, street imagery.
 * Provides high-level overview and drill-down capabilities.
 */

const API_BASE = "/api/data";

interface GIBSLayer {
  name: string;
  description: string;
  category: string;
  resolution: string;
  temporal: boolean;
}

export default function GlobalPanel({
  onGIBSLayerSelect,
  selectedGIBSLayer,
  cameraCount,
  aircraftCount,
  satelliteCount,
}: {
  onGIBSLayerSelect?: (layerId: string | null) => void;
  selectedGIBSLayer?: string | null;
  cameraCount: number;
  aircraftCount: number;
  satelliteCount: number;
}) {
  const [gibsCatalog, setGibsCatalog] = useState<Record<string, GIBSLayer>>({});
  const [gibsCategories, setGibsCategories] = useState<string[]>([]);
  const [activeGibsCategory, setActiveGibsCategory] = useState<string>("visible");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchGIBSCatalog();
  }, []);

  const fetchGIBSCatalog = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/gibs`);
      if (res.ok) {
        const data = await res.json();
        setGibsCatalog(data.catalog || {});
        setGibsCategories(data.categories || []);
      }
    } catch { /* empty */ }
    setLoading(false);
  };

  const filteredGIBS = Object.entries(gibsCatalog).filter(
    ([, layer]) => layer.category === activeGibsCategory
  );

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 grid-overlay">
      <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-4">
        Global Intelligence Overview
      </h2>

      {/* Global Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <div className="metric-card glow-green">
          <div className="text-[9px] text-[#454a58] uppercase">Surveillance Cameras</div>
          <div className="text-3xl font-mono text-[#ff4d6a] mt-1">{cameraCount}</div>
          <div className="text-[10px] text-[#454a58] mt-1">OSM + Traffic + ALPR</div>
        </div>
        <div className="metric-card glow-blue">
          <div className="text-[9px] text-[#454a58] uppercase">Live Aircraft</div>
          <div className="text-3xl font-mono text-[#4a9eff] mt-1">{aircraftCount}</div>
          <div className="text-[10px] text-[#454a58] mt-1">OpenSky ADS-B</div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Satellites Tracked</div>
          <div className="text-3xl font-mono text-[#ff6600] mt-1">{satelliteCount}</div>
          <div className="text-[10px] text-[#454a58] mt-1">CelesTrak TLE</div>
        </div>
      </div>

      {/* NASA GIBS Satellite Imagery Layers */}
      <div className="border border-[#1e2028] rounded-lg bg-[#111318] mb-4">
        <div className="px-4 py-3 border-b border-[#1e2028]">
          <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider">
            NASA GIBS Satellite Imagery
          </h3>
          <p className="text-[10px] font-mono text-[#454a58] mt-1">
            Global satellite imagery products from NASA EOSDIS
          </p>
        </div>

        {/* Category tabs */}
        <div className="flex flex-wrap gap-1 px-4 py-2 border-b border-[#1e2028]">
          {gibsCategories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveGibsCategory(cat)}
              className={`px-2 py-1 rounded text-[9px] font-mono transition-all ${
                activeGibsCategory === cat
                  ? "bg-[#00d4aa15] text-[#00d4aa] border border-[#00d4aa33]"
                  : "text-[#454a58] hover:text-[#6b7080]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Layer list */}
        <div className="max-h-[300px] overflow-y-auto p-2">
          {loading ? (
            <div className="p-4 text-xs font-mono text-[#454a58] text-center animate-pulse">
              Loading GIBS catalog...
            </div>
          ) : filteredGIBS.length > 0 ? (
            <div className="space-y-1">
              {filteredGIBS.map(([key, layer]) => (
                <button
                  key={key}
                  onClick={() => onGIBSLayerSelect?.(selectedGIBSLayer === key ? null : key)}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all ${
                    selectedGIBSLayer === key
                      ? "bg-[#00d4aa15] text-[#00d4aa] border border-[#00d4aa33]"
                      : "text-[#e2e4e9] hover:bg-[#1e2028]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span>{layer.name}</span>
                    <span className="text-[9px] text-[#454a58]">{layer.resolution}</span>
                  </div>
                  <div className="text-[10px] text-[#454a58] mt-0.5">{layer.description}</div>
                </button>
              ))}
            </div>
          ) : (
            <div className="p-4 text-xs font-mono text-[#454a58] text-center">
              No layers in this category
            </div>
          )}
        </div>
      </div>

      {/* System Architecture */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318] mb-4">
        <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-4">
          Global Intelligence Stack
        </h3>
        <div className="space-y-3 text-xs text-[#6b7080] leading-relaxed">
          <div className="flex gap-3">
            <span className="text-[#00d4aa] font-mono shrink-0">3D</span>
            <span>CesiumJS globe with ESRI satellite imagery, 3D Tiles, terrain, and real-time entity tracking</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#ff4d6a] font-mono shrink-0">CAM</span>
            <span>OpenStreetMap surveillance tags + NCDOT traffic feeds + ALPR/FLOCK network mapping + PanoptiCity FOV analysis</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#4a9eff] font-mono shrink-0">ADS</span>
            <span>OpenSky Network live ADS-B aircraft positions with 15-second refresh across global regions</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#ff6600] font-mono shrink-0">SAT</span>
            <span>CelesTrak TLE orbit propagation for stations, visual, GPS, weather, military, and Starlink constellations</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#a050ff] font-mono shrink-0">IMG</span>
            <span>NASA GIBS (MODIS, VIIRS, Sentinel-2), Mapillary/KartaView street-level panoramas, OSM geotagged photos</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#ffaa00] font-mono shrink-0">VIZ</span>
            <span>Night vision (Gen III phosphor), FLIR thermal, CRT retro display modes with GPU-accelerated shaders</span>
          </div>
        </div>
      </div>

      {/* Technology Credits */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318]">
        <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
          Data Sources & Technology
        </h3>
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-[#454a58]">
          {[
            { name: "CesiumJS", desc: "3D Globe" },
            { name: "MapLibre GL", desc: "2D Maps" },
            { name: "OpenStreetMap", desc: "Vector Data" },
            { name: "ESRI Imagery", desc: "Satellite Tiles" },
            { name: "NASA GIBS", desc: "Earth Observation" },
            { name: "OpenSky Network", desc: "Aircraft ADS-B" },
            { name: "CelesTrak", desc: "Satellite TLE" },
            { name: "Mapillary", desc: "Street Photos" },
            { name: "KartaView", desc: "Driving Imagery" },
            { name: "NCDOT", desc: "Traffic Cams" },
            { name: "Sentinel-2", desc: "EU Imaging" },
            { name: "Google Trends", desc: "Search Intel" },
          ].map((t) => (
            <div key={t.name} className="flex items-center gap-2">
              <span className="w-1 h-1 rounded-full bg-[#00d4aa]" />
              <span className="text-[#6b7080]">{t.name}</span>
              <span className="text-[#454a58]">— {t.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
