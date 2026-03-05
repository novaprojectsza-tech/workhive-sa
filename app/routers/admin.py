from fastapi import APIRouter, HTTPException, Request
import aiosqlite
from app.models.database import DATABASE_URL
from app.routers.auth import verify_token
from app.services.scheduler import run_all_scrapers

router = APIRouter(tags=["Admin"])


def require_admin(request: Request):
    user = verify_token(request)
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin only")
    return user


@router.get("/admin/stats")
async def admin_stats(request: Request):
    require_admin(request)
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        jobs  = (await db.execute_fetchall("SELECT COUNT(*) as c FROM jobs WHERE is_active=1"))[0]["c"]
        users = (await db.execute_fetchall("SELECT COUNT(*) as c FROM users"))[0]["c"]
        apps  = (await db.execute_fetchall("SELECT COUNT(*) as c FROM applications"))[0]["c"]
        logs  = await db.execute_fetchall("SELECT * FROM scrape_log ORDER BY ran_at DESC LIMIT 10")
    return {"jobs": jobs, "users": users, "applications": apps,
            "recent_scrapes": [dict(r) for r in logs]}


@router.get("/admin/users")
async def admin_users(request: Request):
    require_admin(request)
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC"
        )
    return [dict(r) for r in rows]


@router.post("/admin/scrape-now")
async def scrape_now(request: Request):
    require_admin(request)
    results = await run_all_scrapers()
    return {"success": True, "results": results}


@router.patch("/admin/jobs/{job_id}/feature")
async def toggle_feature(job_id: int, request: Request):
    require_admin(request)
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE jobs SET is_featured = CASE WHEN is_featured=1 THEN 0 ELSE 1 END WHERE id=?",
            [job_id]
        )
        await db.commit()
    return {"success": True}
