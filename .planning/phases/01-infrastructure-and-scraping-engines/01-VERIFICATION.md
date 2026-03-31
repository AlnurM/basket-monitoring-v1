---
phase: 01-infrastructure-and-scraping-engines
verified: 2026-03-30T20:00:00Z
status: human_needed
score: 22/22 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 19/22
  gaps_closed:
    - "SCRP-05: ProductNameCache model + migration + ProductCacheRepository added; ScraperService checks cache before scraping and writes name on first hit"
    - "INFR-05: SQLAlchemyJobStore with sync DATABASE_URL added to AsyncIOScheduler in on_startup"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Bot end-to-end startup and Telegram interaction"
    expected: "Bot starts with 'Startup check: DB connection OK', 'Playwright Chromium OK', 'Bot token OK (@your_bot_name)', then responds to /start with two-button language keyboard, selects language and shows welcome message, /help shows command list in chosen language"
    why_human: "Requires live Telegram bot token, running PostgreSQL, and Playwright execution — cannot verify programmatically without the running system"
  - test: "APScheduler PostgreSQL jobstore creation at runtime"
    expected: "On first startup, APScheduler creates its apscheduler_jobs table in PostgreSQL via SQLAlchemyJobStore; daily_scrape job row is visible after bot starts"
    why_human: "Requires running PostgreSQL to verify the jobstore table is actually created and the job row is persisted"
  - test: "product_name_cache table created by Alembic migration"
    expected: "uv run alembic upgrade head runs migrations 001 then 002; psql shows product_name_cache table with product_url UNIQUE, name TEXT columns"
    why_human: "Requires running PostgreSQL instance"
  - test: "Docker image build"
    expected: "docker compose build completes without errors; docker compose up starts bot + PostgreSQL successfully"
    why_human: "Cannot run docker build in this environment"
  - test: "Railway deployment"
    expected: "Bot deployed and running on Railway with PostgreSQL connected"
    why_human: "Requires Railway account, live credentials, and network access"
---

# Phase 01: Infrastructure and Scraping Engines — Verification Report

**Phase Goal:** A deployed, running Telegram bot on Railway with PostgreSQL, Playwright, and all three scraper engines producing validated price data

**Verified:** 2026-03-30T20:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (previous status: gaps_found, 19/22)

---

## Re-Verification Summary

| Gap | Previous Status | Current Status | Evidence |
|-----|----------------|----------------|----------|
| SCRP-05: Product name cached after first scrape | FAILED | CLOSED | `product_name_cache` model, migration 002, `ProductCacheRepository`, `ScraperService` cache read/write all verified |
| INFR-05: APScheduler uses PostgreSQL jobstore | FAILED | CLOSED | `SQLAlchemyJobStore(url=settings.database_url_sync)` passed to `AsyncIOScheduler` in `on_startup` |

