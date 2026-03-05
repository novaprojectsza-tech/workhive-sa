"""
WorkHive SA — FastAPI Backend
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models.database import init_db
from app.routers.jobs import router as jobs_router
from app.routers.auth import router as auth_router
from app.routers.applications import router as app_router
from app.services.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("✅ Database initialised")
    asyncio.create_task(start_scheduler())
    yield


app = FastAPI(title="WorkHive SA API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(app_router, prefix="/api/v1")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
async def serve_frontend():
    return FileResponse("static/index.html")
