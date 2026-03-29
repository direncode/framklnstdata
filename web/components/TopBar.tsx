"use client";

import { useEffect, useState } from "react";

export default function TopBar() {
  const [time, setTime] = useState("");

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString("en-US", { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="h-10 md:h-12 flex items-center justify-between px-3 md:px-5 border-b border-[#1e2028] bg-[#0d0e13] shrink-0 z-50">
      <div className="flex items-center gap-2 md:gap-3">
        <div className="w-2 h-2 rounded-full bg-[#00d4aa] status-live" />
        <span className="text-[10px] md:text-xs font-mono tracking-[0.15em] md:tracking-[0.2em] text-[#00d4aa] uppercase">
          Franklin St Data
        </span>
      </div>

      <div className="flex items-center gap-2 md:gap-6 text-[9px] md:text-xs text-[#6b7080] font-mono">
        <span className="hidden md:inline">35.9132&deg;N 79.0555&deg;W</span>
        <span className="hidden md:inline text-[#454a58]">|</span>
        <span className="hidden sm:inline">Chapel Hill, NC</span>
        <span className="hidden sm:inline text-[#454a58]">|</span>
        <span className="text-[#e2e4e9]">{time}</span>
      </div>
    </header>
  );
}
