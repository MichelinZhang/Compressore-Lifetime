import { useEffect, useState } from "react";
import { X } from "lucide-react";

import { postJson } from "../../../shared/api/http";
import { toErrorMessage } from "../../../shared/utils/errors";

const IO_LABELS = ["V1", "V2", "V3", "COMPRESSOR", "P_SENSOR", "COUNTER_PWR", "COUNTER_SIG", "BUZZER"] as const;
type IoLabel = (typeof IO_LABELS)[number];

type Props = {
  onClose: () => void;
  stationId: number;
  pressure: number;
  onLog: (line: string) => void;
};

export function DebugModal({ onClose, stationId, pressure, onLog }: Props) {
  const [ioStates, setIoStates] = useState<boolean[]>(Array(8).fill(false));
  const [rawPressure, setRawPressure] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setRawPressure(Math.max(0, pressure + (Math.random() * 0.1 - 0.05)));
    }, 100);
    return () => clearInterval(timer);
  }, [pressure]);

  const toggleIO = async (idx: number) => {
    const next = !ioStates[idx];
    const arr = [...ioStates];
    arr[idx] = next;
    setIoStates(arr);
    try {
      await postJson(`/api/stations/${stationId}/debug/io-toggle`, {
        signal: IO_LABELS[idx] as IoLabel,
        state: next,
      });
      onLog(`[Station ${stationId}] IO ${IO_LABELS[idx]} => ${next ? "ON" : "OFF"}`);
    } catch (err) {
      onLog(`[Station ${stationId}] IO toggle failed: ${toErrorMessage(err)}`);
    }
  };

  const forceStatus = async (status: "running" | "paused" | "error" | "idle", label: string) => {
    try {
      await postJson(`/api/stations/${stationId}/debug/force-status`, { status });
      onLog(`[Station ${stationId}] forced status: ${label}`);
    } catch (err) {
      onLog(`[Station ${stationId}] force status failed: ${toErrorMessage(err)}`);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="relative flex max-h-[90vh] w-full max-w-md flex-col gap-6 overflow-y-auto rounded-3xl border border-white/10 bg-[#111318] p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Station {String(stationId).padStart(2, "0")} - Debug Mode</h2>
          <button
            onClick={onClose}
            className="cursor-pointer rounded-full border border-white/5 bg-white/5 p-2 text-white/80 transition-colors hover:bg-white/10 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex flex-col gap-2 rounded-2xl border border-white/5 bg-white/5 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-white/60">Filtered Pressure:</span>
            <span className="text-2xl font-black text-blue-400">{pressure.toFixed(2)} Bar</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/40">Raw Pressure:</span>
            <span className="font-mono text-sm text-rose-400">{rawPressure.toFixed(2)} Bar</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {IO_LABELS.map((name, idx) => (
            <button
              key={name}
              onClick={() => toggleIO(idx)}
              className={`cursor-pointer rounded-xl border px-4 py-3 text-sm font-bold transition-all ${
                ioStates[idx]
                  ? "border-emerald-500/30 bg-emerald-500/20 text-emerald-400 shadow-[0_0_15px_rgba(52,211,106,0.1)]"
                  : "border-white/5 bg-white/5 text-white/40 hover:bg-white/10"
              }`}
            >
              <div className="mb-1 text-xs font-normal opacity-60">Signal</div>
              {name} {ioStates[idx] ? "ON" : "OFF"}
            </button>
          ))}
        </div>

        <div className="flex gap-2 border-t border-white/10 pt-4">
          <button
            onClick={() => forceStatus("running", "running")}
            className="flex-1 cursor-pointer rounded-lg bg-emerald-500/20 py-2 text-xs font-bold text-emerald-400 transition-colors hover:bg-emerald-500/30"
          >
            Force Run
          </button>
          <button
            onClick={() => forceStatus("error", "alarm")}
            className="flex-1 cursor-pointer rounded-lg bg-rose-500/20 py-2 text-xs font-bold text-rose-400 transition-colors hover:bg-rose-500/30"
          >
            Force Alarm
          </button>
          <button
            onClick={() => forceStatus("paused", "paused")}
            className="flex-1 cursor-pointer rounded-lg bg-orange-500/20 py-2 text-xs font-bold text-orange-400 transition-colors hover:bg-orange-500/30"
          >
            Force Pause
          </button>
          <button
            onClick={() => forceStatus("idle", "idle")}
            className="flex-1 cursor-pointer rounded-lg bg-white/10 py-2 text-xs font-bold text-white/60 transition-colors hover:bg-white/20"
          >
            Reset
          </button>
        </div>

        <button
          onClick={onClose}
          className="mt-2 w-full cursor-pointer rounded-xl border border-white/10 bg-white/5 py-3 text-sm font-bold text-white/80 shadow-lg transition-all hover:bg-white/10 hover:text-white"
        >
          Back to Main
        </button>
      </div>
    </div>
  );
}

