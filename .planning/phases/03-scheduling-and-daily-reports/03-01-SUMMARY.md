---
phase: 03-scheduling-and-daily-reports
plan: 01
subsystem: services
tags: [scraping, reports, telegram, sqlalchemy, async]

# Dependency graph
requires:
  - phase: 02-basket-management
    provides: Basket, BasketItem, PriceHistory models and repositories
provides:
  - scrape_all_baskets() for daily scheduled scraping with URL deduplication
  - scrape_single_basket() for /scrape command handler
  - generate_user_report() for task.md 7.1 formatted daily reports
  - generate_basket_section() for per-basket report text
  - split_message() for Telegram 4096-char message splitting
  - Repository query methods for daily scrape and report workflows
affects: [03-02-scheduler-and-handlers, 04-charts-and-export]

# Tech tracking
tech-stack:
  added: [zoneinfo]
  patterns: [self-managed sessions for scheduled jobs, URL deduplication across baskets, bilingual report strings as local dict]

key-files:
  created:
    - src/price_spy/services/daily_scrape.py
    - src/price_spy/services/report.py
    - src/price_spy/services/message_utils.py
  modified:
    - src/price_spy/db/repositories/basket.py
    - src/price_spy/db/repositories/user.py
    - src/price_spy/db/repositories/price_history.py
    - src/price_spy/db/repositories/basket_item.py

key-decisions:
  - "Report strings defined locally in report.py as REPORT_STRINGS dict instead of touching i18n files"
  - "DISTINCT ON used in get_previous_prices for PostgreSQL-efficient yesterday price lookup"
  - "All baskets scraped regardless of is_active flag (is_active is UI selection state, not scrape filter)"

patterns-established:
  - "Self-managed sessions: scheduled jobs and service functions open their own async_session context"
  - "URL deduplication: scrape_all_baskets builds url_to_item_ids map to avoid scraping same URL twice"
  - "Number formatting: space as thousands separator for tenge amounts (e.g. 28 450)"

requirements-completed: [REPT-01, REPT-02, REPT-03, REPT-04, REPT-05, REPT-06]

# Metrics
duration: 4min
completed: 2026-03-30
---

# Phase 03 Plan 01: Daily Scrape & Report Services Summary

**Scrape orchestration with URL dedup across all baskets and bilingual report generation matching task.md 7.1 format with price change tracking and out-of-stock markers**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-30T23:25:25Z
- **Completed:** 2026-03-30T23:29:24Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Extended 4 repositories with 5 new query methods for daily scrape and report workflows
- Created scrape orchestration service with URL deduplication across all baskets and per-basket scraping
- Built report generation service producing exact task.md 7.1 formatted text with price changes, out-of-stock markers, and cross-store comparison
- Added Telegram message splitting utility for 4096-char limit

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend repositories with new query methods** - `ecd331b` (feat)
2. **Task 2: Create daily scrape and report generation services** - `36f3869` (feat)

## Files Created/Modified
- `src/price_spy/services/daily_scrape.py` - Scrape orchestration: scrape_all_baskets() with URL dedup, scrape_single_basket() for /scrape
- `src/price_spy/services/report.py` - Report generation: generate_user_report(), generate_basket_section() with bilingual REPORT_STRINGS
- `src/price_spy/services/message_utils.py` - split_message() for Telegram 4096-char limit
- `src/price_spy/db/repositories/basket.py` - Added get_all_active_baskets(), get_user_baskets_for_report()
- `src/price_spy/db/repositories/user.py` - Added get_users_by_notify_time()
- `src/price_spy/db/repositories/price_history.py` - Added get_previous_prices() with DISTINCT ON
- `src/price_spy/db/repositories/basket_item.py` - Added get_items_by_basket()

## Decisions Made
- Report strings defined locally in report.py as REPORT_STRINGS dict rather than modifying i18n files (avoids file conflicts with Plan 02)
- DISTINCT ON used for get_previous_prices to efficiently get most recent price per item before a cutoff
- All baskets scraped regardless of is_active flag (is_active controls UI basket selection, not scrape eligibility)
- zoneinfo used for Asia/Almaty timezone-aware cutoff in report generation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff f-string warning in report.py**
- **Found during:** Task 2 (report service creation)
- **Issue:** f-string without placeholders on the "no price" fallback line
- **Fix:** Removed extraneous f prefix
- **Files modified:** src/price_spy/services/report.py
- **Verification:** ruff check passes clean
- **Committed in:** 36f3869 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor lint fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Daily scrape and report services ready for Plan 02 (APScheduler integration and Telegram handlers)
- scrape_all_baskets() ready to be called from scheduled job
- scrape_single_basket() ready to be called from /scrape handler
- generate_user_report() ready to be called from notification dispatcher

---
*Phase: 03-scheduling-and-daily-reports*
*Completed: 2026-03-30*
