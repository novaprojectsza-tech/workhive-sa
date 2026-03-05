from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import FetchLog
from app.models.database import get_db
from app.models.schemas import FetchLogOut

router = APIRouter()


@router.get("", response_model=list[FetchLogOut])
async def list_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FetchLog).order_by(FetchLog.ran_at.desc()).limit(limit))
    return result.scalars().all()


@router.get("/health")
async def source_health(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FetchLog.source, FetchLog.status, FetchLog.jobs_new, FetchLog.ran_at)
        .order_by(FetchLog.ran_at.desc())
    )
    rows = result.all()
    seen = {}
    for r in rows:
        if r[0] not in seen:
            seen[r[0]] = {"source": r[0], "status": r[1], "jobs_new": r[2], "last_ran": str(r[3])}
    return list(seen.values())
