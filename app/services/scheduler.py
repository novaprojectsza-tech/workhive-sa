"""Runs all scrapers and expires old jobs."""

import logging
import aiosqlite
from app.models.database import DATABASE_URL

log = logging.getLogger(__name__)


async def run_all_scrapers():
    from app.scrapers.adzuna import AdzunaScraper
    scrapers = [AdzunaScraper()]

    log.info(f"🔍 Starting scrape run — {len(scrapers)} source(s)...")
    results = []
    for scraper in scrapers:
        result = await scraper.run()
        results.append(result)

    total_new = sum(r["new"] for r in results)
    log.info(f"✅ Scrape complete — {total_new} new jobs stored.")

    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE jobs SET is_active=0 WHERE fetched_at < datetime('now', '-30 days') AND is_active=1"
        )
        await db.commit()

    return results
