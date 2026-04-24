import { useState } from "react";
import { createPortal } from "react-dom";
import { Plus } from "lucide-react";

import { StationCard } from "../../features/station/components/StationCard";
import { SystemSettingsModal } from "../../features/system/components/SystemSettingsModal";
import { DashboardHeader } from "./components/DashboardHeader";
import { SystemTicker } from "./components/SystemTicker";
import { useDashboardController } from "./hooks/useDashboardController";

const customStyles = `
  @keyframes cardEnter {
    0% { opacity: 0; transform: scale(0.9) translateY(20px); }
    100% { opacity: 1; transform: scale(1) translateY(0); }
  }
  @keyframes cardExit {
    0% { opacity: 1; transform: scale(1); }
    100% { opacity: 0; transform: scale(0.9) translateY(-20px); }
  }
  .animate-card-enter { animation: cardEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
  .animate-card-exit { animation: cardExit 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; pointer-events: none; }
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
`;

export default function DashboardPage() {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const {
    stations,
    logs,
    historyMap,
    systemConfig,
    refreshStations,
    addLog,
    handleAddStation,
    handleRemoveStation,
    saveSystemConfig,
    pickLogDir,
    onUpdateStationConfig,
    connect,
    start,
    pause,
    resume,
    stop,
    dragStart,
    dragEnter,
    drop,
  } = useDashboardController();

  return (
    <div className="flex min-h-screen flex-col bg-[#050505] font-sans text-white selection:bg-white/20">
      <style dangerouslySetInnerHTML={{ __html: customStyles }} />

      <DashboardHeader config={systemConfig} onOpenSettings={() => setIsSettingsOpen(true)} />

      <main className="z-10 flex-1 overflow-auto px-8 pb-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {stations.map((station, index) => (
            <StationCard
              key={station.config.stationId}
              index={index}
              station={station}
              history={historyMap[station.config.stationId] || Array(40).fill(0)}
              onRemove={handleRemoveStation}
              onLog={addLog}
              onStart={async (id) => {
                await start(id);
              }}
              onPause={async (id) => {
                await pause(id);
              }}
              onResume={async (id) => {
                await resume(id);
              }}
              onStop={async (id) => {
                await stop(id);
              }}
              onConnect={async (id) => {
                await connect(id);
              }}
              onUpdateConfig={onUpdateStationConfig}
              onRefreshStations={refreshStations}
              isSimulation={Boolean(systemConfig.simulation)}
              dragStart={dragStart}
              dragEnter={dragEnter}
              drop={drop}
            />
          ))}

          <button onClick={handleAddStation} className="group relative flex min-h-[460px] cursor-pointer flex-col items-center justify-center rounded-[32px] border border-white/10 bg-white/[0.02] transition-all hover:bg-white/[0.05]">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/5 transition-all duration-300 group-hover:scale-110 group-hover:bg-white/10">
              <Plus className="h-6 w-6 text-white/50 group-hover:text-white" />
            </div>
            <span className="mt-4 text-xs font-bold uppercase tracking-widest text-white/30 transition-colors group-hover:text-white/70">Add Station</span>
          </button>
        </div>
      </main>

      <SystemTicker message={logs[logs.length - 1]} simulation={Boolean(systemConfig.simulation)} />

      {isSettingsOpen &&
        typeof document !== "undefined" &&
        createPortal(
          <SystemSettingsModal
            onClose={() => setIsSettingsOpen(false)}
            config={systemConfig}
            onSaveConfig={saveSystemConfig}
            onPickLogDir={pickLogDir}
          />,
          document.body,
        )}
    </div>
  );
}

