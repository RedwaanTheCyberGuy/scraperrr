"""
Tool: run_all_scrapers.py
Layer 3 — Orchestrates all scrapers and writes merged output to .tmp/all_articles.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)
TMP_DIR = Path(__file__).parent.parent / ".tmp"
OUTPUT_FILE = TMP_DIR / "all_articles.json"


def run() -> dict:
    TMP_DIR.mkdir(exist_ok=True)
    all_articles = []
    seen_urls = set()
    errors = []

    # Run Ben's Bites scraper
    try:
        from tools.scrape_bens_bites import run as run_bens_bites
        result = run_bens_bites()
        for a in result.get("articles", []):
            if a["url"] not in seen_urls:
                all_articles.append(a)
                seen_urls.add(a["url"])
        errors.extend(result.get("errors", []))
    except Exception as e:
        log.error(f"Ben's Bites scraper failed: {e}")
        errors.append(f"bens_bites: {str(e)}")

    # Run The Rundown AI scraper
    try:
        from tools.scrape_ai_rundown import run as run_ai_rundown
        result = run_ai_rundown()
        for a in result.get("articles", []):
            if a["url"] not in seen_urls:
                all_articles.append(a)
                seen_urls.add(a["url"])
        errors.extend(result.get("errors", []))
    except Exception as e:
        log.error(f"AI Rundown scraper failed: {e}")
        errors.append(f"ai_rundown: {str(e)}")

    # Sort by published_at descending (newest first)
    all_articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    merged = {
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "total_count": len(all_articles),
        "articles": all_articles,
        "errors": errors,
    }
    OUTPUT_FILE.write_text(json.dumps(merged, indent=2))
    log.info(f"All scrapers done. {len(all_articles)} total articles written to {OUTPUT_FILE}")
    return merged


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    result = run()
    print(json.dumps(result, indent=2))
