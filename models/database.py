"""
Database setup — aiosqlite for async SQLite
"""
import os
import aiosqlite

DATABASE_URL = os.getenv("DATABASE_URL", "workhive.db")


async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL,
                company      TEXT NOT NULL,
                location     TEXT,
                province     TEXT,
                is_remote    INTEGER DEFAULT 0,
                category     TEXT,
                job_type     TEXT DEFAULT 'full-time',
                salary_min   REAL,
                salary_max   REAL,
                salary_text  TEXT,
                description  TEXT,
                url          TEXT NOT NULL UNIQUE,
                source       TEXT,
                source_job_id TEXT,
                fingerprint  TEXT UNIQUE,
                is_active    INTEGER DEFAULT 1,
                is_featured  INTEGER DEFAULT 0,
                posted_at    TEXT,
                fetched_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS job_alerts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL,
                keyword    TEXT,
                location   TEXT,
                is_active  INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scrape_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                source     TEXT,
                status     TEXT,
                jobs_found INTEGER DEFAULT 0,
                jobs_new   INTEGER DEFAULT 0,
                error_msg  TEXT,
                ran_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS ix_jobs_category ON jobs(category)")
        await db.execute("CREATE INDEX IF NOT EXISTS ix_jobs_is_remote ON jobs(is_remote)")
        await db.execute("CREATE INDEX IF NOT EXISTS ix_jobs_source ON jobs(source)")
        await db.commit()


async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        yield db
