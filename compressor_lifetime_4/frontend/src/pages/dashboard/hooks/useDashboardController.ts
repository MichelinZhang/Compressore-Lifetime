import { useCallback, useEffect, useRef, useState } from "react";

import type { SystemConfig } from "../../../features/system/api/systemApi";
import {
  fetchSystemConfig,
  pickSystemLogDir,
  setSimulationMode,
  setSystemLogDir,
} from "../../../features/system/api/systemApi";
import {
  addStation,
  connectStation,
  listStations,
  pauseStation,
  removeStation as removeStationApi,
  resumeStation,
  startStation,
  stopStation,
  updateStationConfig,
} from "../../../features/station/api/stationApi";
import { createEventSocket } from "../../../shared/api/wsClient";
import type { EventEnvelope, StationConfig, StationView } from "../../../shared/types/contracts";
import { toErrorMessage } from "../../../shared/utils/errors";

const PRESSURE_EASE_FACTOR = 0.22;
const PRESSURE_SMOOTH_MS = 120;
const HISTORY_POINTS = 40;
const POLL_FAST_MS = 900;
const POLL_SLOW_MS = 2600;

export type StationUi = StationView & {
  isRemoving?: boolean;
};

export function useDashboardController() {
  const [stations, setStations] = useState<StationUi[]>([]);
  const [logs, setLogs] = useState<string[]>([`[SYSTEM] UI rendered at ${new Date().toLocaleTimeString()}`]);
  const [historyMap, setHistoryMap] = useState<Record<number, number[]>>({});
  const [systemConfig, setSystemConfig] = useState<SystemConfig>({ simulation: false, log_dir: "data" });
  const [isRealtimeDegraded, setIsRealtimeDegraded] = useState(false);

  const dragItem = useRef<number | null>(null);
  const pressureBufferRef = useRef<Record<number, number>>({});

  const addLog = useCallback((msg: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`].slice(-120));
  }, []);

  const refreshStations = useCallback(async () => {
    const data = await listStations();
    setStations((prev) => {
      const removeState = new Map(prev.map((s) => [s.config.stationId, s.isRemoving]));
      const prevById = new Map(prev.map((s) => [s.config.stationId, s]));
      return data.map((s) => {
        const prevStation = prevById.get(s.config.stationId);
        return {
          ...s,
          runtime: {
            ...s.runtime,
            currentPressure: Number(prevStation?.runtime?.currentPressure ?? s.runtime.currentPressure),
          },
          isRemoving: Boolean(removeState.get(s.config.stationId)),
        };
      });
    });

    for (const s of data) {
      pressureBufferRef.current[s.config.stationId] = Number(s.runtime.currentPressure || 0);
    }

    setHistoryMap((prev) => {
      const next = { ...prev };
      for (const s of data) {
        if (!next[s.config.stationId]) {
          next[s.config.stationId] = Array(HISTORY_POINTS).fill(Number(s.runtime.currentPressure || 0));
        }
      }
      return next;
    });
  }, []);

  const refreshSystem = useCallback(async () => {
    const cfg = await fetchSystemConfig();
    setSystemConfig(cfg);
  }, []);

  const handleEvent = useCallback(
    (evt: EventEnvelope) => {
      if (evt.event === "station.pressure" && evt.stationId) {
        const p = Number(evt.payload?.pressure || 0);
        pressureBufferRef.current[evt.stationId] = p;
        const t = Number(evt.payload?.temperature || 25);
        setStations((prev) =>
          prev.map((s) =>
            s.config.stationId === evt.stationId
              ? {
                  ...s,
                  runtime: {
                    ...s.runtime,
                    currentTemperature: t,
                  },
                }
              : s,
          ),
        );
      }
      if (evt.event === "station.status" && evt.stationId) {
        setStations((prev) =>
          prev.map((s) =>
            s.config.stationId === evt.stationId
              ? {
                  ...s,
                  runtime: {
                    ...s.runtime,
                    status: (evt.payload?.status as StationView["runtime"]["status"]) || s.runtime.status,
                    fault: evt.payload?.fault as string | undefined,
                    connected: (evt.payload?.connected as boolean | undefined) ?? s.runtime.connected,
                  },
                }
              : s,
          ),
        );
      }
      if (evt.event === "station.progress" && evt.stationId) {
        const cycle = Number(evt.payload?.currentCycle || 0);
        setStations((prev) =>
          prev.map((s) =>
            s.config.stationId === evt.stationId ? { ...s, runtime: { ...s.runtime, currentCycle: cycle } } : s,
          ),
        );
      }
      if (evt.event === "station.log" || evt.event === "station.alarm" || evt.event === "system.log") {
        addLog(`[${evt.event}] ${evt.stationId || "-"} ${JSON.stringify(evt.payload)}`);
      }
    },
    [addLog],
  );

  useEffect(() => {
    refreshStations().catch((err) => addLog(`load stations failed: ${toErrorMessage(err)}`));
    refreshSystem().catch((err) => addLog(`load system config failed: ${toErrorMessage(err)}`));

    const socket = createEventSocket(handleEvent, {
      reconnectMs: 1200,
      maxReconnectAttempts: 6,
      onOpen: () => {
        setIsRealtimeDegraded(false);
      },
      onUnavailable: () => {
        setIsRealtimeDegraded(true);
        addLog("event socket unavailable, switched to polling");
      },
      onError: () => {
        setIsRealtimeDegraded(true);
      },
    });

    return () => socket.close();
  }, [addLog, handleEvent, refreshStations, refreshSystem]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStations((prev) => {
        let changed = false;
        const next = prev.map((s) => {
          const target = pressureBufferRef.current[s.config.stationId];
          if (target === undefined) {
            return s;
          }
          const current = Number(s.runtime.currentPressure || 0);
          const delta = Number(target) - current;
          if (Math.abs(delta) < 0.002) {
            if (current === Number(target)) {
              return s;
            }
            changed = true;
            return { ...s, runtime: { ...s.runtime, currentPressure: Number(target) } };
          }
          changed = true;
          return { ...s, runtime: { ...s.runtime, currentPressure: current + delta * PRESSURE_EASE_FACTOR } };
        });
        return changed ? next : prev;
      });

      setHistoryMap((prev) => {
        const next = { ...prev };
        let changed = false;
        for (const key of Object.keys(next)) {
          const id = Number(key);
          const arr = next[id] || Array(HISTORY_POINTS).fill(0);
          const last = arr.length ? Number(arr[arr.length - 1]) : 0;
          const target = Number(pressureBufferRef.current[id] ?? last);
          if (Math.abs(target - last) < 0.001) {
            continue;
          }
          const eased = last + (target - last) * PRESSURE_EASE_FACTOR;
          const updated = [...arr, eased];
          if (updated.length > HISTORY_POINTS) {
            updated.shift();
          }
          next[id] = updated;
          changed = true;
        }
        return changed ? next : prev;
      });
    }, PRESSURE_SMOOTH_MS);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const poll = window.setInterval(() => {
      refreshStations().catch(() => {
        // Silent: heartbeat sync for no-websocket environments.
      });
    }, isRealtimeDegraded ? POLL_FAST_MS : POLL_SLOW_MS);
    return () => window.clearInterval(poll);
  }, [isRealtimeDegraded, refreshStations]);

  const handleAddStation = useCallback(async () => {
    try {
      await addStation();
      await refreshStations();
      addLog("Station added");
    } catch (err) {
      addLog(`add station failed: ${toErrorMessage(err)}`);
    }
  }, [addLog, refreshStations]);

  const handleRemoveStation = useCallback(
    (id: number) => {
      setStations((current) => current.map((s) => (s.config.stationId === id ? { ...s, isRemoving: true } : s)));
      window.setTimeout(async () => {
        try {
          await removeStationApi(id);
          await refreshStations();
          addLog(`Station ${id} removed`);
        } catch (err) {
          addLog(`remove station ${id} failed: ${toErrorMessage(err)}`);
        }
      }, 400);
    },
    [addLog, refreshStations],
  );

  const saveSystemConfig = useCallback(
    async ({ simulation, logDir }: { simulation: boolean; logDir: string }) => {
      try {
        await setSimulationMode(simulation);
        addLog(`Simulation mode switched: ${simulation ? "ON" : "OFF"}`);
      } catch (err) {
        addLog(`Simulation switch failed: ${toErrorMessage(err)}`);
      }
      try {
        await setSystemLogDir(logDir);
        addLog(`Log directory set: ${logDir}`);
      } catch (err) {
        addLog(`Set log directory failed: ${toErrorMessage(err)}`);
      }
      await refreshSystem();
    },
    [addLog, refreshSystem],
  );

  const pickLogDir = useCallback(async () => {
    try {
      const res = await pickSystemLogDir();
      if (res?.ok && res?.log_dir) {
        addLog(`Log directory selected: ${res.log_dir}`);
        return res.log_dir;
      }
      if (res?.cancelled) {
        addLog("Folder selection cancelled");
      }
    } catch (err) {
      addLog(`Folder picker failed: ${toErrorMessage(err)}`);
    }
    return null;
  }, [addLog]);

  const onUpdateStationConfig = useCallback(async (id: number, cfg: StationConfig) => {
    await updateStationConfig(id, cfg);
  }, []);

  const dragStart = useCallback((event: React.DragEvent<HTMLDivElement>, position: number) => {
    dragItem.current = position;
    window.setTimeout(() => event.currentTarget.classList.add("opacity-50"), 0);
  }, []);

  const dragEnter = useCallback((_: React.DragEvent<HTMLDivElement>, position: number) => {
    if (dragItem.current === null || dragItem.current === position) {
      return;
    }
    setStations((prev) => {
      const copy = [...prev];
      const item = copy[dragItem.current as number];
      copy.splice(dragItem.current as number, 1);
      copy.splice(position, 0, item);
      dragItem.current = position;
      return copy;
    });
  }, []);

  const drop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    dragItem.current = null;
    event.currentTarget.classList.remove("opacity-50");
  }, []);

  return {
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
    connect: connectStation,
    start: startStation,
    pause: pauseStation,
    resume: resumeStation,
    stop: stopStation,
    dragStart,
    dragEnter,
    drop,
  };
}
