---
phase: 04-analytics-charts-and-export
plan: 02
subsystem: analytics
tags: [matplotlib, csv, alerts, charts, telegram]

# Dependency graph
requires:
  - phase: 04-01
    provides: "Repository methods (get_daily_basket_totals, get_price_range, get_export_data, get_previous_prices)"
provides:
  - "Chart generation service (basket total + item price PNG charts)"
  - "CSV export service with UTF-8 BOM"
  - "Price drop alert detection and notification service"
affects: [04-03-handlers]

# Tech tracking
tech-stack:
  added: [matplotlib]
  patterns: [run_in_executor for CPU-bound chart generation, UTF-8 BOM for Excel/Cyrillic CSV]

key-files:
  created:
    - src/price_spy/services/charts.py
    - src/price_spy/services/export.py
    - src/price_spy/services/alerts.py

key-decisions:
  - "Copied _format_number locally in each service to avoid circular deps (same as 04-01)"
  - "Lazy-load User inside alerts loop to avoid extra query when no alerts found"

patterns-established:
  - "run_in_executor pattern: sync chart functions wrapped in async with try/finally for figure cleanup"
  - "UTF-8 BOM prefix pattern: b'\\xef\\xbb\\xbf' + csv_text.encode('utf-8') for Excel compatibility"

requirements-completed: [CHRT-01, CHRT-02, CHRT-03, CHRT-04, CHRT-05, ALRT-01, ALRT-02, EXPT-01, EXPT-02, EXPT-03]

# Metrics
duration: 3min
completed: 2026-03-31
---

# Phase 04 Plan 02: Charts, CSV Export, and Price Alerts Summary

**Matplotlib PNG chart generation with run_in_executor, UTF-8 BOM CSV export, and >10% price drop alert notifications**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-31T08:52:39Z
- **Completed:** 2026-03-31T08:55:50Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Basket total line chart and individual item price chart as PNG bytes via matplotlib Agg backend
- Item charts mark discount prices with green dots and out-of-stock with red X markers
- CSV export with UTF-8 BOM, 8-column format (date, basket, source, product, quantity, unit_price, total, available)
- Price drop alert service detecting >10% drops, batched bilingual notifications per user

## Task Commits

Each task was committed atomically:

1. **Task 1: Create chart generation service with matplotlib** - `6c1cf78` (feat)
2. **Task 2: Create CSV export service and price drop alert service** - `41790c8` (feat)

## Files Created/Modified
- `src/price_spy/services/charts.py` - Basket total and item price chart PNG generation using matplotlib with run_in_executor
- `src/price_spy/services/export.py` - CSV export with UTF-8 BOM for Excel/Cyrillic compatibility
- `src/price_spy/services/alerts.py` - Price drop detection (>10%) and batched Telegram alert delivery

## Decisions Made
- Copied _format_number locally in export.py and alerts.py to avoid cross-module import (same pattern as 04-01)
- Lazy-load User model inside alerts loop to skip DB query when no price drops detected for a user
- Used FuncFormatter for y-axis tenge formatting with space-separated thousands

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three service modules ready for handler wiring in Plan 03
- charts.py provides generate_basket_chart and generate_item_chart for /chart and /chart_item commands
- export.py provides generate_export for /export command
- alerts.py provides check_and_send_alerts for scheduler integration after daily scrape

---
*Phase: 04-analytics-charts-and-export*
*Completed: 2026-03-31*
