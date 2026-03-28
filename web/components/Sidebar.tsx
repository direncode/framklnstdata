"use client";

type Tab = "map" | "feed" | "intel";

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "map", label: "SURVEILLANCE", icon: "◎" },
  { id: "feed", label: "TRENDS", icon: "◈" },
  { id: "intel", label: "INTEL", icon: "◆" },
];

export default function Sidebar({
  active,
  onTabChange,
}: {
  active: Tab;
  onTabChange: (tab: Tab) => void;
}) {
  return (
    <nav className="w-14 bg-[#0d0e13] border-r border-[#1e2028] flex flex-col items-center pt-4 gap-1 shrink-0">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg transition-all
            ${
              active === tab.id
                ? "bg-[#00d4aa15] text-[#00d4aa] border border-[#00d4aa33]"
                : "text-[#454a58] hover:text-[#6b7080] hover:bg-[#111318]"
            }`}
          title={tab.label}
        >
          {tab.icon}
        </button>
      ))}

      <div className="flex-1" />

      <div className="mb-4 w-8 h-8 rounded-full bg-[#111318] border border-[#1e2028] flex items-center justify-center text-[10px] text-[#454a58]">
        v3
      </div>
    </nav>
  );
}
