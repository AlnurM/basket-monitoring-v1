---
phase: 03-scheduling-and-daily-reports
plan: 02
subsystem: bot, scheduling
tags: [apscheduler, aiogram, telegram-bot, i18n, rate-limiting]

# Dependency graph
requires:
  - phase: 03-01
    provides: "scrape_all_baskets, scrape_single_basket, generate_user_report, split_message services"
provides:
  - "Real daily_scrape job calling scrape_all_baskets()"
  - "Minute-tick deliver_reports job with flood control"
  - "/notify HH:MM command handler for notification time"
  - "/scrape command handler with 1-hour rate limiting"
  - "i18n keys for /notify and /scrape in RU and EN"
affects: [04-charts-csv-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns: [function-attribute bot reference, in-memory rate limiting dict, import alias for name collision]

key-files:
  created:
    - src/price_spy/bot/handlers/settings.py
    - src/price_spy/bot/handlers/scrape.py
  modified:
    - src/price_spy/__main__.py
    - src/price_spy/bot/create.py
    - src/price_spy/i18n/ru.py
    - src/price_spy/i18n/en.py

key-decisions:
  - "Import alias settings_handlers to avoid collision with config.settings in create.py"

patterns-established:
  - "Function attribute pattern: deliver_reports._bot = bot for scheduler job bot access"
  - "In-memory rate limiting via module-level dict for simple per-user cooldowns"

requirements-completed: [REPT-01, REPT-02, REPT-07, REPT-08, MSCR-01, MSCR-02, MSCR-03]

# Metrics
duration: 3min
completed: 2026-03-31
---

# Phase 03 Plan 02: Scheduler Wiring and Bot Handlers Summary

**Real scheduler jobs wired (daily scrape + minute-tick report delivery), /notify and /scrape bot commands with rate limiting and progress feedback**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-31T07:31:31Z
- **Completed:** 2026-03-31T07:34:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Replaced daily_scrape placeholder with real scrape_all_baskets() call and error handling
- Added deliver_reports() running every minute via IntervalTrigger, querying users by notify_time, sending reports with TelegramForbiddenError/TelegramRetryAfter handling and 1s flood control delay
- Created /notify command with HH:MM validation, current time display, and User.notify_time update
- Created /scrape command with in-memory 1-hour rate limiting, progress message editing, and scrape_single_basket integration
- Added all i18n keys for both commands in RU and EN, updated help text

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire scheduler jobs and add i18n keys** - `af1f997` (feat)
2. **Task 2: Create /notify and /scrape handlers and register routers** - `16be426` (feat)

## Files Created/Modified
- `src/price_spy/__main__.py` - Real daily_scrape and deliver_reports scheduler jobs
- `src/price_spy/bot/handlers/settings.py` - /notify command handler (new)
- `src/price_spy/bot/handlers/scrape.py` - /scrape command handler with rate limiting (new)
- `src/price_spy/bot/create.py` - Router registration for settings and scrape
- `src/price_spy/i18n/ru.py` - Russian translations for /notify, /scrape, and help update
- `src/price_spy/i18n/en.py` - English translations for /notify, /scrape, and help update

## Decisions Made
- Used import alias `settings_handlers` in create.py to avoid name collision with `config.settings` (Rule 1 - bug fix)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed settings import name collision in create.py**
- **Found during:** Task 2 (Router registration)
- **Issue:** `from price_spy.bot.handlers import settings` was shadowed by `from price_spy.config import settings` on the next line, causing AttributeError when accessing `settings.router`
- **Fix:** Used `from price_spy.bot.handlers import settings as settings_handlers` and referenced `settings_handlers.router`
- **Files modified:** src/price_spy/bot/create.py
- **Verification:** create_dispatcher() imports succeed, router names include 'settings' and 'scrape'
- **Committed in:** 16be426 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correct module resolution. No scope creep.

## Issues Encountered
None beyond the import collision addressed above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all handlers are fully wired to real services.

## Next Phase Readiness
- Phase 03 scheduling and daily reports is complete
- All scheduler jobs, bot commands, i18n, and router registration in place
- Ready for Phase 04 (charts, CSV export, comparison features)

---
*Phase: 03-scheduling-and-daily-reports*
*Completed: 2026-03-31*
