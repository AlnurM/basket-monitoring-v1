---
phase: 02-basket-and-product-management
plan: 01
subsystem: database, ui
tags: [sqlalchemy, alembic, aiogram, callback-data, fsm, i18n, postgresql]

# Dependency graph
requires:
  - phase: 01-infrastructure-and-scraping
    provides: User model, Base class, UserRepository pattern, i18n core, scraper service
provides:
  - Basket, BasketItem, PriceHistory SQLAlchemy models
  - Migration 003 for baskets/items/price_history tables
  - BasketRepository, BasketItemRepository, PriceHistoryRepository
  - CallbackData factories (BasketCB, BasketActionCB, ItemCB)
  - FSM states (CreateBasket, AddProduct)
  - Keyboard builders for basket navigation
  - ~35 i18n keys in RU and EN
affects: [02-02, 02-03, 03-daily-scraping-and-scheduling, 04-analytics-and-charts]

# Tech tracking
tech-stack:
  added: []
  patterns: [LATERAL join for latest-price-per-item, TYPE_CHECKING for cross-model relationships, correlated subquery for item counts]

key-files:
  created:
    - src/price_spy/db/models/basket.py
    - src/price_spy/db/models/basket_item.py
    - src/price_spy/db/models/price_history.py
    - alembic/versions/003_add_baskets_items_price_history.py
    - src/price_spy/db/repositories/basket.py
    - src/price_spy/db/repositories/basket_item.py
    - src/price_spy/db/repositories/price_history.py
    - src/price_spy/bot/callbacks/factories.py
    - src/price_spy/bot/states/basket.py
    - src/price_spy/bot/keyboards/basket.py
    - src/price_spy/bot/keyboards/pagination.py
  modified:
    - src/price_spy/db/models/__init__.py
    - src/price_spy/i18n/ru.py
    - src/price_spy/i18n/en.py

key-decisions:
  - "Used TYPE_CHECKING imports for cross-model relationship annotations to satisfy ruff F821"
  - "LATERAL join in BasketItemRepository for latest price per item avoids N+1"
  - "Short callback prefixes bsk/bact/itm to stay within 64-byte Telegram limit"

patterns-established:
  - "TYPE_CHECKING guard for forward-reference relationship types across model files"
  - "Correlated scalar subquery for count aggregation (item counts per basket)"
  - "CallbackData prefix convention: 3-4 char abbreviations"

requirements-completed: [BSKT-01, BSKT-02, BSKT-03, BSKT-04, BSKT-05, PROD-07, PROD-09, HIST-01, HIST-02, HIST-03, TXUX-01, TXUX-02]

# Metrics
duration: 4min
completed: 2026-03-31
---

# Phase 2 Plan 1: Data Layer and UI Contracts Summary

**SQLAlchemy models for baskets/items/prices with migration, async repositories with LATERAL join, aiogram CallbackData/FSM/keyboards, and 35 bilingual i18n keys**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-31T06:46:34Z
- **Completed:** 2026-03-31T06:50:56Z
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments
- Basket, BasketItem, PriceHistory models with CASCADE foreign keys and check constraints
- Migration 003 creating all 3 tables with composite index on price_history
- Three async repositories with count queries for limit enforcement and LATERAL join for item+price display
- CallbackData factories, FSM states, and 5 keyboard builder functions for basket navigation
- 35 i18n keys in both Russian and English including updated /help text

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DB models, migration, and repositories** - `19fdd93` (feat)
2. **Task 2: Create CallbackData factories, FSM states, keyboard builders, and i18n keys** - `fc65dc2` (feat)

## Files Created/Modified
- `src/price_spy/db/models/basket.py` - Basket ORM model with user FK and is_active flag
- `src/price_spy/db/models/basket_item.py` - BasketItem with unique constraint on basket+URL
- `src/price_spy/db/models/price_history.py` - PriceHistory with Numeric prices and availability
- `src/price_spy/db/models/__init__.py` - Updated exports with new models
- `alembic/versions/003_add_baskets_items_price_history.py` - Migration with check constraints and DESC index
- `src/price_spy/db/repositories/basket.py` - BasketRepository with item count subquery and set_active
- `src/price_spy/db/repositories/basket_item.py` - BasketItemRepository with LATERAL join
- `src/price_spy/db/repositories/price_history.py` - PriceHistoryRepository with cleanup
- `src/price_spy/bot/callbacks/factories.py` - BasketCB, BasketActionCB, ItemCB
- `src/price_spy/bot/states/basket.py` - CreateBasket and AddProduct FSM groups
- `src/price_spy/bot/keyboards/basket.py` - 5 keyboard builders for basket UI
- `src/price_spy/bot/keyboards/pagination.py` - Paginated item list with navigation
- `src/price_spy/i18n/ru.py` - 35 new Russian translation keys
- `src/price_spy/i18n/en.py` - 35 new English translation keys

## Decisions Made
- Used TYPE_CHECKING imports for cross-model forward references to pass ruff F821 lint
- Short callback prefixes (bsk/bact/itm) to stay within Telegram's 64-byte callback_data limit
- LATERAL join pattern for fetching latest price per item in a single query

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff F821 undefined name errors in model relationships**
- **Found during:** Task 1 (DB models)
- **Issue:** Cross-module relationship type annotations triggered ruff F821 even with `from __future__ import annotations`
- **Fix:** Added `TYPE_CHECKING` guarded imports in each model file
- **Files modified:** basket.py, basket_item.py, price_history.py
- **Verification:** `ruff check` passes clean
- **Committed in:** 19fdd93

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor lint fix, no scope change.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All data layer contracts ready for handler implementation (Plan 02-02, 02-03)
- Repositories expose all methods handlers will need (create, list, delete, count for limits)
- Keyboard builders produce correct layouts; handlers just need to call them
- i18n keys complete for all basket management messages

## Self-Check: PASSED

All 11 created files verified present. Both task commits (19fdd93, fc65dc2) verified in git log.

---
*Phase: 02-basket-and-product-management*
*Completed: 2026-03-31*
