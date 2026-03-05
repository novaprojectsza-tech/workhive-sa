"""
WorkHive SA — Single File Backend
Everything in one file to avoid import issues.
"""

import os
import asyncio
import hashlib
import logging
import aiosqlite
import aiohttp
import jwt as pyjwt
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────
DB = os.getenv("DATABASE_URL", "workhive.db")
JWT_SECRET = os.getenv("JWT_SECRET", "workhive2026secretkey")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── DATABASE ──────────────────────────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            company     TEXT DEFAULT 'Unknown',
            location    TEXT DEFAULT 'South Africa',
            province    TEXT,
            is_remote   INTEGER DEFAULT 0,
            category    TEXT,
            job_type    TEXT DEFAULT 'full-time',
            salary_min  REAL,
            salary_max  REAL,
            salary      TEXT,
            description TEXT,
            url         TEXT UNIQUE NOT NULL,
            source      TEXT DEFAULT 'Adzuna',
            source_job_id TEXT,
            fingerprint TEXT UNIQUE,
            is_active   INTEGER DEFAULT 1,
            is_featured INTEGER DEFAULT 0,
            posted_at   TEXT,
            fetched_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT DEFAULT 'user',
            created_at    TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS applications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            job_id     INTEGER NOT NULL,
            job_title  TEXT,
            company    TEXT,
            status     TEXT DEFAULT 'applied',
            notes      TEXT,
            applied_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, job_id)
        );
        CREATE INDEX IF NOT EXISTS ix_jobs_category  ON jobs(category);
        CREATE INDEX IF NOT EXISTS ix_jobs_is_remote ON jobs(is_remote);
        """)
        await db.commit()
    log.info("✅ Database ready")

# ── ADZUNA FETCHER ────────────────────────────────────────────────────────────
CATEGORY_MAP = {
    "it-jobs": "tech", "engineering-jobs": "engineering",
    "accounting-finance-jobs": "finance", "healthcare-nursing-jobs": "healthcare",
    "sales-jobs": "sales", "marketing-jobs": "marketing",
    "education-jobs": "education", "admin-jobs": "admin",
}
SA_PROVINCES = {
    "johannesburg": "Gauteng", "sandton": "Gauteng", "pretoria": "Gauteng",
    "midrand": "Gauteng", "cape town": "Western Cape", "stellenbosch": "Western Cape",
    "durban": "KwaZulu-Natal", "port elizabeth": "Eastern Cape",
}

def detect_province(location):
    loc = location.lower()
    for city, prov in SA_PROVINCES.items():
        if city in loc:
            return prov
    return "Other"

def make_fingerprint(title, company, location):
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()

def parse_job(raw):
    title    = raw.get("title", "").strip()
    company  = raw.get("company", {}).get("display_name", "Unknown")
    location = raw.get("location", {}).get("display_name", "South Africa")
    url      = raw.get("redirect_url", "")
    desc     = raw.get("description", "")
    cat_raw  = raw.get("category", {}).get("tag", "general")
    category = CATEGORY_MAP.get(cat_raw, "general")
    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    salary_text = ""
    if salary_min and salary_max:
        salary_text = f"R{int(salary_min):,} – R{int(salary_max):,}/mo"
    elif salary_min:
        salary_text = f"From R{int(salary_min):,}/mo"
    is_remote = any(kw in (title + desc).lower() for kw in ["remote", "work from home", "wfh"])
    posted_at = raw.get("created", "")
    return {
        "title": title, "company": company, "location": location,
        "province": detect_province(location), "is_remote": is_remote,
        "category": category, "job_type": "full-time",
        "salary_min": salary_min, "salary_max": salary_max, "salary": salary_text,
        "description": desc[:3000], "url": url, "source": "Adzuna",
        "source_job_id": str(raw.get("id", "")),
        "fingerprint": make_fingerprint(title, company, location),
        "posted_at": posted_at,
    }

async def fetch_adzuna(pages=5):
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        log.warning("Adzuna credentials not set")
        return []
    jobs = []
    params = {"app_id": ADZUNA_APP_ID, "app_key": ADZUNA_APP_KEY,
              "results_per_page": 50, "where": "south africa"}
    async with aiohttp.ClientSession() as session:
        for page in range(1, pages + 1):
            try:
                url = f"https://api.adzuna.com/v1/api/jobs/za/search/{page}"
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    for r in results:
                        jobs.append(parse_job(r))
            except Exception as e:
                log.error(f"Adzuna page {page} error: {e}")
                break
    log.info(f"Adzuna fetched {len(jobs)} jobs")
    return jobs

async def save_jobs(jobs):
    async with aiosqlite.connect(DB) as db:
        new = 0
        for j in jobs:
            try:
                await db.execute(
                    """INSERT OR IGNORE INTO jobs
                       (title,company,location,province,is_remote,category,job_type,
                        salary_min,salary_max,salary,description,url,source,source_job_id,fingerprint,posted_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [j["title"], j["company"], j["location"], j["province"],
                     1 if j["is_remote"] else 0, j["category"], j["job_type"],
                     j["salary_min"], j["salary_max"], j["salary"],
                     j["description"], j["url"], j["source"],
                     j["source_job_id"], j["fingerprint"], j["posted_at"]]
                )
                new += 1
            except Exception:
                pass
        await db.commit()
    log.info(f"Saved {new} new jobs to DB")

