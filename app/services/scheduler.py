import asyncio
import logging
from app.services.fetcher_adzuna import fetch_adzuna
from app.models.database import DATABASE_URL
import aiosqlite

logger = logging.getLogger(__name__)

FETCH_INTERVAL_HOURS = 6


async def save_jobs(jobs):
    new_count = 0
    async with aiosqlite.connect(DATABASE_URL) as db:
        for job in jobs:
            try:
                await db.execute(
                    """INSERT OR IGNORE INTO jobs
                       (title,company,location,province,is_remote,category,job_type,
                        salary_min,salary_max,salary,description,url,source,source_job_id,fingerprint,posted_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [job.get("title"), job.get("company"), job.get("location"),
                     job.get("province"), 1 if job.get("is_remote") else 0,
                     job.get("category"), job.get("job_type","full-time"),
                     job.get("salary_min"), job.get("salary_max"), job.get("salary_text"),
                     job.get("description"), job.get("url"), job.get("source"),
                     job.get("source_job_id"), job.get("fingerprint"),
                     str(job.get("posted_at",""))]
                )
                new_count += 1
            except Exception:
                pass
        await db.commit()
    logger.info(f"Saved {new_count} new jobs")


async def run_all_fetchers():
    logger.info("Starting job fetch cycle...")
    try:
        jobs = await fetch_adzuna(pages=5)
        await save_jobs(jobs)
        logger.info(f"Fetch complete: {len(jobs)} jobs fetched")
    except Exception as e:
        logger.error(f"Fetch failed: {e}")


async def start_scheduler():
    await run_all_fetchers()
    while True:
        await asyncio.sleep(FETCH_INTERVAL_HOURS * 3600)
        await run_all_fetchers()
