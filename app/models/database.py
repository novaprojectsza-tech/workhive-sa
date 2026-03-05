import os
import aiosqlite

DATABASE_URL = os.getenv("DATABASE_URL", "workhive.db")

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL DEFAULT 'Unknown',
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
    source      TEXT,
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
    user_id    TEXT NOT NULL,
    job_id     TEXT NOT NULL,
    job_title  TEXT,
    company    TEXT,
    status     TEXT DEFAULT 'applied',
    notes      TEXT,
    applied_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, job_id)
);

CREATE TABLE IF NOT EXISTS fetch_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT,
    status     TEXT,
    jobs_found INTEGER DEFAULT 0,
    jobs_new   INTEGER DEFAULT 0,
    error_msg  TEXT,
    ran_at     TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_jobs_category  ON jobs(category);
CREATE INDEX IF NOT EXISTS ix_jobs_is_remote ON jobs(is_remote);
"""


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()


async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        yield db
