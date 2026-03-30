# Project Research Summary

**Project:** price-spy — Grocery Price Tracker Bot
**Domain:** Telegram bot with web scraping, scheduling, and analytics (Almaty, Kazakhstan)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

price-spy is a Telegram bot that tracks grocery prices across Almaty e-commerce stores (Arbuz.kz, Magnum.kz, Kaspi.kz), organizes tracked products into named baskets, and delivers daily price reports with trend charts and cross-store comparisons. No existing Telegram bot serves this market, and the combination of basket-level cross-store comparison, visual price history charts, and bilingual (RU/EN) delivery in a Telegram interface is genuinely unique. The recommended approach is a layered async Python architecture: aiogram 3 for the bot layer, Playwright for the two JS-rendered stores (Arbuz, Magnum) and httpx for the SSR store (Kaspi), PostgreSQL for price history, APScheduler for daily scraping and report delivery, and Railway for single-process hosting.

The critical recommendation is to treat infrastructure correctness as the first deliverable, not an afterthought. Three of the seven critical pitfalls identified apply to Phase 1 alone: Playwright/Chromium must be configured with specific Docker flags and version pins before any scraping logic is written; the database connection pool must be sized against Railway's connection limit before handler code exists; and APScheduler must be initialized inside the aiogram startup hook, not at module import time. Getting these wrong causes silent failures that are hard to diagnose once the codebase grows. Building in this order — infrastructure, scraper engines, bot skeleton, basket management, scheduling, analytics/reports, and then polish — follows the natural dependency graph and prevents costly rewrites.

The main ongoing risk is anti-bot detection escalation. Both Arbuz.kz and Magnum.kz are SPAs that block direct HTTP, and playwright-stealth patches the most common detection vectors but is not Cloudflare-grade. The recommended mitigation is to prefer intercepting the internal XHR/fetch API calls that load product data (JSON API interception) over DOM selector scraping, which is both more stable and less detectable. If a store's IP reputation deteriorates on Railway's shared infrastructure, the stealth approach degrades gradually rather than breaking suddenly. All scraped data must be validated before storage (price > 0, name non-empty) to prevent silent data corruption from going undetected.

## Key Findings

### Recommended Stack

The stack is pre-validated in PROJECT.md and confirmed by research. Python 3.12 (not 3.13) is required for C-extension wheel coverage with matplotlib and selectolax. The Playwright Docker image version must exactly match the pinned Python package version — use `mcr.microsoft.com/playwright/python:v1.50.0-noble` and `playwright==1.50.0`; any mismatch causes "browser executable not found" on Railway. APScheduler 3.11 is the correct version; 4.x has been in alpha since 2023 and has an unstable API. The asyncpg + SQLAlchemy 2.0 pairing requires keeping both current together (asyncpg 0.31.0 + SQLAlchemy 2.0.48). The uv package manager replaces pip and pip-tools for this project.

**Core technologies:**
- aiogram 3.26: Telegram bot framework — async-native, superior middleware/router architecture vs python-telegram-bot
- Playwright 1.50 + playwright-stealth 1.0.6: Browser automation for Arbuz/Magnum SPAs — both block direct HTTP; stealth patches navigator.webdriver and UA
- httpx 0.28 + selectolax 0.4.7: Async HTTP + fast HTML parsing for Kaspi.kz — SSR site, no JS needed; selectolax 20x faster than BeautifulSoup
- PostgreSQL 16 + SQLAlchemy 2.0 + asyncpg 0.31: Database layer — Railway managed PG, async ORM, 5x faster driver
- Alembic 1.18: Schema migrations — essential from Phase 1; never use raw CREATE TABLE
- APScheduler 3.11: Scheduling — daily scraping at 07:00 Asia/Almaty + per-user report delivery
- matplotlib 3.10: Chart generation — PNG charts sent as Telegram photos; run in `asyncio.to_thread()` to avoid blocking
- pydantic 2.12 + pydantic-settings 2.13: Validation and config — type-safe scraping results, Railway env vars
- Docker (mcr.microsoft.com/playwright/python base): Container for Railway — Chromium requires system deps; base image ships them

### Expected Features

