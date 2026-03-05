"""Base scraper — all source scrapers inherit from this."""

import hashlib
import aiosqlite
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from app.models.database import DATABASE_URL

log = logging.getLogger(__name__)

TECH_KEYWORDS = [
    "developer", "engineer", "devops", "data", "cloud", "software",
    "frontend", "backend", "fullstack", "python", "java", "aws",
    "machine learning", "ml", "ai", "cybersecurity", "network",
    "qa", "scrum", "product manager", "ux", "ui", "designer",
]


def make_hash(title: str, company: str, location: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def infer_category(title: str, is_remote: bool = False) -> str:
    t = title.lower()
    if any(k in t for k in TECH_KEYWORDS):
        return "tech"
    if is_remote:
        return "remote"
    return "general"


class BaseScraper(ABC):
    source_name: str = "unknown"

    @abstractmethod
    async def fetch_jobs(self) -> list[dict]: ...

    async def run(self) -> dict:
        started = datetime.utcnow().isoformat()
        jobs_found = jobs_new = 0
        status = "success"
        error_msg = None

        try:
            raw_jobs = await self.fetch_jobs()
            jobs_found = len(raw_jobs)

            async with aiosqlite.connect(DATABASE_URL) as db:
                before = db.total_changes
                for job in raw_jobs:
                    job = self._normalise(job)
                    h = make_hash(job["title"], job.get("company", ""), job.get("location", ""))
                    try:
                        await db.execute(
                            """
                            INSERT OR IGNORE INTO jobs
                              (hash,title,company,location,salary,description,
                               url,source,category,job_type,is_remote,posted_at)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                            """,
                            [
                                h, job["title"], job.get("company"), job.get("location"),
                                job.get("salary"), job.get("description"), job.get("url"),
                                self.source_name,
                                job.get("category", infer_category(job["title"])),
                                job.get("job_type", "full-time"),
                                1 if job.get("is_remote") else 0,
                                job.get("posted_at"),
                            ],
                        )
                    except Exception as e:
                        log.warning(f"[{self.source_name}] Skipped job: {e}")

                await db.commit()
                jobs_new = db.total_changes - before

        except Exception as e:
            status = "error"
            error_msg = str(e)
            log.error(f"[{self.source_name}] Scrape failed: {e}")

        async with aiosqlite.connect(DATABASE_URL) as db:
            await db.execute(
                "INSERT INTO scrape_log (source,jobs_found,jobs_new,status,error_msg) VALUES (?,?,?,?,?)",
                [self.source_name, jobs_found, jobs_new, status, error_msg],
            )
            await db.commit()

        log.info(f"[{self.source_name}] {jobs_new}/{jobs_found} new jobs saved.")
        return {"source": self.source_name, "found": jobs_found, "new": jobs_new, "status": status}

    def _normalise(self, job: dict) -> dict:
        return job
