"use client";

import { useState, useEffect } from "react";

/**
 * Street-Level Imagery Panel
 *
 * Integrates with Mapillary, KartaView, and OSM photo data.
 * Shows coverage info and provides links to panoramic viewers.
 * Inspired by tjhorner/streetlens (self-hosted panorama viewer).
 */

interface StreetImagery {
  sources: {
    mapillary: { count: number; viewer_url: string };
    kartaview: { count: number; viewer_url: string };
    osm_photos: { count: number };
  };
  total_images: number;
  panorama_urls: {
    mapillary: string;
    kartaview: string;
    google: string;
  };
}

const API_BASE = "/api/data";

export default function StreetView({
  lat = 35.9132,
  lon = -79.0555,
}: {
  lat?: number;
  lon?: number;
}) {
  const [data, setData] = useState<StreetImagery | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeViewer, setActiveViewer] = useState<string | null>(null);

  useEffect(() => {
    fetchImagery();
  }, [lat, lon]);

  const fetchImagery = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/street-imagery?lat=${lat}&lon=${lon}`);
      if (res.ok) {
        setData(await res.json());
      }
    } catch { /* empty */ }
    setLoading(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 grid-overlay">
      <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#a050ff] uppercase mb-4">
        Street-Level Imagery Intelligence
      </h2>

      {/* Location Header */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318] mb-4">
        <div className="text-xs font-mono text-[#6b7080]">
          Analyzing coverage at {lat.toFixed(4)}°N, {Math.abs(lon).toFixed(4)}°W
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Mapillary</div>
          <div className="text-2xl font-mono text-[#00d4aa] mt-1">
            {loading ? "..." : data?.sources.mapillary.count || 0}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">KartaView</div>
          <div className="text-2xl font-mono text-[#4a9eff] mt-1">
            {loading ? "..." : data?.sources.kartaview.count || 0}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">OSM Photos</div>
          <div className="text-2xl font-mono text-[#ffaa00] mt-1">
            {loading ? "..." : data?.sources.osm_photos.count || 0}
          </div>
        </div>
      </div>

      {/* Panorama Viewer Links */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318] mb-4">
        <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
          Open Panoramic Viewer
        </h3>
        <div className="space-y-2">
          {data?.panorama_urls && Object.entries(data.panorama_urls).map(([source, url]) => (
            <a
              key={source}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full px-3 py-2 rounded text-xs font-mono bg-[#0d0e13] border border-[#1e2028] hover:border-[#a050ff44] transition-all group"
            >
              <div className="flex items-center justify-between">
                <span className="text-[#e2e4e9] group-hover:text-[#a050ff]">
                  {source.charAt(0).toUpperCase() + source.slice(1)} Street View
                </span>
                <span className="text-[#454a58] group-hover:text-[#6b7080]">→</span>
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* Embedded Viewer (Mapillary iFrame) */}
      <div className="border border-[#1e2028] rounded-lg overflow-hidden mb-4">
        <div className="flex items-center justify-between px-3 py-2 bg-[#111318] border-b border-[#1e2028]">
          <span className="text-[10px] font-mono text-[#6b7080] uppercase">
            Embedded Street View
          </span>
          <div className="flex gap-2">
            {["mapillary", "kartaview"].map((src) => (
              <button
                key={src}
                onClick={() => setActiveViewer(activeViewer === src ? null : src)}
                className={`px-2 py-1 rounded text-[9px] font-mono ${
                  activeViewer === src
                    ? "bg-[#a050ff20] text-[#a050ff] border border-[#a050ff44]"
                    : "text-[#454a58] hover:text-[#6b7080]"
                }`}
              >
                {src}
              </button>
            ))}
          </div>
        </div>

        {activeViewer === "mapillary" && (
          <iframe
            src={`https://www.mapillary.com/embed?map_style=Mapillary+light&image_key=&style=photo&lat=${lat}&lng=${lon}&z=16`}
            className="w-full h-[350px] border-0"
            title="Mapillary Street View"
            allow="fullscreen"
          />
        )}

        {activeViewer === "kartaview" && data?.sources.kartaview.viewer_url && (
          <div className="w-full h-[350px] flex items-center justify-center bg-[#0a0b0f]">
            <div className="text-center text-xs font-mono text-[#454a58]">
              <a
                href={data.sources.kartaview.viewer_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#4a9eff] hover:underline"
              >
                Open KartaView in new tab →
              </a>
            </div>
          </div>
        )}

        {!activeViewer && (
          <div className="w-full h-[200px] flex items-center justify-center bg-[#0a0b0f]">
            <div className="text-center text-xs font-mono text-[#454a58]">
              Select a viewer source above
            </div>
          </div>
        )}
      </div>

      {/* Capability Info */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318]">
        <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
          Capabilities
        </h3>
        <div className="space-y-2 text-xs font-mono text-[#454a58]">
          <div className="flex gap-3">
            <span className="text-[#a050ff] shrink-0">01</span>
            <span>Crowdsourced 360° panoramas from Mapillary (Meta) and KartaView</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#a050ff] shrink-0">02</span>
            <span>OSM-linked geotagged photos with wikimedia commons integration</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#a050ff] shrink-0">03</span>
            <span>Self-hostable with streetlens for private panorama indexing</span>
          </div>
          <div className="flex gap-3">
            <span className="text-[#a050ff] shrink-0">04</span>
            <span>Netryx-compatible geolocation from arbitrary street photos</span>
          </div>
        </div>
      </div>
    </div>
  );
}