**Must have (table stakes — v1):**
- User registration with RU/EN language selection — identity prerequisite for all features
- Basket CRUD (create with store type, list, delete, switch active) — organizational foundation
- Add products by URL with validation — core input mechanism; URL must be validated to correct domain and product page
- Scraper infrastructure (Playwright for Arbuz/Magnum, httpx for Kaspi) — data acquisition engine
- Price history storage (original price, discount price, availability) — required by all analytics
- Daily automated scraping at 07:00 Asia/Almaty — keeps data fresh
- Daily price report at user-configurable time — the core engagement loop
- Price change tracking (was/became) — users need visibility into what moved
- Inline button navigation — Telegram UX standard

**Should have (competitive differentiators — v1.x after validation):**
- Price drop alerts at >10% threshold — high perceived value, low implementation cost
- Cross-store comparison (Arbuz vs Magnum basket totals + per-item where overlap exists) — the primary market differentiator; no other KZ Telegram bot does this
- Price trend charts via matplotlib — visual history is rare in Telegram bots
- CSV export of price history — power users; UTF-8 with BOM for Excel + Cyrillic compatibility
- Manual scrape trigger with per-user rate limiting (1/hour) — user agency
- Configurable notification time — personalizes the experience

**Defer (v2+):**
- Scraper optimizations (API interception, browser reuse, parallelism enhancements) — optimize when load matters
- Product name caching after first scrape — performance optimization; defer until item count is meaningful
- Additional stores beyond Arbuz/Magnum/Kaspi — architecture supports it via strategy pattern; commit only when current stores are stable and users request specific additions
- Shared basket export/sharing — only if collaborative use cases emerge

**Anti-features to explicitly reject:**
- Product search by name without URL — scope explosion; require URL input
- Real-time price monitoring (multiple times daily) — unnecessary for groceries, risks rate limiting
- Barcode/QR scanning — requires different architecture; not a Telegram interaction pattern
- Price prediction / AI recommendations — overpromise risk; 90 days of single-city data is insufficient

### Architecture Approach

The project follows a four-layer architecture: Presentation (aiogram routers, keyboards, i18n middleware), Service (basket, scraper, analytics, report services), Scraper Engines (strategy pattern — one class per store implementing `BaseScraper.scrape(url) -> PriceResult`), and Infrastructure (PostgreSQL via asyncpg, APScheduler, Playwright BrowserManager). The key structural discipline is strict layer separation: handlers call services, services call repositories, no layer skips. The BrowserManager is a singleton that starts Playwright once at application boot; scrapers request fresh browser contexts from it per batch (never reuse contexts indefinitely — this is a documented memory leak). The project structure separates `bot/` (Telegram-specific), `services/` (business logic), `scrapers/` (store engines), `db/` (models + repositories), `i18n/` (RU/EN strings), and `utils/` (URL parsing, chart helpers).

**Major components:**
1. Bot Handlers (aiogram Routers) — process Telegram commands/callbacks, dispatch to services; one router per feature domain
2. BrowserManager — singleton managing Playwright browser lifecycle; scrapers get contexts via async context manager
3. Scraper Engines (ArbuzScraper, MagnumScraper, KaspiScraper) — strategy pattern; each implements `BaseScraper`; ScraperService dispatches by URL domain
4. Service Layer (BasketService, ScraperService, AnalyticsService, ReportService) — business logic decoupled from Telegram; testable independently
5. Repository Layer (UserRepo, BasketRepo, ProductRepo, PriceRepo) — owns all DB queries; services never import SQLAlchemy directly
6. APScheduler AsyncIOScheduler — cron jobs for 07:00 scrape and per-user report delivery; initialized in aiogram `on_startup` hook
7. i18n Layer — dictionary-based RU/EN translation; cross-cutting concern wired via aiogram middleware

### Critical Pitfalls

1. **Playwright Chromium OOM on Railway** — Use the official Playwright Docker base image (`mcr.microsoft.com/playwright/python:v1.50.0-noble`); launch with `--no-sandbox`, `--disable-gpu`, `--disable-dev-shm-usage`, `--single-process`; pin Playwright version to match Docker image exactly. Address in Phase 1 before writing any scraping logic.

2. **Browser context memory leak** — Never reuse a browser context across multiple scraping sessions. Create a fresh `BrowserContext` per store per batch; close it in `try/finally`. Recycle the `Browser` instance itself every 24 hours or every 100 pages. Address in Phase 2 when building BrowserManager.

