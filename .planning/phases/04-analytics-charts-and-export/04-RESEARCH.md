# Phase 4: Analytics, Charts, and Export - Research

**Researched:** 2026-03-30
**Domain:** Price analytics, matplotlib charting, CSV export, Telegram bot alerts
**Confidence:** HIGH

## Summary

Phase 4 adds five major feature groups to the bot: price change analytics (/changes), cross-store comparison (/compare), matplotlib charts (/chart, /chart_item), automatic price drop alerts, and CSV export (/export). It also requires a bilingual audit to ensure TXUX-03 compliance across all existing and new messages.

The existing codebase provides strong foundations: PriceHistoryRepository for data queries, the REPORT_STRINGS bilingual dict pattern from report.py, split_message() for long output, and the daily_scrape() flow for hooking alerts. The primary technical risks are (1) matplotlib blocking the asyncio event loop (must use run_in_executor), (2) Telegram flood control when sending alert messages after daily scrape, and (3) fuzzy matching quality for cross-store product comparison.

**Primary recommendation:** Structure implementation as service-layer modules (analytics.py, charts.py, comparison.py, export.py) following the report.py pattern, with a single new analytics router handling all five commands. Add matplotlib to pyproject.toml as it is currently missing. Use `asyncio.get_event_loop().run_in_executor()` for all matplotlib rendering.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: `/changes [N]` shows price changes over last N days (default 7). Groups items by: price increased, price decreased, unchanged, unavailable/restored. Format matches task.md section 7.2.
- D-02: Percentage shown for each changed item: "Молоко: 700 ₸ -> 800 ₸ (+14.3%)"
- D-03: `/compare` compares user's Arbuz basket(s) vs Magnum basket(s). Shows total cost per store and difference with percentage.
- D-04: Per-item comparison where same product exists in both stores -- match by product name similarity (fuzzy match) since product_ids differ across stores. Show side-by-side prices.
- D-05: If user only has baskets from one store, show message "Need baskets from both Arbuz and Magnum to compare."
- D-06: matplotlib with clean style. Charts generated as PNG, sent as Telegram photos via bot.send_photo().
- D-07: Basket total chart: X-axis dates, Y-axis tenge. Line plot of daily basket total over time.
- D-08: Individual item chart: single item price over time, with green dots for discount prices and red X markers for out-of-stock dates.
- D-09: Default period 30 days, user can specify: `/chart 14` or `/chart_item 3 60`.
- D-10: Chart styling: title in user's language, axis labels, grid lines, tenge symbol on Y-axis.
- D-11: Check for >10% price drops during the daily scrape job. After scraping completes and prices are stored, compare new prices against previous day's prices.
- D-12: Send alert immediately after detection: "... [Product name] dropped by X%: old_price ₸ -> new_price ₸"
- D-13: Alerts are per-user -- only alert users who have the product in their baskets.
- D-14: `/export` exports active basket's price history as CSV. Sent as Telegram document.
- D-15: CSV format per task.md section 7.4: date, basket, source, product, quantity, unit_price, total, available.
- D-16: UTF-8 encoding with BOM (\xEF\xBB\xBF) for Excel compatibility with Cyrillic text.
- D-17: Audit all existing messages across all handlers -- ensure every user-facing string uses get_text() with both RU and EN translations. Add any missing keys.
- D-18: New Phase 4 messages all use get_text() from the start.

### Claude's Discretion
- Fuzzy matching algorithm for cross-store product comparison (Levenshtein, token overlap, etc.)
- matplotlib figure size and DPI for Telegram readability
- Whether to add a "comparative chart" (Arbuz vs Magnum lines) or keep it simple
- Chart color palette

