---
phase: 04-analytics-charts-and-export
verified: 2026-03-30T00:00:00Z
status: passed
score: 16/16 must-haves verified
re_verification: false
---

# Phase 4: Analytics, Charts, and Export Verification Report

**Phase Goal:** Users can compare stores, visualize price trends, receive price drop alerts, and export their data
**Verified:** 2026-03-30
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | generate_changes_report() returns grouped text (increased, decreased, unchanged, unavailable) for a basket over N days | VERIFIED | analytics.py lines 91-157: four categorized lists built and formatted with bilingual headers and percentage changes |
| 2 | generate_comparison_report() returns per-store totals, matched items with price differences, and total cost difference with percentage | VERIFIED | comparison.py lines 101-201: arbuz/magnum split, fuzzy matching via SequenceMatcher, per-store totals, percentage diff |
| 3 | PriceHistoryRepository has methods to query price ranges and first/last prices for analytics | VERIFIED | price_history.py: get_price_range, get_first_prices_in_range, get_daily_basket_totals, get_export_data all present |
| 4 | generate_basket_chart() returns PNG bytes of a line chart showing basket total over time | VERIFIED | charts.py lines 160-211: async wrapper calls _generate_basket_chart_sync in run_in_executor; spot-check produced 31,761-byte PNG |
| 5 | generate_item_chart() returns PNG bytes with green discount dots and red X out-of-stock markers | VERIFIED | charts.py lines 92-157: scatter plots with #4CAF50 green dots and #F44336 red X markers, try/finally closes figure |
| 6 | generate_csv_bytes() returns UTF-8 bytes with BOM containing date,basket,source,product,quantity,unit_price,total,available columns | VERIFIED | export.py line 86: b"\xef\xbb\xbf" prepended; spot-check confirmed BOM and exact header |
| 7 | check_and_send_alerts() finds products with >10% price drop and sends bilingual alert messages | VERIFIED | alerts.py line 128: new_price < old_price * Decimal("0.9"), batched per-user messages with bilingual ALERT_STRINGS |
| 8 | User can send /changes and receive grouped price changes report | VERIFIED | analytics handler cmd_changes: parses days arg (default 7, clamp 1-90), calls generate_changes_report, splits long output |
| 9 | User can send /compare and receive cross-store comparison | VERIFIED | analytics handler cmd_compare: calls generate_comparison_report, splits output |
| 10 | User can send /chart and receive a basket total chart as Telegram photo | VERIFIED | cmd_chart: gets active basket, parses days (default 30, clamp 7-90), calls generate_basket_chart, sends via BufferedInputFile + answer_photo |
| 11 | User can send /chart_item N and receive an item price chart as Telegram photo | VERIFIED | cmd_chart_item: parses 1-based item index, calls generate_item_chart, sends via BufferedInputFile + answer_photo |
| 12 | User can send /export and receive a CSV document | VERIFIED | cmd_export: calls generate_export, sends via BufferedInputFile + answer_document with filename {basket.name}_prices.csv |
| 13 | Price drop alerts are sent automatically after daily scrape | VERIFIED | __main__.py lines 67-74: check_and_send_alerts hooked inside daily_scrape() after scrape_all_baskets completes |
| 14 | All user-facing messages across all handlers use get_text() with both RU and EN translations | VERIFIED | analytics.py handler uses get_text() throughout; 78-key parity confirmed in ru.py and en.py; all Phase 4 keys present |
| 15 | matplotlib.use('Agg') called before pyplot import | VERIFIED | charts.py line 15: matplotlib.use("Agg") before pyplot import on line 17 |
| 16 | Analytics router registered in bot dispatcher | VERIFIED | create.py line 36: dp.include_router(analytics.router); import on line 5 |

