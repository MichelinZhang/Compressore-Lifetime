import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Activity, Cpu, GripHorizontal, Pause, Play, Settings, Sliders, Square, X } from "lucide-react";

import { DebugModal } from "../../debug/components/DebugModal";
import { IoMappingModal } from "../../mapping/components/IoMappingModal";
import { toErrorMessage } from "../../../shared/utils/errors";
import type { StationConfig, StationView } from "../../../shared/types/contracts";

type StationUi = StationView & {
  isRemoving?: boolean;
};

type Props = {
  station: StationUi;
  history: number[];
  onRemove: (stationId: number) => void;
  onLog: (line: string) => void;
  onStart: (stationId: number) => Promise<void>;
  onPause: (stationId: number) => Promise<void>;
  onResume: (stationId: number) => Promise<void>;
  onStop: (stationId: number) => Promise<void>;
  onConnect: (stationId: number) => Promise<void>;
  onUpdateConfig: (stationId: number, config: StationConfig) => Promise<void>;
  onRefreshStations: () => Promise<void>;
  isSimulation: boolean;
  index: number;
  dragStart: (event: React.DragEvent<HTMLDivElement>, position: number) => void;
  dragEnter: (event: React.DragEvent<HTMLDivElement>, position: number) => void;
  drop: (event: React.DragEvent<HTMLDivElement>) => void;
};

type SparkLineProps = {
  data: number[];
  colorHex: string;
};