### Deferred Ideas (OUT OF SCOPE)
None -- auto-mode discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANLT-01 | User can view price changes over N days via /changes command | New repository method get_price_history_range() + analytics service; follows report.py pattern |
| ANLT-02 | Changes report groups items by: price increased, price decreased, unchanged, unavailable | Service-layer grouping logic in analytics.py using comparison of first/last prices in range |
| ANLT-03 | User can compare Arbuz vs Magnum basket totals via /compare | comparison.py service fetching baskets by source, computing totals from latest prices |
| ANLT-04 | Comparison shows per-item price differences where same product exists in both stores | Fuzzy matching on product names (token-based recommended); see Architecture Patterns |
| ANLT-05 | Comparison shows total cost difference with percentage | Reuse _format_number() from report.py; percentage calculation pattern already in report.py |
| CHRT-01 | User can view basket total price chart over time via /chart command | matplotlib line chart; new get_basket_price_history() repo method; BytesIO + BufferedInputFile |
| CHRT-02 | User can view individual product price chart via /chart_item command | matplotlib with conditional markers for discount/out-of-stock |
| CHRT-03 | Charts default to 30-day period, user can specify custom period | Command argument parsing (same pattern as /changes N) |
| CHRT-04 | Charts mark discount prices (green dots) and out-of-stock periods (red X) | matplotlib scatter overlay on line plot using original_price and is_available fields |
| CHRT-05 | Charts are generated via matplotlib and sent as Telegram photos | run_in_executor for thread safety; BufferedInputFile from BytesIO buffer |
| ALRT-01 | Bot notifies user when a product price drops by more than 10% | Post-scrape hook in daily_scrape(); compare new vs previous prices |
| ALRT-02 | Alert includes product name, old price, new price, and percentage drop | Bilingual alert message template in i18n |
| EXPT-01 | User can export basket price history as CSV via /export | csv.writer to StringIO/BytesIO; sent as BufferedInputFile document |
| EXPT-02 | CSV includes: date, basket name, source, product, quantity, unit price, total, availability | New repo method to fetch full price history with item/basket joins |
| EXPT-03 | CSV is UTF-8 with BOM for Excel compatibility with Cyrillic text | Prepend b'\xef\xbb\xbf' to output bytes |
| TXUX-03 | All user-facing messages are bilingual (Russian and English based on user preference) | Audit existing handlers; add missing keys to ru.py and en.py |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| matplotlib | ~=3.10 | Chart generation (PNG) | Already in project stack definition (CLAUDE.md). Generates static PNGs for Telegram. Must add to pyproject.toml (currently missing). |
| csv (stdlib) | -- | CSV export | Built-in Python module. No external library needed. |
| io (stdlib) | -- | BytesIO/StringIO for in-memory file generation | Standard pattern for Telegram file sending without disk I/O. |
| difflib (stdlib) | -- | SequenceMatcher for fuzzy product name matching | No external dependency needed; sufficient for token-based similarity. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiogram BufferedInputFile | (bundled) | Send in-memory bytes as Telegram photos/documents | For chart PNGs and CSV files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| difflib.SequenceMatcher | python-Levenshtein / rapidfuzz | External dep for marginal improvement; difflib is sufficient for grocery product names |
| matplotlib | plotly | Plotly generates interactive HTML, not static PNGs needed by Telegram |

**Installation (add to pyproject.toml):**
```bash
uv add "matplotlib~=3.10"
```

## Architecture Patterns

### Recommended Project Structure
```
src/price_spy/
├── services/
│   ├── analytics.py       # /changes logic (ANLT-01, ANLT-02)
│   ├── comparison.py      # /compare logic (ANLT-03..05)
│   ├── charts.py          # matplotlib chart generation (CHRT-01..05)
│   ├── export.py          # CSV export (EXPT-01..03)
│   ├── alerts.py          # Price drop detection + notification (ALRT-01..02)
│   ├── report.py          # (existing) daily report
│   ├── daily_scrape.py    # (existing) add alert hook post-scrape
│   └── message_utils.py   # (existing) split_message()
├── bot/handlers/
│   ├── analytics.py       # NEW: /changes, /compare, /chart, /chart_item, /export handlers
│   └── ...                # (existing handlers)
├── db/repositories/
│   └── price_history.py   # (extend) add range queries for analytics/charts/export
├── i18n/
│   ├── ru.py              # (extend) add Phase 4 keys + audit gaps
│   └── en.py              # (extend) add Phase 4 keys + audit gaps
└── __main__.py            # (modify) hook alerts into daily_scrape job
```

### Pattern 1: Service-Layer Analytics (follow report.py)
**What:** Each analytics feature is a service function that takes a session + user/basket and returns formatted text or bytes.
**When to use:** All /changes, /compare, /export logic.
**Example:**
```python
# services/analytics.py — follows report.py pattern
ANALYTICS_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "changes_title": "📈 Изменения цен за {days} дней",
        "price_increased_header": "🔴 Подорожали:",
        "price_decreased_header": "🟢 Подешевели:",
        "unchanged_header": "⚪ Без изменений: {count} товаров",
        "unavailable_header": "🔴 Пропали из наличия: {count} товар(ов)",
        # ...
    },
    "en": { ... },
}

async def generate_changes_report(
    session: AsyncSession, user_id: int, basket_id: int, days: int, lang: str
) -> str | None:
    """Generate price changes report for a basket over N days."""
    # Query price history for first and last prices in range
    # Group into increased/decreased/unchanged/unavailable
    # Format using bilingual strings
```

