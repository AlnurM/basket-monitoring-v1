# Pitfalls Research

**Domain:** Telegram bot + web scraping + price tracking (Kazakh e-commerce)
**Researched:** 2026-03-30
**Confidence:** HIGH (most pitfalls verified across multiple sources and official docs)

## Critical Pitfalls

### Pitfall 1: Playwright Chromium OOM Crashes in Railway Containers

**What goes wrong:**
Chromium silently crashes or the entire Railway container restarts. Scraping jobs return empty results or hang indefinitely. Docker defaults `/dev/shm` to 64MB, but Chromium uses shared memory for rendering -- it crashes when that fills up. Since Playwright 1.57, the default browser switched to "Chrome for Testing" which uses dramatically more memory (20GB+ per instance reported) vs the old open-source Chromium build.

**Why it happens:**
Developers test locally with ample RAM and no `/dev/shm` limits. Railway Starter plan has limited memory. Without explicit `--disable-dev-shm-usage` and `--no-sandbox` flags, Chromium will silently fail. Additionally, not pinning the Playwright version can pull in the heavier Chrome for Testing binary.

**How to avoid:**
- Use the official Playwright Docker base image (`mcr.microsoft.com/playwright/python:v1.49.0-noble`) with browsers pre-installed -- avoids CDN download failures on Railway and guarantees all system deps are present.
- Pin Playwright version in requirements.txt to control which Chromium ships.
- Launch with explicit args: `--disable-dev-shm-usage`, `--disable-gpu`, `--no-sandbox`, `--single-process`.
- Set `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` in the Dockerfile so browsers are found at runtime.
- Keep Railway service memory limit at minimum 512MB (ideally 1GB for parallel scraping).

**Warning signs:**
- Scraping returns `None` or empty strings intermittently but works locally.
- Railway logs show `Crashed` or `SIGKILL` without Python tracebacks.
- Container restarts during scraping windows.

**Phase to address:**
Phase 1 (Infrastructure/Deployment) -- get the Dockerfile right before writing any scraping logic. Test the container on Railway with a trivial Playwright script first.

---

### Pitfall 2: Browser Context Memory Leaks in Long-Running Scraper

**What goes wrong:**
Memory grows unboundedly over days. After scraping 50+ products daily, Chromium accumulates cached responses, DOM state, and WebSocket connections inside reused browser contexts. Within 2-3 days the Railway container OOMs and restarts, losing any in-progress scrape.

**Why it happens:**
Developers reuse a single browser context (or even a single page) for all scraping to "save startup time." Request/response/route objects in Playwright only get flushed when a new context is created -- reusing a context indefinitely is a documented memory leak.

**How to avoid:**
- Create a fresh `BrowserContext` per scraping batch (e.g., per store per run). Close it in a `try/finally` block.
- Recycle the Browser instance itself every N runs (e.g., every 24 hours or every 100 pages). Kill and relaunch.
- Close every `Page` immediately after extracting data -- do not accumulate open pages.
- Force Python garbage collection (`gc.collect()`) after closing contexts in memory-constrained environments.
- Monitor RSS memory via a simple log line at scrape start/end to catch drift early.

**Warning signs:**
- Memory usage trends upward across days in Railway metrics.
- Scraping gets progressively slower over time.
- OOM crashes happen not on the first scrape of the day but the second or third.

**Phase to address:**
Phase 2 (Scraping Implementation) -- build the browser lifecycle manager with context recycling from the start, not as an afterthought.

---

### Pitfall 3: Arbuz/Magnum Anti-Bot Detection Escalation

**What goes wrong:**
Scraping works perfectly for 2-4 weeks, then suddenly returns 403s, CAPTCHAs, or empty product pages. The site has updated its anti-bot measures or flagged your Railway IP. Since Railway uses shared infrastructure, other scrapers on the same IP range may have already poisoned the IP reputation.

**Why it happens:**
Kazakh e-commerce sites use a mix of Cloudflare, DataDome, or custom WAFs. Detection vectors include: `navigator.webdriver=true` (the default in automation), consistent TLS fingerprints (JA3), missing browser fonts/plugins in headless mode, and inhuman request timing (zero scroll, zero mouse movement, instant page loads). The `playwright-stealth` plugin patches many of these but not all.

