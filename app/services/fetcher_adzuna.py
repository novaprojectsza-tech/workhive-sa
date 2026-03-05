"""Adzuna scraper — best free API for SA jobs."""

import os
import aiohttp
import logging
from app.services.base import BaseScraper, infer_category

log = logging.getLogger(__name__)

APP_ID  = os.getenv("ADZUNA_APP_ID",  "27f39157")
APP_KEY = os.getenv("ADZUNA_APP_KEY", "99161492f112afc832eb7610d6b9de89")
BASE    = "https://api.adzuna.com/v1/api/jobs/za/search"

QUERIES = [
    ("", "johannesburg"),
    ("", "cape town"),
    ("", "durban"),
    ("", "pretoria"),
    ("remote", "south africa"),
    ("developer engineer", ""),
    ("nurse doctor health", ""),
    ("finance accounting", ""),
    ("sales marketing", ""),
    ("teacher lecturer", ""),
]


class AdzunaScraper(BaseScraper):
    source_name = "adzuna"

    async def fetch_jobs(self) -> list[dict]:
        if not APP_ID or not APP_KEY:
            log.warning("[adzuna] Missing credentials")
            return []

        results = []
        async with aiohttp.ClientSession() as session:
            for what, where in QUERIES:
                params = {"app_id": APP_ID, "app_key": APP_KEY, "results_per_page": 50, "content-type": "application/json"}
                if what:  params["what"] = what
                if where: params["where"] = where
                try:
                    async with session.get(f"{BASE}/1", params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                        if r.status == 200:
                            data = await r.json()
                            jobs = data.get("results", [])
                            results.extend(jobs)
                            log.info(f"[adzuna] '{what or '*'}/{where or 'SA'}' → {len(jobs)} jobs")
                        else:
                            log.warning(f"[adzuna] HTTP {r.status}")
                except Exception as e:
                    log.warning(f"[adzuna] {e}")
        return results

    def _normalise(self, j: dict) -> dict:
        title    = j.get("title", "").strip()
        company  = j.get("company", {}).get("display_name", "Unknown")
        location = j.get("location", {}).get("display_name", "South Africa")
        is_remote = "remote" in title.lower() or "remote" in location.lower()

        lo, hi = j.get("salary_min"), j.get("salary_max")
        if lo and hi:   salary = f"R{int(lo):,} – R{int(hi):,}/yr"
        elif lo:        salary = f"From R{int(lo):,}/yr"
        else:           salary = None

        ct = j.get("contract_time", "")
        job_type = {"full_time": "full-time", "part_time": "part-time", "contract": "contract"}.get(ct, "full-time")

        return {
            "title":       title,
            "company":     company,
            "location":    location,
            "salary":      salary,
            "description": (j.get("description") or "")[:1000],
            "url":         j.get("redirect_url", ""),
            "category":    infer_category(title, is_remote),
            "job_type":    job_type,
            "is_remote":   is_remote,
            "posted_at":   j.get("created", ""),
        }
