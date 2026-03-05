"""
Adzuna Fetcher — South Africa jobs
"""
import os, hashlib, logging, aiohttp
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "27f39157")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "99161492f112afc832eb7610d6b9de89")
BASE_URL       = "https://api.adzuna.com/v1/api/jobs/za/search"

CATEGORY_MAP = {
    "it-jobs": "tech", "engineering-jobs": "engineering",
    "accounting-finance-jobs": "finance", "healthcare-nursing-jobs": "healthcare",
    "sales-jobs": "sales", "marketing-jobs": "marketing",
    "education-jobs": "education", "admin-jobs": "admin",
    "legal-jobs": "legal", "trade-construction-jobs": "construction",
}

SA_PROVINCES = {
    "johannesburg": "Gauteng", "sandton": "Gauteng", "pretoria": "Gauteng",
    "midrand": "Gauteng", "cape town": "Western Cape", "stellenbosch": "Western Cape",
    "durban": "KwaZulu-Natal", "port elizabeth": "Eastern Cape",
    "gqeberha": "Eastern Cape", "bloemfontein": "Free State",
}

def detect_province(location: str) -> str:
    loc = location.lower()
    for city, prov in SA_PROVINCES.items():
        if city in loc:
            return prov
    return "Other"

def make_fingerprint(title: str, company: str, location: str) -> str:
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()

def parse_job(raw: Dict[str, Any]) -> Dict[str, Any]:
    title    = raw.get("title", "").strip()
    company  = raw.get("company", {}).get("display_name", "Unknown")
    location = raw.get("location", {}).get("display_name", "South Africa")
    url      = raw.get("redirect_url", "")
    desc     = raw.get("description", "")
    cat_raw  = raw.get("category", {}).get("tag", "general")
    category = CATEGORY_MAP.get(cat_raw, "general")
    sal_min  = raw.get("salary_min")
    sal_max  = raw.get("salary_max")
    sal_text = ""
    if sal_min and sal_max:
        sal_text = f"R{int(sal_min):,} – R{int(sal_max):,}/yr"
    elif sal_min:
        sal_text = f"From R{int(sal_min):,}/yr"
    is_remote = any(kw in (title + desc).lower() for kw in ["remote", "work from home", "wfh"])
    posted_at = None
    try:
        posted_at = datetime.fromisoformat(raw.get("created", "").replace("Z", "+00:00")).isoformat()
    except Exception:
        pass
    return {
        "title": title, "company": company, "location": location,
        "province": detect_province(location), "is_remote": is_remote,
        "category": category, "job_type": "full-time",
        "salary_min": sal_min, "salary_max": sal_max, "salary_text": sal_text,
        "description": desc[:3000], "url": url, "source": "Adzuna",
        "source_job_id": str(raw.get("id", "")),
        "fingerprint": make_fingerprint(title, company, location),
        "posted_at": posted_at,
    }

async def fetch_adzuna(pages: int = 5) -> List[Dict[str, Any]]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.warning("Adzuna credentials not set — skipping.")
        return []
    jobs = []
    params = {
        "app_id": ADZUNA_APP_ID, "app_key": ADZUNA_APP_KEY,
        "results_per_page": 50, "content-type": "application/json",
        "where": "south africa",
    }
    async with aiohttp.ClientSession() as session:
        for page in range(1, pages + 1):
            try:
                async with session.get(f"{BASE_URL}/{page}", params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.error(f"Adzuna page {page}: HTTP {resp.status}")
                        break
                    data = await resp.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    jobs.extend(parse_job(r) for r in results)
                    logger.info(f"Adzuna page {page}: {len(results)} jobs")
            except Exception as e:
                logger.error(f"Adzuna page {page} error: {e}")
                break
    logger.info(f"Adzuna total: {len(jobs)} jobs")
    return jobs
