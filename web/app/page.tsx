"use client";

import { useState, useEffect, useCallback } from "react";
import TopBar from "@/components/TopBar";
import Sidebar from "@/components/Sidebar";
import MapView from "@/components/MapView";
import VenuePanel from "@/components/VenuePanel";
import FeedView from "@/components/FeedView";
import HourSlider from "@/components/HourSlider";
import StatusBar from "@/components/StatusBar";

type Tab = "map" | "feed" | "intel";

interface Venue {
  name: string;
  lat: number;
  lon: number;
  amenity_type: string;
  busyness: number | null;
  hourly_profile: number[] | null;
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

export default function Home() {
  const [tab, setTab] = useState<Tab>("map");
  const [hour, setHour] = useState(new Date().getHours());
  const [venues, setVenues] = useState<Venue[]>([]);
  const [selectedVenue, setSelectedVenue] = useState<string | null>(null);
  const [trends, setTrends] = useState<TrendsData | null>(null);
  const [apiConnected, setApiConnected] = useState(false);

  const fetchVenues = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/spots?hour=${hour}`);
      if (res.ok) {
        const data = await res.json();
        // Backend returns {spots: [...]} or {query: ..., spots: [...]}
        const list = data?.spots || data?.venues || (Array.isArray(data) ? data : []);
        if (list.length > 0) {
          setVenues(list);
          setApiConnected(true);
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
          return;
        }
      }
    } catch { /* empty */ }
    setVenues([]);
    setApiConnected(false);
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

  useEffect(() => {
    fetchVenues();
  }, [fetchVenues]);

  useEffect(() => {
    if (tab === "feed") fetchTrends();
  }, [tab, fetchTrends]);

  const liveCount = venues.filter((v) => v.busyness != null && v.busyness > 0).length;

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <TopBar />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar active={tab} onTabChange={setTab} />

        {/* Main content area */}
        {tab === "map" && (
          <>
            {/* Left control strip */}
            <div className="w-52 bg-[#0d0e13] border-r border-[#1e2028] flex flex-col shrink-0">
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
            <div className="flex-1">
              <MapView
                venues={venues}
                hour={hour}
                onVenueClick={(v) => setSelectedVenue(v.name)}
              />
            </div>

            {/* Right panel - venue list */}
            <VenuePanel
              venues={venues}
              selectedVenue={selectedVenue}
              onSelect={setSelectedVenue}
            />
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

        {tab === "intel" && (
          <div className="flex-1 p-8 overflow-y-auto grid-overlay">
            <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-6">
              Intelligence Summary
            </h2>

            <div className="grid grid-cols-3 gap-4 mb-8">
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
                <div className={`text-3xl font-mono mt-1 ${apiConnected ? "text-[#00d4aa]" : "text-[#ff4d6a]"}`}>
                  {apiConnected ? "LIVE" : "OFFLINE"}
                </div>
                <div className="text-[10px] text-[#454a58] mt-1">
                  {apiConnected ? "All feeds active" : "Set BACKEND_URL"}
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
