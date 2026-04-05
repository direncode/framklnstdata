"use client";

/**
 * Display Mode Switcher
 *
 * Military-grade visualization modes:
 * - Normal: Standard satellite imagery
 * - Night Vision (Green): Amplified light / phosphor green
 * - FLIR Thermal: Infrared thermal imaging simulation
 * - CRT Retro: Cold-war era monitor aesthetic with scanlines
 */

export type DisplayMode = "normal" | "night_vision" | "flir" | "crt";

const MODES: { id: DisplayMode; label: string; color: string; icon: string; description: string }[] = [
  {
    id: "normal",
    label: "NORMAL",
    color: "#e2e4e9",
    icon: "◎",
    description: "Standard satellite imagery",
  },
  {
    id: "night_vision",
    label: "NIGHT VISION",
    color: "#00ff41",
    icon: "◉",
    description: "Gen III phosphor green amplification",
  },
  {
    id: "flir",
    label: "FLIR",
    color: "#ff6600",
    icon: "◈",
    description: "Forward-looking infrared thermal",
  },
  {
    id: "crt",
    label: "CRT",
    color: "#00d4aa",
    icon: "▣",
    description: "Retro CRT monitor with scanlines",
  },
];

export function getDisplayModeFilter(mode: DisplayMode): string {
  switch (mode) {
    case "night_vision":
      return "hue-rotate(90deg) saturate(3) brightness(1.5) contrast(1.2)";
    case "flir":
      return "hue-rotate(180deg) saturate(0.3) brightness(1.2) contrast(2)";
    case "crt":
      return "sepia(0.3) contrast(1.4) brightness(0.9)";
    default:
      return "none";
  }
}

export default function DisplayModes({
  active,
  onChange,
}: {
  active: DisplayMode;
  onChange: (mode: DisplayMode) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="text-[10px] font-mono tracking-[0.15em] text-[#454a58] uppercase mb-2">
        Display Mode
      </div>
      {MODES.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onChange(mode.id)}
          className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-[10px] font-mono transition-all ${
            active === mode.id
              ? `border`
              : "text-[#454a58] hover:text-[#6b7080] hover:bg-[#111318]"
          }`}
          style={
            active === mode.id
              ? {
                  backgroundColor: `${mode.color}15`,
                  color: mode.color,
                  borderColor: `${mode.color}44`,
                  textShadow: mode.id !== "normal" ? `0 0 6px ${mode.color}66` : "none",
                }
              : undefined
          }
          title={mode.description}
        >
          <span>{mode.icon}</span>
          <span>{mode.label}</span>
        </button>
      ))}
    </div>
  );
}