3. **APScheduler silently dying after Railway restart** — Use `SQLAlchemyJobStore` backed by PostgreSQL (or reconstruct jobs from user settings on startup). Set `misfire_grace_time=900` and `coalesce=True` on cron triggers. Initialize `AsyncIOScheduler` inside the aiogram `on_startup` hook — never at module import time. Address in Phase 1 (bot setup) and Phase 3 (scheduling).

4. **Anti-bot detection escalation** — Use playwright-stealth as baseline. Prefer XHR/fetch API interception over DOM selector scraping (JSON schema changes less frequently than CSS class names). Add realistic delays (2-5 seconds with jitter). Validate scraped data before storage; alert admin when >20% of products in a basket fail. Address in Phase 2.

5. **asyncpg connection pool exhaustion** — Configure explicitly: `pool_size=5`, `max_overflow=5`, `pool_timeout=30`, `pool_recycle=1800`. Use a semaphore to limit concurrent scraping to 3-5 pages, matching pool capacity. Use `pool_pre_ping=True` to handle Railway PostgreSQL restarts. Address in Phase 1 (database setup).

6. **Telegram flood control banning the bot** — Stagger report delivery (1-second delay per user). Catch `TelegramRetryAfter` exceptions and sleep for `retry_after` seconds. Send text + chart as a single `send_photo` with caption rather than separate messages. Address in Phase 4 (notifications).

7. **Storing prices as floats** — Store prices as integer tenge (Kazakhstan does not use tiyn for grocery pricing). Float comparison bugs in price change detection are subtle and persistent. This is a schema decision; fix it in Phase 1 before any data is stored.

## Implications for Roadmap

Based on research, the dependency graph from ARCHITECTURE.md dictates a clear build order. Infrastructure must precede scraping, scraping must precede scheduling, and scheduling must precede analytics. Bilingual support is cross-cutting and must be architected in from Phase 1, not bolted on later.

### Phase 1: Infrastructure and Bot Foundation

**Rationale:** Three critical pitfalls (Playwright OOM, connection pool exhaustion, APScheduler initialization order) must be resolved before any feature code is written. This phase produces a working, deployed bot skeleton that proves Railway + Playwright + PostgreSQL work together correctly.
**Delivers:** Docker image running on Railway with Playwright smoke test passing; PostgreSQL with Alembic migrations; bot responding to `/start` with user registration and language selection; DB session middleware; correct APScheduler initialization hook.
**Addresses:** User registration (table stakes), bilingual architecture foundation, inline button navigation
**Avoids:** Chromium OOM (Dockerfile flags + version pins), connection pool exhaustion (pool config), APScheduler initialization bug, float price storage (integer tenge schema from day 1)

### Phase 2: Scraping Engines

**Rationale:** Scraping is the most technically risky component and depends only on Phase 1 infrastructure. It must be validated early, before features that depend on scraped data are built. Anti-bot detection is an ongoing risk that needs its mitigation strategy established now.
**Delivers:** Working ArbuzScraper (Playwright + stealth + API interception preference), MagnumScraper (Playwright + stealth), KaspiScraper (httpx + selectolax); BrowserManager with context-per-batch lifecycle; scrape result validation (price > 0, name non-empty, 50% sanity check against previous price); ScraperService dispatching by URL domain.
**Uses:** Playwright 1.50, playwright-stealth, httpx 0.28, selectolax 0.4.7 (Lexbor backend), pydantic PriceResult model
**Implements:** Strategy pattern (BaseScraper + per-store engines), BrowserManager singleton, concurrent scraping semaphore (3-5 pages)
**Avoids:** Browser memory leak (context recycling), anti-bot detection (stealth + API interception + jitter delays), selector breakage going undetected (validation before storage)

### Phase 3: Basket Management and Product Tracking

