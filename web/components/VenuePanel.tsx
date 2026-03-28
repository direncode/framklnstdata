"use client";

interface Venue {
  name: string;
  lat: number;
  lon: number;
  amenity_type: string;
  busyness: number | null;
  hourly_profile: number[] | null;
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

            <div className="text-[10px] text-[#454a58] mt-0.5">{v.amenity_type}</div>

            {v.busyness != null && v.busyness > 0 && (
              <div className="mt-1.5">
                <BusynessBar value={v.busyness} />
              </div>
            )}

            {selectedVenue === v.name && v.hourly_profile && (
              <div className="mt-2">
                <div className="text-[9px] text-[#454a58] font-mono mb-0.5">24h profile</div>
                <Sparkline data={v.hourly_profile} />
                <div className="flex justify-between text-[8px] text-[#454a58] font-mono mt-0.5">
                  <span>0:00</span>
                  <span>12:00</span>
                  <span>23:00</span>
                </div>
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
