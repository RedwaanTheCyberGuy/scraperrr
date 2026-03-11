"""
Tool: serve_dashboard.py
Layer 3 — Flask server that serves the dashboard and /api/articles endpoint

When running locally: runs scrapers on startup + every 24h via APScheduler.
When on Vercel (serverless): serves dashboard + API only (no scheduler, no auto-scrape).
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

# Ensure project root is in path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

TMP_DIR = ROOT / ".tmp"
ARTICLES_FILE = TMP_DIR / "all_articles.json"
STATIC_DIR = ROOT / "static"

# Detect serverless environment
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Server] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder=str(STATIC_DIR))
_scraper_lock = threading.Lock()


def run_scrapers():
    """Run all scrapers. Skipped automatically in serverless environments."""
    if IS_SERVERLESS:
        log.warning("Scraper run skipped — serverless environment detected.")
        return {"total_count": 0, "skipped": True}

    with _scraper_lock:
        log.info("Running all scrapers...")
        try:
            from tools.run_all_scrapers import run
            result = run()
            log.info(f"Scrapers complete. {result['total_count']} articles found.")
            return result
        except Exception as e:
            log.error(f"Scraper run failed: {e}")
            return {"total_count": 0, "error": str(e)}


def load_articles() -> dict:
    if not ARTICLES_FILE.exists():
        return {"last_fetched": None, "total_count": 0, "articles": [], "errors": []}
    try:
        return json.loads(ARTICLES_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Failed to load articles file: {e}")
        return {"last_fetched": None, "total_count": 0, "articles": [], "errors": [str(e)]}


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/articles")
def get_articles():
    data = load_articles()
    return jsonify(data)


@app.route("/api/refresh", methods=["POST"])
def refresh():
    if IS_SERVERLESS:
        return jsonify({
            "error": "Scraping is not available in serverless mode. "
                     "Use an external scheduler or Vercel Cron Jobs."
        }), 503

    thread = threading.Thread(target=run_scrapers, daemon=True)
    thread.start()
    thread.join(timeout=120)
    data = load_articles()
    return jsonify(data)


@app.route("/api/status")
def status():
    data = load_articles()
    return jsonify({
        "status": "ok",
        "environment": "serverless" if IS_SERVERLESS else "local",
        "last_fetched": data.get("last_fetched"),
        "article_count": data.get("total_count", 0),
        "server_time": datetime.now(timezone.utc).isoformat(),
    })


# --- Local-only startup logic ---
if __name__ == "__main__":
    TMP_DIR.mkdir(exist_ok=True)

    if not ARTICLES_FILE.exists():
        log.info("No cached articles found. Running initial scrape...")
        run_scrapers()
    else:
        log.info("Cached articles found. Skipping initial scrape.")

    # APScheduler only runs locally
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scrapers, "interval", hours=24, id="scrape_job")
    scheduler.start()
    log.info("Scheduler started (24h interval).")

    log.info("Starting dashboard at http://localhost:5001")
    try:
        app.run(debug=False, host="0.0.0.0", port=5001, use_reloader=False)
    finally:
        scheduler.shutdown()
