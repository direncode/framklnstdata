"use client";

import { useState, useEffect, useCallback } from "react";
import TopBar from "@/components/TopBar";
import Sidebar from "@/components/Sidebar";
import MapView from "@/components/MapView";
import VenuePanel from "@/components/VenuePanel";
import FeedView from "@/components/FeedView";
import HourSlider from "@/components/HourSlider";
import StatusBar from "@/components/StatusBar";
import CommandPanel from "@/components/CommandPanel";

type Tab = "map" | "feed" | "intel" | "command";

interface Venue {
  name: string;
  lat: number;
  lon: number;
  amenity_type: string;
  busyness: number | null;
  hourly_profile: number[] | null;
  cuisine?: string;
  address?: string;
  category?: string;
  phone?: string;
  website?: string;
  opening_hours?: string;
  outdoor_seating?: string;
  brand?: string;
  signals?: Record<string, string>;
}

interface TrendsData {
  has_data: boolean;
  geo: string;
  geo_description: string;
  suggestions: Array<{
    category: string;
    keyword: string;
    score: number;
    strength: string;
    suggestion: string;
    rising_queries: string[];
    rising_topics: string[];
    top_cities: Array<{ city: string; interest: number }>;
  }>;
  trending_now: string[];
  locally_relevant: string[];
  interest_by_city: Record<string, Array<{ city: string; interest: number }>>;
}

const API_BASE = "/api/data";

interface HeatmapPoint {
  lat: number;
  lon: number;
  weight: number;
}

