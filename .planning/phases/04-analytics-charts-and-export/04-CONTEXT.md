# Phase 4: Analytics, Charts, and Export - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Source:** Auto-mode (recommended defaults selected)

<domain>
## Phase Boundary

Price change analytics (/changes), cross-store comparison (/compare), matplotlib price charts (/chart, /chart_item), automatic price drop alerts (>10%), CSV export (/export), and ensuring all user-facing messages across the entire bot are bilingual (TXUX-03).

</domain>

<decisions>
## Implementation Decisions

### Price Changes (/changes) (ANLT-01, ANLT-02)
- **D-01:** `/changes [N]` shows price changes over last N days (default 7). Groups items by: price increased (🔴), price decreased (🟢), unchanged (⚪), unavailable/restored. Format matches task.md section 7.2.
- **D-02:** Percentage shown for each changed item: "Молоко: 700 ₸ → 800 ₸ (+14.3%)"

### Cross-Store Comparison (/compare) (ANLT-03, ANLT-04, ANLT-05)
- **D-03:** `/compare` compares user's Arbuz basket(s) vs Magnum basket(s). Shows total cost per store and difference with percentage.
- **D-04:** Per-item comparison where same product exists in both stores — match by product name similarity (fuzzy match) since product_ids differ across stores. Show side-by-side prices.
- **D-05:** If user only has baskets from one store, show message "Need baskets from both Arbuz and Magnum to compare."

### Charts (/chart, /chart_item) (CHRT-01 through CHRT-05)
- **D-06:** matplotlib with clean style. Charts generated as PNG, sent as Telegram photos via `bot.send_photo()`.
- **D-07:** Basket total chart: X-axis dates, Y-axis tenge. Line plot of daily basket total over time.
- **D-08:** Individual item chart: single item price over time, with green dots for discount prices and red X markers for out-of-stock dates.
- **D-09:** Default period 30 days, user can specify: `/chart 14` or `/chart_item 3 60`.
- **D-10:** Chart styling: title in user's language, axis labels, grid lines, tenge symbol (₸) on Y-axis.

### Price Drop Alerts (ALRT-01, ALRT-02)
- **D-11:** Check for >10% price drops during the daily scrape job. After scraping completes and prices are stored, compare new prices against previous day's prices.
- **D-12:** Send alert immediately after detection: "🟢 [Product name] dropped by X%: old_price ₸ → new_price ₸"
- **D-13:** Alerts are per-user — only alert users who have the product in their baskets.

### CSV Export (/export) (EXPT-01, EXPT-02, EXPT-03)
- **D-14:** `/export` exports active basket's price history as CSV. Sent as Telegram document.
- **D-15:** CSV format per task.md section 7.4: date, basket, source, product, quantity, unit_price, total, available.
- **D-16:** UTF-8 encoding with BOM (\xEF\xBB\xBF) for Excel compatibility with Cyrillic text.

### Full Bilingual (TXUX-03)
- **D-17:** Audit all existing messages across all handlers — ensure every user-facing string uses get_text() with both RU and EN translations. Add any missing keys.
- **D-18:** New Phase 4 messages all use get_text() from the start.

### Carrying Forward from Prior Phases
- PriceHistoryRepository with get_previous_prices() — reuse for changes/comparison
- Daily scrape flow in __main__.py — hook alerts into post-scrape
- ScraperService result handling — ScrapeResult model
- i18n get_text() pattern — extend with all new keys
- Message splitting utility — reuse for long comparison/changes output
- Inline keyboard patterns — extend for chart/export navigation
- Report generation pattern from services/report.py — follow same structure

### Claude's Discretion
- Fuzzy matching algorithm for cross-store product comparison (Levenshtein, token overlap, etc.)
- matplotlib figure size and DPI for Telegram readability
- Whether to add a "comparative chart" (Arbuz vs Magnum lines) or keep it simple
- Chart color palette

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specification
- `task.md` — Section 7.2 (changes format), 7.3 (chart specs), 7.4 (CSV format), 6.1 (/changes, /chart, /chart_item, /compare, /export commands)

### Phase 1-3 Code
- `src/price_spy/services/report.py` — Report generation pattern, REPORT_STRINGS bilingual dict
- `src/price_spy/services/daily_scrape.py` — scrape_all_baskets() where alerts hook in
- `src/price_spy/services/message_utils.py` — split_message() for long output
- `src/price_spy/db/repositories/price_history.py` — get_previous_prices(), create()
- `src/price_spy/db/repositories/basket.py` — get_user_baskets_for_report()
- `src/price_spy/db/repositories/basket_item.py` — get_items_by_basket()
- `src/price_spy/bot/handlers/basket.py` — Handler pattern with inline keyboards
- `src/price_spy/bot/handlers/scrape.py` — /scrape pattern (command + progress)
- `src/price_spy/bot/create.py` — Router registration
- `src/price_spy/i18n/ru.py` — Russian translations
- `src/price_spy/i18n/en.py` — English translations
- `src/price_spy/__main__.py` — Scheduler jobs, bot reference pattern

### Research
- `.planning/research/FEATURES.md` — Cross-store comparison as key differentiator
- `.planning/research/PITFALLS.md` — Telegram flood control for alerts

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints
- `.planning/REQUIREMENTS.md` — Phase 4 requirements: ANLT-01..05, CHRT-01..05, ALRT-01..02, EXPT-01..03, TXUX-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PriceHistoryRepository` — query price history for charts/changes/export
- `generate_user_report()` pattern — follow for analytics services
- `REPORT_STRINGS` bilingual dict pattern — replicate for analytics strings
- `split_message()` — reuse for long /changes and /compare output
- `daily_scrape()` in __main__.py — hook price drop alert check after scrape
- `_bot_ref` module-level reference — use for sending alerts from scheduler context

### Established Patterns
- Service layer (services/) for business logic, handlers for bot interaction
- Repository pattern for DB queries
- i18n keys in both ru.py and en.py dictionaries
- Router registration in create.py

### Integration Points
- New analytics router registered in create.py
- Alert logic hooks into daily_scrape() post-scrape flow
- matplotlib must be available (already in pyproject.toml dependencies)
- CSV generation uses Python stdlib (csv, io modules)

</code_context>

<specifics>
## Specific Ideas

- task.md section 7.3 specifies chart parameters: X-axis dates, Y-axis tenge, green dots for discounts, red X for out-of-stock
- task.md section 7.4 has exact CSV column format
- Cross-store comparison is the primary differentiator (research FEATURES.md) — make it work well
- Telegram photo sending: generate PNG to BytesIO, send via bot.send_photo(chat_id, photo=BufferedInputFile)
- matplotlib needs `matplotlib.use('Agg')` for headless rendering (no display server)

</specifics>

<deferred>
## Deferred Ideas

None — auto-mode discussion stayed within phase scope

</deferred>

---

*Phase: 04-analytics-charts-and-export*
*Context gathered: 2026-03-31 via auto-mode*
