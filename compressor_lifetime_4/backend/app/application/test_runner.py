from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.adapters.base import AoIoDriver
from app.domain.models import LogicalSignal, StationConfig, StationIoMapping, StationRuntime, StationStatus
from app.infrastructure.csv_logger import CsvLogger
from app.infrastructure.event_bus import EventBus


@dataclass
class StationRunner:
    station_id: int
    config: StationConfig
    mapping: StationIoMapping
    driver: AoIoDriver
    bus: EventBus
    logger: CsvLogger
    runtime: StationRuntime = field(default_factory=StationRuntime)
    _task: asyncio.Task | None = None
    _paused: asyncio.Event = field(default_factory=asyncio.Event)
    _stop: asyncio.Event = field(default_factory=asyncio.Event)
    _csv_path: Path | None = None

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running():
            return
        self._paused.set()
        self._stop.clear()
        # Let simulation follow the same runtime max pressure envelope as real mode.
        if hasattr(self.driver, "set_runtime_limit"):
            self.driver.set_runtime_limit(self.config.maxP)
        # Keep the same runtime object reference so StationManager/API always sees latest state.
        self.runtime.status = StationStatus.RUNNING
        self.runtime.currentPressure = 0.0
        self.runtime.currentCycle = 0
        self.runtime.timerRemaining = "--"
        self.runtime.fault = None
        self._task = asyncio.create_task(self._run())

    async def pause(self) -> None:
        self._paused.clear()
        self.runtime.status = StationStatus.PAUSED
        await self.bus.publish("station.status", {"status": self.runtime.status}, self.station_id)

    async def resume(self) -> None:
        self._paused.set()
        self.runtime.status = StationStatus.RUNNING
        await self.bus.publish("station.status", {"status": self.runtime.status}, self.station_id)

    async def stop(self) -> None:
        self._stop.set()
        self._paused.set()
        if self._task:
            await self._task
        self.runtime.status = StationStatus.STOPPED
        await self.bus.publish("station.status", {"status": self.runtime.status}, self.station_id)

    async def _run(self) -> None:
        csv_path, meta_path = self.logger.build_files(self.station_id, self.config.deviceName)
        self._csv_path = csv_path
        max_p = 0.0
        min_p = 999.0
        start_ts = time.time()
        try:
            for cycle in range(1, self.config.cycles + 1):
                if self._stop.is_set():
                    break
                await self._phase_pressure(cycle, "PHASE_1", repeats=4)
                await self._phase_pressure(cycle, "PHASE_2", repeats=14)
                self.runtime.currentCycle = cycle
                await self.bus.publish("station.progress", {"currentCycle": cycle}, self.station_id)
                pressure = await self.driver.read_pressure(self.mapping.resolve(LogicalSignal.P_SENSOR))
                max_p = max(max_p, pressure)
                min_p = min(min_p, pressure)
                self.logger.append_row(csv_path, cycle, "CYCLE", "DONE", pressure, max_p, min_p)
                if pressure > self.config.maxP:
                    self.runtime.status = StationStatus.ERROR
                    self.runtime.fault = f"Pressure over limit: {pressure:.2f} > {self.config.maxP:.2f}"
                    await self.bus.publish("station.alarm", {"fault": self.runtime.fault}, self.station_id)
                    await self.driver.emergency_shutdown(self.mapping.bindings)
                    return
        finally:
            if not self.runtime.fault and not self._stop.is_set():
                self.runtime.status = StationStatus.IDLE
            payload = {
                "stationId": self.station_id,
                "durationSec": round(time.time() - start_ts, 2),
                "finalStatus": self.runtime.status,
                "fault": self.runtime.fault,
            }
            self.logger.write_meta(meta_path, payload)
            await self.bus.publish("station.status", {"status": self.runtime.status, "fault": self.runtime.fault}, self.station_id)

    async def _phase_pressure(self, cycle: int, phase_name: str, repeats: int) -> None:
        for idx in range(repeats):
            if self._stop.is_set():
                return
            await self._paused.wait()
            reached_target = await self._drive_pressurize_to_target(timeout_sec=12.0)
            reached_floor = await self._drive_release_to_floor(timeout_sec=12.0)
            pressure = await self.driver.read_pressure(self.mapping.resolve(LogicalSignal.P_SENSOR))
            temperature = await self.driver.read_temperature(self.mapping.resolve(LogicalSignal.P_SENSOR))
            self.runtime.currentPressure = pressure
            self.runtime.currentTemperature = temperature
            await self.bus.publish("station.pressure", {"pressure": pressure, "temperature": temperature}, self.station_id)
            await self.bus.publish(
                "station.log",
                {
                    "line": (
                        f"{phase_name} {idx+1}/{repeats} done "
                        f"(target={'ok' if reached_target else 'timeout'}, floor={'ok' if reached_floor else 'timeout'})"
                    )
                },
                self.station_id,
            )
            if self._csv_path is not None:
                self.logger.append_row(self._csv_path, cycle, phase_name, f"{idx+1}/{repeats}", pressure, pressure, pressure)

    async def _drive_pressurize_to_target(self, timeout_sec: float) -> bool:
        states = {
            LogicalSignal.V1: True,
            LogicalSignal.V2: False,
            LogicalSignal.V3: False,
            LogicalSignal.COMPRESSOR: True,
            LogicalSignal.COUNTER_PWR: True,
            LogicalSignal.P_SENSOR: False,
            LogicalSignal.COUNTER_SIG: False,
            LogicalSignal.BUZZER: False,
        }
        start = time.monotonic()
        while not self._stop.is_set():
            await self._paused.wait()
            await self.driver.set_outputs(states, self.mapping.bindings)
            p = await self.driver.read_pressure(self.mapping.resolve(LogicalSignal.P_SENSOR))
            t = await self.driver.read_temperature(self.mapping.resolve(LogicalSignal.P_SENSOR))
            self.runtime.currentPressure = p
            self.runtime.currentTemperature = t
            await self.bus.publish("station.pressure", {"pressure": p, "temperature": t}, self.station_id)
            if p >= self.config.targetP:
                return True
            if (time.monotonic() - start) >= timeout_sec:
                return False
            await asyncio.sleep(0.08)
        return False

    async def _drive_release_to_floor(self, timeout_sec: float) -> bool:
        states = {
            LogicalSignal.V1: False,
            LogicalSignal.V2: True,
            LogicalSignal.V3: True,
            LogicalSignal.COMPRESSOR: False,
            LogicalSignal.COUNTER_PWR: True,
            LogicalSignal.P_SENSOR: False,
            LogicalSignal.COUNTER_SIG: False,
            LogicalSignal.BUZZER: False,
        }
        start = time.monotonic()
        while not self._stop.is_set():
            await self._paused.wait()
            await self.driver.set_outputs(states, self.mapping.bindings)
            p = await self.driver.read_pressure(self.mapping.resolve(LogicalSignal.P_SENSOR))
            t = await self.driver.read_temperature(self.mapping.resolve(LogicalSignal.P_SENSOR))
            self.runtime.currentPressure = p
            self.runtime.currentTemperature = t
            await self.bus.publish("station.pressure", {"pressure": p, "temperature": t}, self.station_id)
            if p <= self.config.floorP:
                return True
            if (time.monotonic() - start) >= timeout_sec:
                return False
            await asyncio.sleep(0.08)
        return False
