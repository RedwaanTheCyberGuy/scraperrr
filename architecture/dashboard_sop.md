# SOP: Dashboard Server
> Layer 1 — Architecture Document
> Last Updated: 2026-03-10

## Goal
Serve a beautiful, interactive single-page dashboard that displays scraped articles, supports saving, and persists state across page refreshes.

---

## Tool: tools/serve_dashboard.py

### Stack
- **Backend**: Flask (Python)
- **Frontend**: Static HTML/CSS/JS (served from `static/`)
- **Scheduler**: APScheduler (background thread, 24h interval)

### API Endpoints

#### GET /api/articles
- Returns JSON array of all articles from `.tmp/all_articles.json`
- If file missing → triggers scraper run first
- Response: `{ "articles": [...], "last_fetched": "ISO datetime", "count": N }`

#### POST /api/refresh
- Manually triggers scraper run
- Returns updated article list

### Startup Sequence
1. Flask app initializes
2. APScheduler starts with 24h interval job → `run_all_scrapers()`
3. On first start: run scrapers immediately (populate cache)
4. Serve `static/index.html` at `/`

---

## Frontend: static/index.html

### Design Principles
- Dark theme: deep navy/black background (#0a0a0f)
- Cards with subtle glassmorphism borders
- Source badges (colored per source)
- Smooth hover animations
- Mobile responsive

### Features
1. **Article Grid** — cards with title, source badge, date, summary
2. **Save Button** — bookmark icon per card; saved state stored in localStorage
3. **Saved Tab** — filter view showing only saved articles
4. **Source Filter** — toggle between All / Ben's Bites / The Rundown AI
5. **Last Refreshed** timestamp + manual Refresh button
6. **Empty State** — clean message when no articles in last 24h

### Persistence (localStorage)
- Key: `scraperrr_saved_ids` → JSON array of article IDs
- On load: read saved IDs, apply `.saved` state to matching cards
- On save/unsave: update localStorage immediately

### Data Flow
1. Page loads → `fetch('/api/articles')` → render cards
2. User saves article → add ID to localStorage → update UI
3. User refreshes page → saved IDs loaded from localStorage → re-applied to cards
4. Refresh button → `POST /api/refresh` → re-render with new data
