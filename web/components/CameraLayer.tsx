"use client";

import { useState, useEffect } from "react";

interface Camera {
  id: string | number;
  lat: number;
  lon: number;
  type: string;
  operator: string;
  zone?: string;
  brand?: string;
  source?: string;
  fov_polygon?: number[][];
  feed_url?: string;
  name?: string;
}

interface CameraStats {
  total_count: number;
  coverage: {
    coverage_pct: number;
    camera_count: number;
    area_km2?: number;
    types: Record<string, number>;
    operators?: string[];
  };
  sources: Record<string, number>;
}

interface CameraHotspot {
  city: string;
  lat: number;
  lon: number;
  estimated_cameras: number;
  country: string;
}

const API_BASE = "/api/data";

export default function CameraLayer({
  onCamerasLoaded,
}: {
  onCamerasLoaded?: (cameras: Camera[]) => void;
}) {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [stats, setStats] = useState<CameraStats | null>(null);
  const [globalStats, setGlobalStats] = useState<{
    hotspots: CameraHotspot[];
    global_estimate: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [showGlobal, setShowGlobal] = useState(false);

  useEffect(() => {
    fetchCameras();
    fetchGlobalStats();
  }, []);

  const fetchCameras = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/cameras`);
      if (res.ok) {
        const data = await res.json();
        setCameras(data.cameras || []);
        setStats(data);
        onCamerasLoaded?.(data.cameras || []);
      }
    } catch { /* empty */ }
    setLoading(false);
  };

  const fetchGlobalStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/cameras/global`);
      if (res.ok) {
        const data = await res.json();
        setGlobalStats(data);
      }
    } catch { /* empty */ }
  };

  const typeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "alpr": return "#ff4d6a";
      case "traffic": return "#ffaa00";
      case "cctv": case "camera": return "#00d4aa";
      case "webcam": return "#4a9eff";
      default: return "#6b7080";
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 grid-overlay">
      <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#ff4d6a] uppercase mb-4">
        Surveillance Camera Intelligence
      </h2>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Local Cameras</div>
          <div className="text-2xl font-mono text-[#ff4d6a] mt-1">
            {loading ? "..." : stats?.total_count || 0}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Coverage</div>
          <div className="text-2xl font-mono text-[#ffaa00] mt-1">
            {stats?.coverage?.coverage_pct || 0}%
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Global Est.</div>
          <div className="text-2xl font-mono text-[#00d4aa] mt-1">
            {globalStats ? `${(globalStats.global_estimate / 1e6).toFixed(0)}M` : "..."}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Sources</div>
          <div className="text-2xl font-mono text-[#4a9eff] mt-1">
            {stats ? Object.keys(stats.sources || {}).length : 0}
          </div>
        </div>
      </div>

      {/* Camera Type Breakdown */}
      {stats?.coverage?.types && Object.keys(stats.coverage.types).length > 0 && (
        <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318] mb-4">
          <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
            Camera Types
          </h3>
          <div className="space-y-2">
            {Object.entries(stats.coverage.types)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: typeColor(type) }} />
                    <span className="text-xs font-mono text-[#e2e4e9]">{type}</span>
                  </div>
                  <span className="text-xs font-mono text-[#6b7080]">{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Global Hotspots Toggle */}
      <button
        onClick={() => setShowGlobal(!showGlobal)}
        className={`w-full flex items-center justify-between px-4 py-2 rounded-lg mb-4 text-xs font-mono transition-all ${
          showGlobal
            ? "bg-[#ff4d6a15] text-[#ff4d6a] border border-[#ff4d6a33]"
            : "bg-[#111318] text-[#6b7080] border border-[#1e2028] hover:border-[#ff4d6a33]"
        }`}
      >
        <span>Global Surveillance Hotspots</span>
        <span>{showGlobal ? "▾" : "▸"}</span>
      </button>

      {showGlobal && globalStats?.hotspots && (
        <div className="border border-[#1e2028] rounded-lg overflow-hidden mb-4">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-[#1e2028] bg-[#111318]">
                <th className="text-left px-3 py-2 text-[#454a58]">City</th>
                <th className="text-left px-3 py-2 text-[#454a58]">Country</th>
                <th className="text-right px-3 py-2 text-[#454a58]">Est. Cameras</th>
              </tr>
            </thead>
            <tbody>
              {globalStats.hotspots
                .sort((a, b) => b.estimated_cameras - a.estimated_cameras)
                .map((h) => (
                  <tr key={h.city} className="border-b border-[#1e2028] hover:bg-[#111318]">
                    <td className="px-3 py-1.5 text-[#e2e4e9]">{h.city}</td>
                    <td className="px-3 py-1.5 text-[#6b7080]">{h.country}</td>
                    <td className="px-3 py-1.5 text-right text-[#ff4d6a]">
                      {h.estimated_cameras.toLocaleString()}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* FLOCK/ALPR Network Info */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318] mb-4">
        <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
          ALPR Networks
        </h3>
        <div className="space-y-2 text-xs text-[#6b7080]">
          <div className="flex justify-between">
            <span>Flock Safety Network</span>
            <span className="text-[#ff4d6a]">336,000+ cameras</span>
          </div>
          <div className="flex justify-between">
            <span>Coverage</span>
            <span>United States</span>
          </div>
          <div className="flex justify-between">
            <span>Data Sharing</span>
            <span className="text-[#ffaa00]">Cross-Agency Active</span>
          </div>
        </div>
      </div>

      {/* Data Sources */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318]">
        <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
          Data Sources
        </h3>
        <div className="space-y-2 text-xs font-mono text-[#454a58]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00d4aa]" />
            OpenStreetMap (man_made=surveillance)
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ffaa00]" />
            NCDOT Traffic Camera Feeds
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#ff4d6a]" />
            ALPR/Flock Safety (OSM-tagged)
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4a9eff]" />
            PanoptiCity Field-of-View Analysis
          </div>
        </div>
      </div>
    </div>
  );
}