**How to avoid:**
- Use `playwright-stealth` (or `playwright-extra` with stealth plugin) as baseline -- this patches `navigator.webdriver`, Chrome runtime properties, and WebGL fingerprints.
- Rotate User-Agent strings per scrape session (not per request -- that is itself a detection signal).
- Add realistic delays between page loads (2-5 seconds with jitter, not fixed intervals).
- Prefer API interception over DOM scraping: open the page, intercept the XHR/fetch calls that load product data (Arbuz likely uses a JSON API internally), and extract from the API response. This is faster, more stable, and less detectable.
- Monitor for soft blocks: if product name returns but price is "0" or missing, the site may be serving degraded content to bots.
- Have a fallback: if Playwright gets blocked, Kaspi.kz product pages (SSR) can be scraped with `httpx` + `selectolax` as already planned for Magnum baskets.

**Warning signs:**
- Prices returning as 0, None, or "unavailable" for products that are clearly in stock.
- HTTP 403 or 429 responses appearing in logs.
- Response HTML containing CAPTCHA challenge scripts.
- Scrape time suddenly increasing (bot challenges add latency).

**Phase to address:**
Phase 2 (Scraping) -- implement stealth and API interception from the start. Phase 3+ -- add monitoring/alerting for scrape failures.

---

### Pitfall 4: APScheduler Jobs Silently Dying After Railway Restart

**What goes wrong:**
The daily 07:00 scrape just stops happening. No errors, no logs -- the scheduler simply is not firing. Users notice they stopped getting daily reports but there is no alert. This can go unnoticed for days.

**Why it happens:**
Railway restarts containers during deploys, maintenance, or OOM events. If APScheduler uses the default `MemoryJobStore`, all scheduled jobs vanish on restart. Even with a PostgreSQL job store, the scheduler can miss its window: if the container was down at 07:00 and `misfire_grace_time` is too short (default: 1 second for cron triggers), the job is silently skipped. Additionally, if APScheduler's `AsyncIOScheduler` is initialized before the asyncio event loop starts (a common mistake with aiogram), it silently fails to schedule anything.

**How to avoid:**
- Use `SQLAlchemyJobStore` backed by PostgreSQL so jobs survive restarts.
- Set `misfire_grace_time` to a generous value (e.g., 900 seconds / 15 minutes) so jobs run even after a delayed restart.
- Set `coalesce=True` on cron jobs so multiple missed firings collapse into one execution.
- Initialize the scheduler AFTER the aiogram event loop starts (in the `on_startup` hook, not at module level).
- Add a self-health-check: log every scheduler firing with a timestamp. If the bot receives a `/status` command, report when the last scrape ran and whether it succeeded.
- Consider a dead-man's switch: if no scrape has run in 25 hours, send an alert to the admin.

**Warning signs:**
- No scrape logs at the expected time.
- Users report stale data (same prices for multiple days).
- APScheduler logs show "Adding job" at startup but no "Running job" entries after.

**Phase to address:**
Phase 3 (Scheduling/Automation) -- configure job store and misfire handling. But the event loop initialization order must be correct from Phase 1 (bot setup).

---

### Pitfall 5: Telegram Flood Control Banning the Bot During Bulk Reporting

**What goes wrong:**
At 07:00, the bot scrapes prices and then tries to send daily reports to all users simultaneously. After ~30 messages, Telegram returns `429 Too Many Requests` with a `retry_after` value. If the bot does not respect this, it gets temporarily banned (up to 15 minutes). Users receive their reports hours late or not at all.

**Why it happens:**
Telegram enforces rate limits: roughly 30 messages per second globally, 1 message per second to the same chat, and 20 messages per minute to the same group. Developers write a simple `for user in users: await bot.send_message(...)` loop which fires as fast as asyncio allows. With 10 users each getting a text report + chart image + CSV, that is 30+ messages in under a second.

**How to avoid:**
- Stagger report delivery: do not send all reports at once. Add a 1-second delay between users (at 10 users this takes 10 seconds -- acceptable).
- Respect `retry_after` dynamically: catch `TelegramRetryAfter` exceptions in aiogram and `await asyncio.sleep(retry_after)` before retrying.
- Batch per-user messages: combine text + chart into a single `send_photo` with a caption rather than separate messages.
- Use aiogram's built-in throttling middleware if available, or implement a simple token-bucket rate limiter.
- For future scale (50+ users): stagger notification times (each user has their own preferred time, which the project already supports -- use this as the primary scaling mechanism).

**Warning signs:**
- `TelegramRetryAfter` exceptions in logs.
- Users complaining reports arrive 5-15 minutes late.
- Some users get reports and others do not on the same day.

**Phase to address:**
Phase 4 (Reporting/Notifications) -- implement rate-limited message sending from day one of the notification system.

---

