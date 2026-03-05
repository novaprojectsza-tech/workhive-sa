"""
WorkHive SA — FastAPI Backend
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import os

from app.models.database import init_db
from app.routers import jobs, sources, alerts
from app.routers.auth import router as auth_router, app_router as applications_router
from app.services.scheduler import run_all_scrapers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

_scheduler_task = None


async def _scheduler_loop():
    while True:
        await asyncio.sleep(6 * 60 * 60)
        log.info("⏰ Scheduled scrape starting...")
        await run_all_scrapers()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task
    await init_db()
    log.info("✅ Database initialised")
    # First scrape on startup
    asyncio.create_task(run_all_scrapers())
    # Schedule every 6h
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    yield
    if _scheduler_task:
        _scheduler_task.cancel()


app = FastAPI(
    title="WorkHive SA API",
    description="South Africa job aggregator API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router,            prefix="/api/v1/jobs",         tags=["Jobs"])
app.include_router(sources.router,         prefix="/api/v1/sources",      tags=["Sources"])
app.include_router(alerts.router,          prefix="/api/v1/alerts",       tags=["Alerts"])
app.include_router(auth_router,            prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(applications_router,    prefix="/api/v1/applications", tags=["Applications"])

# Serve frontend
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "WorkHive SA API", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}
