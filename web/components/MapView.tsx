"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { FRANKLIN_STREET, MAP_STYLES } from "@/lib/config";

interface Venue {
  name: string;
  lat: number;
  lon: number;
  amenity_type: string;
  busyness: number | null;
}

function busynessColor(b: number | null): string {
  if (b === null) return "#4a9eff";
  if (b >= 80) return "#ff2244";
  if (b >= 60) return "#ff6600";
  if (b >= 40) return "#ffaa00";
  if (b >= 20) return "#00d4aa";
  return "#4a9eff";
}

function busynessRadius(b: number | null): number {
  if (b === null) return 6;
  return 6 + (b / 100) * 14;
}

export default function MapView({
  venues,
  hour,
  onVenueClick,
}: {
  venues: Venue[];
  hour: number;
  onVenueClick?: (v: Venue) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; venue: Venue } | null>(null);

  // Simple Mercator projection for the Franklin Street area
  const project = useCallback((lat: number, lon: number, w: number, h: number) => {
    const b = FRANKLIN_STREET.bounds;
    const x = ((lon - b.west) / (b.east - b.west)) * w;
    const y = ((b.north - lat) / (b.north - b.south)) * h;
    return { x, y };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const w = container.clientWidth;
    const h = container.clientHeight;
    canvas.width = w * 2;
    canvas.height = h * 2;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(2, 2);

    // Background
    ctx.fillStyle = "#0a0b0f";
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = "#1e202822";
    ctx.lineWidth = 0.5;
    for (let gx = 0; gx < w; gx += 40) {
      ctx.beginPath();
      ctx.moveTo(gx, 0);
      ctx.lineTo(gx, h);
      ctx.stroke();
    }
    for (let gy = 0; gy < h; gy += 40) {
      ctx.beginPath();
      ctx.moveTo(0, gy);
      ctx.lineTo(w, gy);
      ctx.stroke();
    }

    // Franklin Street spine line
    const spine = [
      [35.9126, -79.059],
      [35.9128, -79.0575],
      [35.913, -79.0562],
      [35.9131, -79.0555],
      [35.9132, -79.0548],
      [35.9133, -79.054],
      [35.9134, -79.053],
      [35.9135, -79.052],
      [35.9136, -79.051],
    ];
    ctx.strokeStyle = "#1e2028";
    ctx.lineWidth = 2;
    ctx.beginPath();
    spine.forEach(([lat, lon], i) => {
      const p = project(lat, lon, w, h);
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();

    // Heat glow for each venue
    venues.forEach((v) => {
      const p = project(v.lat, v.lon, w, h);
      const b = v.busyness;
      if (b !== null && b > 10) {
        const r = 30 + (b / 100) * 60;
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
        const color = busynessColor(b);
        grad.addColorStop(0, color + "40");
        grad.addColorStop(0.5, color + "15");
        grad.addColorStop(1, color + "00");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // Venue dots
    venues.forEach((v) => {
      const p = project(v.lat, v.lon, w, h);
      const r = busynessRadius(v.busyness);
      const color = busynessColor(v.busyness);

      // Outer ring
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.stroke();

      // Inner fill
      ctx.fillStyle = color + "44";
      ctx.beginPath();
      ctx.arc(p.x, p.y, r * 0.6, 0, Math.PI * 2);
      ctx.fill();
    });

    // Labels for high-busyness venues
    ctx.font = "10px 'Inter', system-ui, sans-serif";
    ctx.textAlign = "left";
    venues.forEach((v) => {
      if (v.busyness !== null && v.busyness >= 40) {
        const p = project(v.lat, v.lon, w, h);
        const r = busynessRadius(v.busyness);
        ctx.fillStyle = "#e2e4e9aa";
        ctx.fillText(v.name.slice(0, 20), p.x + r + 4, p.y + 3);
      }
    });
  }, [venues, hour, project]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      const rect = container.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const w = container.clientWidth;
      const h = container.clientHeight;

      let found: Venue | null = null;
      for (const v of venues) {
        const p = project(v.lat, v.lon, w, h);
        const dist = Math.sqrt((mx - p.x) ** 2 + (my - p.y) ** 2);
        if (dist < busynessRadius(v.busyness) + 8) {
          found = v;
          break;
        }
      }

      if (found) {
        setTooltip({ x: mx, y: my, venue: found });
      } else {
        setTooltip(null);
      }
    },
    [venues, project]
  );

  const handleClick = useCallback(() => {
    if (tooltip && onVenueClick) {
      onVenueClick(tooltip.venue);
    }
  }, [tooltip, onVenueClick]);

  return (
    <div ref={containerRef} className="relative w-full h-full bg-[#0a0b0f]">
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-crosshair"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
        onClick={handleClick}
      />

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute pointer-events-none z-40 bg-[#111318ee] border border-[#2a2d38] rounded-lg px-3 py-2 text-xs font-mono"
          style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
        >
          <div className="text-[#00d4aa] font-semibold">{tooltip.venue.name}</div>
          <div className="text-[#6b7080] mt-1">
            {tooltip.venue.busyness !== null
              ? `${tooltip.venue.busyness}% busy`
              : "busyness unknown"}
          </div>
          <div className="text-[#454a58]">{tooltip.venue.amenity_type}</div>
        </div>
      )}

      {/* Overlay labels */}
      <div className="absolute top-3 left-3 text-[10px] font-mono text-[#454a58] tracking-wider uppercase">
        Venue Popularity — {hour}:00
      </div>
      <div className="absolute bottom-3 right-3 flex gap-3 text-[9px] font-mono text-[#454a58]">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#ff2244]" /> 80%+
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#ff6600]" /> 60%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#ffaa00]" /> 40%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#00d4aa]" /> 20%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#4a9eff]" /> no data
        </span>
      </div>
    </div>
  );
}
