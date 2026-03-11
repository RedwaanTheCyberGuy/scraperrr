"""
Vercel serverless entry point.
Exposes the Flask app for Vercel's Python runtime.

NOTE: On Vercel (serverless), the following features are disabled:
- APScheduler (no persistent process to run cron jobs)
- Background scraper threads (functions are short-lived)
- Playwright browser automation (no browser binaries available)
- File-system persistence (.tmp/all_articles.json won't survive between requests)

The dashboard and /api/articles endpoint will work, but articles
must be populated via an external data source (e.g., Supabase)
or by using Vercel Cron Jobs to trigger /api/refresh externally.
"""

import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Import the Flask app — this is what Vercel looks for
from tools.serve_dashboard import app

# Vercel expects the variable to be named `app`
# No need to call app.run() — Vercel handles that
