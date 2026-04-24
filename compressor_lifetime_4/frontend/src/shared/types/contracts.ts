export type LogicalSignal =
  | "V1"
  | "V2"
  | "V3"
  | "COMPRESSOR"
  | "P_SENSOR"
  | "COUNTER_PWR"
  | "COUNTER_SIG"
  | "BUZZER";

export type ModuleType = "DO" | "DI" | "AI" | "AO";
export type Direction = "IN" | "OUT";
export type StationStatus = "idle" | "running" | "paused" | "error" | "stopped";

export interface PhysicalChannelRef {
  device: string;
  moduleType: ModuleType;
  channel: number;
  direction: Direction;
  invert: boolean;
}

export interface StationIoMapping {
  stationId: number;
  templateId?: string;
  version: number;
  bindings: Record<LogicalSignal, PhysicalChannelRef>;
}

export interface StationConfig {
  stationId: number;
  deviceName: string;
  cycles: number;
  targetP: number;
  floorP: number;
  maxP: number;
  simulation: boolean;
}

export interface StationRuntime {
  status: StationStatus;
  connected: boolean;
  currentPressure: number;
  currentTemperature: number;
  currentCycle: number;
  timerRemaining: string;
  fault?: string;
}

export interface StationView {
  config: StationConfig;
  runtime: StationRuntime;
  mapping: StationIoMapping;
}

export interface ValidationIssue {
  level: "error" | "warning";
  message: string;
}

export interface ValidateMappingResponse {
  valid: boolean;
  issues: ValidationIssue[];
}

export interface IoTemplate {
  templateId: string;
  name: string;
  bindings: Record<LogicalSignal, PhysicalChannelRef>;
}

export interface HardwareChannel {
  moduleType: ModuleType;
  direction: Direction;
  channels: number[];
}

export interface HardwareCapabilities {
  device: string;
  supports: string[];
  details: HardwareChannel[];
}

export interface EventEnvelope {
  event: string;
  stationId?: number;
  ts: number;
  payload: Record<string, unknown>;
}
