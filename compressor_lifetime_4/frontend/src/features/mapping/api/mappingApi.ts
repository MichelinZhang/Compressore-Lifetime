import { getJson, postJson, putJson } from "../../../shared/api/http";
import type {
  HardwareCapabilities,
  IoTemplate,
  StationIoMapping,
  ValidateMappingResponse,
} from "../../../shared/types/contracts";

export async function fetchHardwareCapabilities(device: string): Promise<HardwareCapabilities> {
  return getJson<HardwareCapabilities>(`/api/hardware/capabilities?device=${encodeURIComponent(device)}`);
}

export async function listIoTemplates(): Promise<IoTemplate[]> {
  return getJson<IoTemplate[]>("/api/io-templates");
}

export async function saveIoTemplate(template: IoTemplate): Promise<IoTemplate> {
  return postJson<IoTemplate>("/api/io-templates", template);
}

export async function validateStationMapping(stationId: number, mapping: StationIoMapping): Promise<ValidateMappingResponse> {
  return postJson<ValidateMappingResponse>(`/api/stations/${stationId}/io-mapping/validate`, { mapping });
}

export async function saveStationMapping(stationId: number, mapping: StationIoMapping): Promise<StationIoMapping> {
  return putJson<StationIoMapping>(`/api/stations/${stationId}/io-mapping`, mapping);
}

