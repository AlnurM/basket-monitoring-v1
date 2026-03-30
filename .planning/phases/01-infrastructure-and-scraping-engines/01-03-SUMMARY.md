---
phase: 01-infrastructure-and-scraping-engines
plan: 03
subsystem: bot
tags: [aiogram, telegram, i18n, middleware, handlers]

# Dependency graph
requires:
  - phase: 01-infrastructure-and-scraping-engines (plan 01)
    provides: "Settings, DB engine, User model, UserRepository"
provides:
  - "Dictionary-based i18n with get_text() for RU and EN"
  - "Bot and Dispatcher factory with middleware chain"
  - "DbSessionMiddleware for async session injection"
  - "I18nMiddleware for user/language resolution"
  - "/start, /help, /language handlers with forced language selection"
affects: [02-basket-management, 03-reporting, 04-charts-export]

# Tech tracking
tech-stack:
  added: [aiogram 3 middlewares, inline keyboards]
  patterns: [dictionary-based i18n, middleware injection, forced language selection]

key-files:
  created:
    - src/price_spy/i18n/core.py
    - src/price_spy/i18n/en.py
    - src/price_spy/i18n/ru.py
    - src/price_spy/bot/create.py
    - src/price_spy/bot/middlewares/db.py
    - src/price_spy/bot/middlewares/i18n.py
    - src/price_spy/bot/handlers/start.py
  modified: []

key-decisions:
  - "Dictionary-based i18n per D-05 (not gettext, not Fluent) for simplicity with two languages"
  - "Forced language selection on /start per D-06 -- no functionality before language is chosen"
  - "Middleware chain: DbSession first (outer), then I18n, so I18n can use the session"

patterns-established:
  - "i18n pattern: all user-facing strings via get_text(key, lang) -- never hardcoded"
  - "Middleware injection: session, user, user_repo, lang available to all handlers via data dict"
  - "D-06 enforcement: /help redirects to language selection if user not registered"

requirements-completed: [USER-01, USER-02, USER-03, USER-04]

# Metrics
duration: 2min
completed: 2026-03-30
---

# Phase 01 Plan 03: Telegram Bot Skeleton Summary

**aiogram 3 bot with dictionary-based i18n (RU/EN), DB+i18n middleware chain, and /start /help /language handlers enforcing language selection before any interaction**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-30T17:36:55Z
- **Completed:** 2026-03-30T17:39:25Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Dictionary-based i18n module with Russian and English translations, string formatting for dynamic values, fallback chain
- Bot factory creating Bot (HTML parse mode) and Dispatcher with DbSession + I18n middleware chain
- /start forces language selection (D-06), /help checks registration, /language allows switching anytime
- All handler responses use get_text() -- zero hardcoded user-facing strings

## Task Commits

Each task was committed atomically:

1. **Task 1: Create i18n module with dictionary-based translations** - `2e6d879` (feat)
2. **Task 2: Create bot factory, middlewares, and handlers** - `ac11c8c` (feat)

## Files Created/Modified
- `src/price_spy/i18n/__init__.py` - Re-exports get_text and SUPPORTED_LANGUAGES
- `src/price_spy/i18n/core.py` - Translation lookup with language fallback
- `src/price_spy/i18n/en.py` - English string dictionary
- `src/price_spy/i18n/ru.py` - Russian string dictionary
- `src/price_spy/bot/__init__.py` - Package init
- `src/price_spy/bot/create.py` - Bot and Dispatcher factory
- `src/price_spy/bot/middlewares/__init__.py` - Package init
- `src/price_spy/bot/middlewares/db.py` - Async DB session injection with commit/rollback
- `src/price_spy/bot/middlewares/i18n.py` - User and language resolution from DB
- `src/price_spy/bot/handlers/__init__.py` - Package init
- `src/price_spy/bot/handlers/start.py` - /start, /help, /language, language callback handlers

## Decisions Made
- Dictionary-based i18n per D-05 (not gettext, not Fluent) -- simple dict lookup sufficient for two languages
- Forced language selection on /start per D-06 -- middleware does not block, handlers check user existence
- Middleware chain order: DbSession (outer) then I18n (inner) so I18n can query user from DB
- File paths adjusted to src/ layout (plan referenced price_spy/ but project uses src/price_spy/)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adjusted file paths from price_spy/ to src/price_spy/**
- **Found during:** Task 1 (i18n module creation)
- **Issue:** Plan specified paths like `price_spy/i18n/core.py` but project uses src/ layout per earlier decision
- **Fix:** All files created under `src/price_spy/` instead of `price_spy/`
- **Files modified:** All 11 files
- **Verification:** Imports work correctly with installed package

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Path adjustment necessary for project layout. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Bot skeleton complete, ready for basket management handlers (Phase 2)
- All future handlers can use get_text() and middleware-injected session/user/lang
- Language selection flow ensures every user has a language before interacting

## Self-Check: PASSED

All 11 created files verified present. Both task commits (2e6d879, ac11c8c) verified in git log.

---
*Phase: 01-infrastructure-and-scraping-engines*
*Completed: 2026-03-30*
