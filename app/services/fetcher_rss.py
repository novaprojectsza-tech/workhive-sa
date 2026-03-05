"""RSS scraper — free SA job board feeds, no API key needed."""

import aiohttp, logging
from xml.etree import ElementTree as ET
from app.services.base import BaseScraper, infer_category

log = logging.getLogger(__name__)

RSS_FEEDS = [
    {"name": "careers24",    "url": "https://www.careers24.com/jobs/rss/"},
    {"name": "jobmail",      "url": "https://www.jobmail.co.za/rss/"},
    {"name": "bizcommunity", "url": "https://www.bizcommunity.com/rss/196/16.rss"},
]
DC_NS = "http://purl.org/dc/elements/1.1/"


class RSSJobScraper(BaseScraper):
    source_name = "rss"

    async def fetch_jobs(self) -> list[dict]:
        all_jobs = []
        async with aiohttp.ClientSession(headers={"User-Agent": "WorkHiveSA/1.0"}) as session:
            for feed in RSS_FEEDS:
                try:
                    async with session.get(feed["url"], timeout=aiohttp.ClientTimeout(total=15)) as r:
                        if r.status != 200: continue
                        text = await r.text()
                        items = self._parse(text, feed["name"])
                        all_jobs.extend(items)
                        log.info(f"[rss:{feed['name']}] → {len(items)} jobs")
                except Exception as e:
                    log.warning(f"[rss:{feed['name']}] {e}")
        return all_jobs

    def _parse(self, xml: str, feed_name: str) -> list[dict]:
        jobs = []
        try:
            root = ET.fromstring(xml)
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items:
                def t(tag, ns=""): el = item.find(f"{{{ns}}}{tag}" if ns else tag); return (el.text or "").strip() if el is not None else ""
                title = t("title"); url = t("link") or t("guid")
                if not title or not url: continue
                company = t("creator", DC_NS) or t("author") or "Unknown"
                desc = t("description") or t("summary")
                is_remote = "remote" in title.lower()
                jobs.append({
                    "title": title, "company": company, "location": "South Africa",
                    "salary": None, "description": desc[:1000] if desc else None,
                    "url": url, "source": f"rss_{feed_name}",
                    "category": infer_category(title, is_remote),
                    "job_type": "full-time", "is_remote": is_remote,
                    "posted_at": t("pubDate") or t("published"),
                })
        except ET.ParseError as e:
            log.error(f"[rss:{feed_name}] XML error: {e}")
        return jobs

    def _normalise(self, job: dict) -> dict:
        return job