No regressions found in previously-passing items.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | uv project initialized with Python 3.12 and all core dependencies | VERIFIED | pyproject.toml contains 12 core deps + setuptools; requires-python = ">=3.12" |
| 2 | Database engine connects to PostgreSQL with async pool (pool_size=5, max_overflow=5) | VERIFIED | src/price_spy/db/engine.py: create_async_engine with pool_size=5, max_overflow=5, pool_pre_ping=True |
| 3 | Alembic migration creates users table with all required columns | VERIFIED | alembic/versions/001_initial_users.py: creates users table with id, telegram_id (UNIQUE), username, language, notify_time, timezone, created_at (TIMESTAMPTZ) |
| 4 | User repository can create and retrieve users by telegram_id | VERIFIED | src/price_spy/db/repositories/user.py: UserRepository with get_by_telegram_id, create, update_language, get_or_create — all implemented substantively |
| 5 | All timestamps use TIMESTAMPTZ for Asia/Almaty timezone handling | VERIFIED | Migration uses sa.DateTime(timezone=True); User model uses server_default=func.now(); default timezone column = "Asia/Almaty" |
| 6 | PriceResult model validates price > 0, non-empty name, correct types | VERIFIED | src/price_spy/scrapers/models.py: field_validator on price (must be positive) and name (no empty string) |
| 7 | BrowserManager creates single Chromium instance and yields fresh contexts | VERIFIED | src/price_spy/scrapers/browser.py: singleton BrowserManager, new_context() asynccontextmanager, recycles after 100 pages |
| 8 | ArbuzScraper uses API interception then falls back to DOM extraction | VERIFIED | src/price_spy/scrapers/arbuz.py: page.on("response", capture_response) before page.goto; falls back to _extract_from_dom |
| 9 | MagnumScraper uses API interception then __NEXT_DATA__ then DOM extraction | VERIFIED | src/price_spy/scrapers/magnum.py: three-tier fallback: API intercept -> __NEXT_DATA__ script tag -> multi-selector DOM |
| 10 | KaspiScraper uses httpx + selectolax without Playwright | VERIFIED | src/price_spy/scrapers/kaspi.py: httpx.AsyncClient with HTTP/2, selectolax HTMLParser, no Playwright import |
| 11 | ScraperService orchestrates parallel scraping with semaphore limits | VERIFIED | src/price_spy/services/scraper.py: Semaphore(settings.scrape_concurrency) for Playwright, Semaphore(10) for httpx; asyncio.gather |
| 12 | Failed scrapes retry 3 times with exponential backoff before reporting | VERIFIED | src/price_spy/services/scraper.py: range(settings.scrape_retry_count) loop, delay = 2**attempt + random.uniform(0,1) |
| 13 | User can /start the bot and is presented with language selection | VERIFIED | src/price_spy/bot/handlers/start.py: cmd_start shows InlineKeyboardBuilder with lang:ru and lang:en buttons |
| 14 | Language selection creates user record in DB and shows welcome message | VERIFIED | callback_language: calls user_repo.get_or_create for new users, edit_text(language_set) + answer(welcome) |
| 15 | User can /help and see available commands in their language | VERIFIED | cmd_help: checks user existence, redirects to language selection if unregistered, else sends get_text("help", lang) |
| 16 | User can switch language at any time | VERIFIED | cmd_language: shows keyboard; callback_language: calls user_repo.update_language for existing users |
| 17 | All handler responses use i18n get_text, not hardcoded strings | VERIFIED | All four handlers in start.py import and call get_text(); no hardcoded Russian or English strings in handler bodies |
| 18 | python -m price_spy starts bot with startup validation and polling | VERIFIED | __main__.py: validate_startup (DB SELECT 1 + Playwright launch/close + bot.get_me), then create_bot/create_dispatcher, then dp.start_polling |
| 19 | Docker image builds with Playwright Chromium and all dependencies | VERIFIED | Dockerfile uses mcr.microsoft.com/playwright/python:v1.50.0-noble; uv sync --frozen --no-dev; CMD uv run python -m price_spy |
| 20 | docker-compose.yml starts bot + PostgreSQL for local development | VERIFIED | docker-compose.yml: postgres:16 with healthcheck; bot service depends_on db with service_healthy condition |
| 21 | SCRP-05: Product name cached after first scrape (no re-extraction) | VERIFIED | ProductNameCache model + migration 002 + ProductCacheRepository.get_name/set_name + ScraperService reads cache before scrape, writes on first hit — full cache read/write/upsert pipeline implemented |
| 22 | INFR-05: APScheduler uses PostgreSQL jobstore for persistent tasks | VERIFIED | __main__.py imports SQLAlchemyJobStore; on_startup creates AsyncIOScheduler(timezone="Asia/Almaty", jobstores={"default": SQLAlchemyJobStore(url=settings.database_url_sync)}) |