**Score:** 16/16 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/price_spy/db/repositories/price_history.py` | get_price_range(), get_first_prices_in_range() methods | VERIFIED | 205 lines; 4 new methods: get_price_range, get_first_prices_in_range, get_daily_basket_totals, get_export_data |
| `src/price_spy/services/analytics.py` | generate_changes_report() service | VERIFIED | 157 lines; full categorization logic with bilingual ANALYTICS_STRINGS |
| `src/price_spy/services/comparison.py` | generate_comparison_report() with fuzzy matching | VERIFIED | 201 lines; SequenceMatcher fuzzy matching with name normalization |
| `src/price_spy/services/charts.py` | Chart generation with matplotlib in run_in_executor | VERIFIED | 274 lines; Agg backend, run_in_executor, try/finally figure cleanup |
| `src/price_spy/services/export.py` | CSV export with BOM | VERIFIED | 137 lines; BOM at line 86: b"\xef\xbb\xbf" |
| `src/price_spy/services/alerts.py` | Price drop alert detection and sending | VERIFIED | 191 lines; check_and_send_alerts with TelegramForbiddenError and TelegramRetryAfter handling |
| `src/price_spy/bot/handlers/analytics.py` | Handlers for /changes, /compare, /chart, /chart_item, /export | VERIFIED | 217 lines; cmd_changes, cmd_compare, cmd_chart, cmd_chart_item, cmd_export all present |
| `src/price_spy/bot/create.py` | Analytics router registration | VERIFIED | analytics imported line 5, dp.include_router(analytics.router) line 36 |
| `src/price_spy/__main__.py` | Alert hook in daily_scrape function | VERIFIED | check_and_send_alerts called at lines 68-72 inside daily_scrape |
| `pyproject.toml` | matplotlib~=3.10 dependency | VERIFIED | Line 24: "matplotlib~=3.10" |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| services/analytics.py | db/repositories/price_history.py | get_first_prices_in_range and get_previous_prices | WIRED | Lines 84-85: both methods called |
| services/comparison.py | db/repositories/basket_item.py | get_basket_items_with_latest_price | WIRED | Lines 132, 143: called for both arbuz and magnum baskets |
| services/charts.py | matplotlib | matplotlib.use('Agg') before pyplot import | WIRED | Line 15 Agg, line 17 pyplot import |
| services/alerts.py | db/repositories/price_history.py | get_previous_prices for old price comparison | WIRED | Line 98: get_previous_prices called |
| bot/handlers/analytics.py | services/analytics.py | generate_changes_report import | WIRED | Line 46: lazy import inside handler |
| bot/handlers/analytics.py | services/charts.py | generate_basket_chart import | WIRED | Lines 113, 173: lazy imports inside handlers |
| __main__.py | services/alerts.py | check_and_send_alerts call after scrape_all_baskets | WIRED | Lines 68-72 inside daily_scrape try block |
| bot/create.py | bot/handlers/analytics.py | dp.include_router(analytics.router) | WIRED | Line 5 import, line 36 registration |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| analytics.py generate_changes_report | first_prices, latest_prices | get_first_prices_in_range(), get_previous_prices() via DISTINCT ON PostgreSQL query | Yes — queries PriceHistory table with real date range filters | FLOWING |
| comparison.py generate_comparison_report | arbuz_products, magnum_products | get_basket_items_with_latest_price() via DB | Yes — real DB query per basket | FLOWING |
| charts.py generate_basket_chart | daily_totals | get_daily_basket_totals() which calls get_price_range() | Yes — aggregates real PriceHistory records | FLOWING |
| charts.py generate_item_chart | records (PriceHistory list) | get_price_range([item.id], ...) | Yes — real DB query | FLOWING |
| export.py generate_export | records (PriceHistory list) | get_export_data() with selectinload | Yes — real DB query with eager loaded basket_item | FLOWING |
| alerts.py check_and_send_alerts | today_prices, previous_prices | get_price_range() and get_previous_prices() | Yes — real DB queries | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| _generate_basket_chart_sync produces valid PNG bytes | uv run python -c "from price_spy.services.charts import _generate_basket_chart_sync; r=_generate_basket_chart_sync(['01.01','02.01','03.01'],[1000.0,1100.0,1050.0],'T','P'); print(len(r))" | 31761 bytes | PASS |
| generate_csv_bytes produces BOM-prefixed CSV with correct header | uv run python -c "from price_spy.services.export import generate_csv_bytes; r=generate_csv_bytes([],'X','y'); assert r[:3]==b'\\xef\\xbb\\xbf'" | BOM and header confirmed | PASS |
| All Phase 4 i18n keys present and RU/EN parity at 78 keys each | uv run python -c "from price_spy.i18n.ru import STRINGS as ru; from price_spy.i18n.en import STRINGS as en; assert len(ru)==len(en)" | 78 == 78 | PASS |
| Analytics router loads and is named correctly | uv run python -c "from price_spy.bot.handlers.analytics import router; assert router.name=='analytics'" | Passed | PASS |
| Fuzzy matching returns correct product pairs | uv run python with two arbuz/magnum lists | 2 correct matches found | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ANLT-01 | 04-01 | User can view price changes over N days via /changes | SATISFIED | cmd_changes handler + generate_changes_report |
| ANLT-02 | 04-01 | Changes report groups items: increased, decreased, unchanged, unavailable | SATISFIED | analytics.py lines 91-156: four explicit lists |
| ANLT-03 | 04-01 | User can compare Arbuz vs Magnum basket totals via /compare | SATISFIED | cmd_compare + generate_comparison_report |
| ANLT-04 | 04-01 | Comparison shows per-item price differences where same product exists | SATISFIED | find_matching_products() with per-item diff formatting |
| ANLT-05 | 04-01 | Comparison shows total cost difference with percentage | SATISFIED | comparison.py lines 159-173: delta and pct computed |
| CHRT-01 | 04-02 | User can view basket total price chart via /chart | SATISFIED | cmd_chart + generate_basket_chart + answer_photo |
| CHRT-02 | 04-02 | User can view individual product price chart via /chart_item | SATISFIED | cmd_chart_item + generate_item_chart + answer_photo |
| CHRT-03 | 04-02 | Charts default to 30-day period, user can specify custom period | SATISFIED | Both generate_basket_chart and generate_item_chart default to days=30; handlers clamp args 7-90 |
| CHRT-04 | 04-02 | Charts mark discount prices (green dots) and out-of-stock (red X) | SATISFIED | charts.py lines 118-143: #4CAF50 scatter for discount, #F44336 scatter for OOS |
| CHRT-05 | 04-02 | Charts generated via matplotlib and sent as Telegram photos | SATISFIED | matplotlib Agg backend, run_in_executor, BufferedInputFile + answer_photo |
| ALRT-01 | 04-02 | Bot notifies user when product price drops by more than 10% | SATISFIED | alerts.py line 128: new_price < old_price * Decimal("0.9") |
| ALRT-02 | 04-02 | Alert includes product name, old price, new price, percentage drop | SATISFIED | ALERT_STRINGS format: "{name} dropped by {pct}%: {old} -> {new}" |
| EXPT-01 | 04-02 | User can export basket price history as CSV via /export | SATISFIED | cmd_export + generate_export + answer_document |
| EXPT-02 | 04-02 | CSV includes: date, basket, source, product, quantity, unit_price, total, available | SATISFIED | export.py CSV_HEADER constant, confirmed by spot-check |
| EXPT-03 | 04-02 | CSV is UTF-8 with BOM for Excel compatibility with Cyrillic text | SATISFIED | export.py line 86: b"\xef\xbb\xbf" + csv_text.encode("utf-8") |
| TXUX-03 | 04-03 | All user-facing messages are bilingual (RU and EN) | SATISFIED | 78-key parity in ru.py and en.py; all handlers use get_text(); service modules use local bilingual STRINGS dicts |

All 16 requirement IDs from plan frontmatter are covered. All 16 are marked complete in REQUIREMENTS.md. No orphaned requirements found.

---

### Anti-Patterns Found

No anti-patterns found. Scan of all 6 phase-4 source files produced zero TODO/FIXME/placeholder hits and zero empty return stubs. All data paths connect to real DB queries.

One item examined: the `charts_coming_soon` key in i18n files — this was intentionally retained and updated to redirect users to `/chart` and `/chart_item` commands. The key is still used by the basket action button inline keyboard handler. This is not a stub — it is a working redirect message.

---

### Human Verification Required

The following behaviors require running the bot against a live Telegram environment and cannot be verified programmatically:

#### 1. /changes Output Formatting

**Test:** Add a basket with 3+ items that have price history spanning 7 days. Send `/changes 7`.
**Expected:** Reply with grouped sections: red circle header for increased prices with bullet items showing old -> new and percentage; green circle for decreased; grey circle for unchanged count; sections omitted when empty.
**Why human:** Telegram message rendering with emoji and Unicode arrows cannot be confirmed by static analysis.

#### 2. /chart Photo Delivery

**Test:** Create a basket with price history across multiple days. Send `/chart`.
**Expected:** Bot sends "Generating chart..." then follows with a photo message containing the PNG line chart.
**Why human:** Telegram photo upload and rendering requires live bot session.

#### 3. /export Document Delivery and Excel Opening

**Test:** Send `/export` on a basket with price history.
**Expected:** Bot sends a .csv file attachment. Opening in Excel shows Cyrillic product names without garbling, with correct column layout.
**Why human:** Excel file opening and Cyrillic rendering cannot be tested without live environment.

#### 4. Price Drop Alert Trigger

**Test:** Manually lower a product's price in the DB by >10% relative to yesterday's record, then trigger daily_scrape.
**Expected:** Bot sends alert message to the relevant user within a few seconds.
**Why human:** Requires live bot session, DB manipulation, and scheduler trigger.

---

### Gaps Summary

No gaps. All 16 must-haves verified at all four levels (exists, substantive, wired, data flowing). All 16 requirement IDs satisfied. No blocker or warning anti-patterns found. Four items routed to human verification for final end-to-end testing in a live Telegram environment.

---

_Verified: 2026-03-30_
_Verifier: Claude (gsd-verifier)_
