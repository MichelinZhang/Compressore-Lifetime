from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class LogicalSignal(str, Enum):
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    COMPRESSOR = "COMPRESSOR"
    P_SENSOR = "P_SENSOR"
    COUNTER_PWR = "COUNTER_PWR"
    COUNTER_SIG = "COUNTER_SIG"
    BUZZER = "BUZZER"


class ModuleType(str, Enum):
    DO = "DO"
    DI = "DI"
    AI = "AI"
    AO = "AO"


class Direction(str, Enum):
    IN = "IN"
    OUT = "OUT"


class StationStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class PhysicalChannelRef(BaseModel):
    device: str
    moduleType: ModuleType
    channel: int = Field(ge=0)
    direction: Direction
    invert: bool = False


class StationIoMapping(BaseModel):
    stationId: int
    templateId: Optional[str] = None
    version: int = 1
    bindings: Dict[LogicalSignal, PhysicalChannelRef]

    def resolve(self, signal: LogicalSignal) -> PhysicalChannelRef:
        return self.bindings[signal]


class StationConfig(BaseModel):
    stationId: int
    deviceName: str = "Dev1"
    cycles: int = Field(default=350, gt=0)
    targetP: float = 2.02
    floorP: float = 0.02
    maxP: float = 2.5
    simulation: bool = False

    @model_validator(mode="after")
    def validate_pressure(self) -> "StationConfig":
        if self.floorP < 0:
            raise ValueError("floorP must be >= 0")
        if self.targetP <= self.floorP:
            raise ValueError("targetP must be greater than floorP")
        if self.maxP <= self.targetP:
            raise ValueError("maxP must be greater than targetP")
        return self


class StationRuntime(BaseModel):
    status: StationStatus = StationStatus.IDLE
    connected: bool = False
    currentPressure: float = 0.0
    currentTemperature: float = 25.0
    currentCycle: int = 0
    timerRemaining: str = "--"
    fault: Optional[str] = None


class StationView(BaseModel):
    config: StationConfig
    runtime: StationRuntime
    mapping: StationIoMapping


class IoTemplate(BaseModel):
    templateId: str
    name: str
    bindings: Dict[LogicalSignal, PhysicalChannelRef]


class ValidateMappingRequest(BaseModel):
    mapping: StationIoMapping


class ValidationIssue(BaseModel):
    level: Literal["error", "warning"]
    message: str


class ValidateMappingResponse(BaseModel):
    valid: bool
    issues: List[ValidationIssue]


class HardwareChannel(BaseModel):
    moduleType: ModuleType
    direction: Direction
    channels: List[int]


class HardwareCapabilities(BaseModel):
    device: str
    supports: List[str]
    details: List[HardwareChannel]


class EventEnvelope(BaseModel):
    event: str
    stationId: Optional[int] = None
    ts: float
    payload: dict
