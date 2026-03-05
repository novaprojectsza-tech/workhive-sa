from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import aiosqlite
from app.models.database import DATABASE_URL

router = APIRouter(tags=["Jobs"])


@router.get("/jobs")
async def list_jobs(
    q: Optional[str] = None,
    location: Optional[str] = None,
    category: Optional[str] = None,
    job_type: Optional[str] = None,
    is_remote: Optional[bool] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * per_page
    conditions = ["is_active = 1"]
    params: list = []

    if q:
        conditions.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if location:
        conditions.append("(location LIKE ? OR (? = 'Remote' AND is_remote = 1))")
        params += [f"%{location}%", location]
    if category and category != "all":
        conditions.append("category = ?")
        params.append(category)
    if job_type:
        conditions.append("job_type = ?")
        params.append(job_type)
    if is_remote is not None:
        conditions.append("is_remote = ?")
        params.append(1 if is_remote else 0)

    where = " AND ".join(conditions)

    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        total_row = await db.execute_fetchall(f"SELECT COUNT(*) as c FROM jobs WHERE {where}", params)
        total = total_row[0]["c"]
        rows = await db.execute_fetchall(
            f"""SELECT id,title,company,location,salary,category,job_type,
                       is_remote,is_featured,source,posted_at,fetched_at
                FROM jobs WHERE {where}
                ORDER BY is_featured DESC, fetched_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        )

    jobs = [dict(r) for r in rows]
    for j in jobs:
        j["is_remote"] = bool(j["is_remote"])
        j["is_featured"] = bool(j["is_featured"])

    return {"total": total, "page": page, "per_page": per_page,
            "pages": -(-total // per_page), "jobs": jobs}


@router.get("/jobs/meta/categories")
async def job_categories():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT category, COUNT(*) as count FROM jobs WHERE is_active=1 "
            "GROUP BY category ORDER BY count DESC"
        )
    return [dict(r) for r in rows]


@router.get("/jobs/{job_id}")
async def get_job(job_id: int):
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT * FROM jobs WHERE id=? AND is_active=1", [job_id]
        )
        if not rows:
            raise HTTPException(404, "Job not found")
        j = dict(rows[0])
        j["is_remote"] = bool(j["is_remote"])
        j["is_featured"] = bool(j["is_featured"])
        return j


@router.get("/stats")
async def stats():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        total  = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM jobs WHERE is_active=1"))[0]["c"]
        remote = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM jobs WHERE is_active=1 AND is_remote=1"))[0]["c"]
        tech   = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM jobs WHERE is_active=1 AND category='tech'"))[0]["c"]
        last   = (await db.execute_fetchall(
            "SELECT MAX(fetched_at) as t FROM jobs"))[0]["t"]
    return {"total_jobs": total, "remote_jobs": remote, "tech_jobs": tech, "last_updated": last}