function SparkLine({ data, colorHex }: SparkLineProps) {
  const safeData = data.length ? data : [0, 0];
  const max = Math.max(3.0, ...safeData);
  const min = 0;
  const points = safeData.map((val, i) => {
    const x = (i / (safeData.length - 1 || 1)) * 100;
    const y = 100 - ((val - min) / (max - min || 1)) * 100;
    return { x, y };
  });

  const polylineStr = points.map((p) => `${p.x},${p.y}`).join(" ");
  const lastPoint = points[points.length - 1] || { x: 100, y: 100 };

  return (
    <div className="relative mb-6 mt-[-10px] h-24 w-full">
      <div
        className="absolute inset-0 border-b border-white/10"
        style={{ background: "linear-gradient(90deg, transparent 95%, rgba(255,255,255,0.05) 100%)", backgroundSize: "10% 100%" }}
      />
      <div className="pointer-events-none absolute bottom-0 right-0 top-0 z-20 w-1/4 bg-gradient-to-r from-transparent to-black/40" />

      <svg className="relative z-10 h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
        <polygon points={`0,100 ${polylineStr} 100,100`} fill={`url(#gradient-${colorHex.replace("#", "")})`} opacity="0.6" />
        <polyline
          points={polylineStr}
          fill="none"
          stroke={colorHex}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: `drop-shadow(0 0 6px ${colorHex})` }}
        />
        <circle
          cx={lastPoint.x}
          cy={lastPoint.y}
          r="3"
          fill="#FFFFFF"
          stroke={colorHex}
          strokeWidth="1.5"
          style={{ filter: `drop-shadow(0 0 8px ${colorHex})` }}
        />
        <line x1="0" y1={lastPoint.y} x2={lastPoint.x} y2={lastPoint.y} stroke={colorHex} strokeWidth="0.5" strokeDasharray="2,2" opacity="0.5" />

        <defs>
          <linearGradient id={`gradient-${colorHex.replace("#", "")}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={colorHex} stopOpacity="0.9" />
            <stop offset="100%" stopColor={colorHex} stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

type RingTheme = {
  glow: string;
  text: string;
  hex: string;
};

type GlowingPressureRingProps = {
  pressure: number;
  maxP: number;
  colorTheme: RingTheme;
};

function GlowingPressureRing({ pressure, maxP, colorTheme }: GlowingPressureRingProps) {
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const fillPercentage = Math.min((pressure / (maxP || 1)) * 100, 100);
  const strokeDashoffset = circumference - (fillPercentage / 100) * circumference;

  return (
    <div className="pointer-events-none relative z-10 mx-auto my-4 flex h-40 w-40 items-center justify-center">
      <div className={`absolute inset-0 rounded-full blur-3xl opacity-40 transition-colors duration-700 ${colorTheme.glow}`} />
      <svg className="absolute inset-0 h-full w-full -rotate-90 drop-shadow-2xl" viewBox="0 0 160 160">
        <circle cx="80" cy="80" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className={`transition-all duration-300 ${colorTheme.text}`}
          style={{ filter: `drop-shadow(0 0 8px ${colorTheme.hex})` }}
        />
      </svg>
      <div className="relative z-10 flex flex-col items-center justify-center">
        <span className="text-3xl font-black tracking-tighter text-white" style={{ textShadow: "0 2px 10px rgba(0,0,0,0.5)" }}>
          {pressure.toFixed(2)}
        </span>
        <span className="mt-1 text-[10px] font-bold tracking-widest text-white/50">BAR</span>
      </div>
    </div>
  );
}

export function StationCard({
  station,
  history,
  onRemove,
  onLog,
  onStart,
  onPause,
  onResume,
  onStop,
  onConnect,
  onUpdateConfig,
  onRefreshStations,
  isSimulation,
  index,
  dragStart,
  dragEnter,
  drop,
}: Props) {
  const [isDebugOpen, setIsDebugOpen] = useState(false);
  const [isMappingOpen, setIsMappingOpen] = useState(false);

  const statusRaw = station?.runtime?.status || "idle";
  const status = statusRaw === "stopped" ? "idle" : statusRaw;
  const pressure = Number(station?.runtime?.currentPressure || 0);
  const cycle = Number(station?.runtime?.currentCycle || 0);
  const params = {
    cycles: Number(station?.config?.cycles || 350),
    targetP: Number(station?.config?.targetP || 2.02),
    floorP: Number(station?.config?.floorP || 0.02),
    maxP: Number(station?.config?.maxP || 2.5),
  };
  const [editParams, setEditParams] = useState(params);

  useEffect(() => {
    setEditParams(params);
  }, [station?.config?.cycles, station?.config?.targetP, station?.config?.floorP, station?.config?.maxP]);

  const themes = {
    idle: { bg: "bg-[#1a1c23]", glow: "bg-slate-500", text: "text-slate-400", hex: "#94a3b8", border: "border-white/5" },
    running: { bg: "bg-[#0f2118]", glow: "bg-emerald-500", text: "text-emerald-400", hex: "#34d399", border: "border-emerald-500/20" },
    paused: { bg: "bg-[#2a1c0d]", glow: "bg-orange-500", text: "text-orange-400", hex: "#fb923c", border: "border-orange-500/20" },
    error: { bg: "bg-[#2a0d12]", glow: "bg-rose-600", text: "text-rose-500", hex: "#f43f5e", border: "border-rose-500/30" },
  };
  const theme = themes[status as keyof typeof themes] || themes.idle;

  const handleToggle = async () => {
    try {
      if (status === "idle" || status === "error") {
        if (!isSimulation) {
          await onConnect(station.config.stationId);
        }
        await onStart(station.config.stationId);
        await onRefreshStations();
      } else if (status === "running") {
        await onPause(station.config.stationId);
        await onRefreshStations();
      } else if (status === "paused") {
        await onResume(station.config.stationId);
        await onRefreshStations();
      }
    } catch (err) {
      onLog(`[Station ${station.config.stationId}] action failed: ${toErrorMessage(err)}`);
    }
  };

  const handleStop = async () => {
    try {
      await onStop(station.config.stationId);
      await onRefreshStations();
    } catch (err) {
      onLog(`[Station ${station.config.stationId}] stop failed: ${toErrorMessage(err)}`);
    }
  };

  const saveParam = async (field: keyof typeof editParams, rawValue: string) => {
    const num = Number(rawValue);
    if (!Number.isFinite(num)) {
      return;
    }
    const next = { ...editParams, [field]: num };
    setEditParams(next);
    try {
      await onUpdateConfig(station.config.stationId, {
        ...station.config,
        cycles: Math.max(1, Math.round(next.cycles)),
        targetP: Number(next.targetP),
        floorP: Number(next.floorP),
        maxP: Number(next.maxP),
      });
      await onRefreshStations();
      onLog(`[Station ${station.config.stationId}] config updated`);
    } catch (err) {
      onLog(`[Station ${station.config.stationId}] config update failed: ${toErrorMessage(err)}`);
    }
  };

  return (
    <div
      draggable
      onDragStart={(e) => dragStart(e, index)}
      onDragEnter={(e) => dragEnter(e, index)}
      onDragEnd={drop}
      onDragOver={(e) => e.preventDefault()}
      className={`relative flex cursor-grab flex-col overflow-hidden rounded-[32px] border p-6 shadow-2xl transition-colors duration-700 active:cursor-grabbing hover:border-white/20 ${theme.bg} ${theme.border} ${
        station.isRemoving ? "animate-card-exit" : "animate-card-enter"
      }`}
    >
      <div className={`pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full blur-[100px] opacity-20 transition-colors duration-700 ${theme.glow}`} />

      <div className="relative z-10 flex cursor-grab items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`rounded-full border border-white/10 bg-white/5 p-2 backdrop-blur-md ${theme.text}`}>
            {status === "running" ? <Cpu className="h-5 w-5 animate-pulse" /> : <Activity className="h-5 w-5" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold tracking-wide text-white">Station {String(station.config.stationId).padStart(2, "0")}</h3>
              <span
                title={station?.runtime?.connected ? "Hardware Connected" : "Hardware Disconnected"}
                className={`inline-block h-2.5 w-2.5 rounded-full ${
                  station?.runtime?.connected ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]" : "bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.8)]"
                }`}
              />
              <GripHorizontal className="h-4 w-4 text-white/20" />
            </div>
            <p className={`mt-0.5 text-xs font-bold uppercase tracking-widest ${theme.text}`}>{status}</p>
          </div>
        </div>
        <div className="z-20 flex items-center gap-2" onMouseDown={(e) => e.stopPropagation()}>
          <button
            onClick={() => setIsMappingOpen(true)}
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-white/5 text-white/30 backdrop-blur-md transition-all hover:bg-violet-500/20 hover:text-violet-300"
          >
            <Settings className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsDebugOpen(true)}
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-white/5 text-white/30 backdrop-blur-md transition-all hover:bg-blue-500/20 hover:text-blue-400"
          >
            <Sliders className="h-4 w-4" />
          </button>
          <button
            onClick={() => onRemove(station.config.stationId)}
            disabled={status === "running"}
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-white/5 text-white/30 backdrop-blur-md transition-all hover:bg-red-500/20 hover:text-red-400 disabled:opacity-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <GlowingPressureRing pressure={pressure} maxP={params.maxP} colorTheme={theme} />
      <SparkLine data={history} colorHex={theme.hex} />

      <div className="relative z-10 mb-6 grid grid-cols-4 gap-2">
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-md">
          <span className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-white/40">Cycle</span>
          <input
            type="number"
            min={1}
            value={editParams.cycles}
            onChange={(e) => setEditParams((p) => ({ ...p, cycles: Number(e.target.value) }))}
            onBlur={(e) => saveParam("cycles", e.target.value)}
            className="w-16 rounded border border-white/20 bg-black/40 px-2 py-1 text-center text-sm text-white"
          />
          <span className="mt-1 text-[10px] text-white/30">{cycle} / run</span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-md">
          <span className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-white/40">Target</span>
          <input
            type="number"
            step="0.01"
            value={editParams.targetP}
            onChange={(e) => setEditParams((p) => ({ ...p, targetP: Number(e.target.value) }))}
            onBlur={(e) => saveParam("targetP", e.target.value)}
            className="w-16 rounded border border-white/20 bg-black/40 px-2 py-1 text-center text-sm text-white"
          />
          <span className="mt-1 text-[10px] text-white/30">bar</span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-md">
          <span className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-white/40">Floor</span>
          <input
            type="number"
            step="0.01"
            value={editParams.floorP}
            onChange={(e) => setEditParams((p) => ({ ...p, floorP: Number(e.target.value) }))}
            onBlur={(e) => saveParam("floorP", e.target.value)}
            className="w-16 rounded border border-white/20 bg-black/40 px-2 py-1 text-center text-sm text-white"
          />
          <span className="mt-1 text-[10px] text-white/30">bar</span>
        </div>
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-md">
          <span className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-white/40">Max</span>
          <input
            type="number"
            step="0.01"
            value={editParams.maxP}
            onChange={(e) => setEditParams((p) => ({ ...p, maxP: Number(e.target.value) }))}
            onBlur={(e) => saveParam("maxP", e.target.value)}
            className={`w-16 rounded border bg-black/40 px-2 py-1 text-center text-sm ${pressure > editParams.maxP * 0.9 ? "border-red-400/40 text-red-300" : "border-white/20 text-white"}`}
          />
          <span className="mt-1 text-[10px] text-white/30">bar</span>
        </div>
      </div>

      <div className="relative z-10 mt-auto flex gap-3 rounded-full border border-white/10 bg-black/40 p-1.5 backdrop-blur-xl" onMouseDown={(e) => e.stopPropagation()}>
        <button
          onClick={handleToggle}
          className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-full py-3 text-sm font-bold transition-all duration-300 ${
            status === "running"
              ? "bg-white/10 text-white hover:bg-white/20"
              : status === "idle"
                ? "bg-white text-black shadow-[0_0_20px_rgba(255,255,255,0.3)] hover:bg-gray-200"
                : "bg-orange-500 text-white shadow-[0_0_20px_rgba(244,146,54,0.3)] hover:bg-orange-400"
          }`}
        >
          {status === "running" ? <Pause className="h-4 w-4" fill="currentColor" /> : <Play className="h-4 w-4" fill="currentColor" />}
          {status === "running" ? "Pause" : status === "paused" ? "Resume" : "Start Test"}
        </button>
        <button onClick={handleStop} disabled={status === "idle"} className="flex w-14 cursor-pointer items-center justify-center rounded-full bg-white/5 text-white/50 transition-all hover:bg-rose-500 hover:text-white disabled:opacity-20">
          <Square className="h-4 w-4" fill="currentColor" />
        </button>
      </div>

      {isDebugOpen &&
        typeof document !== "undefined" &&
        createPortal(
          <DebugModal onClose={() => setIsDebugOpen(false)} stationId={station.config.stationId} pressure={pressure} onLog={onLog} />,
          document.body,
        )}

      {isMappingOpen &&
        typeof document !== "undefined" &&
        createPortal(
          <IoMappingModal
            stationId={station.config.stationId}
            mapping={station.mapping}
            onClose={() => setIsMappingOpen(false)}
            onSaved={async () => {
              await onRefreshStations();
            }}
          />,
          document.body,
        )}
    </div>
  );
}
