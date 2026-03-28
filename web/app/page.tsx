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

interface FeedData {
  reddit: Array<{ source: string; title: string; score?: number; comments?: number }> | null;
  dth: Array<{ source: string; title: string; summary?: string }> | null;
  trends: {
    nationally_trending: string[];
    locally_relevant: string[];
    core_keyword_interest: Record<string, number>;
  } | null;
  unc_events: Array<{ title: string; location: string; date: string }> | null;
  extracted_keywords: Array<{ keyword: string; frequency: number }>;
  trivia_suggestions: Array<{
    source: string;
    topic: string;
    signal: string;
    suggestion: string;
  }>;
}

const API_BASE = "/api/data";

export default function Home() {
  const [tab, setTab] = useState<Tab>("map");
  const [hour, setHour] = useState(new Date().getHours());
  const [venues, setVenues] = useState<Venue[]>([]);
  const [selectedVenue, setSelectedVenue] = useState<string | null>(null);
  const [feed, setFeed] = useState<FeedData | null>(null);
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

  const fetchFeed = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/livefeed`);
      if (res.ok) {
        const data = await res.json();
        setFeed(data);
      }
    } catch { /* empty */ }
  }, []);

  useEffect(() => {
    fetchVenues();
  }, [fetchVenues]);

  useEffect(() => {
    if (tab === "feed") fetchFeed();
  }, [tab, fetchFeed]);

  const liveCount = venues.filter((v) => v.busyness !== null).length;

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
                        {Math.max(...venues.filter(v => v.busyness !== null).map(v => v.busyness!))}%
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
                    { name: "OpenStreetMap", status: apiConnected },
                    { name: "Google Places", status: liveCount > 0 },
                    { name: "NCDOT ArcGIS", status: apiConnected },
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

        {tab === "feed" && feed && (
          <FeedView
            reddit={feed.reddit}
            dth={feed.dth}
            keywords={feed.extracted_keywords}
            suggestions={feed.trivia_suggestions}
            trending={feed.trends?.locally_relevant || null}
            events={feed.unc_events}
          />
        )}

        {tab === "feed" && !feed && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-[#454a58] text-sm">Loading live feed...</div>
              <div className="text-[#454a58] text-xs mt-2">
                Connect to Franklin Street Data API for Reddit, DTH, UNC Calendar, and Trends data
              </div>
            </div>
          </div>
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
                <div className="text-[9px] text-[#454a58] uppercase">Live Busyness</div>
                <div className="text-3xl font-mono text-[#4a9eff] mt-1">{liveCount}</div>
                <div className="text-[10px] text-[#454a58] mt-1">via Google Places API</div>
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
                  <span>Google Places API fetches hourly busyness (0-100%) for each venue. This is the only ranking signal.</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">03</span>
                  <span>Busyness values become heat map weights. Linear interpolation between venues creates a convergent foot traffic corridor.</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">04</span>
                  <span>Live feeds (Reddit, DTH, UNC Calendar, Google Trends) extract keywords and generate trivia topic suggestions.</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-[#00d4aa] font-mono shrink-0">05</span>
                  <span>Move the hour slider. Watch busyness shift. Go where the convergence is hottest.</span>
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
                            {v.busyness !== null ? (
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
