# Phase 3: Scheduling and Daily Reports - Research

**Researched:** 2026-03-30
**Domain:** APScheduler scheduling, Telegram report formatting, daily scrape orchestration
**Confidence:** HIGH

## Summary

Phase 3 fills in the `daily_scrape()` placeholder in `__main__.py` with real scraping orchestration, builds a report generation service, adds a minute-granularity notification delivery job, and implements `/notify` and `/scrape` commands. The existing infrastructure is solid: APScheduler is already configured with PostgreSQL jobstore, `ScraperService.scrape_urls()` handles concurrency and retries, and the User model already has `notify_time` and `timezone` fields.

The main technical challenges are: (1) orchestrating the daily scrape across all users' baskets efficiently without exhausting the DB connection pool, (2) formatting multi-basket reports that respect Telegram's 4096-char limit, (3) delivering reports at per-user times without flooding Telegram, and (4) handling edge cases like blocked users and empty baskets gracefully.

**Primary recommendation:** Use a single APScheduler `IntervalTrigger(minutes=1)` job that checks which users are due for notification each minute, rather than per-user jobs or a single cron. Keep daily scrape as the existing cron at 07:00. Build report generation as a standalone service callable from both the scheduled job and the `/scrape` command.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Replace the placeholder `daily_scrape()` in `__main__.py` with real implementation that iterates all active baskets, scrapes all items via ScraperService, and stores results in price_history.
- D-02: Scrape orchestration: query all active baskets -> group items by URL source -> scrape via ScraperService.scrape_urls() -> store PriceHistory records -> update ProductNameCache for new names.
- D-03: APScheduler already has the cron job at `scrape_daily_hour` (07:00). Phase 3 fills in the actual logic. The PostgreSQL jobstore (INFR-05) persists the job across restarts.
- D-04: Report format matches task.md section 7.1 exactly -- per-basket sections with numbered items, unit price x quantity = line total, basket total, comparison to yesterday, price change indicators, out-of-stock markers.
- D-05: Report is generated per user, covering all their active baskets. Each basket gets its own section.
- D-06: Price changes show: old price -> new price with percentage and direction arrow. Only items that changed are highlighted.
- D-07: Out-of-stock items show red circle marker and "Out of stock!" in user's language.
- D-08: Each user has a `notify_time` (default 09:00) stored in the User model. Reports are delivered at this time.
- D-09: Implementation approach: single APScheduler job runs every minute, queries users whose notify_time matches current time (within the minute window), generates and sends their reports.
- D-10: Rejected: per-user APScheduler jobs (job explosion, complex management).
- D-11: `/notify HH:MM` updates user's notify_time. Validates format. Shows current time and confirmation in user's language.
- D-12: `/scrape` triggers immediate scrape of the user's active basket only (not all baskets).
- D-13: Rate limiting: 1 per hour per user. Track via `last_manual_scrape` column on User or in-memory dict.
- D-14: Progress feedback: send initial "Scraping N items..." message, then edit it with results when done.

