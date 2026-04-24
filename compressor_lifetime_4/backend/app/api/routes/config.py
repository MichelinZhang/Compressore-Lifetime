from __future__ import annotations

from fastapi import APIRouter, Depends


def get_manager():
    from app.main import manager

    return manager


router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config(mgr=Depends(get_manager)):
    return mgr.system


@router.post("/reload")
def reload_config(mgr=Depends(get_manager)):
    mgr.system = mgr.store.load_system()
    return {"ok": True, "system": mgr.system}

