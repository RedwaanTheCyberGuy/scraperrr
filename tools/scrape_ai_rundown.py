"""
Tool: scrape_ai_rundown.py
Layer 3 — Deterministic scraper for The Rundown AI newsletter (therundown.ai)
Strategy: sitemap.xml first, fallback to Playwright for JS-rendered archive
Output: .tmp/ai_rundown_raw.json (ScraperRunResult schema)
"""

import json
import time
import uuid
import logging
import defusedxml.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AIRundown] %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.therundown.ai"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
ARCHIVE_URL = f"{BASE_URL}/archive"
TMP_DIR = Path(__file__).parent.parent / ".tmp"
OUTPUT_FILE = TMP_DIR / "ai_rundown_raw.json"
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
            log.warning(f"Request error: {e} (attempt {attempt + 1})")
        if attempt < retries - 1:
            time.sleep(2 ** (attempt + 1))
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
    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(date_str).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def get_links_from_sitemap(cutoff: datetime) -> list[str]:
    log.info(f"Trying sitemap: {SITEMAP_URL}")
    resp = fetch_with_retry(SITEMAP_URL)
    if not resp:
        return []

    try:
        root = ET.fromstring(resp.text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []
        for url_el in root.findall(".//sm:url", ns):
            loc = url_el.findtext("sm:loc", namespaces=ns)
            lastmod = url_el.findtext("sm:lastmod", namespaces=ns)
            if not loc:
                continue
            # Only include /p/ post URLs
            if "/p/" not in loc and "/newsletter/" not in loc:
                continue
            if lastmod:
                dt = parse_date(lastmod)
                if dt and dt >= cutoff:
                    urls.append(loc)
            else:
                urls.append(loc)
        log.info(f"Found {len(urls)} recent URLs in sitemap.")
        return urls[:MAX_ARTICLES]
    except ET.ParseError as e:
        log.warning(f"Sitemap parse error: {e}")
        return []


def get_links_from_playwright(cutoff: datetime) -> list[str]:
    log.info("Falling back to Playwright for JS-rendered archive.")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    links = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(ARCHIVE_URL, wait_until="networkidle", timeout=30000)

            # Try common selectors for Beehiiv post cards
            selectors = [
                "a[href*='/p/']",
                "a[href*='/newsletter/']",
                "a[href*='/post/']",
                ".post-card a",
                "article a",
            ]
            for selector in selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        for el in elements:
                            href = el.get_attribute("href")
                            if href:
                                if href.startswith("http"):
                                    links.append(href)
                                elif href.startswith("/"):
                                    links.append(f"{BASE_URL}{href}")
                        if links:
                            log.info(f"Found {len(links)} links via selector '{selector}'")
                            break
                except Exception:
                    continue

            browser.close()
    except Exception as e:
        log.error(f"Playwright failed: {e}")

    return list(set(links))[:MAX_ARTICLES]


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


def scrape_post(url: str, cutoff: datetime) -> dict | None:
    log.info(f"Scraping: {url}")
    resp = fetch_with_retry(url)
    if not resp:
        log.error(f"Failed to fetch: {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try JSON-LD first
    ld = extract_json_ld(soup)
    if ld:
        date_str = ld.get("datePublished") or ld.get("dateCreated")
        pub_date = parse_date(date_str)
        if not pub_date:
            log.warning(f"Could not parse date from JSON-LD: {url}")
            return None
        if pub_date < cutoff:
            log.info(f"Skipping (too old: {pub_date.date()}): {url}")
            return None
        return {
            "id": str(uuid.uuid4()),
            "title": ld.get("headline", "").strip(),
            "summary": ld.get("description", "").strip() or None,
            "url": ld.get("url") or url,
            "source": "ai_rundown",
            "published_at": pub_date.isoformat(),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "tags": [],
            "content": None,
        }

    # Fallback: OG/meta tags
    date_meta = (
        soup.find("meta", property="article:published_time")
        or soup.find("meta", attrs={"name": "date"})
        or soup.find("meta", attrs={"name": "publish_date"})
    )
    date_str = date_meta["content"] if date_meta else None
    pub_date = parse_date(date_str)
    if not pub_date:
        log.warning(f"No parseable date for {url}, skipping.")
        return None
    if pub_date < cutoff:
        log.info(f"Skipping (too old: {pub_date.date()}): {url}")
        return None

    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    title = og_title["content"].strip() if og_title else (soup.find("h1") or {}).get_text("", strip=True) or url
    summary = og_desc["content"].strip() if og_desc else None

    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "summary": summary,
        "url": url,
        "source": "ai_rundown",
        "published_at": pub_date.isoformat(),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "tags": [],
        "content": None,
    }


def run() -> dict:
    TMP_DIR.mkdir(exist_ok=True)
    run_at = datetime.now(timezone.utc)
    cutoff = run_at - timedelta(hours=24)
    errors = []
    articles = []

    log.info(f"Starting scrape. Cutoff: {cutoff.isoformat()}")

    # Get post URLs — sitemap first, Playwright fallback
    links = get_links_from_sitemap(cutoff)
    if not links:
        log.info("Sitemap yielded no links. Trying Playwright.")
        links = get_links_from_playwright(cutoff)

    if not links:
        errors.append("No links found via sitemap or Playwright")
        result = {
            "source": "ai_rundown",
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

    log.info(f"Scraped {len(articles)} article(s) from The Rundown AI in last 24h.")
    result = {
        "source": "ai_rundown",
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