**Rationale:** Basket and product CRUD are the user-facing foundation of the value loop. They depend on Phase 1 (DB, bot skeleton) and Phase 2 (scraping for first-scrape on product add). This phase closes the loop: user can create a basket, add a product URL, and see a scraped price.
**Delivers:** Basket CRUD (create with store type, list, delete, switch active); add product by URL (validation + first scrape on add); remove/edit products; quantity tracking per item; basket item list with current prices; FSM states for multi-step flows.
**Addresses:** Basket management, add by URL, view tracked items, remove/edit items, original vs discount price display, availability status (all table stakes)
**Avoids:** SSRF from unvalidated URLs (domain allowlist: arbuz.kz, magnum.kz, kaspi.kz only), unlimited baskets (enforce 10 baskets, 50 items at DB constraint level), accidental basket deletion (inline confirmation button)

### Phase 4: Scheduling and Daily Reports

**Rationale:** Daily reports are the core engagement loop — the reason users keep the bot. They depend on Phase 2 (scrapers), Phase 3 (baskets with products), and correctly initialized APScheduler. This phase completes the minimum viable product.
**Delivers:** Daily automated scraping at 07:00 Asia/Almaty (not UTC); per-user configurable report delivery time; daily report with basket total, per-item prices, notable changes; job persistence via PostgreSQL jobstore or startup reconstruction; `/status` command reporting last scrape time.
**Uses:** APScheduler 3.11 AsyncIOScheduler, `misfire_grace_time=900`, `coalesce=True`, Asia/Almaty timezone explicit in all cron triggers
**Implements:** Scheduler service, job registration on startup, report formatting (ReportService)
**Avoids:** Scheduler silent death (PostgreSQL jobstore + misfire config), Telegram flood control (stagger delivery, `TelegramRetryAfter` handling), UTC vs Asia/Almaty timezone confusion

### Phase 5: Analytics, Alerts, and Differentiating Features

**Rationale:** With reliable data collection and daily reports established, this phase adds the competitive differentiators. Cross-store comparison, price charts, and CSV export are the features that distinguish price-spy from any existing tool. They depend on at least a few days of price history (minimum 2 data points for trends).
**Delivers:** Price drop alerts (>10% threshold); cross-store basket comparison (Arbuz vs Magnum totals + per-item where overlap); price trend charts via matplotlib (PNG sent as Telegram photo, generated in `asyncio.to_thread()`); CSV export (UTF-8 with BOM for Cyrillic/Excel); manual scrape trigger (rate-limited 1/hour per user).
**Addresses:** All v1.x (P2) features from FEATURES.md
**Avoids:** matplotlib blocking the event loop (`asyncio.to_thread()`), Cyrillic encoding in CSV (UTF-8 BOM), misleading comparisons without noting different package sizes

### Phase 6: Polish and Hardening

**Rationale:** After the core value loop is running and validated with real users, this phase addresses UX quality, observability, and resilience. These are not launch blockers but significantly affect retention.
**Delivers:** URL normalization (strip tracking params, handle mobile subdomains); user-facing error messages fully translated (no English technical errors surfaced to RU users); feedback during long scrapes ("Checking prices..." with edit on completion); paginated reports for large baskets; admin monitoring (scrape failure rate alerts, dead-man's switch if no scrape in 25 hours); lazy-import matplotlib (reduce cold start from 2-3 seconds).
**Addresses:** All UX pitfalls from PITFALLS.md, "looks done but isn't" checklist items

### Phase Ordering Rationale

- Infrastructure before scraping: Three of seven critical pitfalls must be addressed before any scraping code runs. Getting Docker, pool config, and scheduler initialization wrong causes silent failures that are hard to diagnose in a running system.
- Scraping before basket management: The first-scrape-on-add flow (Phase 3) requires working scrapers. Testing basket management with mock scrapers is possible but delays validating the highest-risk component.
- Basket management before scheduling: Scheduling requires products in baskets to scrape. The daily scrape job is meaningless without user data.
- Scheduling before analytics: Analytics requires multiple days of price history. The scheduling infrastructure must run in production before analytics can be meaningfully tested.
- Analytics/differentiators after core loop: Cross-store comparison and charts are compelling but not the baseline. Users need reliable daily reports before they will care about trends. Validate the core loop first.
- Bilingual support is cross-cutting from Phase 1: Every user-facing string needs RU and EN versions. This is an architectural decision (middleware + i18n module structure) that cannot be retrofitted without touching every handler.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Scraping Engines):** Arbuz.kz and Magnum.kz DOM structures and internal API endpoints are not documented. Research phase needed to identify actual CSS selectors or XHR endpoints before implementation. Anti-bot detection specifics (Cloudflare vs DataDome vs custom WAF) unknown until live testing.
- **Phase 5 (Cross-store comparison):** Product matching across Arbuz and Magnum is the hardest algorithmic problem in the project. Products have different names, different package sizes, and no common identifier. Research needed for matching heuristics (name similarity, unit normalization) before implementation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Well-documented Playwright + Railway + PostgreSQL patterns. STACK.md and PITFALLS.md provide all necessary configuration details.
- **Phase 3 (Basket Management):** Standard CRUD with aiogram FSM patterns. Well-documented in aiogram 3 docs. No novel problems.
- **Phase 4 (Scheduling):** APScheduler + aiogram integration patterns are well-documented. PITFALLS.md covers the initialization gotcha in detail.
- **Phase 6 (Polish):** UX improvements with known solutions. No novel technical problems.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions confirmed on PyPI as of 2026-03-30. Critical compatibility notes (Playwright/Docker pin, asyncpg/SQLAlchemy version lock) are verified. |
| Features | HIGH | Competitor analysis covers 5+ real products. Feature dependency graph is internally consistent. MVP scope is conservative and achievable. |
| Architecture | HIGH | Patterns (strategy, middleware injection, repository) are industry-standard for this problem type. Build order follows actual dependency graph. |
| Pitfalls | HIGH | 7 critical pitfalls all verified with GitHub issues, official docs, or Railway support threads. Recovery costs are realistic. |

