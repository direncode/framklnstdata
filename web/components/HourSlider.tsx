"use client";

export default function HourSlider({
  value,
  onChange,
}: {
  value: number;
  onChange: (h: number) => void;
}) {
  return (
    <div className="px-4 py-3 border-b border-[#1e2028] bg-[#0d0e13]">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono tracking-[0.15em] text-[#454a58] uppercase">
          Analysis Hour
        </span>
        <span className="text-sm font-mono text-[#00d4aa]">{value}:00</span>
      </div>
      <input
        type="range"
        min={0}
        max={23}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-1 bg-[#1e2028] rounded-full appearance-none cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3
          [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:bg-[#00d4aa] [&::-webkit-slider-thumb]:cursor-pointer
          [&::-webkit-slider-thumb]:shadow-[0_0_8px_#00d4aa55]"
      />
      <div className="flex justify-between text-[8px] font-mono text-[#454a58] mt-0.5">
        <span>0:00</span>
        <span>6:00</span>
        <span>12:00</span>
        <span>18:00</span>
        <span>23:00</span>
      </div>
    </div>
  );
}
