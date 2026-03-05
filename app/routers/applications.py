from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import aiosqlite
from app.models.database import DATABASE_URL
from app.routers.auth import get_current_user

router = APIRouter(tags=["Applications"])


class AppIn(BaseModel):
    job_id: int
    notes: Optional[str] = None

class AppUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


VALID_STATUSES = {"applied", "interview", "offer", "rejected", "withdrawn"}


@router.get("/applications")
async def get_applications(request: Request):
    user = get_current_user(request)
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT a.*, j.salary, j.location, j.category, j.url as job_url
               FROM applications a LEFT JOIN jobs j ON a.job_id=j.id
               WHERE a.user_id=? ORDER BY a.applied_at DESC""",
            [user["id"]]
        )
    return [dict(r) for r in rows]


@router.post("/applications", status_code=201)
async def create_application(body: AppIn, request: Request):
    user = get_current_user(request)
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        job_rows = await db.execute_fetchall("SELECT * FROM jobs WHERE id=?", [body.job_id])
        if not job_rows:
            raise HTTPException(404, "Job not found")
        job = dict(job_rows[0])
        try:
            cur = await db.execute(
                "INSERT INTO applications (user_id,job_id,job_title,company,notes) VALUES (?,?,?,?,?)",
                [user["id"], body.job_id, job["title"], job["company"], body.notes]
            )
            await db.commit()
            return {"success": True, "id": cur.lastrowid}
        except Exception:
            raise HTTPException(400, "Already tracking this job")


@router.patch("/applications/{app_id}")
async def update_application(app_id: int, body: AppUpdate, request: Request):
    user = get_current_user(request)
    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Use: {', '.join(VALID_STATUSES)}")
    async with aiosqlite.connect(DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT id FROM applications WHERE id=? AND user_id=?", [app_id, user["id"]]
        )
        if not rows:
            raise HTTPException(404, "Application not found")
        await db.execute(
            """UPDATE applications SET
               status=COALESCE(?,status), notes=COALESCE(?,notes),
               updated_at=datetime('now') WHERE id=?""",
            [body.status, body.notes, app_id]
        )
        await db.commit()
    return {"success": True}


@router.delete("/applications/{app_id}")
async def delete_application(app_id: int, request: Request):
    user = get_current_user(request)
    async with aiosqlite.connect(DATABASE_URL) as db:
        result = await db.execute(
            "DELETE FROM applications WHERE id=? AND user_id=?", [app_id, user["id"]]
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(404, "Not found")
    return {"success": True}
