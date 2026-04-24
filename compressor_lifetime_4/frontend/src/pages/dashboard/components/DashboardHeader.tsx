import { Settings } from "lucide-react";

import type { SystemConfig } from "../../../features/system/api/systemApi";

type Props = {
  config: SystemConfig;
  onOpenSettings: () => void;
};

export function DashboardHeader({ config, onOpenSettings }: Props) {
  return (
    <header className="z-10 flex items-center justify-between px-8 py-6">
      <div>
        <h1 className="bg-gradient-to-r from-white to-white/50 bg-clip-text text-2xl font-black tracking-tighter text-transparent">COMPRESSOR CORE</h1>
        <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">Lifetime Testing System V4.1</p>
      </div>
      <div className="flex items-center gap-4">
        <div className={`rounded-full border px-3 py-1 text-[11px] ${config.simulation ? "border-orange-400/40 text-orange-300" : "border-emerald-400/40 text-emerald-300"}`}>
          {config.simulation ? "Simulation Mode" : "Hardware Mode"}
        </div>
        <button onClick={onOpenSettings} className="rounded-full border border-white/10 bg-white/5 p-3 text-white/70 backdrop-blur-md transition-all hover:bg-white/10">
          <Settings className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
}