**Score:** 22/22 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/price_spy/config.py` | Pydantic Settings configuration | VERIFIED | class Settings(BaseSettings) with all required keys; database_url_sync property returns sync URL by stripping "+asyncpg" |
| `src/price_spy/db/engine.py` | Async engine and session factory | VERIFIED | create_async_engine with pool_size=5, async_sessionmaker |
| `src/price_spy/db/models/user.py` | User SQLAlchemy model | VERIFIED | class User(Base) with telegram_id unique index, language, notify_time, timezone, created_at |
| `src/price_spy/db/models/product_cache.py` | ProductNameCache SQLAlchemy model (SCRP-05) | VERIFIED | class ProductNameCache(Base) with product_url (UNIQUE), url_source, product_id, name columns |
| `src/price_spy/db/repositories/user.py` | User CRUD operations | VERIFIED | UserRepository with get_by_telegram_id, create, update_language, get_or_create |
| `src/price_spy/db/repositories/product_cache.py` | Product name cache operations (SCRP-05) | VERIFIED | ProductCacheRepository with get_name(url) and set_name(url, source, pid, name) upsert — substantive, not stubs |
| `alembic/versions/001_initial_users.py` | Initial migration | VERIFIED | Creates users table with all columns; DateTime(timezone=True) for TIMESTAMPTZ |
| `alembic/versions/002_add_product_name_cache.py` | Cache table migration (SCRP-05) | VERIFIED | Creates product_name_cache table with product_url UNIQUE, url_source, product_id, name; down_revision = "001" |
| `src/price_spy/scrapers/models.py` | PriceResult Pydantic model | VERIFIED | class PriceResult with price/name validators |
| `src/price_spy/scrapers/base.py` | Abstract BaseScraper interface | VERIFIED | ABC with abstractmethods scrape() and close() |
| `src/price_spy/scrapers/browser.py` | BrowserManager singleton | VERIFIED | Full lifecycle management with new_context() and recycling |
| `src/price_spy/scrapers/stealth.py` | Stealth config and UA rotation | VERIFIED | USER_AGENTS (8 entries), VIEWPORT_SIZES (5 entries), apply_stealth |
| `src/price_spy/scrapers/arbuz.py` | ArbuzScraper with API interception | VERIFIED | Three-layer extraction; substantive DOM fallback with multi-selectors |
| `src/price_spy/scrapers/magnum.py` | MagnumScraper with API interception | VERIFIED | Three-layer extraction including __NEXT_DATA__ |
| `src/price_spy/scrapers/kaspi.py` | KaspiScraper with httpx + selectolax | VERIFIED | httpx.AsyncClient + selectolax HTMLParser; no Playwright |
| `src/price_spy/services/scraper.py` | ScraperService orchestration | VERIFIED | URL dispatch, semaphore concurrency, exponential backoff retry, SCRP-05 cache read/write |
| `src/price_spy/i18n/core.py` | Translation lookup function | VERIFIED | def get_text with language fallback chain |
| `src/price_spy/i18n/ru.py` | Russian translations | VERIFIED | STRINGS dict with Cyrillic values for all required keys |
| `src/price_spy/i18n/en.py` | English translations | VERIFIED | STRINGS dict with English values for all required keys |
| `src/price_spy/bot/create.py` | Bot and Dispatcher factory | VERIFIED | create_bot() and create_dispatcher() with both middlewares on message + callback_query |
| `src/price_spy/bot/middlewares/db.py` | Database session injection middleware | VERIFIED | DbSessionMiddleware commits on success, rolls back on exception |
| `src/price_spy/bot/middlewares/i18n.py` | Language resolution middleware | VERIFIED | Injects user, user_repo, lang; defaults lang="en" for unregistered |
| `src/price_spy/bot/handlers/start.py` | /start, /help, language handlers | VERIFIED | cmd_start, callback_language, cmd_help, cmd_language — all substantive |
| `src/price_spy/__main__.py` | Application entry point | VERIFIED | validate_startup, on_startup (browser + SQLAlchemyJobStore scheduler), on_shutdown, main, daily_scrape (placeholder) |
| `Dockerfile` | Docker image with Playwright Chromium | VERIFIED | mcr.microsoft.com/playwright/python:v1.50.0-noble base, uv sync, correct CMD |
| `docker-compose.yml` | Local dev stack | VERIFIED | postgres:16 with healthcheck + bot service with DATABASE_URL |
| `railway.toml` | Railway deployment config | VERIFIED | builder = "dockerfile"; restartPolicyType = "ON_FAILURE"; no healthcheckPath |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `config.py` | `db/engine.py` | Settings.database_url | VERIFIED | engine.py imports settings and uses settings.database_url directly |
| `config.py` | `__main__.py` | Settings.database_url_sync | VERIFIED | __main__.py uses settings.database_url_sync in SQLAlchemyJobStore constructor |
| `db/engine.py` | `db/models/user.py` | SQLAlchemy mapped class | VERIFIED | async_session factory used by middlewares; User model in metadata |
| `db/models/product_cache.py` | `db/repositories/product_cache.py` | ProductNameCache import | VERIFIED | ProductCacheRepository imports and queries ProductNameCache directly |
| `db/repositories/product_cache.py` | `services/scraper.py` | ProductCacheRepository used in ScraperService | VERIFIED | ScraperService.__init__ creates self._cache = ProductCacheRepository(session); _scrape_single reads cache before scrape, writes on miss |
| `bot/middlewares/i18n.py` | `db/repositories/user.py` | reads user.language | VERIFIED | I18nMiddleware imports UserRepository; sets data["lang"] = user.language |
| `bot/handlers/start.py` | `i18n/core.py` | get_text for all strings | VERIFIED | All 4 handlers import and call get_text(); no hardcoded strings |
| `bot/middlewares/db.py` | `db/engine.py` | async_session factory | VERIFIED | DbSessionMiddleware imports async_session; uses as context manager |
| `__main__.py` | `bot/create.py` | create_bot and create_dispatcher | VERIFIED | __main__.py imports both and calls them in main() |
| `__main__.py` | `scrapers/browser.py` | browser_manager.start() | VERIFIED | on_startup calls await browser_manager.start(); on_shutdown calls browser_manager.close() |
| `__main__.py` | APScheduler SQLAlchemyJobStore | jobstores={"default": SQLAlchemyJobStore(url=settings.database_url_sync)} | VERIFIED | Line 66-68 in __main__.py; jobstores dict passed to AsyncIOScheduler constructor |
| `Dockerfile` | `__main__.py` | CMD python -m price_spy | VERIFIED | CMD ["uv", "run", "python", "-m", "price_spy"] |
| `scrapers/arbuz.py` | `scrapers/browser.py` | BrowserManager.new_context() | VERIFIED | ArbuzScraper uses `async with browser_manager.new_context() as ctx` |
| `scrapers/arbuz.py` | `scrapers/models.py` | returns PriceResult | VERIFIED | Both _parse_api_response and _extract_from_dom return PriceResult instances |
| `services/scraper.py` | `scrapers/arbuz.py` + magnum + kaspi | dispatches by URL domain | VERIFIED | URL_PATTERNS dict routes to ArbuzScraper, MagnumScraper, KaspiScraper by regex match |
| `db/models/__init__.py` | `product_cache.py` | exports ProductNameCache | VERIFIED | __init__.py: from .product_cache import ProductNameCache; __all__ includes it |

---

## Data-Flow Trace (Level 4)

*Scrapers produce dynamic data but do not render UI — this is a CLI/bot backend. Level 4 trace applies to the scraper data pipeline and the new cache pipeline.*

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `scrapers/arbuz.py` | `api_data["response"]` | page.on("response") during live Playwright request | DOM selectors are placeholder fallbacks (known per D-02) | PARTIAL — API interception path is real; DOM fallback selectors are unvalidated against live site |
| `scrapers/magnum.py` | `api_data["response"]` | page.on("response") + __NEXT_DATA__ | Same as Arbuz — DOM fallback unvalidated against live site | PARTIAL — API/NEXT_DATA path is real; DOM fallback unvalidated |
| `scrapers/kaspi.py` | `tree = HTMLParser(resp.text)` | httpx GET + selectolax parse | CSS selectors (itemprop="price", h1) are standard and more reliable | LIKELY_VALID — uses structured data (meta[itemprop]) which is stable |
| `services/scraper.py` | `cached_name` | ProductCacheRepository.get_name(url) -> DB read | Real DB query (SELECT name WHERE product_url = url) | VERIFIED — cache lookup is a real query, not a stub |
| `services/scraper.py` | `data.name` written to cache | ProductCacheRepository.set_name(url, source, pid, name) | Real DB upsert (SELECT then INSERT or UPDATE) | VERIFIED — cache write is a real upsert, not a stub |
| `__main__.py` | APScheduler jobstore | SQLAlchemyJobStore(url=settings.database_url_sync) | Real PostgreSQL table (apscheduler_jobs) created at runtime | PENDING HUMAN — the jobstore object is correctly constructed in code; actual table creation only verifiable with running PostgreSQL |

**Note on DOM selectors:** The SUMMARY explicitly acknowledges selector placeholders as intentional per D-02 (will be refined during live testing). The API interception path (primary) does not depend on these selectors. This is a known and accepted risk, not a verification failure.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Config imports without .env | `python -c "from price_spy.config import Settings; s=Settings(); print(s.scrape_concurrency)"` | Settings has defaults for all fields; bot_token defaults to ""; database_url_sync strips "+asyncpg" | PASS (by code inspection) |
| DB models import correctly including ProductNameCache | `python -c "from price_spy.db.models import Base, User, ProductNameCache; print(list(Base.metadata.tables.keys()))"` | Should print ["users", "product_name_cache"] — both models exported in __init__.py | PASS (by code inspection) |
| ProductCacheRepository methods are substantive | Inspect get_name and set_name | get_name: SELECT query with scalar_one_or_none; set_name: SELECT then INSERT or row.name=name with flush — neither is a stub | PASS (by code inspection) |
| ScraperService cache integration | Inspect _scrape_single | Lines 104-118: checks cache before scraping, applies cached_name if hit, writes to cache on miss — full cache pipeline present | PASS (by code inspection) |
| SQLAlchemyJobStore import chain | `python -c "from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore"` | apscheduler is in pyproject.toml dependencies; import in __main__.py present | PASS (by code inspection) |
| Scrapers import chain | `python -c "from price_spy.services.scraper import ScraperService"` | All imports resolve: ProductCacheRepository, ArbuzScraper, MagnumScraper, KaspiScraper, browser_manager | PASS (by code inspection) |
| Bot factory imports | `python -c "from price_spy.bot.create import create_bot, create_dispatcher"` | Imports settings.bot_token (empty string default), middlewares, handlers | PASS (by code inspection) |

*Note: Live execution not possible in this environment. Spot-checks verified by static code analysis.*

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFR-02 | 01-01 | PostgreSQL database on Railway for all persistent data | SATISFIED | SQLAlchemy async engine, Alembic migrations (001 + 002), User model all exist |
| INFR-06 | 01-01 | DB connection pool sized for concurrent scraping + bot handlers | SATISFIED | pool_size=5, max_overflow=5 in db/engine.py |
| INFR-07 | 01-01, 01-04 | All times in Asia/Almaty timezone | SATISFIED | User.timezone default "Asia/Almaty"; BrowserContext locale; APScheduler timezone="Asia/Almaty"; migration uses TIMESTAMPTZ |
| USER-01 | 01-01, 01-03 | User can register via /start | SATISFIED | /start shows language keyboard; callback_language calls get_or_create |
| USER-02 | 01-03 | User can select interface language at registration | SATISFIED | Inline keyboard with Русский/English; lang_code stored via get_or_create |
| USER-03 | 01-03 | User can switch language at any time | SATISFIED | /language command and callback_language update_language path |
| USER-04 | 01-03 | User can view help via /help | SATISFIED | cmd_help sends get_text("help", lang) in user's language |
| SCRP-01 | 01-02 | Scrape Arbuz.kz via Playwright | SATISFIED | ArbuzScraper uses Playwright page.goto and BrowserManager |
| SCRP-02 | 01-02 | Scrape Magnum.kz via Playwright | SATISFIED | MagnumScraper uses Playwright with __NEXT_DATA__ fallback |
| SCRP-03 | 01-02 | Scrape Kaspi.kz via httpx + selectolax | SATISFIED | KaspiScraper uses only httpx + selectolax; no Playwright |
| SCRP-04 | 01-02 | Extract current price, original price, name, availability | SATISFIED | PriceResult: price, original_price, name, is_available — all four fields |
| SCRP-05 | 01-02, 01-04 | Product name cached after first scrape | SATISFIED | ProductNameCache model + migration 002 + ProductCacheRepository.get_name/set_name + ScraperService reads cache before scrape and writes on first hit. Cache is DB-backed and persists across restarts. |
| SCRP-06 | 01-02 | API interception via Playwright network events | SATISFIED | page.on("response", capture_response) in both ArbuzScraper and MagnumScraper |
| SCRP-07 | 01-02 | playwright-stealth and UA rotation | SATISFIED | stealth.py: apply_stealth() wraps stealth_async; USER_AGENTS pool of 8; BrowserContext sets random_ua() |
| SCRP-08 | 01-02, 01-04 | Reuse browser instance across scrape cycle | SATISFIED | BrowserManager singleton; start() in on_startup; close() in on_shutdown |
| SCRP-09 | 01-02 | Parallelism: max 3 Playwright, max 10 httpx | SATISFIED | ScraperService: Semaphore(settings.scrape_concurrency=3), Semaphore(10) |
| SCRP-10 | 01-02 | Retry 3 times with exponential backoff | SATISFIED | range(settings.scrape_retry_count=3) loop; delay = 2**attempt + random.uniform |
| INFR-01 | 01-04 | Single process (bot + scheduler) on Railway | SATISFIED | __main__.py runs dp.start_polling in single asyncio.run(main()); APScheduler in same event loop |
| INFR-03 | 01-04 | Playwright headless without GPU/sandbox in Docker | SATISFIED | CHROMIUM_ARGS in browser.py: --no-sandbox, --disable-gpu, --disable-dev-shm-usage, --single-process |
| INFR-04 | 01-04 | Docker image handles Playwright system dependencies | SATISFIED | Dockerfile uses mcr.microsoft.com/playwright/python:v1.50.0-noble which pre-installs all system deps |
| INFR-05 | 01-04 | APScheduler uses PostgreSQL jobstore | SATISFIED | SQLAlchemyJobStore(url=settings.database_url_sync) in on_startup; AsyncIOScheduler(jobstores={"default": SQLAlchemyJobStore(...)}) — sync URL derived correctly by stripping "+asyncpg" |

**Note on REQUIREMENTS.md tracking table:** The tracking table at the bottom of REQUIREMENTS.md still shows INFR-01, INFR-03, INFR-04, INFR-05 as "Pending". This is a documentation artifact — the code fully implements all four. The tracking table should be updated to "Complete" to reflect the gap closure. The `[x]`/`[ ]` checkboxes in the requirement list above the table are also inconsistent (INFR-05 has `[ ]` despite being implemented). These are documentation issues only, not code gaps.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/price_spy/__main__.py` | 52-54 | `daily_scrape()` is a `logger.info` placeholder only | Warning | Scheduled job exists but does nothing; safe for Phase 1 since scraping orchestration is Phase 3 |
| `src/price_spy/scrapers/arbuz.py` | ~21-40 | DOM selector lists are placeholder guesses (D-02) | Warning | API interception is primary path; DOM fallback selectors unvalidated against live Arbuz.kz HTML |
| `src/price_spy/scrapers/magnum.py` | ~20-41 | DOM selector lists are placeholder guesses (D-02) | Warning | Same as Arbuz — API/NEXT_DATA is primary; DOM selectors need live site validation |
| `src/price_spy/config.py` | 5-6 | `bot_token: str = ""` — empty default token | Info | Allows import without .env; startup validation will catch empty token before polling |
| `src/price_spy/db/models/product_cache.py` | all | No `created_at` or `updated_at` timestamp column | Info | No audit trail for when a cache entry was created or last refreshed; acceptable for Phase 1 |
| REQUIREMENTS.md | 165-169 | Tracking table shows INFR-01, INFR-03, INFR-04, INFR-05 as "Pending" | Warning | Documentation inconsistency — code implements all four; should be updated to "Complete" |

