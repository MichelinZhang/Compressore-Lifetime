from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter()


@router.websocket("/ws/events")
async def events(websocket: WebSocket):
    from app.main import bus

    await websocket.accept()
    queue = bus.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.model_dump())
    except WebSocketDisconnect:
        bus.unsubscribe(queue)