### Pitfall 6: Site Layout/Selector Breakage Going Undetected

**What goes wrong:**
Arbuz.kz or Magnum.kz redesigns their product page (or even just changes a CSS class name). Selectors that extracted price/name now return `None`. The scraper writes `null` prices to the database. Users see "$0" in their reports or the bot reports everything as "unavailable." This can persist for days if there is no validation.

**Why it happens:**
E-commerce sites update their frontend frequently -- class names generated by build tools (e.g., `_price_a3f2x`) change on every deployment. Scraping by CSS class is inherently fragile. Developers often scrape and store whatever comes back without validating it makes sense.

**How to avoid:**
- Prefer API interception over DOM selectors. If Arbuz loads product data via an internal API (XHR/fetch), intercept that response and parse JSON. JSON API schemas change far less frequently than HTML class names.
- Validate scraped data before storing: price must be > 0, product name must be non-empty, currency must be tenge. Reject and log invalid scrapes rather than storing garbage.
- Compare new price against last known price: if price changed by more than 50% in a single day, flag it as suspicious rather than storing it silently.
- Store the raw scraped HTML/JSON snippet alongside extracted values (at least temporarily) for debugging when things break.
- Alert the admin when scrape failure rate exceeds a threshold (e.g., >20% of products in a basket failed to scrape).

**Warning signs:**
- Sudden spike in `None` or `0` prices across multiple products.
- All products from one store failing while the other store works fine.
- Scrape completes in unusually short time (nothing was actually loaded).

**Phase to address:**
Phase 2 (Scraping) -- build validation into the scraper from the start. Phase 3 -- add monitoring/alerting for scrape quality.

---

### Pitfall 7: asyncpg Connection Pool Exhaustion Under Concurrent Scraping + Bot Traffic

**What goes wrong:**
The bot becomes unresponsive -- users press buttons and nothing happens. Database queries hang, then timeout. The scraper is holding multiple connections open (one per concurrent page scrape), and simultaneously the bot handlers need connections for user commands. The pool (default 10 connections in SQLAlchemy async) is exhausted.

**Why it happens:**
Railway's managed PostgreSQL allows limited connections (20 on Starter plan). SQLAlchemy's `AsyncEngine` with asyncpg defaults to `pool_size=5` and `max_overflow=10`. A scraping batch that opens 10 concurrent pages, each inserting price records in separate sessions, can consume all available connections. Additionally, asyncpg leaks open transactions when asyncio tasks are cancelled (a known issue documented in March 2025) -- cancelled scrape tasks leave connections in a broken state.

**How to avoid:**
- Configure pool explicitly: `pool_size=5`, `max_overflow=5`, `pool_timeout=30`, `pool_recycle=1800`. Keep total under Railway's connection limit.
- Use a semaphore to limit concurrent scraping to 3-5 pages at a time, matching available pool connections.
- Always use `async with session:` (context manager) to guarantee sessions are returned to the pool, even on errors or cancellations.
- Add `pool_pre_ping=True` to detect stale connections after Railway PostgreSQL restarts.
- Separate concerns: use one session-per-request for bot handlers (short-lived), and a dedicated session scope for scraping batches.

**Warning signs:**
- Bot commands timing out intermittently, especially during scraping windows.
- `asyncpg.exceptions.TooManyConnectionsError` or `TimeoutError` in logs.
- Database queries that normally take <100ms suddenly taking 30+ seconds.

