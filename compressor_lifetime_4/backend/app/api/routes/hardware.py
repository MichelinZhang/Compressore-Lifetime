from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query


def get_manager():
    from app.main import manager

    return manager


router = APIRouter(prefix="/api/hardware", tags=["hardware"])


@router.get("/capabilities")
async def capabilities(device: str = Query(default="Dev1"), mgr=Depends(get_manager)):
    try:
        return await mgr.driver.get_capabilities(device)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