### Claude's Discretion
- Whether to use in-memory dict or DB column for manual scrape rate limiting
- Exact minute-window logic for notification delivery (+/-30s tolerance vs exact minute match)
- Whether to send reports as one long message or split per basket
- Telegram message length handling (split if >4096 chars)

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REPT-01 | Bot scrapes all active baskets daily at 07:00 Asia/Almaty | Replace `daily_scrape()` placeholder; reuse ScraperService; group by source for efficiency |
| REPT-02 | Bot sends daily price report to each user at their configured notification time | IntervalTrigger(minutes=1) job queries users by notify_time match |
| REPT-03 | Daily report shows per-item prices with quantity totals | Report formatter builds per-item lines: name x qty = total |
| REPT-04 | Daily report shows basket total and change from previous day | Query yesterday's prices via PriceHistoryRepository; compute delta |
| REPT-05 | Daily report highlights items that changed price (was/became with percentage) | Compare today's price vs yesterday's for each item; show arrows and percentages |
| REPT-06 | Daily report flags out-of-stock items | Check `is_available` field from latest scrape; show red circle + localized message |
| REPT-07 | User can configure notification time via /notify command | New handler in settings router; validate HH:MM; update User.notify_time |
| REPT-08 | Default notification time is 09:00 Asia/Almaty | Already set in User model default; confirmed in code |
| MSCR-01 | User can trigger manual scrape via /scrape command | New handler; scrape active basket only via ScraperService |
| MSCR-02 | Manual scrape is rate-limited to once per hour per user | In-memory dict or DB column tracking; check before scraping |
| MSCR-03 | Bot shows progress feedback during manual scrape | Send "Scraping..." message, then edit with results |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack**: Python only -- aiogram 3, Playwright, httpx, selectolax, SQLAlchemy 2, asyncpg, APScheduler, matplotlib, Pydantic Settings
- **Hosting**: Railway (Starter plan)
- **Database**: PostgreSQL (Railway managed)
- **GSD Workflow**: Must use GSD entry points for changes; no direct repo edits outside workflow
- APScheduler **3.11.x only** (NOT 4.x)
- AsyncIOScheduler with PostgreSQL jobstore
- All times in Asia/Almaty timezone

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | ~=3.11 | Cron + interval scheduling | Already configured with AsyncIOScheduler + PostgreSQL jobstore |
| aiogram | ~=3.26 | Telegram Bot API | Already in use; provides TelegramRetryAfter, TelegramForbiddenError exceptions |
| SQLAlchemy | ~=2.0.48 | ORM + async queries | Already in use; needed for new queries (users by notify_time, yesterday's prices) |

### No New Dependencies Required
This phase requires no new packages. All functionality is built on top of the existing stack: APScheduler for scheduling, aiogram for message sending, SQLAlchemy for data queries.

## Architecture Patterns

### Recommended New Files
```
src/price_spy/
  services/
    daily_scrape.py      # Daily scrape orchestration (REPT-01)
    report.py            # Report generation service (REPT-02..06)
  bot/handlers/
    settings.py          # /notify handler (REPT-07)
    scrape.py            # /scrape handler (MSCR-01..03)
```

### Pattern 1: Scrape Orchestration Service
**What:** A `DailyScrapeService` that queries all baskets, deduplicates URLs, scrapes via ScraperService, and stores results.
**When to use:** Called from both `daily_scrape()` job and `/scrape` handler (with single-basket scope).

```python
# src/price_spy/services/daily_scrape.py
from decimal import Decimal
from price_spy.db.engine import async_session
from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.db.repositories.price_history import PriceHistoryRepository
from price_spy.services.scraper import ScraperService

async def scrape_all_baskets() -> dict[int, list]:
    """Scrape all active baskets for all users. Returns {basket_id: [ScrapeResult]}."""
    async with async_session() as session:
        basket_repo = BasketRepository(session)
        item_repo = BasketItemRepository(session)
        price_repo = PriceHistoryRepository(session)

        # Get ALL baskets (not just one user)
        # Need a new repository method: get_all_active_baskets()
        baskets = await basket_repo.get_all_active_baskets()

        # Collect all unique URLs across all baskets
        url_to_items: dict[str, list[int]] = {}  # url -> [basket_item_id, ...]
        for basket in baskets:
            items = await item_repo.get_items_by_basket(basket.id)
            for item in items:
                url_to_items.setdefault(item.product_url, []).append(item.id)

        # Scrape all unique URLs at once (deduplication saves time)
        scraper = ScraperService(session)
        try:
            results = await scraper.scrape_urls(list(url_to_items.keys()))
            # Store price history for each basket_item
            for result in results:
                if result.ok and result.data:
                    for item_id in url_to_items.get(result.url, []):
                        await price_repo.create(
                            basket_item_id=item_id,
                            price=Decimal(str(result.data.price)),
                            original_price=(
                                Decimal(str(result.data.original_price))
                                if result.data.original_price else None
                            ),
                            is_available=result.data.is_available,
                        )
            await session.commit()
        finally:
            await scraper.close()
```

### Pattern 2: Minute-Tick Notification Delivery
**What:** An APScheduler `IntervalTrigger(minutes=1)` job that queries users whose `notify_time` matches the current minute and sends their reports.
**When to use:** Runs continuously; the main mechanism for per-user report delivery.

```python
# In __main__.py, alongside daily_scrape
from apscheduler.triggers.interval import IntervalTrigger
import datetime
import zoneinfo

async def deliver_reports() -> None:
    """Check for users due for notification this minute and send reports."""
    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    current_time = now.time().replace(second=0, microsecond=0)

    async with async_session() as session:
        user_repo = UserRepository(session)
        users = await user_repo.get_users_by_notify_time(current_time)

        for user in users:
            try:
                report = await generate_report(session, user)
                if report:
                    await send_report_to_user(bot, user, report)
            except TelegramForbiddenError:
                logger.warning("User %d blocked bot, skipping", user.telegram_id)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                # Retry once
                await send_report_to_user(bot, user, report)
            await asyncio.sleep(1)  # 1s delay between users (flood control)

# Register in on_startup:
scheduler.add_job(
    deliver_reports,
    trigger=IntervalTrigger(minutes=1),
    id="deliver_reports",
    replace_existing=True,
    misfire_grace_time=60,
    coalesce=True,
)
```

### Pattern 3: Report Format (matching task.md 7.1)
**What:** Generate report text per user with per-basket sections.

The report format from task.md section 7.1:
```
report_header = "report_title"  # e.g., "Report for 30.03.2026"

Per basket section:
- Basket name + item count header
- Separator line
- Numbered items: name x qty, price -> total, change indicators
- Basket total + yesterday comparison
- Out-of-stock items with red circle

Bottom comparison section (only if user has both arbuz and magnum baskets)
```

### Pattern 4: Handler Pattern (from existing code)
**What:** Handlers follow the established pattern: Router + Command filter + middleware-injected session/user/lang.

```python
# src/price_spy/bot/handlers/settings.py
router = Router(name="settings")

@router.message(Command("notify"))
async def cmd_notify(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    if user is None:
        # Force language selection
        ...
        return
    # Parse HH:MM from message.text
    # Validate and update user.notify_time
```

### Anti-Patterns to Avoid
- **Per-user APScheduler jobs:** Creates N jobs for N users. Hard to manage additions/deletions. Use single minute-tick job instead (D-09/D-10).
- **Scraping inside the report delivery job:** Scrape should complete BEFORE report delivery begins. Keep `daily_scrape` at 07:00 and `deliver_reports` running every minute. Users with notify_time < 07:00 would get yesterday's data (acceptable).
- **Blocking the event loop during scraping:** The `/scrape` handler must send a "Scraping..." message immediately and edit it when done. Do NOT await the full scrape before responding.
- **Sending all baskets in one message without checking length:** Telegram's 4096 char limit will cause `MessageIsTooLong` errors. Split per basket or at natural boundaries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Telegram flood control | Custom rate limiter | Catch `TelegramRetryAfter` + 1s inter-user delay | aiogram provides the exception with `retry_after` value; simple sleep handles it |
| Cron scheduling | asyncio.sleep loops | APScheduler CronTrigger / IntervalTrigger | Already configured; handles timezone, misfire, persistence |
| Message splitting | Manual string slicing | Split at newline boundaries within 4096 chars | Simple utility function (10 lines); do not use external packages |
| Time validation | Regex parsing | `datetime.time(hour, minute)` with try/except | Python stdlib handles edge cases |

## Common Pitfalls

### Pitfall 1: Bot Reference in Scheduled Jobs
**What goes wrong:** The `deliver_reports()` job needs a Bot instance to send messages, but APScheduler job functions are called outside the handler context -- no middleware injection.
**Why it happens:** APScheduler calls the function directly; it has no access to the aiogram dispatcher or bot instance.
**How to avoid:** Store the Bot instance as an attribute on the scheduler or pass it via a module-level reference. The existing code already stores `on_startup._scheduler` on the function object; use a similar pattern for the bot: `deliver_reports._bot = bot` set during `on_startup`.
**Warning signs:** `NameError: 'bot' is not defined` in scheduled job logs.

### Pitfall 2: Telegram Flood Control During Bulk Reporting (Pitfall 5 from PITFALLS.md)
**What goes wrong:** Sending reports to many users simultaneously triggers Telegram's 429 Too Many Requests.
**Why it happens:** The bot sends ~30 messages per second when looping without delays.
**How to avoid:**
1. Add `await asyncio.sleep(1)` between each user's report delivery.
2. Catch `TelegramRetryAfter` and sleep for `e.retry_after` seconds.
3. Per-user notification times naturally stagger delivery (most users will have different times).
**Warning signs:** `TelegramRetryAfter` exceptions in logs; users receiving reports late.

### Pitfall 3: User Blocked Bot
**What goes wrong:** `send_message` raises `TelegramForbiddenError` when user has blocked the bot. If unhandled, the entire report delivery loop crashes.
**Why it happens:** Users block bots. The bot does not know until it tries to send.
**How to avoid:** Wrap each user's send in try/except catching `TelegramForbiddenError`. Log and skip. Optionally deactivate notifications for that user.
**Warning signs:** Unhandled exception in deliver_reports job causing all subsequent users to miss their reports.

### Pitfall 4: Database Session Scope in Scheduled Jobs
**What goes wrong:** Scheduled jobs run outside aiogram middleware, so there's no automatic session management. Using a stale session or forgetting to commit leads to data loss or connection leaks.
**Why it happens:** The `DbSessionMiddleware` only wraps handler calls. APScheduler jobs must manage their own sessions.
**How to avoid:** Always use `async with async_session() as session:` in scheduled job functions, exactly as `cleanup_old_prices()` already does. Commit within the context manager.
**Warning signs:** "Connection pool exhausted" errors during scrape + normal bot usage.

### Pitfall 5: Notify Time Comparison Precision
**What goes wrong:** `datetime.time(9, 0)` stored in DB does not match the current time because of seconds/microseconds.
**Why it happens:** `datetime.now().time()` includes seconds and microseconds. `user.notify_time` is `time(9, 0)` (no seconds).
**How to avoid:** Truncate current time to minute precision before comparing: `now.time().replace(second=0, microsecond=0)`. Query users with `WHERE notify_time = :current_minute`.
**Warning signs:** Users never receive reports because the time never exactly matches.

### Pitfall 6: Daily Scrape Takes Longer Than Expected
**What goes wrong:** With 10 users x 10 baskets x 50 items = 5000 items, scraping could take 30+ minutes. If notify_time is 07:30, the report uses stale data.
**Why it happens:** Playwright scraping is slow (3-5s per page). Even with deduplication and parallelism, large datasets take time.
**How to avoid:** URL deduplication across all baskets (same product in multiple baskets only scraped once). Consider scraping as a prerequisite: if today's scrape is not complete for a user's basket, delay that user's notification. For MVP with few users, this is unlikely to be an issue.
**Warning signs:** Reports showing yesterday's data for items that should have been scraped today.

## Code Examples

### New Repository Method: Get All Active Baskets
```python
# In BasketRepository
async def get_all_active_baskets(self) -> list[Basket]:
    """Get all baskets that have at least one item (for daily scrape)."""
    stmt = (
        select(Basket)
        .where(Basket.is_active.is_(True))
        .order_by(Basket.user_id, Basket.id)
    )
    result = await self._session.execute(stmt)
    return list(result.scalars().all())
```

### New Repository Method: Get Users by Notify Time
```python
# In UserRepository
async def get_users_by_notify_time(self, target_time: datetime.time) -> list[User]:
    """Get all users whose notify_time matches the given time (minute precision)."""
    stmt = select(User).where(User.notify_time == target_time)
    result = await self._session.execute(stmt)
    return list(result.scalars().all())
```

### New Repository Method: Get Yesterday's Prices for Comparison
```python
# In PriceHistoryRepository
async def get_previous_prices(
    self, basket_item_ids: list[int], before: datetime.datetime
) -> dict[int, tuple[Decimal | None, bool]]:
    """Get the most recent price for each item BEFORE the given timestamp.

    Returns {basket_item_id: (price, is_available)}.
    """
    # Use LATERAL join or DISTINCT ON for each item's most recent record before cutoff
    ...
```

### Message Splitting Utility
```python
MAX_MESSAGE_LENGTH = 4096

def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split text into chunks that fit Telegram's message limit.

    Splits at newline boundaries to keep formatting intact.
    """
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        # Find last newline within limit
        split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    return parts
```

### Rate Limiting for /scrape (In-Memory Approach)
```python
import time

# Module-level dict (simple, survives within process lifetime)
_last_scrape: dict[int, float] = {}  # user_id -> timestamp
SCRAPE_COOLDOWN = 3600  # 1 hour in seconds

def check_rate_limit(user_id: int) -> int | None:
    """Returns remaining seconds if rate-limited, None if allowed."""
    last = _last_scrape.get(user_id)
    if last is None:
        return None
    elapsed = time.time() - last
    if elapsed < SCRAPE_COOLDOWN:
        return int(SCRAPE_COOLDOWN - elapsed)
    return None

def record_scrape(user_id: int) -> None:
    _last_scrape[user_id] = time.time()
```

### Sending Report with Flood Control
```python
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

async def send_report_to_user(bot: Bot, user: User, report_text: str) -> bool:
    """Send report message(s) to a user. Returns True if successful."""
    parts = split_message(report_text)
    for part in parts:
        try:
            await bot.send_message(chat_id=user.telegram_id, text=part)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await bot.send_message(chat_id=user.telegram_id, text=part)
        except TelegramForbiddenError:
            logger.warning("User %d blocked bot", user.telegram_id)
            return False
    return True
```

## Discretion Recommendations

### Manual Scrape Rate Limiting: Use In-Memory Dict
**Recommendation:** In-memory dict (not DB column).
**Rationale:** Rate limiting does not need to survive restarts -- if the bot restarts, letting users scrape immediately is acceptable. In-memory is simpler (no migration), faster (no DB query), and sufficient for a single-process bot. Railway restarts are rare during normal operation.

### Minute-Window Logic: Exact Minute Match
**Recommendation:** Compare `user.notify_time == current_time` where current_time is truncated to minute precision.
**Rationale:** The IntervalTrigger fires every 60 seconds. As long as the job runs within the minute, exact match works. With `misfire_grace_time=60` and `coalesce=True`, even if a tick is delayed, the next one catches up. No tolerance window needed.

### Report Message Strategy: One Message Per User, Split if Needed
**Recommendation:** Generate one consolidated report per user (all baskets). If it exceeds 4096 chars, split at basket boundaries (each basket is a natural section). If a single basket section exceeds 4096, split at item lines.
**Rationale:** Users prefer one notification rather than N per basket. Splitting at basket boundaries keeps context coherent. The comparison section at the bottom should be in the last message.

### Telegram Message Length: Split at Newlines
**Recommendation:** Use the `split_message()` utility that finds the last newline before the 4096 limit.
**Rationale:** Simple, preserves formatting, avoids cutting items mid-line.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler 4.x alpha | APScheduler 3.11.x stable | Ongoing | 4.x is still alpha; 3.11 is production-ready |
| Per-user cron jobs | Single minute-tick job + DB query | Industry pattern | Scales to thousands of users without job explosion |
| Synchronous scraping | async ScraperService with semaphores | Phase 1 | Already implemented; reuse for daily scrape |

## Open Questions

1. **Bot instance access in scheduled jobs**
   - What we know: APScheduler job functions run outside aiogram context. The bot instance is created in `main()`.
   - What's unclear: Best pattern to pass bot instance to scheduled jobs without global state.
   - Recommendation: Store bot reference during `on_startup` (similar to existing `on_startup._scheduler` pattern). Set `deliver_reports._bot = bot` or use a module-level variable.

2. **Cross-basket URL deduplication scope**
   - What we know: Different users may track the same product URL.
   - What's unclear: How much duplication exists in practice.
   - Recommendation: Implement deduplication at the URL level -- scrape each unique URL once, then distribute results to all basket_items referencing that URL. This is a significant optimization.

3. **Report delivery for users with no baskets or empty baskets**
   - What we know: Users may register but never create baskets.
   - Recommendation: Skip users with no non-empty baskets during report delivery. No need to send "no data" messages.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `__main__.py`, `ScraperService`, `PriceHistoryRepository`, `BasketRepository`, `User` model -- all verified by direct file reading
- task.md section 7.1 -- exact report format specification
- `.planning/phases/03-scheduling-and-daily-reports/03-CONTEXT.md` -- locked decisions

### Secondary (MEDIUM confidence)
- [APScheduler 3.11.x IntervalTrigger docs](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/interval.html) -- minutes parameter, jitter
- [APScheduler AsyncIOScheduler docs](https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html) -- async job support
- [aiogram 3 Errors docs](https://docs.aiogram.dev/en/latest/dispatcher/errors.html) -- TelegramRetryAfter, TelegramForbiddenError
- [aiogram discussion #1489](https://github.com/aiogram/aiogram/discussions/1489) -- TelegramRetryAfter handling strategy
- [aiogram discussion #963](https://github.com/aiogram/aiogram/discussions/963) -- message splitting for 4096 char limit

### Tertiary (LOW confidence)
- `.planning/research/PITFALLS.md` Pitfall 5 -- Telegram flood control specifics (rate limits are approximate, not officially documented exact thresholds)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing code verified
- Architecture: HIGH -- patterns follow existing codebase conventions; decisions are locked
- Pitfalls: HIGH -- Telegram flood control and APScheduler misfire are well-documented; codebase already handles some (misfire_grace_time, PostgreSQL jobstore)

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no fast-moving dependencies)
