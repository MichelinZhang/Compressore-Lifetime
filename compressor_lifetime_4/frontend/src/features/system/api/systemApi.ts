import { getJson, postJson } from "../../../shared/api/http";

export type SystemConfig = {
  simulation: boolean;
  log_dir: string;
  driver?: string;
  cors_origins?: string[];
};

export async function fetchSystemConfig(): Promise<SystemConfig> {
  return getJson<SystemConfig>("/api/system/config");
}

export async function setSimulationMode(simulation: boolean): Promise<{ ok: boolean; simulation: boolean }> {
  return postJson<{ ok: boolean; simulation: boolean }>("/api/system/simulation", { simulation });
}

export async function setSystemLogDir(logDir: string): Promise<{ ok: boolean; log_dir: string }> {
  return postJson<{ ok: boolean; log_dir: string }>("/api/system/log-dir", { log_dir: logDir });
}

export async function pickSystemLogDir(): Promise<{ ok?: boolean; cancelled?: boolean; log_dir?: string }> {
  return postJson<{ ok?: boolean; cancelled?: boolean; log_dir?: string }>("/api/system/pick-log-dir");
}

