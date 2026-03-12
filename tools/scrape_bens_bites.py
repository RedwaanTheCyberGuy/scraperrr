"""
Tool: scrape_bens_bites.py
Layer 3 — Deterministic scraper for Ben's Bites newsletter (bensbites.com)
Output: .tmp/bens_bites_raw.json (ScraperRunResult schema)
"""

import json
import os
import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BensBites] %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.bensbites.com"
ARCHIVE_URL = f"{BASE_URL}/archive"

if os.environ.get("VERCEL"):
    TMP_DIR = Path("/tmp")
else:
    TMP_DIR = Path(__file__).parent.parent / ".tmp"

OUTPUT_FILE = TMP_DIR / "bens_bites_raw.json"
MAX_ARTICLES = 20
REQUEST_DELAY = 1.5
MAX_RETRIES = 3
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_with_retry(url: str, retries: int = MAX_RETRIES) -> requests.Response | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp
            log.warning(f"HTTP {resp.status_code} for {url} (attempt {attempt + 1})")
        except requests.RequestException as e:
            log.warning(f"Request error for {url}: {e} (attempt {attempt + 1})")
        if attempt < retries - 1:
            time.sleep(2 ** (attempt + 1))
    return None


def extract_json_ld(soup: BeautifulSoup) -> dict | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") in ("Article", "NewsArticle", "BlogPosting"):
                        return item
            elif data.get("@type") in ("Article", "NewsArticle", "BlogPosting"):
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # Try dateutil as last resort
    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(date_str).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def get_archive_links() -> list[str]:
    log.info(f"Fetching archive: {ARCHIVE_URL}")
    resp = fetch_with_retry(ARCHIVE_URL)
    if not resp:
        log.error("Failed to fetch archive page")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    seen = set()
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/p/" not in href:
            continue
        # Normalize to absolute URL
        if href.startswith("http"):
            url = href.split("?")[0]  # strip query params
        elif href.startswith("/"):
            url = f"{BASE_URL}{href.split('?')[0]}"
        else:
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)
    log.info(f"Found {len(links)} unique post links in archive")
    return links[:MAX_ARTICLES]


def scrape_post(url: str, cutoff: datetime) -> dict | None:
    """Returns Article dict if within cutoff, None if old or error."""
    log.info(f"Scraping post: {url}")
    resp = fetch_with_retry(url)
    if not resp:
        log.error(f"Failed to fetch: {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Primary: JSON-LD
    ld = extract_json_ld(soup)
    if ld:
        date_str = ld.get("datePublished") or ld.get("dateCreated")
        pub_date = parse_date(date_str)
        if not pub_date:
            log.warning(f"Could not parse date from JSON-LD for {url}")
            return None
        if pub_date < cutoff:
            log.info(f"Skipping (too old: {pub_date.date()}): {url}")
            return None
        return {
            "id": str(uuid.uuid4()),
            "title": ld.get("headline", "").strip(),
            "summary": ld.get("description", "").strip() or None,
            "url": ld.get("url") or url,
            "source": "bens_bites",
            "published_at": pub_date.isoformat(),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "tags": [],
            "content": None,
        }

    # Fallback: meta tags
    pub_meta = soup.find("meta", property="article:published_time")
    date_str = pub_meta["content"] if pub_meta else None
    pub_date = parse_date(date_str)
    if not pub_date:
        log.warning(f"No date found for {url}, skipping.")
        return None
    if pub_date < cutoff:
        log.info(f"Skipping (too old: {pub_date.date()}): {url}")
        return None

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else url
    desc_meta = soup.find("meta", attrs={"name": "description"})
    summary = desc_meta["content"].strip() if desc_meta else None

    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "summary": summary,
        "url": url,
        "source": "bens_bites",
        "published_at": pub_date.isoformat(),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "tags": [],
        "content": None,
    }


def run() -> dict:
    TMP_DIR.mkdir(exist_ok=True)
    run_at = datetime.now(timezone.utc)
    cutoff = run_at - timedelta(days=7)
    errors = []
    articles = []

    log.info(f"Starting scrape. Cutoff: {cutoff.isoformat()}")
    links = get_archive_links()

    if not links:
        errors.append("Archive returned no links")
        result = {
            "source": "bens_bites",
            "run_at": run_at.isoformat(),
            "articles_found": 0,
            "articles": [],
            "errors": errors,
        }
        OUTPUT_FILE.write_text(json.dumps(result, indent=2))
        return result

    for url in links:
        time.sleep(REQUEST_DELAY)
        article = scrape_post(url, cutoff)
        if article:
            articles.append(article)

    log.info(f"Scraped {len(articles)} article(s) from Ben's Bites in last 7 days.")
    result = {
        "source": "bens_bites",
        "run_at": run_at.isoformat(),
        "articles_found": len(articles),
        "articles": articles,
        "errors": errors,
    }
    OUTPUT_FILE.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))