"use client";

export default function StatusBar({
  venueCount,
  liveCount,
  apiConnected,
}: {
  venueCount: number;
  liveCount: number;
  apiConnected: boolean;
}) {
  return (
    <div className="h-7 flex items-center justify-between px-4 border-t border-[#1e2028] bg-[#0d0e13] text-[9px] font-mono text-[#454a58] shrink-0">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              apiConnected ? "bg-[#00d4aa] status-live" : "bg-[#ff4d6a]"
            }`}
          />
          {apiConnected ? "API CONNECTED" : "API OFFLINE"}
        </span>
        <span>{venueCount} venues</span>
        <span>{liveCount} with busyness</span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-[#00d4aa]">BTUT MFG</span>
        <span className="text-[#ffaa00]">Search Conv.</span>
        <span>OSM Overpass</span>
        <span>Google Trends</span>
        <span>UNC Calendar</span>
      </div>
    </div>
  );
}
