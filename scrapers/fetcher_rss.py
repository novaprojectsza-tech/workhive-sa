"""
RSS Feed Fetcher — Careers24, Jobmail, BizCommunity, GovernmentJobs SA
"""
import hashlib, logging, aiohttp, asyncio
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

RSS_SOURCES = [
    {"name": "Careers24",       "url": "https://www.careers24.com/rss/jobs/",             "cat": "general"},
    {"name": "Jobmail",         "url": "https://www.jobmail.co.za/rss/",                  "cat": "general"},
    {"name": "BizCommunity",    "url": "https://www.bizcommunity.com/rss/196/16.rss",     "cat": "marketing"},
    {"name": "GovernmentJobs",  "url": "https://www.governmentjobs.co.za/feed",           "cat": "government"},
]

TECH_KW    = ["developer","engineer","devops","cloud","data","python","react","java","software","sysadmin"]
FINANCE_KW = ["accountant","finance","audit","tax","banking","investment"]
HEALTH_KW  = ["nurse","doctor","pharmacist","clinical","health","medical"]
REMOTE_KW  = ["remote","work from home","wfh","fully remote"]

def guess_category(title: str, desc: str, default: str) -> str:
    text = (title + " " + desc).lower()
    if any(k in text for k in TECH_KW):    return "tech"
    if any(k in text for k in FINANCE_KW): return "finance"
    if any(k in text for k in HEALTH_KW):  return "healthcare"
    return default

def make_fingerprint(title: str, url: str) -> str:
    return hashlib.sha256(f"{title.lower().strip()}|{url.strip()}".encode()).hexdigest()

def parse_item(item: ET.Element, source: str, default_cat: str) -> Dict | None:
    def txt(tag): el = item.find(tag); return (el.text or "").strip() if el is not None else ""
    title = txt("title"); url = txt("link"); desc = txt("description"); pub = txt("pubDate")
    if not title or not url: return None
    posted_at = None
    try: posted_at = parsedate_to_datetime(pub).isoformat()
    except: pass
    return {
        "title": title, "company": source, "location": "South Africa",
        "province": "Other", "is_remote": any(k in (title+desc).lower() for k in REMOTE_KW),
        "category": guess_category(title, desc, default_cat),
        "job_type": "full-time", "salary_min": None, "salary_max": None, "salary_text": "",
        "description": desc[:3000], "url": url, "source": source,
        "source_job_id": url, "fingerprint": make_fingerprint(title, url), "posted_at": posted_at,
    }

async def fetch_rss_source(session, source: Dict) -> List[Dict]:
    jobs = []
    try:
        async with session.get(source["url"], timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200: return []
            root = ET.fromstring(await resp.text())
            channel = root.find("channel")
            items = channel.findall("item") if channel else root.findall(".//item")
            for item in items:
                parsed = parse_item(item, source["name"], source["cat"])
                if parsed: jobs.append(parsed)
            logger.info(f"RSS {source['name']}: {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"RSS {source['name']} error: {e}")
    return jobs

async def fetch_all_rss() -> List[Dict]:
    all_jobs = []
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch_rss_source(session, s) for s in RSS_SOURCES])
        for batch in results: all_jobs.extend(batch)
    logger.info(f"RSS total: {len(all_jobs)} jobs")
    return all_jobs
