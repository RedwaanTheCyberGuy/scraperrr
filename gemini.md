# gemini.md — Project Constitution
> This file is LAW. Only update when: a schema changes, a rule is added, or architecture is modified.

---

## Status
- Phase: 1 → Blueprint APPROVED — Moving to Phase 2: Link
- Last Updated: 2026-03-10

---

## North Star
Scrape the latest articles (last 24h) from Ben's Bytes and The AI Rundown newsletters, display them in a gorgeous interactive dashboard, and allow the user to save articles that persist across page refreshes.

---

## Data Schema

### Article (scraped unit)
```json
{
  "id": "string (uuid4)",
  "title": "string",
  "summary": "string | null",
  "url": "string (canonical article link)",
  "source": "bens_bytes | ai_rundown",
  "published_at": "ISO 8601 datetime string",
  "scraped_at": "ISO 8601 datetime string",
  "tags": ["string"],
  "content": "string | null"
}
```

### Saved State (localStorage / later Supabase)
```json
{
  "saved_article_ids": ["uuid"],
  "last_fetched": "ISO 8601 datetime string"
}
```

### Scraper Run Result
```json
{
  "source": "string",
  "run_at": "ISO 8601 datetime string",
  "articles_found": "integer",
  "articles": ["Article"],
  "errors": ["string"]
}
```

---

## Behavioral Rules
1. Only surface articles published within the last 24 hours. If none, return an empty list — never fabricate or pad.
2. If an article's published_at cannot be parsed, log the error and skip the article — never estimate dates.
3. Retry failed HTTP requests up to 3 times with exponential backoff before marking as error.
4. Never scrape more than 50 articles per source per run.
5. Saved articles persist via browser localStorage (Phase 3). Supabase sync is a future phase.
6. If the user refreshes, all previously saved articles must still be shown.
7. Scrapers run every 24 hours. If no new articles exist, the dashboard shows cached data silently.
8. All intermediate data (raw HTML, scraped JSON) goes to `.tmp/` only.

---

## Architectural Invariants
- All intermediate files → `.tmp/` (ephemeral)
- All secrets → `.env` (never hardcoded)
- No tool built before this schema was confirmed
- Every Tool is atomic and independently testable
- If logic changes, update `architecture/` SOP first, then code

---

## Integrations
| Service | Purpose | Key Ready? |
|---|---|---|
| Ben's Bytes website | Scrape newsletter articles | No key needed (public) |
| The AI Rundown website | Scrape newsletter articles | No key needed (public) |
| Supabase | Persistent article storage | FUTURE PHASE |
| Reddit | Community posts | FUTURE PHASE |

---

## Tech Stack
- **Scraper**: Python 3 (requests + BeautifulSoup4, playwright fallback for JS-heavy pages)
- **Backend**: Python Flask (serves dashboard + exposes `/api/articles` endpoint)
- **Frontend**: Single-page HTML/CSS/JS (vanilla, no framework — keeps it fast and self-contained)
- **Persistence**: Browser localStorage (Phase 3) → Supabase (future)
- **Scheduler**: APScheduler (24h cron inside Flask process)

---

## Maintenance Log
> To be populated in Phase 5 (Trigger).
