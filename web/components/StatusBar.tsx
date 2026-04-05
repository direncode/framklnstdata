"use client";

export default function StatusBar({
  venueCount,
  liveCount,
  apiConnected,
  cameraCount = 0,
  aircraftCount = 0,
  satelliteCount = 0,
}: {
  venueCount: number;
  liveCount: number;
  apiConnected: boolean;
  cameraCount?: number;
  aircraftCount?: number;
  satelliteCount?: number;
}) {
  return (
    <div className="hidden md:flex h-7 items-center justify-between px-4 border-t border-[#1e2028] bg-[#0d0e13] text-[9px] font-mono text-[#454a58] shrink-0">
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
        {cameraCount > 0 && <span className="text-[#ff4d6a]">{cameraCount} cameras</span>}
        {aircraftCount > 0 && <span className="text-[#4a9eff]">{aircraftCount} aircraft</span>}
        {satelliteCount > 0 && <span className="text-[#ff6600]">{satelliteCount} satellites</span>}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[#00d4aa]">BTUT MFG</span>
        <span className="text-[#ff4d6a]">Cameras</span>
        <span className="text-[#4a9eff]">ADS-B</span>
        <span className="text-[#ff6600]">TLE Orbits</span>
        <span className="text-[#a050ff]">NASA GIBS</span>
        <span>OSM</span>
        <span>CesiumJS</span>
      </div>
    </div>
  );
}
