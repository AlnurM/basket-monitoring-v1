---
phase: 02-basket-and-product-management
plan: 03
subsystem: bot
tags: [aiogram, telegram, scraper, product-management, price-history, apscheduler]

# Dependency graph
requires:
  - phase: 02-01
    provides: "DB models, repositories (BasketItem, PriceHistory, Basket)"
  - phase: 02-02
    provides: "Basket handlers, keyboards, callback factories, FSM states"
provides:
  - "Product URL handler (FSM add flow + freeform URL detection)"
  - "URL validation (format + source match)"
  - "First-scrape with price history storage"
  - "Paginated item list with prices, discounts, availability"
  - "Item removal with confirmation"
  - "Monthly price history cleanup job"
affects: [phase-03-daily-scraping, phase-04-analytics]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared _process_urls helper for FSM and freeform URL flows"
    - "Router registration order: start -> basket -> product (FSM before URL catch-all)"

key-files:
  created:
    - src/price_spy/bot/handlers/product.py
  modified:
    - src/price_spy/bot/create.py
    - src/price_spy/__main__.py

key-decisions:
  - "Extracted _process_urls helper to avoid duplication between FSM and freeform URL handlers"
  - "Full basket total calculated across all items, not just current page"

patterns-established:
  - "Product handler pattern: validate URL, check limits, create item, scrape, store price history"
  - "Pagination helper _build_items_text separates display logic from handler"

requirements-completed: [PROD-01, PROD-02, PROD-03, PROD-04, PROD-05, PROD-06, PROD-07, PROD-08, PROD-09, HIST-01, HIST-02, HIST-03]

# Metrics
duration: 2min
completed: 2026-03-31
---

# Phase 02 Plan 03: Product Management Handlers Summary

**Product URL input with validation, first-scrape price storage, paginated item display with discount/availability markers, item removal with confirmation, and monthly price history cleanup via APScheduler**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-31T06:56:52Z
- **Completed:** 2026-03-31T06:59:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Product URL handler processes URLs from both FSM add flow and freeform messages with validation, first-scrape, and price history storage
- Paginated item display with numbered lines showing prices, discount strikethrough, and unavailability markers
- Item removal with confirmation step using confirm_remove_item_keyboard
- Monthly cleanup job registered in APScheduler (1st of month at 03:00, deletes records older than 90 days)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement product handlers (URL input, item display, removal)** - `ea51f47` (feat)
2. **Task 2: Add monthly price history cleanup job to scheduler** - `e14ec04` (feat)

## Files Created/Modified
- `src/price_spy/bot/handlers/product.py` - Product URL handler with parse, validate, scrape, display, remove (307 lines)
- `src/price_spy/bot/create.py` - Added product router registration (3rd router)
- `src/price_spy/__main__.py` - Added cleanup_old_prices function and monthly scheduler job

## Decisions Made
- Extracted shared `_process_urls` helper to avoid code duplication between FSM `receive_product_urls` and freeform `handle_url_message`
- Basket total computed across all items (not just current page) for accuracy in paginated views
- ScraperService.close() called in finally block to ensure cleanup after first-scrape

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all handlers are fully wired with data sources.

## Next Phase Readiness
- Product flow complete: add by URL, view items with prices, remove items
- Price history accumulates on first scrape, ready for daily scraping in Phase 3
- Cleanup job ensures old records are pruned automatically

---
*Phase: 02-basket-and-product-management*
*Completed: 2026-03-31*
