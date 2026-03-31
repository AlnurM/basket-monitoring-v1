---
phase: 03-scheduling-and-daily-reports
verified: 2026-03-30T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Send /notify 08:30 in Telegram and verify bot replies with 'Notification time set to: 08:30'"
    expected: "Bot confirms new notification time and stores it persistently across restarts"
    why_human: "Requires live bot session and database write to verify end-to-end"
  - test: "Wait until configured notify_time and verify report is delivered"
    expected: "Report arrives with per-item prices, total, yesterday comparison, price change arrows, and out-of-stock markers"
    why_human: "Requires real scheduled execution, scraped price data from two consecutive days, and live Telegram delivery"
  - test: "Send /scrape, wait 5 seconds, verify progress message is edited to show item results"
    expected: "Initial 'Scraping N item(s)...' message is replaced (edited) with final per-item results"
    why_human: "message.edit_text() behavior can only be confirmed in a live Telegram session"
  - test: "Send /scrape twice within 1 hour and verify second call is rejected with cooldown message"
    expected: "Bot replies with rate limit message showing remaining minutes"
    why_human: "In-memory rate limit state (_last_scrape dict) and timing requires live user session"
---

# Phase 3: Scheduling and Daily Reports Verification Report

**Phase Goal:** Users receive automated daily price reports at their preferred time, with price changes highlighted and out-of-stock items flagged
**Verified:** 2026-03-30
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Bot automatically scrapes all active baskets daily at 07:00 Asia/Almaty | VERIFIED | `daily_scrape()` in `__main__.py` calls `scrape_all_baskets()`; CronTrigger(hour=settings.scrape_daily_hour) with default `scrape_daily_hour=7`; no placeholder text in function body |
| 2 | User receives a daily report at their configured time showing per-item prices, basket total, and change from previous day | VERIFIED | `deliver_reports()` runs via IntervalTrigger(minutes=1); queries `get_users_by_notify_time(current_time)`; calls `generate_user_report()`; report includes `basket_total`, `yesterday_comparison`, and per-item `item_price` strings |
| 3 | Daily report highlights items that changed price (was/became) and flags out-of-stock items | VERIFIED | `generate_basket_section()` uses `get_previous_prices()` for yesterday comparison; applies `price_decreased`/`price_increased` strings with delta and old price; renders `out_of_stock` marker when `is_available=False` |
| 4 | User can configure notification time via /notify command (default 09:00 Asia/Almaty) | VERIFIED | `settings.py` handler parses HH:MM, validates 0-23/0-59, writes `user.notify_time`; `User` model default is `datetime.time(9, 0)`; i18n keys `notify_current`, `notify_updated`, `notify_usage`, `notify_invalid_format` present in both RU and EN |
| 5 | User can trigger a manual scrape via /scrape with rate limiting (1/hour) and progress feedback | VERIFIED | `scrape.py` handler has `_last_scrape` dict and `SCRAPE_COOLDOWN=3600`; sends progress message then calls `scrape_single_basket(basket.id)`; edits message with `progress_msg.edit_text()` for feedback |

**Score:** 5/5 truths verified

---

### Required Artifacts

#### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/price_spy/services/daily_scrape.py` | Scrape orchestration for all baskets and single-basket | VERIFIED | 161 lines; `scrape_all_baskets()` and `scrape_single_basket()` both async; URL deduplication map built; `ScraperService.scrape_urls()` called; PriceHistory written per item |
| `src/price_spy/services/report.py` | Report text generation per user | VERIFIED | 263 lines; `generate_user_report()` and `generate_basket_section()` async; REPORT_STRINGS dict with all required keys in RU/EN; price change logic; out-of-stock markers; comparison section |
| `src/price_spy/services/message_utils.py` | Telegram message splitting utility | VERIFIED | `MAX_MESSAGE_LENGTH=4096`; `split_message()` splits at newline boundaries; handles edge case of no newline before limit |
| `src/price_spy/db/repositories/basket.py` | `get_all_active_baskets`, `get_user_baskets_for_report` | VERIFIED | Both methods present; `get_all_active_baskets` queries all baskets (no is_active filter) ordered by user_id, id; `get_user_baskets_for_report` filters by user_id |
| `src/price_spy/db/repositories/user.py` | `get_users_by_notify_time` | VERIFIED | Method present; `select(User).where(User.notify_time == target_time)` |
| `src/price_spy/db/repositories/price_history.py` | `get_previous_prices` for yesterday comparison | VERIFIED | Method present; DISTINCT ON pattern via `.distinct(PriceHistory.basket_item_id)`; returns `dict[int, tuple[Decimal | None, bool]]` |
| `src/price_spy/db/repositories/basket_item.py` | `get_items_by_basket` | VERIFIED | Method present; simple select by basket_id for URL extraction |

#### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/price_spy/__main__.py` | Real `daily_scrape()` and `deliver_reports()` scheduler jobs | VERIFIED | `daily_scrape()` calls `scrape_all_baskets()`; no "placeholder" text; `deliver_reports()` uses IntervalTrigger(minutes=1); TelegramForbiddenError/TelegramRetryAfter handling; `asyncio.sleep(1)` flood control; `deliver_reports._bot = bot` wired in `main()` |
| `src/price_spy/bot/handlers/settings.py` | `/notify` command handler | VERIFIED | `router = Router(name="settings")`; `Command("notify")` filter; HH:MM validation; `user.notify_time = new_time`; `await session.flush()` |
| `src/price_spy/bot/handlers/scrape.py` | `/scrape` command handler with rate limiting | VERIFIED | `router = Router(name="scrape")`; `SCRAPE_COOLDOWN=3600`; `_last_scrape` dict; calls `scrape_single_basket(basket.id)`; `progress_msg.edit_text()` |
| `src/price_spy/bot/create.py` | Registration of settings and scrape routers | VERIFIED | `settings_handlers.router` and `scrape.router` both included; import alias used to avoid config.settings collision |
| `src/price_spy/i18n/ru.py` | Russian translations for /notify, /scrape, and help | VERIFIED | All 12 required keys present; help text includes `/notify` and `/scrape` |
| `src/price_spy/i18n/en.py` | English translations for /notify, /scrape, and help | VERIFIED | All 12 required keys present; help text includes `/notify` and `/scrape` |

---

### Key Link Verification

#### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `daily_scrape.py` | `scraper.py` | `scraper.scrape_urls()` | WIRED | Line 64: `results = await scraper.scrape_urls(unique_urls)` |
| `daily_scrape.py` | `price_history.py` | `price_repo.create()` | WIRED | Lines 84, 144: `await price_repo.create(...)` with all required args |
| `report.py` | `price_history.py` | `get_previous_prices` | WIRED | Line 157: `previous_prices = await price_repo.get_previous_prices(item_ids, today_start)` |
| `report.py` | `basket_item.py` | `get_basket_items_with_latest_price` | WIRED | Line 141: `items_with_prices = await item_repo.get_basket_items_with_latest_price(basket.id)` |

#### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__main__.py` | `daily_scrape.py` | `scrape_all_baskets()` | WIRED | Lines 55, 59: imported and awaited inside `daily_scrape()` job |
| `__main__.py` | `report.py` | `generate_user_report()` | WIRED | Lines 80, 99: imported and awaited inside `deliver_reports()` job |
| `scrape.py` | `daily_scrape.py` | `scrape_single_basket()` | WIRED | Lines 86, 88: imported and called with `basket.id` |
| `create.py` | `settings.py` | `settings_handlers.router` | WIRED | Line 34: `dp.include_router(settings_handlers.router)` |
| `create.py` | `scrape.py` | `scrape.router` | WIRED | Line 35: `dp.include_router(scrape.router)` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `report.py: generate_basket_section()` | `items_with_prices` | `BasketItemRepository.get_basket_items_with_latest_price()` — LATERAL join with PriceHistory | Yes — DB query with correlated subquery | FLOWING |
| `report.py: generate_basket_section()` | `previous_prices` | `PriceHistoryRepository.get_previous_prices()` — DISTINCT ON query with `scraped_at < today_start` | Yes — DB query returning dict | FLOWING |
| `__main__.py: deliver_reports()` | `users` | `UserRepository.get_users_by_notify_time(current_time)` | Yes — DB query filtering by `notify_time == current_time` | FLOWING |
| `scrape.py: cmd_scrape()` | `results` | `scrape_single_basket(basket.id)` — scrapes live URLs via ScraperService | Yes — live scraper returning ScrapeResult list | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All service modules import cleanly | `.venv/bin/python` import check | All imports succeeded | PASS |
| `scrape_all_baskets` and `scrape_single_basket` are async coroutines | `inspect.iscoroutinefunction()` | Both True | PASS |
| `generate_user_report` is async | `inspect.iscoroutinefunction()` | True | PASS |
| `MAX_MESSAGE_LENGTH == 4096` | Direct assertion | 4096 | PASS |
| `SCRAPE_COOLDOWN == 3600` | Direct assertion | 3600 | PASS |
| All 5 new repository methods exist | `hasattr()` checks | All found | PASS |
| All 12 i18n keys present in RU and EN | Dict key checks | All present | PASS |
| `split_message('line1\nline2\nline3', max_length=10)` splits to 2+ parts | Split test | 2 parts returned | PASS |
| `split_message('hello')` returns unchanged | Split test | `['hello']` | PASS |
| settings and scrape routers registered in dispatcher | `create_dispatcher()` sub_router check | `['start', 'basket', 'product', 'settings', 'scrape']` | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REPT-01 | 03-01, 03-02 | Bot scrapes all active baskets daily at 07:00 Asia/Almaty | SATISFIED | `daily_scrape()` in `__main__.py` calls `scrape_all_baskets()`; CronTrigger with `hour=7` (from `settings.scrape_daily_hour` default=7) |
| REPT-02 | 03-01, 03-02 | Bot sends daily price report to each user at their configured notification time | SATISFIED | `deliver_reports()` IntervalTrigger(minutes=1) queries users by `notify_time`; sends via `bot.send_message` with `split_message()` |
| REPT-03 | 03-01 | Daily report shows per-item prices with quantity totals | SATISFIED | `generate_basket_section()` renders item price line, quantity multiplier (`qty > 1` shows unit->total), and separator |
| REPT-04 | 03-01 | Daily report shows basket total and change from previous day | SATISFIED | `generate_basket_section()` accumulates `basket_total` and `yesterday_total`; renders `yesterday_comparison` string with delta |
| REPT-05 | 03-01 | Daily report highlights items that changed price (was/became with percentage) | SATISFIED | `generate_basket_section()` checks `prev_price != price`; applies `price_decreased`/`price_increased` with `delta` and `old` values |
| REPT-06 | 03-01 | Daily report flags out-of-stock items | SATISFIED | `generate_basket_section()` renders `out_of_stock` string when `is_available=False` |
| REPT-07 | 03-02 | User can configure notification time via /notify command | SATISFIED | `settings.py` handler parses `/notify HH:MM`, validates range, writes `user.notify_time`, calls `session.flush()` |
| REPT-08 | 03-02 | Default notification time is 09:00 Asia/Almaty | SATISFIED | `User` model: `notify_time: Mapped[datetime.time] = mapped_column(Time, default=datetime.time(9, 0))`; timezone is `Asia/Almaty` by default |
| MSCR-01 | 03-02 | User can trigger manual scrape via /scrape command | SATISFIED | `scrape.py` handler registered; calls `scrape_single_basket(basket.id)` |
| MSCR-02 | 03-02 | Manual scrape is rate-limited to once per hour per user | SATISFIED | `_last_scrape` dict; `SCRAPE_COOLDOWN=3600`; `_check_rate_limit()` returns remaining minutes; rate-limited reply sent |
| MSCR-03 | 03-02 | Bot shows progress feedback during manual scrape | SATISFIED | `progress_msg = await message.answer(...)` before scrape; `await progress_msg.edit_text(...)` after with full results |