**Overall confidence:** HIGH

### Gaps to Address

- **Arbuz.kz and Magnum.kz actual DOM/API structure:** Unknown until live browser inspection. Phase 2 research phase required before implementation. The recommendation to prefer API interception is correct but the actual XHR endpoint paths are unknown.
- **Cross-store product matching algorithm:** No clear solution identified in research. Phase 5 needs dedicated research into fuzzy name matching and unit normalization before implementation. SuperPriceWatchdog (Hong Kong) faced a similar problem but their approach is not documented publicly.
- **Railway memory limits in practice:** STACK.md notes Railway Starter plan should handle Playwright at small scale (1-10 users), but actual memory profile under concurrent scraping is untested. Monitor RSS from day one of Phase 2 testing on Railway.
- **Kaspi.kz Accept-Language behavior:** PITFALLS.md notes Kaspi may serve different content based on locale. Correct headers (`Accept-Language: ru`) need to be validated in Phase 2.

## Sources

### Primary (HIGH confidence)
- [aiogram 3.26 PyPI + docs](https://docs.aiogram.dev/) — router system, middlewares, dispatcher
- [Playwright Python 1.50 PyPI + Docker docs](https://playwright.dev/python/docs/docker) — Docker image, browser flags, memory behavior
- [SQLAlchemy 2.0.48 async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — async engine, pool config
- [APScheduler 3.x docs + FAQ](https://apscheduler.readthedocs.io/en/3.x/faq.html) — AsyncIOScheduler, misfire handling, job stores
- [asyncpg 0.31.0 PyPI](https://pypi.org/project/asyncpg/) — version compatibility notes
- [Railway Help: Playwright in Docker](https://station.railway.com/questions/worker-timeouts-and-playwright-browser-e-d6499ade) — confirmed production deployment patterns

### Secondary (MEDIUM confidence)
- [SuperPriceWatchdog](https://github.com/Jack-cky/SuperPriceWatchdog) — Telegram grocery bot for HK, feature comparison reference
- [Pricegram](https://github.com/AleG94/Pricegram) — Telegram Amazon price tracker, UX patterns
- [Basket App](https://basketsavings.com/index.html) — US cross-store comparison app, competitive reference
- [playwright-stealth PyPI](https://pypi.org/project/playwright-stealth/) — anti-detection patches; MEDIUM because effectiveness against KZ sites is unverified
- [Playwright memory leak issues #286, #6319, #38489](https://github.com/microsoft/playwright-python/issues/286) — documented but behavior may differ across versions

### Tertiary (LOW confidence)
- Product matching approach for cross-store comparison — no verified solution found; needs original research in Phase 5
- Arbuz.kz / Magnum.kz internal API structure — inferred from SPA behavior; needs live browser inspection to confirm

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
