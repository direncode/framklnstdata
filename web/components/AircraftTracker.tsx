"use client";

import { useState, useEffect, useCallback } from "react";

interface Aircraft {
  icao24: string;
  callsign: string;
  origin_country: string;
  lat: number;
  lon: number;
  altitude_m: number;
  velocity_ms: number;
  heading: number;
  category: string;
  source: string;
}

interface AircraftStats {
  count: number;
  altitude_range_m: number[];
  avg_altitude_m: number;
  avg_speed_ms: number;
  countries: Record<string, number>;
  categories: Record<string, number>;
}

const API_BASE = "/api/data";

const REGIONS = [
  { id: "chapel_hill", label: "Chapel Hill Area" },
  { id: "us_east", label: "US East Coast" },
  { id: "us_west", label: "US West Coast" },
  { id: "europe", label: "Europe" },
  { id: "east_asia", label: "East Asia" },
];

export default function AircraftTracker({
  onAircraftLoaded,
}: {
  onAircraftLoaded?: (aircraft: Aircraft[]) => void;
}) {
  const [aircraft, setAircraft] = useState<Aircraft[]>([]);
  const [stats, setStats] = useState<AircraftStats | null>(null);
  const [region, setRegion] = useState("chapel_hill");
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  const fetchAircraft = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/aircraft?region=${region}`);
      if (res.ok) {
        const data = await res.json();
        setAircraft(data.aircraft || []);
        setStats(data.stats || null);
        setLastUpdate(new Date().toLocaleTimeString("en-US", { hour12: false }));
        onAircraftLoaded?.(data.aircraft || []);
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [region, onAircraftLoaded]);

  useEffect(() => {
    fetchAircraft();
  }, [fetchAircraft]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchAircraft, 15000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchAircraft]);

  const metersToFeet = (m: number) => Math.round(m * 3.28084);
  const msToKnots = (ms: number) => Math.round(ms * 1.94384);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 grid-overlay">
      <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#4a9eff] uppercase mb-4">
        Live Aircraft Tracking — ADS-B
      </h2>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="metric-card glow-blue">
          <div className="text-[9px] text-[#454a58] uppercase">Aircraft</div>
          <div className="text-2xl font-mono text-[#4a9eff] mt-1">
            {loading && aircraft.length === 0 ? "..." : aircraft.length}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Avg Altitude</div>
          <div className="text-2xl font-mono text-[#e2e4e9] mt-1">
            {stats?.avg_altitude_m ? `${metersToFeet(stats.avg_altitude_m).toLocaleString()}ft` : "--"}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Avg Speed</div>
          <div className="text-2xl font-mono text-[#e2e4e9] mt-1">
            {stats?.avg_speed_ms ? `${msToKnots(stats.avg_speed_ms)}kt` : "--"}
          </div>
        </div>
        <div className="metric-card">
          <div className="text-[9px] text-[#454a58] uppercase">Countries</div>
          <div className="text-2xl font-mono text-[#00d4aa] mt-1">
            {stats?.countries ? Object.keys(stats.countries).length : 0}
          </div>
        </div>
      </div>

      {/* Region Selector */}
      <div className="flex flex-wrap gap-2 mb-4">
        {REGIONS.map((r) => (
          <button
            key={r.id}
            onClick={() => setRegion(r.id)}
            className={`px-3 py-1.5 rounded text-[10px] font-mono transition-all ${
              region === r.id
                ? "bg-[#4a9eff20] text-[#4a9eff] border border-[#4a9eff44]"
                : "text-[#454a58] hover:text-[#6b7080] bg-[#111318] border border-[#1e2028]"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4 mb-4">
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded text-[10px] font-mono ${
            autoRefresh
              ? "bg-[#00d4aa15] text-[#00d4aa] border border-[#00d4aa33]"
              : "text-[#454a58] bg-[#111318] border border-[#1e2028]"
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${autoRefresh ? "bg-[#00d4aa] status-live" : "bg-[#454a58]"}`} />
          Auto-Refresh (15s)
        </button>
        <button
          onClick={fetchAircraft}
          className="px-3 py-1.5 rounded text-[10px] font-mono text-[#6b7080] bg-[#111318] border border-[#1e2028] hover:border-[#4a9eff44]"
        >
          Refresh Now
        </button>
        {lastUpdate && (
          <span className="text-[9px] font-mono text-[#454a58]">
            Last: {lastUpdate}
          </span>
        )}
      </div>

      {/* Aircraft Table */}
      {aircraft.length > 0 && (
        <div className="border border-[#1e2028] rounded-lg overflow-hidden mb-4">
          <div className="max-h-[400px] overflow-y-auto">
            <table className="w-full text-xs font-mono">
              <thead className="sticky top-0">
                <tr className="border-b border-[#1e2028] bg-[#111318]">
                  <th className="text-left px-3 py-2 text-[#454a58]">Callsign</th>
                  <th className="text-left px-3 py-2 text-[#454a58]">Country</th>
                  <th className="text-right px-3 py-2 text-[#454a58]">Alt (ft)</th>
                  <th className="text-right px-3 py-2 text-[#454a58]">Speed (kt)</th>
                  <th className="text-right px-3 py-2 text-[#454a58]">Hdg</th>
                  <th className="text-left px-3 py-2 text-[#454a58]">Type</th>
                </tr>
              </thead>
              <tbody>
                {aircraft.slice(0, 50).map((ac) => (
                  <tr key={ac.icao24} className="border-b border-[#1e2028] hover:bg-[#111318]">
                    <td className="px-3 py-1.5 text-[#4a9eff]">
                      {ac.callsign || ac.icao24}
                    </td>
                    <td className="px-3 py-1.5 text-[#6b7080]">{ac.origin_country}</td>
                    <td className="px-3 py-1.5 text-right text-[#e2e4e9]">
                      {ac.altitude_m ? metersToFeet(ac.altitude_m).toLocaleString() : "--"}
                    </td>
                    <td className="px-3 py-1.5 text-right text-[#e2e4e9]">
                      {ac.velocity_ms ? msToKnots(ac.velocity_ms) : "--"}
                    </td>
                    <td className="px-3 py-1.5 text-right text-[#6b7080]">
                      {ac.heading ? `${Math.round(ac.heading)}°` : "--"}
                    </td>
                    <td className="px-3 py-1.5 text-[#454a58]">{ac.category}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Country Breakdown */}
      {stats?.countries && Object.keys(stats.countries).length > 0 && (
        <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318] mb-4">
          <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-3">
            Origin Countries
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(stats.countries).slice(0, 10).map(([country, count]) => (
              <div key={country} className="flex justify-between text-xs font-mono">
                <span className="text-[#e2e4e9]">{country}</span>
                <span className="text-[#4a9eff]">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Source Info */}
      <div className="border border-[#1e2028] rounded-lg p-4 bg-[#111318]">
        <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-2">
          Source
        </h3>
        <div className="text-xs font-mono text-[#454a58] space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4a9eff]" />
            OpenSky Network (ADS-B)
          </div>
          <div className="text-[#6b7080] mt-1">
            Real-time aircraft positions from crowd-sourced ADS-B receivers worldwide.
            Updates every 15 seconds.
          </div>
        </div>
      </div>
    </div>
  );
}
