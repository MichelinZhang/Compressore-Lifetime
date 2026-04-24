import { deleteJson, getJson, postJson, putJson } from "../../../shared/api/http";
import type { StationConfig, StationView } from "../../../shared/types/contracts";

export async function listStations(): Promise<StationView[]> {
  return getJson<StationView[]>("/api/stations");
}

export async function addStation(): Promise<StationView> {
  return postJson<StationView>("/api/stations");
}

export async function removeStation(stationId: number): Promise<{ ok: boolean }> {
  return deleteJson<{ ok: boolean }>(`/api/stations/${stationId}`);
}

export async function connectStation(stationId: number): Promise<{ ok: boolean }> {
  return postJson<{ ok: boolean }>(`/api/stations/${stationId}/connect`);
}

export async function startStation(stationId: number): Promise<{ ok: boolean }> {
  return postJson<{ ok: boolean }>(`/api/stations/${stationId}/start`);
}

export async function pauseStation(stationId: number): Promise<{ ok: boolean }> {
  return postJson<{ ok: boolean }>(`/api/stations/${stationId}/pause`);
}

export async function resumeStation(stationId: number): Promise<{ ok: boolean }> {
  return postJson<{ ok: boolean }>(`/api/stations/${stationId}/resume`);
}

export async function stopStation(stationId: number): Promise<{ ok: boolean }> {
  return postJson<{ ok: boolean }>(`/api/stations/${stationId}/stop`);
}

export async function updateStationConfig(stationId: number, config: StationConfig): Promise<StationConfig> {
  return putJson<StationConfig>(`/api/stations/${stationId}/config`, config);
}

