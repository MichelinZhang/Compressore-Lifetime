from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.domain.models import LogicalSignal, StationConfig, StationIoMapping, StationStatus, ValidateMappingRequest


class ToggleIoRequest(BaseModel):
    signal: LogicalSignal
    state: bool


class ForceStatusRequest(BaseModel):
    status: StationStatus


def get_manager():
    from app.main import manager

    return manager


router = APIRouter(prefix="/api/stations", tags=["stations"])


@router.get("")
def list_stations(mgr=Depends(get_manager)):
    return mgr.list_stations()


@router.post("")
def add_station(mgr=Depends(get_manager)):
    return mgr.add_station()


@router.delete("/{station_id}")
def remove_station(station_id: int, mgr=Depends(get_manager)):
    try:
        mgr.remove_station(station_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/{station_id}/io-mapping")
def get_mapping(station_id: int, mgr=Depends(get_manager)):
    try:
        return mgr.get_mapping(station_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{station_id}/config")
def put_config(station_id: int, config: StationConfig, mgr=Depends(get_manager)):
    try:
        return mgr.update_station_config(station_id, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{station_id}/io-mapping")
def put_mapping(station_id: int, mapping: StationIoMapping, mgr=Depends(get_manager)):
    try:
        return mgr.update_mapping(station_id, mapping)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{station_id}/io-mapping/validate")
def validate_mapping(station_id: int, request: ValidateMappingRequest, mgr=Depends(get_manager)):
    return mgr.validate_mapping(station_id, request.mapping)


@router.post("/{station_id}/connect")
async def connect(station_id: int, mgr=Depends(get_manager)):
    try:
        await mgr.connect(station_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{station_id}/disconnect")
async def disconnect(station_id: int, mgr=Depends(get_manager)):
    try:
        await mgr.disconnect(station_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{station_id}/start")
async def start(station_id: int, mgr=Depends(get_manager)):
    try:
        await mgr.start(station_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{station_id}/pause")
async def pause(station_id: int, mgr=Depends(get_manager)):
    try:
        await mgr.pause(station_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{station_id}/resume")
async def resume(station_id: int, mgr=Depends(get_manager)):
    try:
        await mgr.resume(station_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{station_id}/stop")
async def stop(station_id: int, mgr=Depends(get_manager)):
    try:
        await mgr.stop(station_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{station_id}/debug/io-toggle")
async def debug_toggle(station_id: int, req: ToggleIoRequest, mgr=Depends(get_manager)):
    try:
        await mgr.debug_set_output(station_id, req.signal, req.state)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{station_id}/debug/force-status")
async def debug_force_status(station_id: int, req: ForceStatusRequest, mgr=Depends(get_manager)):
    try:
        await mgr.debug_force_status(station_id, req.status)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}