### Pattern 2: matplotlib in run_in_executor (CRITICAL)
**What:** matplotlib is not async-safe and blocks the event loop. All chart generation MUST run in a thread executor.
**When to use:** Every chart generation call.
**Example:**
```python
# services/charts.py
import asyncio
import io
import matplotlib
matplotlib.use('Agg')  # Headless backend — MUST be before pyplot import
import matplotlib.pyplot as plt

def _generate_basket_chart_sync(
    dates: list[str], totals: list[float], title: str, ylabel: str
) -> bytes:
    """Synchronous chart generation — runs in executor."""
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    ax.plot(dates, totals, marker='o', linewidth=2, color='#2196F3')
    ax.set_title(title, fontsize=14)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,} ₸'.replace(',', ' ')))
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)  # CRITICAL: prevent memory leak
    buf.seek(0)
    return buf.read()

async def generate_basket_chart(
    dates: list[str], totals: list[float], title: str, ylabel: str
) -> bytes:
    """Async wrapper — runs matplotlib in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _generate_basket_chart_sync, dates, totals, title, ylabel
    )
```

### Pattern 3: Sending Charts/Files via Telegram
**What:** Use aiogram's BufferedInputFile for in-memory file sending.
**When to use:** Chart PNGs and CSV documents.
**Example:**
```python
from aiogram.types import BufferedInputFile

# Chart as photo
chart_bytes = await generate_basket_chart(dates, totals, title, ylabel)
photo = BufferedInputFile(chart_bytes, filename="chart.png")
await message.answer_photo(photo=photo)

# CSV as document
csv_bytes = generate_csv_export(history_data)
doc = BufferedInputFile(csv_bytes, filename=f"price_history_{basket.name}.csv")
await message.answer_document(document=doc)
```

### Pattern 4: Fuzzy Product Name Matching (cross-store comparison)
**What:** Match products across Arbuz and Magnum baskets by name similarity.
**When to use:** /compare per-item matching (ANLT-04).
**Example:**
```python
from difflib import SequenceMatcher

def _normalize_name(name: str) -> str:
    """Normalize product name for comparison."""
    # Lowercase, strip brand prefixes, remove packaging info
    name = name.lower().strip()
    # Remove weight/volume suffixes like "0.8 л", "425 мл", "1 кг"
    import re
    name = re.sub(r'\d+[.,]?\d*\s*(л|мл|кг|г|шт)\b', '', name)
    return name.strip()

def find_matching_products(
    arbuz_items: list[tuple[str, Decimal]],  # (name, price)
    magnum_items: list[tuple[str, Decimal]],
    threshold: float = 0.6,
) -> list[tuple[str, Decimal, str, Decimal, float]]:
    """Find matching products between stores by name similarity.

    Returns: [(arbuz_name, arbuz_price, magnum_name, magnum_price, similarity)]
    """
    matches = []
    used_magnum = set()

    for a_name, a_price in arbuz_items:
        best_score = 0.0
        best_idx = -1
        a_norm = _normalize_name(a_name)

        for i, (m_name, m_price) in enumerate(magnum_items):
            if i in used_magnum:
                continue
            m_norm = _normalize_name(m_name)
            score = SequenceMatcher(None, a_norm, m_norm).ratio()
            if score > best_score:
                best_score = score
                best_idx = i

        if best_score >= threshold and best_idx >= 0:
            m_name, m_price = magnum_items[best_idx]
            matches.append((a_name, a_price, m_name, m_price, best_score))
            used_magnum.add(best_idx)

    return matches
```

**Recommendation:** Use `difflib.SequenceMatcher` with a 0.6 threshold. This is sufficient for grocery product names which tend to share common terms (brand + product type). No external dependency needed. The threshold can be tuned based on real data.

### Pattern 5: Price Drop Alert Hook in daily_scrape()
**What:** After scrape_all_baskets() completes, compare new prices to previous and send alerts.
**When to use:** ALRT-01, ALRT-02 -- triggered from __main__.py daily_scrape().
**Example:**
```python
# In __main__.py daily_scrape():
async def daily_scrape() -> None:
    from price_spy.services.daily_scrape import scrape_all_baskets
    from price_spy.services.alerts import check_and_send_alerts

    results = await scrape_all_baskets()
    # After scrape, check for price drops and alert users
    bot = deliver_reports._bot  # Reuse same bot reference pattern
    await check_and_send_alerts(bot)
```

