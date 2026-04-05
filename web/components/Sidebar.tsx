"use client";

type Tab = "map" | "globe" | "cameras" | "aircraft" | "satellites" | "street" | "feed" | "intel" | "command" | "global";

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "map", label: "SURVEILLANCE", icon: "◎" },
  { id: "globe", label: "3D GLOBE", icon: "🌐" },
  { id: "cameras", label: "CAMERAS", icon: "📹" },
  { id: "aircraft", label: "AIRCRAFT", icon: "✈" },
  { id: "satellites", label: "SATELLITES", icon: "🛰" },
  { id: "street", label: "STREET", icon: "👁" },
  { id: "command", label: "COMMAND", icon: "⚡" },
  { id: "intel", label: "INTEL", icon: "◆" },
  { id: "global", label: "GLOBAL", icon: "◈" },
];

export default function Sidebar({
  active,
  onTabChange,
}: {
  active: Tab;
  onTabChange: (tab: Tab) => void;
}) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 md:relative md:bottom-auto md:left-auto md:right-auto md:w-14 bg-[#0d0e13] border-t md:border-t-0 md:border-r border-[#1e2028] flex md:flex-col items-center md:justify-start md:pt-3 gap-0.5 shrink-0 overflow-x-auto md:overflow-x-visible md:overflow-y-auto">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`shrink-0 w-11 h-11 md:w-10 md:h-10 rounded-lg flex flex-col md:flex-row items-center justify-center text-sm transition-all
            ${
              active === tab.id
                ? "bg-[#00d4aa15] text-[#00d4aa] border border-[#00d4aa33]"
                : "text-[#454a58] hover:text-[#6b7080] hover:bg-[#111318]"
            }`}
          title={tab.label}
        >
          <span>{tab.icon}</span>
          <span className="text-[6px] md:hidden mt-0.5 leading-none">{tab.label}</span>
        </button>
      ))}

      <div className="hidden md:flex md:flex-1" />

      <div className="hidden md:flex mb-3 w-8 h-8 rounded-full bg-[#111318] border border-[#1e2028] items-center justify-center text-[10px] text-[#454a58]">
        v5
      </div>
    </nav>
  );
}
