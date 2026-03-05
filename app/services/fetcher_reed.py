"""Reed.co.uk scraper — free API key from reed.co.uk/developers/jobseeker"""

import os, base64, aiohttp, logging
from app.services.base import BaseScraper, infer_category

log = logging.getLogger(__name__)
REED_API_KEY = os.getenv("REED_API_KEY", "")
BASE = "https://www.reed.co.uk/api/1.0/search"
QUERIES = [
    {"keywords": "remote south africa"},
    {"keywords": "developer south africa"},
    {"keywords": "finance south africa"},
    {"keywords": "marketing south africa"},
]


class ReedScraper(BaseScraper):
    source_name = "reed"

    async def fetch_jobs(self) -> list[dict]:
        if not REED_API_KEY:
            log.warning("[reed] No REED_API_KEY — skipping")
            return []
        token = base64.b64encode(f"{REED_API_KEY}:".encode()).decode()
        headers = {"Authorization": f"Basic {token}"}
        results = []
        async with aiohttp.ClientSession(headers=headers) as session:
            for q in QUERIES:
                try:
                    async with session.get(BASE, params={**q, "resultsToTake": 100}, timeout=aiohttp.ClientTimeout(total=15)) as r:
                        if r.status == 200:
                            data = await r.json()
                            results.extend(data.get("results", []))
                except Exception as e:
                    log.warning(f"[reed] {e}")
        return results

    def _normalise(self, j: dict) -> dict:
        title    = j.get("jobTitle", "").strip()
        company  = j.get("employerName", "Unknown")
        location = j.get("locationName", "South Africa")
        is_remote = "remote" in location.lower() or "remote" in title.lower()
        lo, hi = j.get("minimumSalary"), j.get("maximumSalary")
        salary = (f"R{int(lo):,} – R{int(hi):,}/yr" if lo and hi else f"From R{int(lo):,}/yr" if lo else None)
        return {
            "title": title, "company": company, "location": location,
            "salary": salary, "description": (j.get("jobDescription") or "")[:1000],
            "url": j.get("jobUrl", ""), "category": infer_category(title, is_remote),
            "job_type": "part-time" if j.get("partTime") else "full-time",
            "is_remote": is_remote, "posted_at": j.get("date", ""),
        }
