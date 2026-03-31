---
phase: 04-analytics-charts-and-export
plan: 01
subsystem: analytics-data-layer
tags: [analytics, comparison, repository, matplotlib]
dependency_graph:
  requires: [price_history_repository, basket_repository, basket_item_repository]
  provides: [analytics_service, comparison_service, extended_price_history_repo]
  affects: [charts, export, bot_commands]
tech_stack:
  added: [matplotlib~=3.10, difflib.SequenceMatcher]
  patterns: [bilingual_strings, DISTINCT_ON, fuzzy_matching, Python-side_aggregation]
key_files:
  created:
    - src/price_spy/services/analytics.py
    - src/price_spy/services/comparison.py
  modified:
    - pyproject.toml
    - src/price_spy/db/repositories/price_history.py
decisions:
  - Copied _format_number locally in analytics.py and comparison.py to avoid circular dependency with report.py
  - Used Python-side aggregation for daily basket totals (max 4500 records is manageable)
  - Used difflib.SequenceMatcher for fuzzy product matching with 0.6 threshold
metrics:
  duration: 3min
  completed: 2026-03-30
  tasks: 2
  files: 4
---

# Phase 04 Plan 01: Analytics Data Layer and Services Summary

Extended PriceHistoryRepository with 4 query methods (range, first-in-range, daily totals, export) and created analytics/comparison service modules with bilingual output and fuzzy cross-store product matching.

## Task Results

### Task 1: Add matplotlib dependency and extend PriceHistoryRepository
- **Commit:** 97bff4d
- **Files:** pyproject.toml, src/price_spy/db/repositories/price_history.py
- Added `matplotlib~=3.10` to project dependencies
- Added `get_price_range()` for date-range queries (charts/export)
- Added `get_first_prices_in_range()` using DISTINCT ON ASC (analytics)
- Added `get_daily_basket_totals()` with Python-side aggregation (charts)
- Added `get_export_data()` with selectinload for basket_item (CSV export)

### Task 2: Create analytics and comparison service modules
- **Commit:** ae13a9a
- **Files:** src/price_spy/services/analytics.py, src/price_spy/services/comparison.py
- `generate_changes_report()` groups items into increased/decreased/unchanged/unavailable with percentages
- `generate_comparison_report()` computes per-store totals with percentage difference
- `find_matching_products()` uses SequenceMatcher with name normalization (strips weight/volume suffixes)
- Both modules use bilingual STRINGS dicts (ru/en) following the report.py pattern

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functions are fully implemented with real logic.

## Verification

```
uv run python -c "from price_spy.services.analytics import generate_changes_report, ANALYTICS_STRINGS; print('analytics OK')"
uv run python -c "from price_spy.services.comparison import generate_comparison_report, find_matching_products, COMPARISON_STRINGS; print('comparison OK')"
grep -q "matplotlib" pyproject.toml && echo "matplotlib OK"
```

All verifications passed.
