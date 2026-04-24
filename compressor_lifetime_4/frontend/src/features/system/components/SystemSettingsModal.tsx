import { useState } from "react";
import { X } from "lucide-react";

import type { SystemConfig } from "../api/systemApi";

type Props = {
  onClose: () => void;
  config: SystemConfig;
  onSaveConfig: (payload: { simulation: boolean; logDir: string }) => Promise<void>;
  onPickLogDir: () => Promise<string | null>;
};

export function SystemSettingsModal({ onClose, config, onSaveConfig, onPickLogDir }: Props) {
  const [simulation, setSimulation] = useState(Boolean(config?.simulation));
  const [logDir, setLogDir] = useState(config?.log_dir || "data");

  const save = async () => {
    await onSaveConfig({ simulation, logDir });
    onClose();
  };

  const browse = async () => {
    const picked = await onPickLogDir();
    if (picked) {
      setLogDir(picked);
    }
  };

  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-3xl border border-white/10 bg-[#111318] p-6 text-white shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-lg font-bold">System Settings</h3>
          <button onClick={onClose} className="rounded-full bg-white/10 p-2 hover:bg-white/20">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="mb-2 text-xs text-white/60">Mode</div>
            <label className="flex cursor-pointer items-center justify-between">
              <span className="text-sm">Simulation mode (same backend logic)</span>
              <input type="checkbox" checked={simulation} onChange={(e) => setSimulation(e.target.checked)} />
            </label>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/5 p-4">
            <div className="mb-2 text-xs text-white/60">Data Save Directory</div>
            <div className="flex gap-2">
              <input
                value={logDir}
                onChange={(e) => setLogDir(e.target.value)}
                className="w-full rounded-lg border border-white/20 bg-black/40 px-3 py-2 text-sm outline-none focus:border-blue-400"
                placeholder="data"
              />
              <button onClick={browse} className="rounded-lg border border-white/20 px-3 py-2 text-sm hover:bg-white/10">
                Browse...
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 flex gap-2">
          <button onClick={save} className="flex-1 rounded-lg bg-white py-2 font-bold text-black hover:bg-gray-200">
            Save
          </button>
          <button onClick={onClose} className="flex-1 rounded-lg border border-white/20 py-2">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

