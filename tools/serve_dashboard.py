"""
Tool: serve_dashboard.py
Layer 3 — Flask server that serves the dashboard and /api/articles endpoint
Runs scrapers on startup and every 24h via APScheduler
"""

import json
import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler

# Ensure project root is in path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

TMP_DIR = ROOT / ".tmp"
ARTICLES_FILE = TMP_DIR / "all_articles.json"
STATIC_DIR = ROOT / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Server] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder=str(STATIC_DIR))
_scraper_lock = threading.Lock()


def run_scrapers():
    with _scraper_lock:
        log.info("Running all scrapers...")
        try:
            from tools.run_all_scrapers import run
            result = run()
            log.info(f"Scrapers complete. {result['total_count']} articles found.")
        except Exception as e:
            log.error(f"Scraper run failed: {e}")


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
    thread = threading.Thread(target=run_scrapers, daemon=True)
    thread.start()
    thread.join(timeout=120)  # Wait up to 2min
    data = load_articles()
    return jsonify(data)


@app.route("/api/status")
def status():
    data = load_articles()
    return jsonify({
        "status": "ok",
        "last_fetched": data.get("last_fetched"),
        "article_count": data.get("total_count", 0),
        "server_time": datetime.now(timezone.utc).isoformat(),
    })


if __name__ == "__main__":
    TMP_DIR.mkdir(exist_ok=True)

    # Run scrapers on startup if no cached data
    if not ARTICLES_FILE.exists():
        log.info("No cached articles found. Running initial scrape...")
        run_scrapers()
    else:
        log.info("Cached articles found. Skipping initial scrape.")

    # Schedule every 24 hours
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scrapers, "interval", hours=24, id="scrape_job")
    scheduler.start()
    log.info("Scheduler started (24h interval).")

    log.info("Starting dashboard at http://localhost:5001")
    try:
        app.run(debug=False, host="0.0.0.0", port=5001, use_reloader=False)
    finally:
        scheduler.shutdown()
