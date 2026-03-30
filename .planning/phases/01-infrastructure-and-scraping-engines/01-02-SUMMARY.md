---
phase: 01-infrastructure-and-scraping-engines
plan: 02
subsystem: scraping
tags: [playwright, httpx, selectolax, pydantic, stealth, semaphore, retry]

# Dependency graph
requires:
  - phase: 01-01
    provides: "Project structure, config.py with scrape_concurrency/timeout/retry settings, uv dependencies"
provides:
  - "PriceResult Pydantic model for validated price data"
  - "BaseScraper abstract interface for all scrapers"
  - "BrowserManager singleton for Chromium lifecycle"
  - "Stealth module with UA rotation and viewport randomization"
  - "ArbuzScraper with API interception + DOM fallback"
  - "MagnumScraper with API interception + __NEXT_DATA__ + DOM fallback"
  - "KaspiScraper with httpx + selectolax (no Playwright)"
  - "ScraperService orchestrating parallel scrapes with concurrency and retries"
  - "URL detection and product ID extraction utilities"
affects: [bot-handlers, scheduler, price-history, daily-reports]

# Tech tracking
tech-stack:
  added: [playwright-stealth, selectolax]
  patterns: [strategy-pattern-scrapers, api-interception-fallback, semaphore-concurrency, exponential-backoff-retry]

key-files:
  created:
    - src/price_spy/scrapers/models.py
    - src/price_spy/scrapers/base.py
    - src/price_spy/scrapers/browser.py
    - src/price_spy/scrapers/stealth.py
    - src/price_spy/scrapers/arbuz.py
    - src/price_spy/scrapers/magnum.py
    - src/price_spy/scrapers/kaspi.py
    - src/price_spy/scrapers/__init__.py
    - src/price_spy/services/__init__.py
    - src/price_spy/services/scraper.py
  modified: []

key-decisions:
  - "Hybrid API interception + DOM fallback for Playwright scrapers (D-01)"
  - "Multi-selector fallback lists for DOM extraction since selectors unknown until live testing (D-02)"
  - "selectolax Lexbor backend for Kaspi SSR parsing (D-03)"
  - "3 Playwright / 10 httpx semaphore split for concurrency control"

patterns-established:
  - "Strategy pattern: BaseScraper ABC with scrape() + close() interface"
  - "API interception: page.on('response') captures JSON during page.goto before DOM fallback"
  - "BrowserManager singleton: one Chromium instance, fresh contexts per scrape, auto-recycle after 100 pages"
  - "ScraperService: URL-based dispatch, semaphore concurrency, exponential backoff retry"

requirements-completed: [SCRP-01, SCRP-02, SCRP-03, SCRP-04, SCRP-05, SCRP-06, SCRP-07, SCRP-08, SCRP-09, SCRP-10]

# Metrics
duration: 4min
completed: 2026-03-30
---

# Phase 01 Plan 02: Scraping Engines Summary

**Three-store scraper system with hybrid API interception + DOM fallback for Arbuz/Magnum via Playwright, httpx+selectolax for Kaspi, and orchestration service with semaphore concurrency and exponential backoff retries**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-30T17:30:19Z
- **Completed:** 2026-03-30T17:34:24Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- PriceResult Pydantic model with integer tenge prices, positive price and non-empty name validation
- BrowserManager singleton managing Chromium lifecycle with context recycling after 100 pages
- Stealth module with 8 user agents, 5 viewport sizes, and playwright-stealth integration
- ArbuzScraper and MagnumScraper with API interception during page.goto, falling back to multi-selector DOM extraction
- MagnumScraper additionally extracts __NEXT_DATA__ script tag as mid-tier fallback (Next.js SPA)
- KaspiScraper using httpx + selectolax only (no Playwright dependency) for SSR HTML parsing
- ScraperService orchestrating parallel scrapes with 3 Playwright / 10 httpx semaphores and 3x retry with exponential backoff

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PriceResult model, BaseScraper interface, BrowserManager, and stealth utilities** - `2430450` (feat)
2. **Task 2: Implement Arbuz, Magnum, and Kaspi scrapers with hybrid API interception** - `6a83dba` (feat)
3. **Task 3: Create scraper orchestration service with concurrency control and retry logic** - `f456215` (feat)

## Files Created/Modified
- `src/price_spy/scrapers/models.py` - PriceResult Pydantic model with price/name validators
- `src/price_spy/scrapers/base.py` - BaseScraper ABC defining scrape() and close() interface
- `src/price_spy/scrapers/browser.py` - BrowserManager singleton with Chromium lifecycle and context recycling
- `src/price_spy/scrapers/stealth.py` - UA rotation pool, viewport randomization, playwright-stealth wrapper
- `src/price_spy/scrapers/arbuz.py` - ArbuzScraper with API interception + multi-selector DOM fallback
- `src/price_spy/scrapers/magnum.py` - MagnumScraper with API interception + __NEXT_DATA__ + DOM fallback
- `src/price_spy/scrapers/kaspi.py` - KaspiScraper with httpx + selectolax HTML parsing
- `src/price_spy/scrapers/__init__.py` - Package exports for PriceResult, BaseScraper, browser_manager
- `src/price_spy/services/__init__.py` - Services package init
- `src/price_spy/services/scraper.py` - ScraperService with URL routing, concurrency, retries

## Decisions Made
- Hybrid API interception + DOM fallback for Playwright scrapers per D-01
- Multi-selector fallback lists for DOM extraction since actual selectors unknown until live testing per D-02
- selectolax with Lexbor backend for Kaspi SSR parsing per D-03
- 3 Playwright / 10 httpx semaphore split matching settings.scrape_concurrency for Playwright, hardcoded 10 for httpx

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed setuptools for playwright-stealth pkg_resources dependency**
- **Found during:** Task 1 (verification)
- **Issue:** playwright-stealth imports pkg_resources which requires setuptools, not installed in uv venv by default
- **Fix:** Installed setuptools<81 via uv pip (82.x removed pkg_resources)
- **Files modified:** None (runtime dependency only)
- **Verification:** All imports succeed after installation
- **Committed in:** Not committed (venv-only change, not tracked in git)

**2. [Rule 3 - Blocking] Adjusted file paths from plan's price_spy/ to actual src/price_spy/ layout**
- **Found during:** Task 1 (file creation)
- **Issue:** Plan referenced price_spy/scrapers/ but project uses src/ layout per 01-01 decision
- **Fix:** Created all files under src/price_spy/ matching existing project structure
- **Files modified:** All files in this plan
- **Verification:** All imports work correctly with src/ layout

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes necessary for correct execution. No scope creep.

## Issues Encountered
None beyond the deviations listed above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
- DOM selectors in arbuz.py, magnum.py are placeholder fallback lists (D-02: will be refined during live testing against actual site HTML). This is intentional per plan design -- API interception is the primary path, DOM selectors are defensive fallbacks.
- API response parsing in _parse_api_response tries common JSON structures but actual API format unknown until live scraping. This is intentional per D-01/D-02 research decisions.

## Next Phase Readiness
- All scraper engines ready to be called from bot handlers or scheduler
- BrowserManager requires start() call during application startup and close() on shutdown
- ScraperService is the primary entry point for scraping operations
- Selectors will need refinement during integration testing with live sites (tracked as known stubs)

## Self-Check: PASSED

All 10 created files verified on disk. All 3 task commit hashes verified in git log.

---
*Phase: 01-infrastructure-and-scraping-engines*
*Completed: 2026-03-30*