### Pattern 6: CSV Export with BOM
**What:** Generate UTF-8 CSV with BOM prefix for Excel Cyrillic compatibility.
**Example:**
```python
import csv
import io

def generate_csv_bytes(rows: list[dict], basket_name: str, source: str) -> bytes:
    """Generate CSV bytes with UTF-8 BOM for Excel compatibility."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "basket", "source", "product", "quantity", "unit_price", "total", "available"])
    for row in rows:
        writer.writerow([
            row["date"].strftime("%Y-%m-%d"),
            basket_name,
            source,
            row["product_name"],
            row["quantity"],
            row["unit_price"],
            row["unit_price"] * row["quantity"],
            row["available"],
        ])
    csv_str = output.getvalue()
    return b'\xef\xbb\xbf' + csv_str.encode('utf-8')
```

### Anti-Patterns to Avoid
- **matplotlib at module level:** Importing matplotlib.pyplot at import time adds 2-3 seconds to cold start. Use lazy imports inside chart functions.
- **Synchronous matplotlib in async handler:** Will freeze the bot for all users during chart generation. Always use run_in_executor.
- **plt.show() or plt.figure() without plt.close():** Memory leak. Every figure must be explicitly closed after saving.
- **Generating chart to disk file:** Unnecessary I/O. Use BytesIO buffer directly.
- **Hardcoded strings in handlers:** All user-facing text must go through get_text() for TXUX-03 compliance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| String similarity | Custom Levenshtein implementation | `difflib.SequenceMatcher` | Stdlib, well-tested, sufficient accuracy for grocery names |
| CSV generation | Manual string formatting | `csv.writer` | Handles quoting, escaping, commas in product names correctly |
| Number formatting | Custom formatter | Reuse `_format_number()` from report.py | Already handles space-separated thousands for tenge |
| Message splitting | Custom splitter | `split_message()` from message_utils.py | Already handles Telegram 4096 char limit |
| Chart PNG output | Save to temp file then read | `BytesIO` buffer | No filesystem dependency, works in containers |

**Key insight:** Most analytics outputs are text formatting + data queries. The existing report.py establishes the exact pattern (bilingual strings dict, service function, format helpers). Follow it exactly.

## Common Pitfalls

### Pitfall 1: matplotlib Blocking the Event Loop
**What goes wrong:** Chart generation takes 0.5-2 seconds synchronously. During this time, the bot cannot process any other messages.
**Why it happens:** matplotlib is CPU-bound and not async-aware. Calling it directly in an async handler blocks the entire event loop.
**How to avoid:** Always wrap chart generation in `asyncio.get_event_loop().run_in_executor(None, sync_func, ...)`.
**Warning signs:** Bot becomes unresponsive when multiple users request charts simultaneously.

### Pitfall 2: matplotlib Memory Leaks from Unclosed Figures
**What goes wrong:** Each chart request creates a new Figure object. Without explicit `plt.close(fig)`, figures accumulate in memory. After ~100 chart requests, the process consumes gigabytes of RAM.
**Why it happens:** matplotlib keeps references to all open figures for its interactive GUI mode, even when using the Agg backend.
**How to avoid:** Always call `plt.close(fig)` in a `finally` block after saving to BytesIO. Never use `plt.figure()` without a corresponding close.
**Warning signs:** Memory usage grows linearly with chart requests.

### Pitfall 3: matplotlib.use('Agg') Must Come Before pyplot Import
**What goes wrong:** ImportError or matplotlib tries to connect to a display server (crashes in Docker/headless).
**Why it happens:** matplotlib.pyplot initializes the backend on import. If pyplot is imported before `matplotlib.use('Agg')`, the backend is already locked.
**How to avoid:** Put `matplotlib.use('Agg')` at the very top of charts.py, before any `import matplotlib.pyplot`.
**Warning signs:** "Tcl_AsyncDelete: async handler deleted by the wrong thread" or "no display name" errors.

### Pitfall 4: Telegram Flood Control During Alert Sending
**What goes wrong:** After daily scrape, if multiple products dropped >10% across multiple users, sending all alerts at once triggers Telegram 429 rate limiting.
**Why it happens:** scrape_all_baskets() processes all users' baskets, potentially generating dozens of alerts that are sent in rapid succession.
**How to avoid:** Add 1-second delay between users when sending alerts (same pattern as deliver_reports). Catch TelegramRetryAfter and respect retry_after. Batch multiple alerts for the same user into a single message.
**Warning signs:** TelegramRetryAfter exceptions in logs after daily scrape.

