"use client";

interface FeedPost {
  source: string;
  title: string;
  score?: number;
  comments?: number;
  url?: string;
  summary?: string;
  published?: string;
}

interface TriviaSuggestion {
  source: string;
  topic: string;
  signal: string;
  suggestion: string;
}

interface Keyword {
  keyword: string;
  frequency: number;
}

function sourceColor(source: string): string {
  if (source.startsWith("r/")) return "#ff6600";
  if (source === "Daily Tar Heel") return "#4a9eff";
  if (source === "Google Trends") return "#00d4aa";
  if (source === "UNC Calendar") return "#ffaa00";
  return "#6b7080";
}

export default function FeedView({
  reddit,
  dth,
  keywords,
  suggestions,
  trending,
  events,
}: {
  reddit: FeedPost[] | null;
  dth: FeedPost[] | null;
  keywords: Keyword[];
  suggestions: TriviaSuggestion[];
  trending: string[] | null;
  events: Array<{ title: string; location: string; date: string }> | null;
}) {
  return (
    <div className="flex-1 overflow-y-auto p-6 grid-overlay">
      {/* Keyword Cloud */}
      {keywords.length > 0 && (
        <section className="mb-8">
          <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-3">
            Extracted Keywords
          </h2>
          <div className="flex flex-wrap gap-2">
            {keywords.slice(0, 25).map((k) => (
              <span
                key={k.keyword}
                className="px-2 py-1 text-xs font-mono rounded bg-[#111318] border border-[#1e2028] text-[#6b7080]"
                style={{
                  opacity: 0.5 + (k.frequency / (keywords[0]?.frequency || 1)) * 0.5,
                }}
              >
                {k.keyword}
                <span className="text-[#454a58] ml-1">{k.frequency}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Trivia Suggestions */}
      {suggestions.length > 0 && (
        <section className="mb-8">
          <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-3">
            Live Trivia Suggestions
          </h2>
          <div className="space-y-2">
            {suggestions.map((s, i) => (
              <div key={i} className="feed-item">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                    style={{
                      color: sourceColor(s.source),
                      backgroundColor: sourceColor(s.source) + "15",
                    }}
                  >
                    {s.source}
                  </span>
                  <span className="text-[9px] text-[#454a58]">{s.signal}</span>
                </div>
                <div className="text-sm text-[#e2e4e9]">{s.suggestion}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Reddit Feed */}
        <section>
          <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#ff6600] uppercase mb-3">
            Reddit — UNC / Chapel Hill
          </h2>
          {reddit ? (
            <div className="space-y-2">
              {reddit.slice(0, 12).map((p, i) => (
                <div key={i} className="feed-item">
                  <div className="flex items-center gap-2 text-[9px] text-[#454a58] font-mono mb-1">
                    <span style={{ color: sourceColor(p.source) }}>{p.source}</span>
                    {p.score !== undefined && <span>{p.score}↑</span>}
                    {p.comments !== undefined && <span>{p.comments}💬</span>}
                  </div>
                  <div className="text-xs text-[#e2e4e9] leading-relaxed">{p.title}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-[#454a58]">Awaiting Reddit feed...</div>
          )}
        </section>

        {/* Right column: DTH + Events + Trending */}
        <div className="space-y-6">
          {/* DTH */}
          <section>
            <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#4a9eff] uppercase mb-3">
              Daily Tar Heel
            </h2>
            {dth ? (
              <div className="space-y-2">
                {dth.slice(0, 6).map((a, i) => (
                  <div key={i} className="feed-item">
                    <div className="text-xs text-[#e2e4e9]">{a.title}</div>
                    {a.summary && (
                      <div className="text-[10px] text-[#454a58] mt-1 line-clamp-2">
                        {a.summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-[#454a58]">Awaiting DTH feed...</div>
            )}
          </section>

          {/* UNC Events */}
          {events && events.length > 0 && (
            <section>
              <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#ffaa00] uppercase mb-3">
                UNC Events (7 days)
              </h2>
              <div className="space-y-2">
                {events.slice(0, 6).map((e, i) => (
                  <div key={i} className="feed-item">
                    <div className="text-xs text-[#e2e4e9]">{e.title}</div>
                    <div className="text-[10px] text-[#454a58] mt-0.5">
                      {e.location} {e.date && `· ${e.date}`}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Trending */}
          {trending && trending.length > 0 && (
            <section>
              <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#00d4aa] uppercase mb-3">
                Trending in NC
              </h2>
              <div className="flex flex-wrap gap-1.5">
                {trending.map((t, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-[10px] font-mono rounded bg-[#00d4aa11] border border-[#00d4aa22] text-[#00d4aa]"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