**Phase to address:**
Phase 1 (Database Setup) -- configure pool correctly. Phase 2 (Scraping) -- add semaphore for concurrent scrape limiting.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded CSS selectors without abstraction layer | Faster initial development | Every site change requires hunting through scraping code | Never -- wrap selectors in a per-store config/class from day 1 |
| Storing prices as floats instead of integers (tenge) | Simpler code | Floating point comparison bugs in price change detection | Never -- store as integer tenge (Kazakhstan does not use tiyn in grocery pricing) |
| Single monolithic scrape function per store | Quick to write | Impossible to test, debug, or partially retry | MVP only -- refactor before adding the second store |
| No database migrations (raw CREATE TABLE) | Faster initial setup | Schema changes require manual intervention or data loss | Never -- use Alembic from Phase 1 |
| Synchronous matplotlib chart generation | Works for 1-2 users | Blocks the event loop, bot freezes during chart generation | Never -- run matplotlib in `run_in_executor` |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| aiogram 3 + APScheduler | Initializing scheduler at module import time before event loop exists | Initialize scheduler in `on_startup` callback, use `AsyncIOScheduler` with the running loop |
| Playwright + asyncio | Calling sync Playwright API from async code (or vice versa) | Always use `async_playwright()` context manager; never mix sync/async Playwright |
| asyncpg + Railway PostgreSQL | Not handling connection drops after Railway maintenance/restarts | Set `pool_pre_ping=True` in SQLAlchemy engine config; handle `ConnectionRefusedError` with retry |
| Telegram Bot API + image sending | Generating chart to file, then reading file to send -- wastes disk I/O | Generate chart to `BytesIO` buffer and send directly via `BufferedInputFile` |
| httpx + Kaspi.kz | Not setting appropriate headers (Accept-Language, etc.) | Set `Accept-Language: ru` and a real User-Agent; Kaspi may serve different content based on locale |
| aiogram + long-running scrape | Running scrape in the message handler -- blocks the handler, Telegram shows "typing..." forever | Trigger scrape as a background `asyncio.Task`; send a "scraping started" message immediately, then edit it when done |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Launching a new browser per scrape request | Each scrape takes 5-10 seconds just for browser startup | Keep one persistent browser, create fresh contexts per batch | Immediately noticeable -- manual scrape takes 15+ seconds |
| Scraping all products sequentially | 50 products x 3 seconds = 2.5 minutes per basket | Scrape in parallel batches of 3-5 using `asyncio.gather` with semaphore | At 20+ products per basket |
| Generating full price history charts for all items on every report | Chart generation grows linearly with basket size and history length | Cache charts; regenerate only when new data arrives | At 30+ products with 30+ days history |
| Loading full price history into memory for analytics | Memory spike when computing trends across months | Use SQL aggregations (AVG, MIN, MAX) instead of fetching all rows into Python | At 90 days retention with 50 products |
| matplotlib importing at module level | Adds 2-3 seconds to cold start, delays bot readiness | Lazy-import matplotlib only when chart generation is needed | Noticeable on every Railway cold start |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing Telegram bot token in code or docker-compose.yml | Token leaked via git history, anyone can impersonate the bot | Use Railway environment variables; load via `pydantic-settings`; add `.env` to `.gitignore` |
| Not validating user-submitted URLs | SSRF: user submits `http://localhost:5432` or internal Railway URLs as a "product URL" | Strict URL validation: must match `arbuz.kz`, `magnum.kz`, or `kaspi.kz/shop` domains only; reject all others |
| Allowing unlimited baskets/products without auth | Resource exhaustion: malicious user creates thousands of baskets to trigger excessive scraping | Enforce limits (10 baskets, 50 items) at the database level with constraints, not just UI checks |
| Logging full page HTML in production | Railway logs may contain sensitive data or balloon in size | Log only status codes, timing, and extracted field counts; store raw HTML only temporarily for debugging |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Requiring exact product URL format | Users paste URLs with tracking params, mobile URLs, or shortened links that fail validation | Normalize URLs: strip query params except essential ones, handle mobile subdomains, extract canonical product ID |
| Sending error messages in English for technical failures | Russian-speaking users see "Scraping failed: TimeoutError" and are confused | Translate all user-facing errors; keep technical details in admin logs only |
| No feedback during scraping (which takes 10-30 seconds) | User thinks bot is broken, sends the command again (triggering duplicate scrapes) | Send immediate "Checking prices..." message with a typing indicator; update the message when done |
| Sending massive text reports for large baskets | 50 items as a text wall is unreadable in Telegram | Paginate reports (show top 10 with biggest changes), offer full report as CSV or chart |
| Not confirming destructive actions | User accidentally deletes a basket with 30 carefully curated items | Add inline confirmation button: "Delete basket 'Weekly Groceries'? [Yes] [Cancel]" |

## "Looks Done But Isn't" Checklist

