"""Adzuna scraper — best free API for SA jobs."""

import os
import aiohttp
import logging
from app.scrapers.base import BaseScraper, infer_category

log = logging.getLogger(__name__)

APP_ID  = os.getenv("ADZUNA_APP_ID",  "27f39157")
APP_KEY = os.getenv("ADZUNA_APP_KEY", "99161492f112afc832eb7610d6b9de89")
BASE    = "https://api.adzuna.com/v1/api/jobs/za/search"

QUERIES = [
    ("", "johannesburg"),
    ("", "cape town"),
    ("", "durban"),
    ("remote", "south africa"),
    ("developer engineer", ""),
    ("nurse doctor health", ""),
    ("finance accounting", ""),
    ("sales marketing", ""),
]


class AdzunaScraper(BaseScraper):
    source_name = "adzuna"

    async def fetch_jobs(self) -> list[dict]:
        if not APP_ID or not APP_KEY:
            log.warning("[adzuna] Missing credentials — skipping.")
            return []

        all_jobs = []
        async with aiohttp.ClientSession() as session:
            for what, where in QUERIES:
                params = {"app_id": APP_ID, "app_key": APP_KEY, "results_per_page": 50, "content-type": "application/json"}
                if what:  params["what"]  = what
                if where: params["where"] = where
                try:
                    async with session.get(f"{BASE}/1", params=params, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status != 200:
                            log.warning(f"[adzuna] HTTP {resp.status} for '{what}/{where}'")
                            continue
                        data = await resp.json()
                        results = data.get("results", [])
                        all_jobs.extend(results)
                        log.info(f"[adzuna] '{what or '*'}/{where or 'SA'}' → {len(results)} jobs")
                except Exception as e:
                    log.warning(f"[adzuna] Failed '{what}/{where}': {e}")

        return all_jobs

    def _normalise(self, job: dict) -> dict:
        title    = job.get("title", "").strip()
        company  = job.get("company", {}).get("display_name", "Unknown")
        location = job.get("location", {}).get("display_name", "South Africa")
        is_remote = "remote" in title.lower() or "remote" in location.lower()

        lo, hi = job.get("salary_min"), job.get("salary_max")
        if lo and hi:   salary = f"R{int(lo):,} – R{int(hi):,}/yr"
        elif lo:        salary = f"From R{int(lo):,}/yr"
        else:           salary = None

        ct = job.get("contract_time", "")
        job_type = {"full_time": "full-time", "part_time": "part-time", "contract": "contract"}.get(ct, "full-time")

        return {
            "title":       title,
            "company":     company,
            "location":    location,
            "salary":      salary,
            "description": job.get("description", "")[:1200],
            "url":         job.get("redirect_url", ""),
            "category":    infer_category(title, is_remote=is_remote),
            "job_type":    job_type,
            "is_remote":   is_remote,
            "posted_at":   job.get("created", ""),
        }
