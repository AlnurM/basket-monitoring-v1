# Phase 3: Scheduling and Daily Reports - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Source:** Auto-mode (recommended defaults selected)

<domain>
## Phase Boundary

Automated daily scraping of all active baskets at 07:00 Asia/Almaty, personalized daily price reports delivered at each user's configured time, price change highlighting (was/became with percentage), out-of-stock flagging, configurable notification time (/notify), and manual scrape trigger (/scrape) with rate limiting and progress feedback.

</domain>

<decisions>
## Implementation Decisions

### Daily Scraping (REPT-01)
- **D-01:** Replace the placeholder `daily_scrape()` in `__main__.py` with real implementation that iterates all active baskets, scrapes all items via ScraperService, and stores results in price_history.
- **D-02:** Scrape orchestration: query all active baskets → group items by URL source → scrape via ScraperService.scrape_urls() → store PriceHistory records → update ProductNameCache for new names.
- **D-03:** APScheduler already has the cron job at `scrape_daily_hour` (07:00). Phase 3 fills in the actual logic. The PostgreSQL jobstore (INFR-05) persists the job across restarts.

### Daily Report Format (REPT-02 through REPT-06)
- **D-04:** Report format matches task.md section 7.1 exactly — per-basket sections with numbered items, unit price × quantity = line total, basket total, comparison to yesterday, price change indicators (⬇️/⬆️), out-of-stock markers (🔴).
- **D-05:** Report is generated per user, covering all their active baskets. Each basket gets its own section.
- **D-06:** Price changes show: old price → new price with percentage and direction arrow. Only items that changed are highlighted.
- **D-07:** Out-of-stock items show 🔴 marker and "Нет в наличии!" / "Out of stock!" in user's language.

### Notification Delivery (REPT-02, REPT-07, REPT-08)
- **D-08:** Each user has a `notify_time` (default 09:00) stored in the User model. Reports are delivered at this time.
- **D-09:** Implementation approach: single APScheduler job runs every minute, queries users whose notify_time matches current time (within the minute window), generates and sends their reports. This avoids per-user APScheduler jobs (simpler, no job explosion).
- **D-10:** Alternative considered but rejected: per-user APScheduler jobs — would create N jobs for N users, complex to manage additions/deletions.

### /notify Command (REPT-07)
- **D-11:** `/notify HH:MM` updates user's notify_time. Validates format (00:00-23:59). Shows current time and confirmation in user's language.

### Manual Scrape (MSCR-01 through MSCR-03)
- **D-12:** `/scrape` triggers immediate scrape of the user's active basket only (not all baskets).
- **D-13:** Rate limiting: 1 per hour per user. Track via a `last_manual_scrape` column on User model or a simple in-memory dict. If under limit, show "Please wait X minutes" message.
- **D-14:** Progress feedback: send initial "Scraping N items..." message, then edit it with results when done. Shows per-item success/failure inline.

### Carrying Forward from Prior Phases
- ScraperService with concurrency control (3 Playwright / 10 httpx) — reuse for all scraping
- PriceHistoryRepository.create() — store scrape results
- BasketRepository.get_user_baskets_with_item_counts() — query user's baskets
- BasketItemRepository — get items for scraping
- ProductNameCache — update on new names
- i18n get_text — all new messages bilingual (RU + EN)
- APScheduler with PostgreSQL jobstore in __main__.py
- User model with notify_time, timezone fields

### Claude's Discretion
- Whether to use in-memory dict or DB column for manual scrape rate limiting
- Exact minute-window logic for notification delivery (±30s tolerance vs exact minute match)
- Whether to send reports as one long message or split per basket
- Telegram message length handling (split if >4096 chars)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specification
- `task.md` — Section 7.1 (daily report format), 7.2 (changes report), 8 (scheduler config), 6.1 (/notify, /scrape commands)

### Phase 1/2 Code
- `src/price_spy/__main__.py` — APScheduler setup, daily_scrape placeholder, cleanup_old_prices pattern
- `src/price_spy/services/scraper.py` — ScraperService.scrape_urls(), detect_source()
- `src/price_spy/db/repositories/price_history.py` — PriceHistoryRepository (create, query methods)
- `src/price_spy/db/repositories/basket.py` — BasketRepository
- `src/price_spy/db/repositories/basket_item.py` — BasketItemRepository
- `src/price_spy/db/models/user.py` — User model with notify_time, timezone
- `src/price_spy/bot/handlers/start.py` — Handler pattern (Router, middleware injection)
- `src/price_spy/bot/handlers/basket.py` — Handler pattern with inline keyboards
- `src/price_spy/bot/handlers/product.py` — Handler pattern with ScraperService usage
- `src/price_spy/i18n/ru.py` — Russian translations to extend
- `src/price_spy/i18n/en.py` — English translations to extend
- `src/price_spy/bot/create.py` — Router registration (add new routers here)

### Research
- `.planning/research/PITFALLS.md` — Pitfall 4: Telegram flood control, rate-limited sending

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints
- `.planning/REQUIREMENTS.md` — Phase 3 requirements: REPT-01..08, MSCR-01..03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `daily_scrape()` placeholder in __main__.py — replace with real implementation
- `ScraperService.scrape_urls(urls)` — core scraping with retry and concurrency
- `PriceHistoryRepository` — already has create() and query methods
- `BasketItemRepository` — get items for a basket
- `cleanup_old_prices()` pattern — reference for new async job functions
- Handler patterns from basket.py and product.py — Router + Command filter + middleware injection

### Established Patterns
- APScheduler CronTrigger jobs registered in on_startup
- Async job functions use `async_session` context manager for DB access
- Handlers receive `session`, `user`, `lang` via middleware
- i18n keys in both ru.py and en.py dictionaries

### Integration Points
- `__main__.py` on_startup — modify existing daily_scrape job, add report delivery job
- `bot/create.py` — register new settings/scrape router
- User.notify_time — already exists, just needs /notify handler to update it

</code_context>

<specifics>
## Specific Ideas

- task.md section 7.1 has the exact report format with emoji markers and price formatting in tenge (₸)
- The daily report includes a comparison section at the bottom when user has both Arbuz and Magnum baskets
- Telegram messages have a 4096 character limit — long reports may need splitting
- Pitfall 4 from research: Telegram flood control will ban the bot if messages are sent too fast during bulk report delivery — add delays between users

</specifics>

<deferred>
## Deferred Ideas

None — auto-mode discussion stayed within phase scope

</deferred>

---

*Phase: 03-scheduling-and-daily-reports*
*Context gathered: 2026-03-31 via auto-mode*
