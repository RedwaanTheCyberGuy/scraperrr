# findings.md — Research, Discoveries & Constraints

---

## 2026-03-10 — Phase 2 Research

### Ben's Bites (bensbites.com)
- **Platform**: Beehiiv (custom domain bensbites.com)
- **Archive URL**: https://www.bensbites.com/archive
- **Post URL pattern**: `https://www.bensbites.com/p/{slug}`
- **Rendering**: Server-side rendered — full HTML returned by requests. No JS execution needed.
- **Key finding**: Each post page embeds **JSON-LD** schema with:
  - `headline` → title
  - `datePublished` → ISO 8601 date
  - `description` → summary
  - `url` → canonical URL
- **Archive scrape strategy**: Fetch /archive, extract all `a[href*="/p/"]` links, deduplicate, fetch each post, parse JSON-LD
- **Date filter**: Compare `datePublished` against `now - 24h`

### The Rundown AI (therundown.ai)
- **Platform**: Beehiiv (confirmed via beehiivusercontent.com references)
- **Archive URL**: https://www.therundown.ai/archive (JS-rendered — returns CSS/JS shell only)
- **Strategy**: Use `playwright` to render archive page and extract post cards
- **Fallback**: Try `therundown.ai/sitemap.xml` for post URLs, then fetch each individually
- **RSS attempts**: /feed → 404, /rss → 404. No public RSS found.

### Constraints
- No authentication required for either source (public newsletters)
- Rate limit: Be respectful — add 1-2s delay between requests
- The Rundown AI requires browser rendering for the archive listing page
- Ben's Bites JSON-LD is the cleanest data source — prefer it over HTML parsing
