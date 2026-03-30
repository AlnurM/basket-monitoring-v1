# Phase 1: Infrastructure and Scraping Engines - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy a running Telegram bot on Railway with PostgreSQL, Playwright headless Chromium, user registration (/start, /help, language selection), bilingual support (RU/EN), and all three scraper engines (Arbuz.kz via Playwright, Magnum.kz via Playwright, Kaspi.kz via httpx) producing validated price data (name, current price, original price, availability).

</domain>

<decisions>
## Implementation Decisions

### Scraper Strategy
- **D-01:** Hybrid approach from day 1 — attempt API interception (capture XHR/fetch JSON responses during page.goto) AND have DOM selectors as fallback in the same scrape cycle. If API yields valid price data, use it; otherwise fall back to DOM extraction.
- **D-02:** Selector discovery approach is Claude's discretion — choose multi-selector fallback or hardcoded based on what the actual site HTML looks like during development.
- **D-03:** Kaspi.kz parser choice is Claude's discretion — selectolax (Lexbor) recommended by research but Claude may choose based on actual HTML structure.
- **D-04:** Full anti-bot evasion suite from Phase 1: playwright-stealth plugin + UA rotation + random delays between requests + viewport randomization + cookie persistence + proxy support architecture (even if no proxy is used initially).

### i18n Architecture
- **D-05:** i18n library/approach is Claude's discretion — choose the best fit for aiogram 3 (gettext, JSON dicts, or Fluent).
- **D-06:** Language selection is forced on /start — bot asks user to choose RU or EN before proceeding with any functionality. No default language assumed.

### Error Reporting
- **D-07:** Detailed diagnostic errors to users — when a scrape fails, show technical details: "[Product name] failed: timeout after 30s on arbuz.kz" or "[Product] failed: price selector not found on magnum.kz".
- **D-08:** Silent retries — retry 3 times with exponential backoff silently. Only report the final failure to the user.
- **D-09:** Individual error reporting per item — even if multiple items fail from the same source, list each failed item separately in reports and error messages.

### Deployment Validation
- **D-10:** Full startup validation on boot — verify DB connection, verify Playwright can launch Chromium, verify bot token is valid, log all results. Fail fast (crash) if any check fails. No /health endpoint needed in Phase 1.
- **D-11:** Docker base image choice is Claude's discretion — python:3.12-slim with manual deps or Microsoft's official Playwright image. Research flagged /dev/shm as critical concern.
- **D-12:** Both local and Docker development supported — Docker Compose for full stack (bot + PostgreSQL), but also runnable directly via `python -m bot.main` with local PostgreSQL and local Playwright for faster iteration.

### Claude's Discretion
- Selector discovery approach (D-02)
- Kaspi.kz HTML parser choice (D-03)
- i18n library choice for aiogram 3 (D-05)
- Docker base image selection (D-11)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specification
- `task.md` — Full technical specification including DB schema, scraper pseudocode, URL patterns, bot commands, project structure, Dockerfile, and Railway config

### Research
- `.planning/research/STACK.md` — Validated technology versions and deployment patterns
- `.planning/research/ARCHITECTURE.md` — Component boundaries and build order
- `.planning/research/PITFALLS.md` — Critical pitfalls: Playwright Docker /dev/shm, browser context memory leaks, APScheduler init order, asyncpg pool sizing

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints, key decisions
- `.planning/REQUIREMENTS.md` — Phase 1 requirements: USER-01..04, SCRP-01..10, INFR-01..07

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project

### Established Patterns
- None — patterns will be established in this phase

### Integration Points
- None — this is the foundation phase

</code_context>

<specifics>
## Specific Ideas

- The task.md spec contains detailed DB schema (4 tables), URL regex patterns, scraper pseudocode, project structure, Dockerfile, and railway.toml — these should be followed closely as the implementation baseline.
- Arbuz.kz returns 403 on direct HTTP — Playwright is confirmed necessary.
- Magnum.kz is a Next.js SPA — Playwright is confirmed necessary.
- Kaspi.kz is SSR — httpx fast-path confirmed working.
- APScheduler 3.11.x (not 4.x alpha) per research.
- Research flagged that APScheduler needs PostgreSQL jobstore to survive container restarts.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-infrastructure-and-scraping-engines*
*Context gathered: 2026-03-30*