---

## Human Verification Required

### 1. Bot End-to-End Startup

**Test:** With a valid BOT_TOKEN in .env and a running PostgreSQL instance (via `docker compose up db -d`), run `uv run python -m price_spy`
**Expected:**
- "Startup check: DB connection OK"
- "Startup check: Playwright Chromium OK"
- "Startup check: Bot token OK (@your_bot_name)"
- Bot begins polling
**Why human:** Requires live Telegram bot token and running PostgreSQL.

### 2. APScheduler PostgreSQL Jobstore at Runtime

**Test:** After the bot starts (Test 1), connect to PostgreSQL and run `SELECT * FROM apscheduler_jobs;`
**Expected:** One row for "daily_scrape" job is present, proving the SQLAlchemyJobStore successfully initialized and persisted the job to PostgreSQL
**Why human:** SQLAlchemyJobStore creates its table automatically on first connection — only verifiable with a running PostgreSQL instance

### 3. Alembic Migration Chain

**Test:** `uv run alembic upgrade head` against running PostgreSQL
**Expected:** Runs migration 001 (creates users table) then migration 002 (creates product_name_cache table); `\d product_name_cache` shows product_url TEXT UNIQUE, url_source VARCHAR(10), product_id VARCHAR(50), name TEXT
**Why human:** Requires a running PostgreSQL instance

