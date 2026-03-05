"""Base scraper — all source scrapers inherit from this."""

import hashlib
import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


def make_fingerprint(title: str, company: str, location: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def infer_category(title: str, is_remote: bool = False) -> str:
    t = title.lower()
    if any(k in t for k in ["developer","engineer","devops","software","frontend","backend","fullstack",
                              "python","java","cloud","aws","data scientist","ml engineer","ai ","ux","ui designer",
                              "cybersecurity","network","sysadmin","qa engineer","scrum"]):
        return "tech"
    if any(k in t for k in ["accountant","finance","financial","analyst","auditor","bookkeeper","cfo","tax"]):
        return "finance"
    if any(k in t for k in ["nurse","doctor","pharmacist","physio","healthcare","medical","clinical","radiolog"]):
        return "healthcare"
    if any(k in t for k in ["civil engineer","mechanical","electrical","structural","draughtsman","autocad"]):
        return "engineering"
    if any(k in t for k in ["sales","business development","account executive","sales rep"]):
        return "sales"
    if any(k in t for k in ["marketing","seo","social media","copywriter","brand","digital marketing"]):
        return "marketing"
    if any(k in t for k in ["teacher","lecturer","tutor","educator","curriculum"]):
        return "education"
    if is_remote:
        return "remote"
    return "general"


class BaseScraper(ABC):
    source_name: str = "unknown"

    @abstractmethod
    async def fetch_jobs(self) -> list[dict]:
        ...

    def _normalise(self, job: dict) -> dict:
        return job

    async def run(self) -> dict:
        from app.models.database import AsyncSessionLocal
        from app.models.models import Job, FetchLog

        jobs_found = 0
        jobs_new = 0
        status = "success"
        error_msg = None

        try:
            raw = await self.fetch_jobs()
            jobs_found = len(raw)

            async with AsyncSessionLocal() as db:
                for raw_job in raw:
                    job_data = self._normalise(raw_job)
                    if not job_data.get("url") or not job_data.get("title"):
                        continue

                    fp = make_fingerprint(
                        job_data.get("title", ""),
                        job_data.get("company", ""),
                        job_data.get("location", ""),
                    )
                    job_data["fingerprint"] = fp
                    job_data["source"] = self.source_name

                    # Check duplicate by fingerprint or URL
                    from sqlalchemy import select, or_
                    exists = (await db.execute(
                        select(Job.id).where(or_(Job.fingerprint == fp, Job.url == job_data["url"]))
                    )).scalar_one_or_none()
                    if exists:
                        continue

                    db.add(Job(**{k: v for k, v in job_data.items() if hasattr(Job, k)}))
                    jobs_new += 1

                await db.commit()

        except Exception as e:
            status = "error"
            error_msg = str(e)
            log.error(f"[{self.source_name}] Scrape failed: {e}")

        async with AsyncSessionLocal() as db:
            db.add(FetchLog(source=self.source_name, status=status, jobs_found=jobs_found, jobs_new=jobs_new, error_msg=error_msg))
            await db.commit()

        log.info(f"[{self.source_name}] {jobs_new}/{jobs_found} new jobs saved. Status: {status}")
        return {"source": self.source_name, "found": jobs_found, "new": jobs_new, "status": status}
