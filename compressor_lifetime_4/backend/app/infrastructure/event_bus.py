from __future__ import annotations

import asyncio
import time
from typing import Set

from app.domain.models import EventEnvelope


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue[EventEnvelope]] = set()

    def subscribe(self) -> asyncio.Queue[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=2000)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[EventEnvelope]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: str, payload: dict, station_id: int | None = None) -> None:
        envelope = EventEnvelope(event=event, stationId=station_id, ts=time.time(), payload=payload)
        dead: list[asyncio.Queue[EventEnvelope]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                dead.append(queue)
        for q in dead:
            self._subscribers.discard(q)