### Pitfall 5: /chart_item with Invalid Item Number
**What goes wrong:** User sends `/chart_item 99` but only has 12 items. Or sends `/chart_item abc`.
**Why it happens:** No input validation on the item number argument.
**How to avoid:** Validate item number is a positive integer and within the basket's item count. Return a helpful error message.
**Warning signs:** Unhandled exceptions in handler.

### Pitfall 6: Empty Price History for Charts
**What goes wrong:** User creates a basket and immediately requests /chart. No price history exists yet, matplotlib receives empty arrays and either crashes or generates a meaningless chart.
**Why it happens:** Charts require at least 2 data points to be useful.
**How to avoid:** Check data availability before generating chart. Return a message like "Not enough price history yet. Try again after the next scrape."
**Warning signs:** Empty or single-point charts being sent.

### Pitfall 7: Cross-Store Comparison with No Overlapping Products
**What goes wrong:** User has Arbuz basket with "Молоко Amiran" and Magnum basket with "Курица филе" -- zero product overlap. Per-item comparison section is empty.
**Why it happens:** Fuzzy matching finds no matches above threshold.
**How to avoid:** Show total comparison (works regardless of overlap) and note "No matching products found for per-item comparison" when overlap is zero.
**Warning signs:** Confusing empty comparison reports.

## Code Examples

### New Repository Methods Needed

```python
# price_history.py — add these methods

async def get_price_range(
    self,
    basket_item_ids: list[int],
    start_date: datetime.datetime,
    end_date: datetime.datetime,
) -> list[PriceHistory]:
    """Get all price history records for items within a date range.

    Used by /changes and /chart commands.
    """
    stmt = (
        select(PriceHistory)
        .where(
            PriceHistory.basket_item_id.in_(basket_item_ids),
            PriceHistory.scraped_at >= start_date,
            PriceHistory.scraped_at <= end_date,
        )
        .order_by(PriceHistory.scraped_at)
    )
    result = await self._session.execute(stmt)
    return list(result.scalars().all())

async def get_first_prices_in_range(
    self,
    basket_item_ids: list[int],
    start_date: datetime.datetime,
) -> dict[int, tuple[Decimal | None, bool]]:
    """Get the earliest price for each item after start_date.

    Used by /changes to compute old prices.
    Uses DISTINCT ON (PostgreSQL) for efficiency.
    """
    stmt = (
        select(
            PriceHistory.basket_item_id,
            PriceHistory.price,
            PriceHistory.is_available,
        )
        .where(
            PriceHistory.basket_item_id.in_(basket_item_ids),
            PriceHistory.scraped_at >= start_date,
        )
        .distinct(PriceHistory.basket_item_id)
        .order_by(
            PriceHistory.basket_item_id,
            PriceHistory.scraped_at.asc(),  # ASC for earliest
        )
    )
    result = await self._session.execute(stmt)
    return {row[0]: (row[1], row[2]) for row in result.all()}

async def get_daily_basket_totals(
    self,
    basket_item_ids: list[int],
    quantities: dict[int, int],
    start_date: datetime.datetime,
) -> list[tuple[datetime.date, Decimal]]:
    """Get daily basket total (sum of price * quantity) for charting.

    Groups by date, uses the latest price per item per day.
    """
    # Implementation: subquery for latest price per item per day,
    # then aggregate with quantities
    ...
```

### Handler Pattern (analytics router)

```python
# bot/handlers/analytics.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from price_spy.db.models.user import User
from price_spy.i18n import get_text

router = Router(name="analytics")

@router.message(Command("changes"))
async def cmd_changes(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    # Parse optional days argument
    args = message.text.split()
    days = 7  # default
    if len(args) > 1:
        try:
            days = int(args[1])
            days = max(1, min(days, 90))
        except ValueError:
            await message.answer(get_text("changes_invalid_days", lang))
            return

    # Delegate to service
    from price_spy.services.analytics import generate_changes_report
    report = await generate_changes_report(session, user.id, days, lang)
    if report is None:
        await message.answer(get_text("changes_no_data", lang))
        return

    from price_spy.services.message_utils import split_message
    for part in split_message(report):
        await message.answer(part)
```

### i18n Keys to Add (both ru.py and en.py)

