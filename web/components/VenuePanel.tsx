"use client";

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
}

function BusynessBar({ value }: { value: number }) {
  const color =
    value >= 80 ? "#ff2244" : value >= 60 ? "#ff6600" : value >= 40 ? "#ffaa00" : "#00d4aa";
  return (
    <div className="w-full h-1.5 bg-[#1e2028] rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${value}%`, backgroundColor: color }}
      />
    </div>
  );
}

function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(...data, 1);
  const w = 180;
  const h = 32;
  const points = data
    .map((v, i) => `${(i / 23) * w},${h - (v / max) * h}`)
    .join(" ");

  return (
    <svg width={w} height={h} className="mt-1">
      <polyline
        points={points}
        fill="none"
        stroke="#00d4aa"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <polyline
        points={`0,${h} ${points} ${w},${h}`}
        fill="url(#sparkGrad)"
        opacity="0.15"
      />
      <defs>
        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#00d4aa" />
          <stop offset="100%" stopColor="transparent" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function VenuePanel({
  venues,
  selectedVenue,
  onSelect,
}: {
  venues: Venue[];
  selectedVenue: string | null;
  onSelect: (name: string) => void;
}) {
  return (
    <div className="w-80 bg-[#0d0e13] border-l border-[#1e2028] flex flex-col shrink-0 overflow-hidden">
      <div className="px-4 py-3 border-b border-[#1e2028]">
        <div className="text-[10px] font-mono tracking-[0.15em] text-[#454a58] uppercase">
          Venue Intelligence
        </div>
        <div className="text-xs text-[#6b7080] mt-1">
          {venues.length} venues discovered
          {" · "}
          {venues.filter((v) => v.busyness != null && v.busyness > 0).length} with live data
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {venues.map((v) => (
          <button
            key={v.name}
            onClick={() => onSelect(v.name)}
            className={`w-full text-left px-4 py-3 border-b border-[#1e2028] transition-all
              ${
                selectedVenue === v.name
                  ? "bg-[#00d4aa08] border-l-2 border-l-[#00d4aa]"
                  : "hover:bg-[#111318]"
              }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#e2e4e9] truncate max-w-[180px]">{v.name}</span>
              {v.busyness != null && v.busyness > 0 ? (
                <span
                  className="text-xs font-mono font-bold"
                  style={{
                    color:
                      v.busyness >= 80
                        ? "#ff2244"
                        : v.busyness >= 60
                        ? "#ff6600"
                        : v.busyness >= 40
                        ? "#ffaa00"
                        : "#00d4aa",
                  }}
                >
                  {v.busyness}%
                </span>
              ) : (
                <span className="text-[10px] text-[#454a58]">--</span>
              )}
            </div>

            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-[#454a58]">{v.amenity_type}</span>
              {v.cuisine && (
                <span className="text-[9px] text-[#6b7080]">{v.cuisine.split(";")[0]}</span>
              )}
            </div>

            {v.busyness != null && v.busyness > 0 && (
              <div className="mt-1.5">
                <BusynessBar value={v.busyness} />
              </div>
            )}

            {selectedVenue === v.name && (
              <div className="mt-2 space-y-1.5">
                {/* Address */}
                {v.address && (
                  <div className="text-[10px] text-[#6b7080]">{v.address}</div>
                )}

                {/* Metadata tags */}
                <div className="flex flex-wrap gap-1">
                  {v.outdoor_seating === "yes" && (
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-[#00d4aa15] text-[#00d4aa] font-mono">PATIO</span>
                  )}
                  {v.category && (
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-[#4a9eff15] text-[#4a9eff] font-mono uppercase">{v.category}</span>
                  )}
                  {v.brand && (
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-[#1e2028] text-[#6b7080] font-mono">{v.brand}</span>
                  )}
                </div>

                {/* Hours */}
                {v.opening_hours && (
                  <div className="text-[9px] text-[#454a58] font-mono truncate">{v.opening_hours}</div>
                )}

                {/* Contact */}
                {v.phone && (
                  <div className="text-[9px] text-[#454a58]">{v.phone}</div>
                )}
                {v.website && (
                  <a
                    href={v.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[9px] text-[#4a9eff] hover:underline truncate block"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {v.website.replace(/^https?:\/\/(www\.)?/, "").slice(0, 40)}
                  </a>
                )}

                {/* 24h profile */}
                {v.hourly_profile && (
                  <div>
                    <div className="text-[9px] text-[#454a58] font-mono mb-0.5">24h profile</div>
                    <Sparkline data={v.hourly_profile} />
                    <div className="flex justify-between text-[8px] text-[#454a58] font-mono mt-0.5">
                      <span>0:00</span>
                      <span>12:00</span>
                      <span>23:00</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </button>
        ))}

        {venues.length === 0 && (
          <div className="px-4 py-8 text-center text-xs text-[#454a58]">
            No venues discovered.
            <br />
            Connect to the Franklin Street Data API to scan Franklin Street.
          </div>
        )}
      </div>
    </div>
  );
}