### 4. Telegram Interaction

**Test:** Send /start, select a language, send /help, send /language and switch to the other language
**Expected:** Language keyboard on /start; welcome in chosen language after selection; command list in correct language for /help; language switches correctly
**Why human:** Requires live Telegram session.

### 5. Docker Build

**Test:** `docker compose build` then `docker compose up`
**Expected:** Build completes; both services (db, bot) start; bot shows startup checks in logs
**Why human:** Cannot run Docker in this environment

### 6. Railway Deployment

**Test:** Verify Railway service is running with environment variables BOT_TOKEN and DATABASE_URL set
**Expected:** Bot responds to Telegram commands from the deployed Railway instance
**Why human:** Requires Railway credentials and live deployment access

---

## Gaps Summary

All automated-verifiable gaps are now closed. The two gaps from the initial verification have been fully resolved:

**Gap 1 — SCRP-05 (product name caching): CLOSED**
`src/price_spy/db/models/product_cache.py` defines `ProductNameCache` with `product_url` (UNIQUE), `url_source`, `product_id`, and `name` columns. `alembic/versions/002_add_product_name_cache.py` creates the table with correct `down_revision = "001"`. `src/price_spy/db/repositories/product_cache.py` implements `get_name(url)` (SELECT query) and `set_name(url, source, pid, name)` (upsert). `ScraperService` in `services/scraper.py` checks the cache before every scrape and writes on first hit. The requirement "no re-extraction needed after first scrape" is now fully satisfied.

**Gap 2 — INFR-05 (APScheduler PostgreSQL jobstore): CLOSED**
`__main__.py` now imports `SQLAlchemyJobStore` from `apscheduler.jobstores.sqlalchemy` and constructs the scheduler as `AsyncIOScheduler(timezone="Asia/Almaty", jobstores={"default": SQLAlchemyJobStore(url=settings.database_url_sync)})`. The sync URL is correctly derived from the async URL by stripping "+asyncpg". The job is added with `replace_existing=True` so restarts handle the existing row gracefully.

**Remaining documentation inconsistency (non-blocking):** REQUIREMENTS.md tracking table still shows INFR-01, INFR-03, INFR-04, INFR-05 as "Pending". This should be updated to "Complete" to reflect reality, but does not affect phase goal achievement.

---

*Verified: 2026-03-30T20:00:00Z*
*Verifier: Claude (gsd-verifier)*
*Re-verification after gap closure — previous score 19/22, current score 22/22*
