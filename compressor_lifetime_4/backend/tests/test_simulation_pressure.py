from __future__ import annotations

import asyncio

from app.adapters.simulated import SimulatedDriver
from app.domain.models import Direction, LogicalSignal, ModuleType, PhysicalChannelRef


def test_simulation_pressure_reaches_target_and_obeys_limit() -> None:
    async def scenario() -> None:
        driver = SimulatedDriver()
        driver.set_runtime_limit(2.5)
        sensor = PhysicalChannelRef(device="Dev1", moduleType=ModuleType.AI, channel=0, direction=Direction.IN, invert=False)

        press_states = {
            LogicalSignal.COMPRESSOR: True,
            LogicalSignal.V1: True,
            LogicalSignal.V2: False,
            LogicalSignal.V3: False,
        }
        release_states = {
            LogicalSignal.COMPRESSOR: False,
            LogicalSignal.V1: False,
            LogicalSignal.V2: True,
            LogicalSignal.V3: True,
        }

        pressure = 0.0
        reached = False
        for _ in range(60):
            await driver.set_outputs(press_states, {})
            pressure = await driver.read_pressure(sensor)
            if pressure >= 2.02:
                reached = True
                break
        assert reached, f"simulation pressure should reach target, got={pressure:.3f}"

        for _ in range(60):
            await driver.set_outputs(release_states, {})
            pressure = await driver.read_pressure(sensor)
            if pressure <= 0.05:
                break
        assert pressure <= 0.2, f"simulation pressure should release close to floor, got={pressure:.3f}"

        for _ in range(80):
            await driver.set_outputs(press_states, {})
            pressure = await driver.read_pressure(sensor)
        assert pressure <= 2.5 + 1e-6, f"simulation pressure must not exceed maxP limit, got={pressure:.3f}"

    asyncio.run(scenario())