async def start_scheduler():
    await fetch_and_save()
    while True:
        await asyncio.sleep(6 * 3600)
        await fetch_and_save()

async def fetch_and_save():
    jobs = await fetch_adzuna(pages=5)
    await save_jobs(jobs)

# ── AUTH HELPERS ──────────────────────────────────────────────────────────────
def make_token(user_id, name, email, role):
    exp = datetime.utcnow() + timedelta(days=7)
    return pyjwt.encode(
        {"id": user_id, "name": name, "email": email, "role": role, "exp": exp},
        JWT_SECRET, algorithm="HS256"
    )

def verify_token(request: Request):
    token = request.cookies.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid token")

# ── APP STARTUP ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(start_scheduler())
    yield

app = FastAPI(title="WorkHive SA", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── PYDANTIC MODELS ───────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    name: str; email: str; password: str

class LoginIn(BaseModel):
    email: str; password: str

class AppIn(BaseModel):
    job_id: int; notes: Optional[str] = None

class AppUpdate(BaseModel):
    status: Optional[str] = None; notes: Optional[str] = None

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.post("/api/v1/register")
async def register(body: RegisterIn, response: Response):
    from fastapi.responses import JSONResponse
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        existing = await db.execute_fetchall("SELECT id FROM users WHERE email=?", [body.email])
        if existing:
            raise HTTPException(400, "Email already registered")
        cur = await db.execute(
            "INSERT INTO users (name,email,password_hash) VALUES (?,?,?)",
            [body.name, body.email, pwd_ctx.hash(body.password)]
        )
        await db.commit()
        user_id = cur.lastrowid
    token = make_token(user_id, body.name, body.email, "user")
    from fastapi import Response as R
    resp = JSONResponse({"user": {"id": user_id, "name": body.name, "email": body.email, "role": "user"}})
    resp.set_cookie("token", token, httponly=True, max_age=604800, samesite="lax")
    return resp

@app.post("/api/v1/login")
async def login(body: LoginIn):
    from fastapi.responses import JSONResponse
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall("SELECT * FROM users WHERE email=?", [body.email])
        if not rows or not pwd_ctx.verify(body.password, rows[0]["password_hash"]):
            raise HTTPException(401, "Invalid credentials")
        u = dict(rows[0])
    token = make_token(u["id"], u["name"], u["email"], u["role"])
    resp = JSONResponse({"user": {"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"]}})
    resp.set_cookie("token", token, httponly=True, max_age=604800, samesite="lax")
    return resp