export default function Home() {
  const [tab, setTab] = useState<Tab>("map");
  const [hour, setHour] = useState(new Date().getHours());
  const [venues, setVenues] = useState<Venue[]>([]);
  const [selectedVenue, setSelectedVenue] = useState<string | null>(null);
  const [trends, setTrends] = useState<TrendsData | null>(null);
  const [apiConnected, setApiConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showTraffic, setShowTraffic] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [trafficHeatmap, setTrafficHeatmap] = useState<HeatmapPoint[]>([]);
  const [searchHeatmap, setSearchHeatmap] = useState<HeatmapPoint[]>([]);

  const fetchVenues = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/spots?hour=${hour}`);
      if (res.ok) {
        const data = await res.json();
        const list = data?.spots || data?.venues || (Array.isArray(data) ? data : []);
        if (list.length > 0) {
          setVenues(list);
          setApiConnected(true);
          setLoading(false);
          return;
        }
      }
    } catch { /* empty */ }
    // Try /venues as fallback
    try {
      const res = await fetch(`${API_BASE}/venues`);
      if (res.ok) {
        const data = await res.json();
        const list = data?.venues || (Array.isArray(data) ? data : []);
        if (list.length > 0) {
          setVenues(list);
          setApiConnected(true);
          setLoading(false);
          return;
        }
      }
    } catch { /* empty */ }
    setVenues([]);
    setApiConnected(false);
    setLoading(false);
  }, [hour]);

  const fetchTrends = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/trends?live=true`);
      if (res.ok) {
        const data = await res.json();
        setTrends(data);
      }
    } catch { /* empty */ }
  }, []);

  const fetchHeatmaps = useCallback(async () => {
    // Traffic heatmap from BTUT density field
    if (showTraffic) {
      try {
        const res = await fetch(`${API_BASE}/heatmap?hour=${hour}`);
        if (res.ok) {
          const data = await res.json();
          const points = data?.heatmap || (Array.isArray(data) ? data : []);
          // Backend returns [[lat, lon, weight], ...] or {heatmap: [...]}
          const mapped = points.map((p: number[] | HeatmapPoint) =>
            Array.isArray(p) ? { lat: p[0], lon: p[1], weight: p[2] } : p
          );
          setTrafficHeatmap(mapped);
        }
      } catch { /* empty */ }
    }
    // Search convergence heatmap
    if (showSearch) {
      try {
        const res = await fetch(`${API_BASE}/convergence?hour=${hour}`);
        if (res.ok) {
          const data = await res.json();
          const points = data?.heatmap || [];
          const mapped = points.map((p: number[] | HeatmapPoint) =>
            Array.isArray(p) ? { lat: p[0], lon: p[1], weight: p[2] } : p
          );
          setSearchHeatmap(mapped);
        }
      } catch { /* empty */ }
    }
  }, [hour, showTraffic, showSearch]);

  useEffect(() => {
    fetchVenues();
  }, [fetchVenues]);

  useEffect(() => {
    fetchHeatmaps();
  }, [fetchHeatmaps]);

  useEffect(() => {
    if (tab === "feed") fetchTrends();
  }, [tab, fetchTrends]);

  const liveCount = venues.filter((v) => v.busyness != null && v.busyness > 0).length;

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Loading overlay */}
      {loading && venues.length === 0 && (
        <div className="fixed inset-0 z-50 bg-[#0a0b0f] flex items-center justify-center">
          <div className="text-center">
            <div className="text-2xl font-mono text-[#00d4aa] mb-3 animate-pulse">
              ███ FRANKLIN STREET DATA ███
            </div>
            <div className="text-sm font-mono text-[#454a58]">
              Connecting to BTUT Mean-Field Game Engine...
            </div>
            <div className="mt-4 w-48 h-0.5 bg-[#1e2028] rounded-full overflow-hidden mx-auto">
              <div className="h-full bg-[#00d4aa] rounded-full animate-[loading_2s_ease-in-out_infinite]" style={{width: "60%"}} />
            </div>
          </div>
        </div>
      )}
      <TopBar />

      <div className="flex-1 flex overflow-hidden pb-14 md:pb-0">
        <Sidebar active={tab} onTabChange={setTab} />

        {/* Main content area */}
        {tab === "map" && (
          <>
            {/* Left control strip — hidden on mobile */}
            <div className="hidden md:flex w-52 bg-[#0d0e13] border-r border-[#1e2028] flex-col shrink-0">
              <HourSlider value={hour} onChange={setHour} />

              {/* Quick stats */}
              <div className="px-4 py-3 border-b border-[#1e2028]">
                <div className="text-[10px] font-mono tracking-[0.15em] text-[#454a58] uppercase mb-2">
                  Status
                </div>
                <div className="space-y-2">
                  <div className="metric-card">
                    <div className="text-[9px] text-[#454a58] uppercase">Venues</div>
                    <div className="text-lg font-mono text-[#e2e4e9]">{venues.length}</div>
                  </div>
                  <div className="metric-card">
                    <div className="text-[9px] text-[#454a58] uppercase">With Busyness</div>
                    <div className="text-lg font-mono text-[#00d4aa]">{liveCount}</div>
                  </div>
                  {liveCount > 0 && (
                    <div className="metric-card">
                      <div className="text-[9px] text-[#454a58] uppercase">Peak</div>
                      <div className="text-lg font-mono text-[#ff6600]">
                        {(() => { const vals = venues.filter(v => v.busyness != null && v.busyness > 0).map(v => v.busyness!); return vals.length > 0 ? Math.max(...vals) : 0; })()}%
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Heatmap Layers */}
              <div className="px-4 py-3 border-b border-[#1e2028]">
                <div className="text-[10px] font-mono tracking-[0.15em] text-[#454a58] uppercase mb-2">
                  Map Layers
                </div>
                <div className="space-y-2">
                  <button
                    onClick={() => setShowTraffic(!showTraffic)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-[10px] font-mono transition-all ${
                      showTraffic
                        ? "bg-[#ff660020] text-[#ff6600] border border-[#ff660044]"
                        : "text-[#454a58] hover:text-[#6b7080] hover:bg-[#111318]"
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${showTraffic ? "bg-[#ff6600]" : "bg-[#1e2028]"}`} />
                    Traffic Density
                  </button>
                  <button
                    onClick={() => setShowSearch(!showSearch)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-[10px] font-mono transition-all ${
                      showSearch
                        ? "bg-[#a050ff20] text-[#a050ff] border border-[#a050ff44]"
                        : "text-[#454a58] hover:text-[#6b7080] hover:bg-[#111318]"
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${showSearch ? "bg-[#a050ff]" : "bg-[#1e2028]"}`} />
                    Search Convergence
                  </button>
                </div>
              </div>

              {/* Data sources */}
              <div className="px-4 py-3 flex-1">
                <div className="text-[10px] font-mono tracking-[0.15em] text-[#454a58] uppercase mb-2">
                  Data Sources
                </div>
                <div className="space-y-1.5 text-[10px] font-mono">
                  {[
                    { name: "BTUT Engine", status: liveCount > 0 },
                    { name: "OpenStreetMap", status: apiConnected },
                    { name: "Google Trends", status: apiConnected },
                  ].map((s) => (
                    <div key={s.name} className="flex items-center gap-2">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          s.status ? "bg-[#00d4aa]" : "bg-[#454a58]"
                        }`}
                      />
                      <span className={s.status ? "text-[#6b7080]" : "text-[#454a58]"}>
                        {s.name}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Map */}
            <div className="flex-1 relative">
              {/* Mobile hour slider + stats overlay */}
              <div className="md:hidden absolute top-2 left-2 right-2 z-10 flex gap-2">
                <div className="flex-1 bg-[#0a0b0fdd] rounded-lg px-3 py-2 backdrop-blur-sm">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[9px] font-mono text-[#454a58] uppercase">Hour</span>
                    <span className="text-xs font-mono text-[#00d4aa]">{hour}:00</span>
                  </div>
                  <input
                    type="range" min={0} max={23} value={hour}
                    onChange={(e) => setHour(parseInt(e.target.value))}
                    className="w-full h-1 bg-[#1e2028] rounded-full appearance-none
                      [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4
                      [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full
                      [&::-webkit-slider-thumb]:bg-[#00d4aa]"
                  />
                </div>
                <div className="bg-[#0a0b0fdd] rounded-lg px-3 py-2 backdrop-blur-sm text-center">
                  <div className="text-[9px] font-mono text-[#454a58]">VENUES</div>
                  <div className="text-sm font-mono text-[#00d4aa]">{liveCount}</div>
                </div>
              </div>
              <MapView
                venues={venues}
                hour={hour}
                onVenueClick={(v) => setSelectedVenue(v.name)}
                trafficHeatmap={trafficHeatmap}
                searchHeatmap={searchHeatmap}
                showTraffic={showTraffic}
                showSearch={showSearch}
              />
            </div>

            {/* Right panel - venue list — hidden on mobile */}
            <div className="hidden lg:block">
              <VenuePanel
                venues={venues}
                selectedVenue={selectedVenue}
                onSelect={setSelectedVenue}
              />
            </div>
          </>
        )}

        {tab === "feed" && (
          <FeedView
            suggestions={trends?.suggestions || []}
            keywords={[]}
            trending={trends?.locally_relevant || null}
            interestByCity={trends?.interest_by_city || {}}
            geoDescription={trends?.geo_description || ""}
          />
        )}

        {tab === "command" && (
          <CommandPanel hour={hour} />
        )}

        {tab === "intel" && (
          <div className="flex-1 p-4 md:p-8 overflow-y-auto grid-overlay pb-16 md:pb-8">
            <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-4 md:mb-6">
              Intelligence Summary
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4 mb-6 md:mb-8">
              <div className="metric-card glow-green">
                <div className="text-[9px] text-[#454a58] uppercase">Venues Discovered</div>
                <div className="text-3xl font-mono text-[#00d4aa] mt-1">{venues.length}</div>
                <div className="text-[10px] text-[#454a58] mt-1">via OpenStreetMap Overpass</div>
              </div>
              <div className="metric-card glow-blue">
                <div className="text-[9px] text-[#454a58] uppercase">BTUT Density</div>
                <div className="text-3xl font-mono text-[#4a9eff] mt-1">{liveCount}</div>
                <div className="text-[10px] text-[#454a58] mt-1">via Fokker-Planck MFG</div>
              </div>
              <div className="metric-card">
                <div className="text-[9px] text-[#454a58] uppercase">API Status</div>
                <div className={`text-3xl font-mono mt-1 ${apiConnected ? "text-[#00d4aa]" : loading ? "text-[#ffaa00]" : "text-[#ff4d6a]"}`}>
                  {apiConnected ? "LIVE" : loading ? "..." : "OFFLINE"}
                </div>
                <div className="text-[10px] text-[#454a58] mt-1">
                  {apiConnected ? "All feeds active" : loading ? "Connecting to BTUT engine" : "Set BACKEND_URL"}
                </div>
              </div>
            </div>

            {/* How it works */}
            <div className="border border-[#1e2028] rounded-lg p-6 bg-[#111318]">
              <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-4">
                How Franklin Street Data Works
              </h3>
              <div className="space-y-3 text-xs text-[#6b7080] leading-relaxed">
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">01</span>
                  <span>OpenStreetMap Overpass API discovers every bar, restaurant, cafe, and nightclub within 500m of Franklin Street.</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">02</span>
                  <span>Live signals are collected: Google Trends interest scores, weather conditions, UNC events calendar, Reddit activity, and time-of-day venue profiles.</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">03</span>
                  <span>The BTUT engine fuses all signals into a drift velocity field v[&rho;], then solves the Fokker-Planck PDE: &part;&rho;/&part;t = -&nabla;&middot;(v[&rho;]&rho;) + &sigma;&sup2;/2 &Delta;&rho; to convergence.</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">04</span>
                  <span>The density field &rho;(x,t) is sampled at each venue position to produce busyness scores (0-100%), and along the corridor spine for the continuous heat map.</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">05</span>
                  <span>Move the hour slider. Watch the density field shift as venue type profiles change — cafes peak at morning, bars at night. The mean-field finds approximate Nash equilibrium.</span>
                </div>
              </div>
            </div>

            {/* Top venues table */}
            {venues.length > 0 && (
              <div className="mt-8">
                <h3 className="text-xs font-mono text-[#6b7080] uppercase tracking-wider mb-4">
                  All Discovered Venues
                </h3>
                <div className="border border-[#1e2028] rounded-lg overflow-hidden">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b border-[#1e2028] bg-[#111318]">
                        <th className="text-left px-3 py-2 text-[#454a58]">Venue</th>
                        <th className="text-left px-3 py-2 text-[#454a58]">Type</th>
                        <th className="text-right px-3 py-2 text-[#454a58]">Busyness</th>
                        <th className="text-right px-3 py-2 text-[#454a58]">Lat</th>
                        <th className="text-right px-3 py-2 text-[#454a58]">Lon</th>
                      </tr>
                    </thead>
                    <tbody>
                      {venues.map((v, i) => (
                        <tr key={i} className="border-b border-[#1e2028] hover:bg-[#111318]">
                          <td className="px-3 py-1.5 text-[#e2e4e9]">{v.name}</td>
                          <td className="px-3 py-1.5 text-[#6b7080]">{v.amenity_type}</td>
                          <td className="px-3 py-1.5 text-right">
                            {v.busyness != null && v.busyness > 0 ? (
                              <span
                                style={{
                                  color:
                                    v.busyness >= 80 ? "#ff2244" :
                                    v.busyness >= 60 ? "#ff6600" :
                                    v.busyness >= 40 ? "#ffaa00" : "#00d4aa",
                                }}
                              >
                                {v.busyness}%
                              </span>
                            ) : (
                              <span className="text-[#454a58]">--</span>
                            )}
                          </td>
                          <td className="px-3 py-1.5 text-right text-[#454a58]">{v.lat.toFixed(4)}</td>
                          <td className="px-3 py-1.5 text-right text-[#454a58]">{v.lon.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <StatusBar
        venueCount={venues.length}
        liveCount={liveCount}
        apiConnected={apiConnected}
      />
    </div>
  );
}
