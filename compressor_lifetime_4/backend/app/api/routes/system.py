from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pathlib import Path

from app.adapters.ni_daq import NiDaqDriver
from app.adapters.simulated import SimulatedDriver


def get_manager():
    from app.main import manager

    return manager


router = APIRouter(prefix="/api/system", tags=["system"])


class SimulationToggle(BaseModel):
    simulation: bool


class LogDirRequest(BaseModel):
    log_dir: str


@router.get("/config")
def get_config(mgr=Depends(get_manager)):
    return mgr.system


@router.post("/simulation")
def set_simulation(req: SimulationToggle, mgr=Depends(get_manager)):
    mgr.system["simulation"] = req.simulation
    mgr.system["driver"] = "simulation" if req.simulation else "ni"
    mgr.driver = SimulatedDriver() if req.simulation else NiDaqDriver()
    mgr.store.save_system(mgr.system)
    return {"ok": True, "simulation": req.simulation}


@router.post("/log-dir")
def set_log_dir(req: LogDirRequest, mgr=Depends(get_manager)):
    try:
        mgr.set_log_dir(req.log_dir)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "log_dir": mgr.system.get("log_dir")}


@router.post("/pick-log-dir")
def pick_log_dir(mgr=Depends(get_manager)):
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        picked = filedialog.askdirectory(title="Select log save directory")
        root.destroy()
        if not picked:
            return {"ok": False, "cancelled": True}
        normalized = str(Path(picked).resolve())
        mgr.set_log_dir(normalized)
        return {"ok": True, "log_dir": mgr.system.get("log_dir")}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to open folder picker: {exc}") from exc


@router.post("/config/reload")
def reload_config(mgr=Depends(get_manager)):
    mgr.system = mgr.store.load_system()
    return {"ok": True, "system": mgr.system}
