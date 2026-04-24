from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.hardware import router as hardware_router
from app.api.routes.io_templates import router as template_router
from app.api.routes.config import router as config_router
from app.api.routes.stations import router as stations_router
from app.api.routes.system import router as system_router
from app.api.ws import router as ws_router
from app.application.station_manager import StationManager
from app.infrastructure.config_store import ConfigStore
from app.infrastructure.event_bus import EventBus

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

bus = EventBus()
store = ConfigStore(CONFIG_DIR)
manager = StationManager(store=store, bus=bus, root_dir=ROOT)
cors_origins = manager.system.get("cors_origins", ["*"])
if isinstance(cors_origins, str):
    cors_origins = [cors_origins]

app = FastAPI(title="Compressor Lifetime Backend", version="4.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(stations_router)
app.include_router(template_router)
app.include_router(hardware_router)
app.include_router(system_router)
app.include_router(config_router)
app.include_router(ws_router)
