"use client";

import { useEffect, useState, useCallback } from "react";

const API_BASE = "/api/data";

interface ConvergenceData {
  venue_scores: Record<string, number>;
  top_searches: Array<{ venue_type: string; score: number }>;
  heatmap: number[][];
  status?: string;
  message?: string;
}

interface LocalTopic {
  source: string;
  topic: string;
  score: number;
}

interface DensityData {
  signal_inputs: Record<string, string>;
  nash_gap: number;
  iterations: number;
  converged: boolean;
}

interface VenueScore {
  name: string;
  score: number;
}

function ScoreBar({ score, color }: { score: number; color: string }) {
  return (
    <div className="w-full h-1 bg-[#1e2028] rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${score}%`, backgroundColor: color }}
      />
    </div>
  );
}

function intensityColor(score: number): string {
  if (score >= 75) return "#ff2244";
  if (score >= 50) return "#ff6600";
  if (score >= 25) return "#ffaa00";
  return "#00d4aa";
}

function intensityLabel(score: number): string {
  if (score >= 75) return "HOT";
  if (score >= 50) return "WARM";
  if (score >= 25) return "MILD";
  return "LOW";
}

export default function CommandPanel({ hour }: { hour: number }) {
  const [convergence, setConvergence] = useState<ConvergenceData | null>(null);
  const [density, setDensity] = useState<DensityData | null>(null);
  const [localTopics, setLocalTopics] = useState<LocalTopic[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);

    // Fetch all four in parallel — all are cache-first (instant)
    const [densRes, spotsRes, trendsRes] = await Promise.allSettled([
      fetch(`${API_BASE}/density?hour=${hour}`).then((r) => r.ok ? r.json() : null),
      fetch(`${API_BASE}/spots?hour=${hour}`).then((r) => r.ok ? r.json() : null),
      fetch(`${API_BASE}/trends?live=true`).then((r) => r.ok ? r.json() : null),
    ]);

    // Extract local topics from trends response
    if (trendsRes.status === "fulfilled" && trendsRes.value) {
      const topics = trendsRes.value?.local_topics || [];
      setLocalTopics(topics);
    }

    if (densRes.status === "fulfilled" && densRes.value) setDensity(densRes.value);

    // Always build from spots data — filtered to food/drink/entertainment only
    const relevantTypes = new Set([
      "bar", "restaurant", "cafe", "pub", "fast_food", "nightclub",
      "ice_cream", "biergarten", "brewery", "wine_bar", "music_venue",
    ]);

    if (spotsRes.status === "fulfilled" && spotsRes.value) {
      const spots = spotsRes.value?.spots || [];
      const typeScores: Record<string, number[]> = {};
      const venueScores: Record<string, number> = {};
      for (const s of spots) {
        const b = s.busyness ?? 0;
        const t = s.amenity_type || "unknown";
        if (b > 0 && relevantTypes.has(t)) {
          if (!typeScores[t]) typeScores[t] = [];
          typeScores[t].push(b);
          venueScores[s.name] = b;
        }
      }
      setConvergence({
        venue_scores: venueScores,
        top_searches: Object.entries(typeScores)
          .map(([vt, scores]) => ({
            venue_type: vt,
            score: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
          }))
          .sort((a, b) => b.score - a.score)
          .slice(0, 15),
        heatmap: spots
          .filter((s: any) => (s.busyness ?? 0) > 0)
          .map((s: any) => [s.lat, s.lon, s.busyness / 100]),
      });
    }

    setLoading(false);
  }, [hour]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sort venue scores descending
  const topVenues: VenueScore[] = convergence?.venue_scores
    ? Object.entries(convergence.venue_scores)
        .map(([name, score]) => ({ name, score }))
        .filter((v) => v.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 20)
    : [];

  const topSearches = convergence?.top_searches || [];
  const signalInputs = density?.signal_inputs || {};
  const warming = !convergence && loading;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: Search Trajectories */}
      <div className="flex-1 overflow-y-auto border-r border-[#1e2028]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#1e2028] bg-[#0a0b0f]">
          <div className="text-[10px] font-mono tracking-[0.2em] text-[#ff6600] uppercase">
            Search Trajectory Analysis
          </div>
          <div className="text-xs text-[#454a58] mt-1">
            Live search signals mapped to venue convergence at {hour}:00
          </div>
        </div>

        {loading ? (
          <div className="px-6 py-8 text-center">
            <div className="text-sm font-mono text-[#454a58] animate-pulse">
              Scanning search trajectories...
            </div>
          </div>
        ) : warming ? (
          <div className="px-6 py-8 text-center">
            <div className="text-sm font-mono text-[#ffaa00] animate-pulse">
              Collecting search signals...
            </div>
            <div className="text-xs text-[#454a58] mt-2">
              Background engine warming up. Data will appear shortly.
            </div>
          </div>
        ) : (
          <>
            {/* Trending Search Types */}
            <div className="px-6 py-4">
              <div className="text-[9px] font-mono tracking-[0.15em] text-[#454a58] uppercase mb-3">
                Live Interest by Venue Type
              </div>
              <div className="space-y-3">
                {topSearches
                  .filter((s) => s.score > 5)
                  .map((s) => {
                  const color = intensityColor(s.score);
                  return (
                    <div key={s.venue_type}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-[#e2e4e9] uppercase">
                          {s.venue_type.replace(/_/g, " ")}
                        </span>
                        <span
                          className="text-[10px] font-mono font-bold"
                          style={{ color }}
                        >
                          {intensityLabel(s.score)} {s.score}%
                        </span>
                      </div>
                      <ScoreBar score={s.score} color={color} />
                    </div>
                  );
                })}
                {topSearches.filter((s) => s.score > 5).length === 0 && (
                  <div className="text-xs text-[#454a58]">No significant activity at this hour</div>
                )}
              </div>
            </div>

            {/* Venue Convergence Log */}
            <div className="px-6 py-4 border-t border-[#1e2028]">
              <div className="text-[9px] font-mono tracking-[0.15em] text-[#454a58] uppercase mb-3">
                Venue Convergence Targets
              </div>
              <div className="space-y-1 font-mono text-[11px]">
                {topVenues.map((v, i) => {
                  const color = intensityColor(v.score);
                  return (
                    <div
                      key={v.name}
                      className="flex items-center gap-2 py-1 border-b border-[#1e2028]/50"
                    >
                      <span className="text-[#454a58] w-5 text-right shrink-0">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="text-[#00d4aa] shrink-0">&gt;</span>
                      <span className="text-[#e2e4e9] truncate flex-1">{v.name}</span>
                      <span
                        className="shrink-0 font-bold"
                        style={{ color }}
                      >
                        {v.score}%
                      </span>
                    </div>
                  );
                })}
                {topVenues.length === 0 && (
                  <div className="text-xs text-[#454a58] py-2">
                    No convergence data — signals warming up
                  </div>
                )}
              </div>
            </div>

            {/* Local Trending Topics */}
            {localTopics.length > 0 && (
              <div className="px-6 py-4 border-t border-[#1e2028]">
                <div className="text-[9px] font-mono tracking-[0.15em] text-[#454a58] uppercase mb-3">
                  Chapel Hill Trending Now
                </div>
                <div className="space-y-2">
                  {localTopics.slice(0, 12).map((t, i) => (
                    <div key={i} className="flex items-start gap-2 text-[11px] font-mono">
                      <span className={`shrink-0 mt-1 w-1.5 h-1.5 rounded-full ${
                        t.source === "Google Trends" ? "bg-[#4a9eff]" :
                        t.source === "UNC Events" ? "bg-[#00d4aa]" :
                        "bg-[#ff6600]"
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="text-[#e2e4e9] truncate">{t.topic}</div>
                        <div className="text-[9px] text-[#454a58]">{t.source}</div>
                      </div>
                      <span className="shrink-0 text-[10px]" style={{
                        color: t.score >= 70 ? "#ff6600" : t.score >= 40 ? "#ffaa00" : "#454a58"
                      }}>
                        {t.score}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Right: Signal Feed */}
      <div className="w-72 overflow-y-auto bg-[#0a0b0f] shrink-0">
        <div className="px-4 py-4 border-b border-[#1e2028]">
          <div className="text-[10px] font-mono tracking-[0.2em] text-[#4a9eff] uppercase">
            Signal Feed
          </div>
          <div className="text-xs text-[#454a58] mt-1">Active intelligence sources</div>
        </div>

        {/* BTUT Engine Status */}
        <div className="px-4 py-3 border-b border-[#1e2028]">
          <div className="text-[9px] font-mono text-[#454a58] uppercase mb-2">Engine</div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="text-[#6b7080]">Nash Gap</span>
              <span className={density?.converged ? "text-[#00d4aa]" : "text-[#ffaa00]"}>
                {density?.nash_gap ? density.nash_gap.toExponential(2) : "--"}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="text-[#6b7080]">Iterations</span>
              <span className="text-[#e2e4e9]">{density?.iterations || "--"}</span>
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="text-[#6b7080]">Converged</span>
              <span className={density?.converged ? "text-[#00d4aa]" : "text-[#ff4d6a]"}>
                {density?.converged ? "YES" : density ? "APPROX" : "--"}
              </span>
            </div>
          </div>
        </div>

        {/* Signal Sources */}
        <div className="px-4 py-3">
          <div className="text-[9px] font-mono text-[#454a58] uppercase mb-2">Signals</div>
          <div className="space-y-1.5">
            {Object.entries(signalInputs).map(([name, status]) => (
              <div key={name} className="flex items-center gap-2 text-[10px] font-mono">
                <span
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    status === "active" ? "bg-[#00d4aa]" : "bg-[#ff4d6a]"
                  }`}
                />
                <span className="text-[#6b7080] flex-1 truncate">
                  {name.replace(/_/g, " ")}
                </span>
                <span
                  className={`shrink-0 ${
                    status === "active" ? "text-[#00d4aa]" : "text-[#454a58]"
                  }`}
                >
                  {status === "active" ? "LIVE" : "OFF"}
                </span>
              </div>
            ))}
            {Object.keys(signalInputs).length === 0 && (
              <div className="text-[10px] text-[#454a58]">Loading signal status...</div>
            )}
          </div>
        </div>

        {/* Convergence Stats */}
        {convergence && !warming && (
          <div className="px-4 py-3 border-t border-[#1e2028]">
            <div className="text-[9px] font-mono text-[#454a58] uppercase mb-2">Convergence</div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[10px] font-mono">
                <span className="text-[#6b7080]">Venues Scanned</span>
                <span className="text-[#e2e4e9]">{convergence.venue_scores ? Object.keys(convergence.venue_scores).length : 0}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono">
                <span className="text-[#6b7080]">With Signal</span>
                <span className="text-[#00d4aa]">{topVenues.length}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono">
                <span className="text-[#6b7080]">Heat Points</span>
                <span className="text-[#ff6600]">{convergence.heatmap?.length || 0}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