@app.post("/api/v1/logout")
async def logout():
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"success": True})
    resp.delete_cookie("token")
    return resp

@app.get("/api/v1/me")
async def me(request: Request):
    return {"user": verify_token(request)}

# ── JOBS ROUTES ───────────────────────────────────────────────────────────────
@app.get("/api/v1/jobs")
async def list_jobs(
    q: Optional[str] = None, location: Optional[str] = None,
    category: Optional[str] = None, is_remote: Optional[bool] = None,
    page: int = Query(1, ge=1), per_page: int = Query(12, ge=1, le=100)
):
    offset = (page - 1) * per_page
    conditions = ["is_active = 1"]
    params = []
    if q:
        conditions.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if location:
        conditions.append("(location LIKE ? OR (? = 'Remote' AND is_remote = 1))")
        params += [f"%{location}%", location]
    if category and category != "all":
        conditions.append("category = ?")
        params.append(category)
    if is_remote:
        conditions.append("is_remote = 1")
    where = " AND ".join(conditions)
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        total = (await db.execute_fetchall(f"SELECT COUNT(*) as c FROM jobs WHERE {where}", params))[0]["c"]
        rows = await db.execute_fetchall(
            f"""SELECT id,title,company,location,salary,category,job_type,
                       is_remote,is_featured,source,posted_at,fetched_at
                FROM jobs WHERE {where}
                ORDER BY is_featured DESC, fetched_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset]
        )
    jobs = [dict(r) for r in rows]
    for j in jobs:
        j["is_remote"] = bool(j["is_remote"])
        j["is_featured"] = bool(j["is_featured"])
    return {"total": total, "page": page, "per_page": per_page,
            "pages": -(-total // per_page), "jobs": jobs}

@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: int):
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall("SELECT * FROM jobs WHERE id=? AND is_active=1", [job_id])
        if not rows:
            raise HTTPException(404, "Job not found")
        j = dict(rows[0])
        j["is_remote"] = bool(j["is_remote"])
        j["is_featured"] = bool(j["is_featured"])
        return j

# ── APPLICATIONS ROUTES ───────────────────────────────────────────────────────
@app.get("/api/v1/applications")
async def get_applications(request: Request):
    user = verify_token(request)
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT a.*, j.salary, j.location, j.url as job_url
               FROM applications a LEFT JOIN jobs j ON a.job_id=j.id
               WHERE a.user_id=? ORDER BY a.applied_at DESC""",
            [user["id"]]
        )
    return [dict(r) for r in rows]

@app.post("/api/v1/applications", status_code=201)
async def create_application(body: AppIn, request: Request):
    user = verify_token(request)
    async with aiosqlite.connect(DB) as db:
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

@app.patch("/api/v1/applications/{app_id}")
async def update_application(app_id: int, body: AppUpdate, request: Request):
    user = verify_token(request)
    valid = {"applied", "interview", "offer", "rejected", "withdrawn"}
    if body.status and body.status not in valid:
        raise HTTPException(400, "Invalid status")
    async with aiosqlite.connect(DB) as db:
        rows = await db.execute_fetchall(
            "SELECT id FROM applications WHERE id=? AND user_id=?", [app_id, user["id"]]
        )
        if not rows:
            raise HTTPException(404, "Not found")
        await db.execute(
            """UPDATE applications SET status=COALESCE(?,status),
               notes=COALESCE(?,notes), updated_at=datetime('now') WHERE id=?""",
            [body.status, body.notes, app_id]
        )
        await db.commit()
    return {"success": True}

@app.delete("/api/v1/applications/{app_id}")
async def delete_application(app_id: int, request: Request):
    user = verify_token(request)
    async with aiosqlite.connect(DB) as db:
        result = await db.execute(
            "DELETE FROM applications WHERE id=? AND user_id=?", [app_id, user["id"]]
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(404, "Not found")
    return {"success": True}

# ── STATIC FILES ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")