```python
# Approximate list of new keys needed:
# Analytics (/changes)
"changes_title", "changes_increased_header", "changes_decreased_header",
"changes_unchanged", "changes_unavailable", "changes_restored",
"changes_item_line", "changes_no_data", "changes_invalid_days",

# Comparison (/compare)
"compare_title", "compare_store_total", "compare_difference",
"compare_cheaper", "compare_same_price", "compare_need_both_stores",
"compare_matched_header", "compare_no_matches", "compare_item_line",

# Charts (/chart, /chart_item)
"chart_title_basket", "chart_title_item", "chart_no_data",
"chart_ylabel", "chart_generating", "chart_item_not_found",
"chart_invalid_period", "chart_invalid_item",

# Alerts
"alert_price_drop",

# Export (/export)
"export_generating", "export_no_data", "export_filename",

# Help update — add new commands to help text
```

### Bilingual Audit Approach (TXUX-03)

```python
# Strategy: grep all handlers for hardcoded strings
# Check pattern: any string in await message.answer() or
# await message.edit_text() that is NOT wrapped in get_text()
#
# Known areas to audit:
# - bot/handlers/start.py
# - bot/handlers/basket.py
# - bot/handlers/product.py
# - bot/handlers/settings.py
# - bot/handlers/scrape.py
# - services/report.py (uses REPORT_STRINGS, may have gaps)
# - Any error messages or edge case responses
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| matplotlib plt.savefig(filename) | BytesIO buffer + BufferedInputFile | Standard since aiogram 3.x | No temp files needed |
| matplotlib.pyplot global state | Explicit Figure/Axes creation | Best practice | Avoids state leaks between chart types |
| BeautifulSoup for text similarity | difflib.SequenceMatcher | Always available | No external dependency |
| Sync chart in handler | run_in_executor | asyncio pattern | Non-blocking chart generation |

## Open Questions

1. **Fuzzy match threshold tuning**
   - What we know: SequenceMatcher with 0.6 threshold should work for grocery names
   - What's unclear: Real product names from Arbuz vs Magnum may vary significantly (different brands, transliterations)
   - Recommendation: Start with 0.6, log match scores, tune based on real data. Can be adjusted without architectural changes.

2. **Comparative chart (Arbuz vs Magnum dual-line)**
   - What we know: CONTEXT.md lists this as Claude's discretion
   - Recommendation: Skip for now. The /compare command provides textual comparison. A dual-line chart adds complexity with limited value until users request it.

3. **Alert batching strategy**
   - What we know: Multiple products may drop simultaneously during a sale event
   - Recommendation: Batch all price drop alerts for one user into a single message to reduce Telegram API calls and improve readability.

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python only -- aiogram 3, matplotlib, SQLAlchemy 2, asyncpg
- **Hosting:** Railway (Starter plan)
- **i18n pattern:** Dictionary-based with get_text() lookup; both ru.py and en.py must be kept in sync
- **Service pattern:** Business logic in services/, handlers for bot interaction, repository pattern for DB
- **Session pattern:** Scheduled jobs open their own async_session context (self-managed sessions)
- **Bot reference pattern:** Module-level _bot reference for sending from scheduler context (deliver_reports._bot)
- **Middleware chain:** DbSession (outer) then I18n (inner)
- **Callback prefixes:** Short prefixes to stay within 64-byte Telegram limit
- **REPORT_STRINGS pattern:** Report-specific bilingual strings defined locally in service module (report.py precedent)
- **GSD workflow:** Do not make direct repo edits outside a GSD workflow unless explicitly asked

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - matplotlib is the locked choice; csv/io/difflib are stdlib
- Architecture: HIGH - follows established patterns from Phases 1-3
- Pitfalls: HIGH - matplotlib async issues and Telegram flood control are well-documented
- Fuzzy matching: MEDIUM - algorithm choice is sound but threshold needs real-data tuning

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no fast-moving dependencies)

## Sources

### Primary (HIGH confidence)
- Existing codebase: report.py, daily_scrape.py, price_history.py, create.py, __main__.py (patterns to follow)
- task.md sections 7.2, 7.3, 7.4 (exact format specifications)
- CONTEXT.md D-01 through D-18 (locked implementation decisions)

### Secondary (MEDIUM confidence)
- PITFALLS.md Pitfall 5 (Telegram flood control) - verified against aiogram docs
- Performance Traps section in PITFALLS.md (matplotlib in run_in_executor)
- CLAUDE.md stack definition (matplotlib ~=3.10 specified)

### Tertiary (LOW confidence)
- Fuzzy matching threshold (0.6) - reasonable default but needs real-data validation