- [ ] **Scraping:** Returns product name and price -- but does not handle "out of stock" products (missing availability tracking leads to phantom price drops when items disappear)
- [ ] **Price history:** Stores prices daily -- but does not distinguish between original price and discount price (comparison reports will be misleading during sales)
- [ ] **Daily reports:** Sends at 07:00 -- but does not handle timezone correctly when Railway server is in UTC (use `Asia/Almaty` explicitly in APScheduler trigger, not system timezone)
- [ ] **URL validation:** Checks domain is correct -- but does not verify the URL actually points to a product (category pages, search results, and homepage URLs pass domain check but fail scraping)
- [ ] **Bilingual support:** Bot menus are translated -- but error messages, edge cases, and dynamic content (product names, store names) are not
- [ ] **CSV export:** Generates a file -- but does not handle Cyrillic product names in the encoding (use UTF-8 with BOM for Excel compatibility)
- [ ] **Price comparison:** Compares Arbuz vs Magnum totals -- but does not account for different package sizes (1kg rice at Arbuz vs 900g at Magnum makes per-item comparison misleading)
- [ ] **Manual scrape rate limiting:** Enforced per user -- but not per product/store (10 users all scraping the same store simultaneously still hammers it)

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Chromium OOM crashes | LOW | Add launch flags to Dockerfile, redeploy. No data loss. |
| Memory leak from context reuse | LOW | Implement context recycling, redeploy. Historical data intact. |
| Anti-bot blocking | MEDIUM | Switch to API interception; if IP is burned, may need proxy or wait for IP rotation. Scraping gap means missing price data points. |
| Scheduler silently stopped | MEDIUM | Fix initialization order, add PostgreSQL job store. Backfill missed scrapes manually or accept data gap. |
| Telegram flood ban | LOW | Add delays between messages. Ban lifts automatically in 15 minutes. |
| Selector breakage undetected | MEDIUM | Fix selectors, but days of bad data may already be stored. Need to identify and purge invalid price records. |
| Connection pool exhaustion | LOW | Adjust pool config, add semaphore. Requires redeploy but no data loss. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Chromium OOM in container | Phase 1 (Infrastructure) | Playwright smoke test passes on Railway with memory < 512MB |
| Browser memory leaks | Phase 2 (Scraping) | Memory stays flat across 3+ consecutive scrape runs in Railway logs |
| Anti-bot detection | Phase 2 (Scraping) | Stealth + API interception implemented; 100 consecutive scrapes without 403 |
| APScheduler silent death | Phase 1 (Bot setup) + Phase 3 (Scheduling) | Job fires correctly after Railway container restart; `/status` command reports last run |
| Telegram flood control | Phase 4 (Notifications) | Send reports to 10 users without triggering 429; `retry_after` handler tested |
| Selector breakage | Phase 2 (Scraping) + Phase 3 (Monitoring) | Validation rejects null prices; admin alert fires when >20% products fail |
| Connection pool exhaustion | Phase 1 (Database) + Phase 2 (Scraping) | Concurrent scraping (5 pages) + bot commands work simultaneously without timeout |

## Sources

- [Railway Help: Playwright browser executable missing](https://station.railway.com/questions/worker-timeouts-and-playwright-browser-e-d6499ade)
- [Railway Help: Playwright missing dependencies](https://station.railway.com/questions/playwright-missing-dependencies-683dd141)
- [Playwright Docker docs](https://playwright.dev/python/docs/docker)
- [Playwright memory leak with context reuse - Issue #286](https://github.com/microsoft/playwright-python/issues/286)
- [Playwright memory increase with same context - Issue #6319](https://github.com/microsoft/playwright/issues/6319)
- [Playwright 1.57 Chrome for Testing memory issue - Issue #38489](https://github.com/microsoft/playwright/issues/38489)
- [grammY: Scaling Up - Flood Limits](https://grammy.dev/advanced/flood)
- [aiogram: Strategy for TelegramRetryAfter - Discussion #1489](https://github.com/aiogram/aiogram/discussions/1489)
- [python-telegram-bot: Avoiding flood limits](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Avoiding-flood-limits)
- [APScheduler FAQ - missed jobs and coalesce](https://apscheduler.readthedocs.io/en/3.x/faq.html)
- [APScheduler AsyncIOScheduler initialization issue - #484](https://github.com/agronholm/apscheduler/issues/484)
- [APScheduler common mistakes (Medium)](https://sepgh.medium.com/common-mistakes-with-using-apscheduler-in-your-python-and-django-applications-100b289b812c)
- [asyncpg transaction leak on task cancellation - SQLAlchemy #12460](https://github.com/sqlalchemy/sqlalchemy/discussions/12460)
- [SQLAlchemy 2.0 Connection Pooling docs](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [Playwright Stealth anti-detection (BrightData)](https://brightdata.com/blog/how-tos/avoid-bot-detection-with-playwright-stealth)
- [ZenRows: Avoid Playwright bot detection](https://www.zenrows.com/blog/avoid-playwright-bot-detection)
- [Playwright production Docker guide (Thomas Bourimech)](https://thomasbourimech.com/blog/en/playwright-chromium-docker-production/)

---
*Pitfalls research for: Telegram grocery price tracking bot (Kazakh e-commerce)*
*Researched: 2026-03-30*
