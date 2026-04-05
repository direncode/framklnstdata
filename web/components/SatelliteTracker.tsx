"use client";

import { useState, useEffect, useCallback } from "react";

interface Satellite {
  name: string;
  norad_id: number;
  inclination: number;
  period_min: number;
  apogee_km: number;
  perigee_km: number;
  country: string;
  category: string;
  object_type: string;
  lat?: number;
  lon?: number;
  alt_km?: number;
}

interface OverheadSat {
  name: string;
  norad_id: number;
  lat: number;
  lon: number;
  alt_km: number;
  elevation_deg: number;
  distance_km: number;
}

interface Constellation {
  name: string;
  operator: string;
  count: number;
  orbit_km: number;
  purpose: string;
  country: string;
}

const API_BASE = "/api/data";

const CATEGORIES = [
  { id: "stations", label: "Space Stations" },
  { id: "visual", label: "Brightest" },
  { id: "gps", label: "GPS" },
  { id: "weather", label: "Weather" },
  { id: "earth_resources", label: "Earth Obs" },
  { id: "military", label: "Military" },
  { id: "starlink", label: "Starlink" },
];

export default function SatelliteTracker({
  onSatellitesLoaded,
  onTrackLoaded,
}: {
  onSatellitesLoaded?: (sats: any[]) => void;
  onTrackLoaded?: (track: any[]) => void;
}) {
  const [satellites, setSatellites] = useState<Satellite[]>([]);
  const [overhead, setOverhead] = useState<OverheadSat[]>([]);
  const [constellations, setConstellations] = useState<Constellation[]>([]);
  const [categories, setCategories] = useState<string[]>(["stations", "visual"]);
  const [loading, setLoading] = useState(false);
  const [selectedSat, setSelectedSat] = useState<string | null>(null);
  const [totalActive, setTotalActive] = useState(0);

  const fetchSatellites = useCallback(async () => {
    setLoading(true);
    try {
      const catStr = categories.join(",");
      const res = await fetch(`${API_BASE}/satellites?category=${catStr}`);
      if (res.ok) {
        const data = await res.json();
        setSatellites(data.satellites || []);
        setOverhead(data.overhead || []);
        setConstellations(data.constellations?.constellations || []);
        setTotalActive(data.constellations?.total_active || 0);

        // Send positions to globe via geojson
        if (data.geojson?.features) {
          onSatellitesLoaded?.(data.geojson.features.map((f: any) => ({
            name: f.properties.name,
            norad_id: f.properties.norad_id,
            lat: f.geometry.coordinates[1],
            lon: f.geometry.coordinates[0],
            alt_km: f.properties.alt_km,
          })));
        }
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [categories, onSatellitesLoaded]);

  useEffect(() => {
    fetchSatellites();
  }, [fetchSatellites]);

  // Fetch ground track when a satellite is selected
  useEffect(() => {
    if (!selectedSat) {
      onTrackLoaded?.([]);
      return;
    }

    const fetchTrack = async () => {
      try {
        const cat = categories[0] || "stations";
        const res = await fetch(
          `${API_BASE}/satellites/track?name=${encodeURIComponent(selectedSat)}&category=${cat}&duration=90`
        );
        if (res.ok) {
          const data = await res.json();
          onTrackLoaded?.(data.track || []);
        }
      } catch { /* empty */ }
    };
    fetchTrack();
  }, [selectedSat, categories, onTrackLoaded]);

  const toggleCategory = (cat: string) => {
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 grid-overlay">
      <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#ff6600] uppercase mb-4">
        Satellite Orbit Tracking — CelesTrak TLE
      </h2>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Tracking</div>
          <div className="text-2xl font-mono text-[#ff6600] mt-1">
            {loading ? "..." : satellites.length}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Overhead</div>
          <div className="text-2xl font-mono text-[#00d4aa] mt-1">
            {overhead.length}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Active Global</div>
          <div className="text-2xl font-mono text-[#4a9eff] mt-1">
            {totalActive ? `${(totalActive / 1000).toFixed(1)}K` : "--"}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Categories</div>
          <div className="text-2xl font-mono text-[#e2e4e9] mt-1">
            {categories.length}
          </div>
        </div>
      </div>

      {/* Category Selector */}
      <div className="flex flex-wrap gap-2 mb-4">
        {CATEGORIES.map((c) => (
          <button
            key={c.id}
            onClick={() => toggleCategory(c.id)}
            className={`px-3 py-1.5 rounded text-[10px] font-mono transition-all ${
              categories.includes(c.id)
                ? "bg-[#ff660020] text-[#ff6600] border border-[#ff660044]"
                : "text-[#454a58] bg-[#111318] border border-[#1e2028] hover:border-[#ff660033]"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Overhead Satellites */}
      {overhead.length > 0 && (
        <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318] mb-4">
          <h3 className="text-xs font-mono text-[#00d4aa] uppercase tracking-wider mb-3">
            Currently Overhead (Chapel Hill)
          </h3>
          <div className="space-y-2">
            {overhead.slice(0, 10).map((sat) => (
              <button
                key={sat.norad_id}
                onClick={() => setSelectedSat(sat.name === selectedSat ? null : sat.name)}
                className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-xs font-mono transition-all ${
                  selectedSat === sat.name
                    ? "bg-[#ff660020] text-[#ff6600]"
                    : "text-[#e2e4e9] hover:bg-[#1e2028]"
                }`}
              >
                <span>{sat.name}</span>
                <span className="text-[#6b7080]">
                  {sat.elevation_deg.toFixed(0)}° elev · {sat.alt_km.toFixed(0)}km
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Satellite Table */}
      {satellites.length > 0 && (
        <div className="border border-[#1e2028] rounded-lg overflow-hidden mb-4">
          <div className="max-h-[300px] overflow-y-auto">
            <table className="w-full text-xs font-mono">
              <thead className="sticky top-0">
                <tr className="border-b border-[#1e2028] bg-[#111318]">
                  <th className="text-left px-3 py-2 text-[#454a58]">Name</th>
                  <th className="text-right px-3 py-2 text-[#454a58]">Incl</th>
                  <th className="text-right px-3 py-2 text-[#454a58]">Period</th>
                  <th className="text-right px-3 py-2 text-[#454a58]">Apogee</th>
                  <th className="text-left px-3 py-2 text-[#454a58]">Country</th>
                </tr>
              </thead>
              <tbody>
                {satellites.slice(0, 50).map((sat) => (
                  <tr
                    key={sat.norad_id}
                    onClick={() => setSelectedSat(sat.name === selectedSat ? null : sat.name)}
                    className={`border-b border-[#1e2028] cursor-pointer ${
                      selectedSat === sat.name ? "bg-[#ff660015]" : "hover:bg-[#111318]"
                    }`}
                  >
                    <td className="px-3 py-1.5 text-[#ff6600]">{sat.name}</td>
                    <td className="px-3 py-1.5 text-right text-[#e2e4e9]">
                      {sat.inclination?.toFixed(1)}°
                    </td>
                    <td className="px-3 py-1.5 text-right text-[#e2e4e9]">
                      {sat.period_min?.toFixed(1)}m
                    </td>
                    <td className="px-3 py-1.5 text-right text-[#6b7080]">
                      {sat.apogee_km?.toFixed(0)}km
                    </td>
                    <td className="px-3 py-1.5 text-[#454a58]">{sat.country}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Constellations */}
      {constellations.length > 0 && (
        <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318]">
          <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
            Major Constellations
          </h3>
          <div className="space-y-2">
            {constellations.map((c) => (
              <div key={c.name} className="flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-[#e2e4e9]">{c.name}</span>
                  <span className="text-[#454a58] ml-2">({c.operator})</span>
                </div>
                <div className="text-[#6b7080]">
                  <span className="text-[#ff6600]">{c.count}</span>
                  <span className="mx-1">·</span>
                  <span>{c.orbit_km}km</span>
                  <span className="mx-1">·</span>
                  <span className="text-[#454a58]">{c.purpose}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
