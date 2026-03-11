# SOP: Newsletter Scraper
> Layer 1 — Architecture Document
> Last Updated: 2026-03-10

## Goal
Scrape articles published in the last 24 hours from Ben's Bites and The Rundown AI. Return a normalized list of Article objects matching the schema in gemini.md.

---

## Tool: tools/scrape_bens_bites.py

### Input
- None (fetches live from bensbites.com)

### Output
- JSON file written to `.tmp/bens_bites_raw.json`
- Shape: `ScraperRunResult` (see gemini.md)

### Logic Flow
1. GET `https://www.bensbites.com/archive` with headers (user-agent spoofing)
2. Parse HTML with BeautifulSoup
3. Extract all `<a href="/p/...">` links → deduplicate → collect up to 20 URLs
4. For each URL (with 1.5s delay + 3x retry with backoff):
   a. GET the post page
   b. Find `<script type="application/ld+json">` tag
   c. Parse JSON-LD: extract `headline`, `datePublished`, `description`, `url`
   d. Parse `datePublished` → datetime
   e. If `now - datePublished < 24h` → include in results
   f. Otherwise → stop iterating (archive is chronological, newest first)
5. Build Article objects with uuid4 IDs
6. Write to `.tmp/bens_bites_raw.json`
7. Return ScraperRunResult

### Error Handling
- If JSON-LD is missing → try `<meta property="article:published_time">` as fallback
- If date cannot be parsed → log error, skip article (NEVER estimate)
- If HTTP status != 200 → retry 3x with 2s, 4s, 8s backoff
- If archive page fails → return empty result with error logged

---

## Tool: tools/scrape_ai_rundown.py

### Input
- None (fetches live from therundown.ai)

### Output
- JSON file written to `.tmp/ai_rundown_raw.json`
- Shape: `ScraperRunResult` (see gemini.md)

### Logic Flow
1. Try sitemap approach first: GET `https://www.therundown.ai/sitemap.xml`
2. If sitemap available → parse post URLs, sort by recency, fetch last 10
3. If sitemap fails → use Playwright to render archive page:
   a. Launch headless Chromium
   b. Navigate to `https://www.therundown.ai/archive`
   c. Wait for post cards to render (wait for `.post-card` or similar)
   d. Extract title, date, URL from rendered DOM
4. For each post URL → GET page, parse JSON-LD or meta tags
5. Filter to last 24h, build Article objects
6. Write to `.tmp/ai_rundown_raw.json`

### Error Handling
- If Playwright fails → log error, return empty result
- Same retry/date-parse rules as Ben's Bites scraper

---

## Tool: tools/run_all_scrapers.py

### Logic
1. Run `scrape_bens_bites.py` → load results
2. Run `scrape_ai_rundown.py` → load results
3. Merge articles, deduplicate by URL
4. Write merged output to `.tmp/all_articles.json`
5. Return total count

---

## Scheduling
- APScheduler runs `run_all_scrapers.py` every 24 hours inside Flask process
- Results are cached in `.tmp/all_articles.json` and served via `/api/articles`
- On first Flask startup → run scrapers immediately
