# task_plan.md — Phases, Goals & Checklists

## Current Phase: 2 — Link (Connectivity Research)

---

## B.L.A.S.T. Phase Checklist

### Phase 0: Initialization ✅
- [x] Create task_plan.md
- [x] Create findings.md
- [x] Create progress.md
- [x] Create gemini.md (Project Constitution)
- [x] Answer 5 Discovery Questions
- [x] Define Data Schema in gemini.md
- [x] Blueprint approved

### Phase 1: Blueprint ✅
- [x] North Star confirmed → scrape last 24h articles, display in dashboard, save articles
- [x] Integrations identified → Ben's Bytes, The AI Rundown (public), Supabase (future)
- [x] Source of Truth → newsletter websites (scraped)
- [x] Delivery Payload → Flask dashboard at localhost, articles via /api/articles
- [x] Behavioral Rules → defined in gemini.md
- [x] Data Schema locked in gemini.md
- [x] Research to complete in Phase 2

### Phase 2: Link (Connectivity)
- [x] Research Ben's Bytes URL structure and archive page
- [x] Research The AI Rundown URL structure and archive page
- [ ] Verify pages are publicly accessible (no auth wall)
- [ ] Identify HTML selectors for title, date, summary, link
- [ ] Log findings in findings.md

### Phase 3: Architect (3-Layer Build)
- [ ] Write SOP: architecture/scraper_sop.md
- [ ] Write SOP: architecture/dashboard_sop.md
- [ ] Build: tools/scrape_bens_bytes.py
- [ ] Build: tools/scrape_ai_rundown.py
- [ ] Build: tools/serve_dashboard.py (Flask server)
- [ ] Build: static/ (HTML/CSS/JS dashboard)
- [ ] Test each tool atomically

### Phase 4: Stylize
- [ ] Dashboard design finalized
- [ ] User feedback collected

### Phase 5: Trigger
- [ ] 24h scheduler configured
- [ ] Maintenance Log in gemini.md updated

---

## Goals
1. Scrape Ben's Bytes and The AI Rundown for last-24h articles
2. Serve a gorgeous, interactive local dashboard
3. Allow article saving with localStorage persistence
4. Run automatically every 24 hours