No orphaned requirements — all 11 IDs (REPT-01 through REPT-08, MSCR-01 through MSCR-03) claimed in plan frontmatter match the REQUIREMENTS.md Phase 3 assignment.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/price_spy/services/daily_scrape.py` | 127 | `return []` | INFO | Legitimate early-return guard when basket has no items; not a stub — `items` list is queried from DB on line 124 |
| `src/price_spy/i18n/ru.py` | 95-97 | `scrape_item_ok/fail/unavailable` lack status emojis (✅ ❌ 🔴) | INFO | Plan spec included these emojis; actual implementation omitted them. Result display is functional but less visually distinct. Does not block any success criterion. |
| `src/price_spy/i18n/en.py` | 95-97 | Same as above for EN | INFO | Same assessment |

No blocker or warning-level anti-patterns found.

---

### Human Verification Required

#### 1. End-to-End Report Delivery

**Test:** Set notify_time to a minute 2 minutes from now via `/notify HH:MM`, wait for that minute, and check for a Telegram message from the bot
**Expected:** Bot sends a formatted report with basket headers, per-item prices, a total line, and yesterday comparison (if prior scrape data exists)
**Why human:** Requires live scheduler execution and Telegram delivery; cannot simulate minute-tick trigger programmatically without a running bot process

#### 2. Price Change Highlighting in Report

**Test:** Ensure two consecutive day scrapes have run, then trigger report delivery and inspect message content
**Expected:** Items whose price changed show an arrow with "was X" notation (e.g. "⬇️ -50 ₸ (было 800 ₸)"); unchanged items show no change annotation
**Why human:** Requires two days of real scraped data and live report delivery to observe the formatted output

#### 3. Out-of-Stock Flag in Report

**Test:** Add a product URL to a basket that is out of stock, run a scrape, then check the report
**Expected:** The item shows "🔴 Нет в наличии!" (RU) or "🔴 Out of stock!" (EN) below its price line
**Why human:** Requires real scraper execution and a product that is actually out of stock at scrape time

#### 4. /scrape Progress Feedback

**Test:** Send /scrape in a chat with the bot when active basket has items
**Expected:** Bot sends an initial "Scraping N item(s)..." message, then edits that same message (no new message) with final results
**Why human:** Message editing behavior and Telegram message ID reuse can only be confirmed in a live session

---

### Gaps Summary

No gaps. All 5 observable truths are verified, all artifacts exist and are substantive and wired, all key links are confirmed, all 11 requirements are satisfied, no blocker anti-patterns were found, and all 10 behavioral spot-checks passed.

The only notable deviation from the plan spec is cosmetic: the `scrape_item_ok`, `scrape_item_fail`, and `scrape_item_unavailable` i18n strings omit the ✅/❌/🔴 emoji prefixes that the plan specified. This does not affect the success criteria for MSCR-03 (progress feedback is present) and is not a blocker.

---

_Verified: 2026-03-30_
_Verifier: Claude (gsd-verifier)_
