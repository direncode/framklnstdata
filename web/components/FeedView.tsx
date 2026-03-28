"use client";

interface TrendSuggestion {
  category: string;
  keyword: string;
  score: number;
  strength: string;
  suggestion: string;
  rising_queries?: string[];
  rising_topics?: string[];
  top_cities?: Array<{ city: string; interest: number }>;
}

interface Keyword {
  keyword: string;
  frequency: number;
}

function strengthColor(s: string): string {
  if (s === "HOT") return "#ff2244";
  if (s === "Warm") return "#ffaa00";
  return "#4a9eff";
}

function InterestBar({ value }: { value: number }) {
  const color = value >= 75 ? "#ff2244" : value >= 50 ? "#ffaa00" : value >= 25 ? "#00d4aa" : "#4a9eff";
  return (
    <div className="w-full h-1 bg-[#1e2028] rounded-full overflow-hidden mt-1">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${value}%`, backgroundColor: color }}
      />
    </div>
  );
}

export default function FeedView({
  suggestions,
  keywords,
  trending,
  interestByCity,
  geoDescription,
}: {
  suggestions: TrendSuggestion[];
  keywords: Keyword[];
  trending: string[] | null;
  interestByCity: Record<string, Array<{ city: string; interest: number }>>;
  geoDescription: string;
}) {
  return (
    <div className="flex-1 overflow-y-auto p-6 grid-overlay">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-[10px] font-mono tracking-[0.3em] text-[#00d4aa] uppercase">
          Search Intelligence
        </h1>
        <p className="text-xs text-[#454a58] mt-1 font-mono">
          {geoDescription || "Raleigh-Durham DMA (includes Chapel Hill)"}
        </p>
      </div>

      {/* Trending Keywords Stream */}
      {keywords.length > 0 && (
        <section className="mb-8">
          <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#6b7080] uppercase mb-3">
            Keyword Stream
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {keywords.slice(0, 30).map((k, i) => {
              const maxFreq = keywords[0]?.frequency || 1;
              const intensity = k.frequency / maxFreq;
              const color = intensity > 0.7 ? "#00d4aa" : intensity > 0.4 ? "#4a9eff" : "#6b7080";
              return (
                <span
                  key={`${k.keyword}-${i}`}
                  className="px-2.5 py-1 text-xs font-mono rounded-sm border transition-all duration-500"
                  style={{
                    color,
                    borderColor: color + "33",
                    backgroundColor: color + "08",
                    fontSize: `${10 + intensity * 4}px`,
                  }}
                >
                  {k.keyword}
                </span>
              );
            })}
          </div>
        </section>
      )}

      {/* Rising Search Categories */}
      {suggestions.length > 0 && (
        <section className="mb-8">
          <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#6b7080] uppercase mb-4">
            What Chapel Hill Is Searching
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {suggestions.map((s, i) => (
              <div
                key={i}
                className="bg-[#111318] border border-[#1e2028] rounded-lg p-4 hover:border-[#2a2d38] transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-[#e2e4e9] font-medium">{s.category}</span>
                  <span
                    className="text-[10px] font-mono font-bold px-2 py-0.5 rounded"
                    style={{
                      color: strengthColor(s.strength),
                      backgroundColor: strengthColor(s.strength) + "15",
                    }}
                  >
                    {s.score}
                  </span>
                </div>

                <InterestBar value={s.score} />

                <div className="text-[11px] text-[#6b7080] mt-2 leading-relaxed">
                  {s.suggestion}
                </div>

                {/* Rising queries */}
                {s.rising_queries && s.rising_queries.length > 0 && (
                  <div className="mt-3">
                    <div className="text-[9px] font-mono text-[#454a58] uppercase mb-1">
                      Rising Searches
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {s.rising_queries.slice(0, 5).map((q, qi) => (
                        <span
                          key={qi}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#00d4aa08] border border-[#00d4aa22] text-[#00d4aa]"
                        >
                          {q}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Rising topics */}
                {s.rising_topics && s.rising_topics.length > 0 && (
                  <div className="mt-2">
                    <div className="text-[9px] font-mono text-[#454a58] uppercase mb-1">
                      Rising Topics
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {s.rising_topics.slice(0, 4).map((t, ti) => (
                        <span
                          key={ti}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#4a9eff08] border border-[#4a9eff22] text-[#4a9eff]"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* City breakdown */}
                {s.top_cities && s.top_cities.length > 0 && (
                  <div className="mt-2">
                    <div className="text-[9px] font-mono text-[#454a58] uppercase mb-1">
                      Interest by City
                    </div>
                    {s.top_cities.slice(0, 3).map((c, ci) => (
                      <div key={ci} className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-[#6b7080] w-20 truncate">{c.city}</span>
                        <div className="flex-1 h-0.5 bg-[#1e2028] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[#ffaa00]"
                            style={{ width: `${c.interest}%` }}
                          />
                        </div>
                        <span className="text-[9px] font-mono text-[#454a58]">{c.interest}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Interest by City (global) */}
      {Object.keys(interestByCity).length > 0 && (
        <section className="mb-8">
          <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#6b7080] uppercase mb-3">
            Where in NC Is Searching
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(interestByCity).map(([keyword, cities]) => (
              <div key={keyword} className="bg-[#111318] border border-[#1e2028] rounded-lg p-3">
                <div className="text-xs text-[#00d4aa] font-mono mb-2">{keyword}</div>
                {cities.slice(0, 5).map((c, i) => (
                  <div key={i} className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-[#6b7080] w-24 truncate">{c.city}</span>
                    <div className="flex-1 h-1 bg-[#1e2028] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#00d4aa]"
                        style={{ width: `${c.interest}%` }}
                      />
                    </div>
                    <span className="text-[9px] font-mono text-[#454a58]">{c.interest}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Nationally Trending (filtered for local) */}
      {trending && trending.length > 0 && (
        <section className="mb-8">
          <h2 className="text-[10px] font-mono tracking-[0.2em] text-[#6b7080] uppercase mb-3">
            Trending in NC Right Now
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {trending.map((t, i) => (
              <span
                key={i}
                className="px-2.5 py-1 text-[11px] font-mono rounded-sm bg-[#ff220408] border border-[#ff220422] text-[#ff6600]"
              >
                {t}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Empty state */}
      {suggestions.length === 0 && keywords.length === 0 && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="text-[#454a58] text-sm">
              Connecting to Google Trends...
            </div>
            <div className="text-[#454a58] text-xs mt-2">
              DMA 560 · Raleigh-Durham-Chapel Hill
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
