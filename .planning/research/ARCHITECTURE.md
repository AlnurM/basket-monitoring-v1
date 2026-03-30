# Architecture Research

**Domain:** Telegram bot with web scraping, scheduling, and analytics
**Researched:** 2026-03-30
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Presentation Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Bot Handlers │  │  Keyboards   │  │  i18n Layer  │           │
│  │  (Routers)   │  │  (Inline)    │  │  (RU + EN)   │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                    │
├─────────┴─────────────────┴─────────────────┴────────────────────┤
│                       Service Layer                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐  │
│  │  Basket    │  │  Scraper   │  │  Analytics  │  │  Report   │  │
│  │  Service   │  │  Service   │  │  Service    │  │  Service  │  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬─────┘  │
│        │               │               │               │        │
├────────┴───────────────┴───────────────┴───────────────┴────────┤
│                     Scraper Engines                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │
│  │  Arbuz Scraper │  │ Magnum Scraper │  │ Kaspi Scraper  │      │
│  │  (Playwright)  │  │  (Playwright)  │  │ (httpx+selecto)│      │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘      │
│           │                   │                   │              │
├───────────┴───────────────────┴───────────────────┴──────────────┤
│                    Infrastructure Layer                           │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Postgres │  │  APScheduler │  │  Playwright  │               │
│  │ (asyncpg)│  │ (AsyncIO)    │  │  Browser Mgr │               │
│  └──────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Bot Handlers (Routers) | Process Telegram commands/callbacks, validate user input, dispatch to services | aiogram 3 Router per feature domain (basket, scrape, report, settings) |
| Keyboards | Build inline button layouts for navigation and actions | aiogram InlineKeyboardBuilder, callback data factories |
| i18n Layer | Translate all user-facing strings to RU/EN based on user preference | aiogram's i18n middleware or fluent-based approach |
| Basket Service | CRUD for baskets and items, enforce limits (10 baskets, 50 items) | Async service class calling repository layer |
| Scraper Service | Orchestrate scraping across engines, manage concurrency, handle retries | Coordinates engine dispatch based on URL/basket source |
| Analytics Service | Compute price changes, comparisons, trends from price history | Pure computation on DB queries, returns structured data |
| Report Service | Generate formatted messages, charts (matplotlib), CSV exports | Renders analytics output into Telegram-friendly formats |
| Scraper Engines | Extract price data from specific stores | Strategy pattern: each store has its own engine class |
| Scheduler | Trigger daily scrapes and report delivery at configured times | APScheduler AsyncIOScheduler with cron triggers |
| Browser Manager | Manage Playwright browser lifecycle, context pooling | Singleton that starts browser on app startup, provides contexts |
| Database | Persist users, baskets, items, price history, settings | SQLAlchemy 2 async ORM with asyncpg driver |

## Recommended Project Structure

```
price_spy/
├── __main__.py              # Entry point: start bot + scheduler
├── config.py                # Pydantic Settings: env vars, constants
├── bot/
│   ├── __init__.py
│   ├── create.py            # Bot and Dispatcher factory
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── db.py            # Inject async session into handler data
│   │   ├── i18n.py          # Language selection middleware
│   │   ├── throttle.py      # Rate limiting for manual scrapes
│   │   └── scheduler.py     # Inject scheduler into handler data
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # /start, registration, language selection
│   │   ├── basket.py        # Basket CRUD commands and callbacks
│   │   ├── product.py       # Add/remove product by URL
│   │   ├── report.py        # On-demand report, chart, CSV commands
│   │   ├── settings.py      # Notification time, language preference
│   │   └── scrape.py        # Manual scrape trigger
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── basket.py        # Basket list, actions
│   │   ├── product.py       # Product actions
│   │   └── common.py        # Back, cancel, pagination
│   ├── callbacks/
│   │   ├── __init__.py
│   │   └── factories.py     # CallbackData factories for type-safe callbacks
│   ├── states/
│   │   ├── __init__.py
│   │   └── forms.py         # FSM states for multi-step flows (add product, create basket)
│   └── filters/
│       ├── __init__.py
│       └── url.py           # URL format validation filters
├── services/
│   ├── __init__.py
│   ├── basket.py            # Basket business logic
│   ├── scraper.py           # Scrape orchestration
│   ├── analytics.py         # Price change computation, comparisons
│   ├── report.py            # Message formatting, chart generation
│   └── scheduler.py         # Job registration and management
├── scrapers/
│   ├── __init__.py
│   ├── base.py              # Abstract base scraper interface
│   ├── arbuz.py             # Arbuz.kz Playwright scraper
│   ├── magnum.py            # Magnum.kz Playwright scraper
│   ├── kaspi.py             # Kaspi.kz httpx + selectolax scraper
│   └── browser.py           # Playwright browser lifecycle manager
├── db/
│   ├── __init__.py
│   ├── engine.py            # create_async_engine, sessionmaker
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # DeclarativeBase
│   │   ├── user.py          # User model
│   │   ├── basket.py        # Basket model
│   │   ├── product.py       # Product model
│   │   └── price.py         # PriceRecord model
│   └── repositories/
│       ├── __init__.py
│       ├── base.py          # Generic async repository
│       ├── user.py          # User queries
│       ├── basket.py        # Basket queries
│       ├── product.py       # Product queries
│       └── price.py         # Price history queries
├── i18n/
│   ├── __init__.py
│   ├── ru.py                # Russian strings
│   └── en.py                # English strings
└── utils/
    ├── __init__.py
    ├── url_parser.py         # Parse and validate store URLs
    └── charts.py             # matplotlib chart generation helpers
```

### Structure Rationale

- **bot/:** Everything Telegram-specific. Handlers, keyboards, middlewares, FSM states. If you swapped Telegram for Discord, only this folder changes.
- **services/:** Business logic that does not know about Telegram. Handlers call services; services call repositories and scrapers.
- **scrapers/:** Isolated scraper engines per store. Each implements a common interface (`scrape(url) -> PriceResult`). The browser manager lives here because it is scraper infrastructure.
- **db/:** Database models and repository classes. Repositories abstract raw SQL/ORM queries behind clean async methods. Services never import from `sqlalchemy` directly.
- **i18n/:** Simple dictionary-based translation. Avoids heavyweight i18n frameworks for a two-language bot.
- **utils/:** Shared utilities that do not fit elsewhere (URL parsing, chart rendering).

## Architectural Patterns

### Pattern 1: Strategy Pattern for Scrapers

**What:** Each store gets its own scraper class implementing a shared interface. The scraper service dispatches to the correct engine based on URL domain or basket source type.
**When to use:** Always. This is the core abstraction for multi-store scraping.
**Trade-offs:** Slight overhead of an interface, but massive gain in testability and extensibility (adding a new store = one new file).

**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PriceResult:
    name: str
    original_price: float
    discount_price: float | None
    available: bool
    currency: str = "KZT"

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> PriceResult:
        """Scrape price data from a product URL."""
        ...

class ArbuzScraper(BaseScraper):
    def __init__(self, browser_manager: BrowserManager):
        self._browser = browser_manager

    async def scrape(self, url: str) -> PriceResult:
        async with self._browser.new_context() as ctx:
            page = await ctx.new_page()
            # ... Playwright logic for arbuz.kz
            return PriceResult(...)
```

### Pattern 2: Middleware Injection for Cross-Cutting Concerns

**What:** aiogram 3 middlewares inject the DB session, scheduler, and i18n context into every handler automatically. Handlers declare what they need via function parameters.
**When to use:** For database sessions, scheduler access, rate limiting, language resolution.
**Trade-offs:** Adds a middleware registration step at startup, but eliminates manual session/resource management in every handler.

**Example:**
```python
from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker

class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(self, handler, event, data):
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)
```

### Pattern 3: Browser Lifecycle as Singleton Manager

**What:** A single BrowserManager starts Playwright and the Chromium browser once at application startup. Scrapers request browser contexts from it. Contexts are created per-scrape and destroyed after.
**When to use:** Always when using Playwright. Browser startup is expensive (~2-5 seconds, ~100MB RAM). Context creation is cheap (~50ms).
**Trade-offs:** Single point of failure if browser crashes. Mitigate with auto-restart logic.

**Example:**
```python
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @asynccontextmanager
    async def new_context(self):
        ctx = await self._browser.new_context(
            user_agent="..."  # Rotated UA
        )
        try:
            yield ctx
        finally:
            await ctx.close()
```

### Pattern 4: Service Layer Separation

**What:** Handlers call service methods. Services contain business logic and call repositories. Repositories handle database queries. No layer skips.
**When to use:** From the start. The bot is complex enough that mixing Telegram handling with DB queries becomes unmaintainable fast.
**Trade-offs:** More files and indirection. Worth it for testability and clarity in a project with scraping + scheduling + analytics.

## Data Flow

### User Command Flow (e.g., "Add product to basket")

```
User sends URL in Telegram
    |
    v
aiogram Dispatcher (polling)
    |
    v
Middleware chain (DB session, i18n, throttle)
    |
    v
Router: product handler
    |
    v
URL validation filter (correct domain? correct basket source?)
    |
    v
BasketService.add_product(session, user_id, url, quantity)
    |
    v
ProductRepository.create(session, product_data)
    |
    v
Response: confirmation message with inline keyboard
```

### Scheduled Scrape Flow (daily at 07:00)

```
APScheduler cron trigger fires at 07:00 Asia/Almaty
    |
    v
ScraperService.run_daily_scrape()
    |
    v
BasketRepository.get_all_active_baskets_with_products()
    |
    v
For each product URL (with semaphore for concurrency):
    |
    v
Dispatch to correct scraper engine (Arbuz/Magnum/Kaspi)
    |
    v
Engine returns PriceResult
    |
    v
PriceRepository.save_price_record(product_id, price_result, timestamp)
    |
    v
AnalyticsService.detect_price_drops(threshold=10%)
    |
    v
For users with drops > 10%: Bot.send_message(alert)
```

### Report Delivery Flow (at user's configured time)

```
APScheduler cron trigger per user (or batched by time slot)
    |
    v
ReportService.generate_daily_report(user_id)
    |
    v
AnalyticsService.get_basket_summary(user_id, days=7)
    |-- Total cost today vs yesterday
    |-- Items with price changes
    |-- Arbuz vs Magnum comparison (if both baskets exist)
    |
    v
ReportService.format_message(summary, user_lang)
    |
    v
Bot.send_message(user_id, formatted_report)
```

### Key Data Flows

1. **Product registration:** User sends URL -> validate -> store product with basket link -> trigger first scrape -> cache product name from scrape result
2. **Price collection:** Scheduler -> scraper engines -> price records stored with timestamp, original price, discount price, availability
3. **Analytics computation:** On-demand or pre-report: query price history -> compute deltas, trends, cross-store comparisons -> return structured results
4. **Report rendering:** Analytics data -> format as Telegram message (markdown) + optional matplotlib chart (PNG buffer) + optional CSV (file upload)

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 users | Single process. Bot polling + APScheduler in same asyncio loop. Sequential or lightly parallel scraping (~3 concurrent contexts). No caching needed. |
| 10-100 users | Same single process works. Add semaphore-controlled parallelism for scraping (5-10 concurrent). Add product name caching to avoid redundant scrapes for shared URLs. Consider batch report generation. |
| 100+ users | Separate scraper worker process with task queue (Redis + arq/celery). Bot process handles only Telegram. Shared Postgres. Add scrape result caching layer. |

### Scaling Priorities

1. **First bottleneck: Scraping time.** With 100 users x 20 products = 2000 URLs. Playwright contexts at ~3 seconds each = ~100 minutes sequential. Fix: deduplicate URLs across users, parallel contexts with semaphore, batch by store. At small scale (1-10 users, ~50-200 URLs), this is manageable in single process with light parallelism.
2. **Second bottleneck: Memory from Playwright.** Each browser context uses ~50-100MB. With 5 concurrent contexts, that is 250-500MB on top of browser base (~150MB). Railway Starter plan should handle this for small scale. Fix: strict concurrency limits, context-per-scrape (never pool idle contexts).
3. **Third bottleneck: Report generation.** matplotlib chart rendering is CPU-bound. At scale, pre-generate charts after scraping rather than on-demand. Not a concern at 1-10 users.

## Anti-Patterns

### Anti-Pattern 1: Browser per Scrape

**What people do:** Launch a new Playwright browser instance for every product scrape.
**Why it is wrong:** Browser launch takes 2-5 seconds and ~150MB RAM. Doing this per URL means 2000 URLs = hours of just browser startup.
**Do this instead:** Single browser started at app boot. Create lightweight browser contexts per scrape, close them after. Context creation is ~50ms.

### Anti-Pattern 2: Database Queries in Handlers

**What people do:** Write raw SQLAlchemy queries directly in aiogram handler functions.
**Why it is wrong:** Handlers become untestable, business logic mixes with presentation logic, and query duplication spreads across handlers.
**Do this instead:** Handlers call service methods. Services call repository methods. Repositories own all database queries.

### Anti-Pattern 3: Monolithic Scraper

**What people do:** One giant function with if/elif branches for each store.
**Why it is wrong:** Adding a new store requires modifying existing scrape logic. Testing requires mocking the entire function. Different stores need different tools (Playwright vs httpx).
**Do this instead:** Strategy pattern. One class per store implementing a shared interface. Scraper service dispatches based on URL domain.

### Anti-Pattern 4: Storing Scheduler Jobs in Memory

**What people do:** Use APScheduler's default MemoryJobStore, losing all scheduled jobs on restart.
**Why it is wrong:** On Railway deploy/restart, all user notification schedules vanish. Users do not get their reports until they reconfigure.
**Do this instead:** Use APScheduler's SQLAlchemyJobStore with the same Postgres database, or reconstruct jobs from user settings on startup. For this project, reconstructing from DB on startup is simpler and avoids APScheduler job store complexity.

### Anti-Pattern 5: Blocking Calls in Async Context

**What people do:** Use synchronous `requests` library or `time.sleep()` in async handlers.
**Why it is wrong:** Blocks the entire event loop. Bot stops responding to all users while one scrape runs.
**Do this instead:** Use `httpx` (async), `playwright.async_api`, and `asyncio.sleep()`. For CPU-bound work (matplotlib), use `asyncio.to_thread()`.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Telegram Bot API | aiogram 3 long polling via Dispatcher.start_polling() | Webhook possible but polling simpler for Railway single-process |
| Arbuz.kz | Playwright page navigation + DOM extraction or API interception | SPA, returns 403 on direct HTTP. Use playwright-stealth. |
| Magnum.kz | Playwright page navigation + DOM extraction | SPA with dynamic rendering. Use playwright-stealth. |
| Kaspi.kz/shop | httpx GET + selectolax HTML parsing | Server-side rendered, no JS needed. Simpler and faster. |
| PostgreSQL | SQLAlchemy 2 async ORM via asyncpg | Railway managed instance. Connection string from env var. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Handlers <-> Services | Direct async method calls | Services are injected or imported. Handlers pass session from middleware. |
| Services <-> Repositories | Direct async method calls | Repositories accept session as parameter. Services own transaction boundaries. |
| Services <-> Scrapers | Direct async method calls | ScraperService selects engine by URL domain, calls engine.scrape(url). |
| Scheduler <-> Services | APScheduler calls service methods as job functions | Scheduler jobs reference service functions with injected dependencies. |
| Scrapers <-> BrowserManager | Context manager pattern | Scrapers call `browser_manager.new_context()` as async context manager. |

## Build Order Dependencies

The following describes what depends on what, informing the order in which components should be built.

### Dependency Graph

```
config.py                (no dependencies -- build first)
    |
    v
db/models + db/engine    (depends on: config)
    |
    v
db/repositories          (depends on: models)
    |
    v
scrapers/base + browser  (depends on: config)
    |
    v
scrapers/arbuz,magnum,kaspi (depends on: base, browser)
    |
    v
services/basket          (depends on: repositories)
services/scraper         (depends on: scrapers, repositories)
services/analytics       (depends on: repositories)
services/report          (depends on: analytics, charts util)
    |
    v
bot/middlewares           (depends on: db/engine, config)
bot/handlers             (depends on: services, keyboards, states)
bot/keyboards            (depends on: callbacks)
    |
    v
services/scheduler       (depends on: services/scraper, services/report, APScheduler)
    |
    v
__main__.py              (depends on: everything -- wires it all together)
```

### Suggested Build Phases

1. **Foundation:** config, database models, engine, basic repository layer. Without this, nothing else can persist data.
2. **Scraping core:** BrowserManager, base scraper interface, one store scraper (Arbuz as primary). Validates that price extraction works end-to-end.
3. **Bot skeleton:** Dispatcher setup, /start handler, basic middleware (DB session). Proves bot responds and can persist a user.
4. **Basket management:** Basket/product services, handlers, keyboards. Users can create baskets and add URLs.
5. **Scraping integration:** Scraper service, connect scrapers to basket products, store price records. Manual scrape trigger.
6. **Scheduling:** APScheduler setup, daily scrape job, job reconstruction on startup.
7. **Analytics and reports:** Analytics service, report formatting, chart generation, daily report delivery.
8. **Polish:** i18n, remaining scrapers (Magnum, Kaspi), comparison features, CSV export, price drop alerts.

## Sources

- [aiogram 3 documentation](https://docs.aiogram.dev/) - Router system, middlewares, dispatcher
- [aiogram bot template by welel](https://github.com/welel/aiogram-bot-template) - Project structure reference
- [aiogram 3 guide: Routers](https://mastergroosha.github.io/aiogram-3-guide/routers/) - Multi-file bot organization
- [APScheduler documentation](https://apscheduler.readthedocs.io/en/3.x/userguide.html) - AsyncIOScheduler, triggers, job stores
- [Playwright web scraping tutorial (Oxylabs)](https://oxylabs.io/blog/playwright-web-scraping) - Browser context management patterns
- [playwright-pool library](https://github.com/tgscan/playwright-pool) - Browser context pooling patterns
- [Repository pattern with SQLAlchemy](https://www.cosmicpython.com/book/chapter_02_repository.html) - Cosmic Python architecture patterns
- [SQLAlchemy 2 async patterns](https://chaoticengineer.hashnode.dev/fastapi-sqlalchemy) - Async session management

---
*Architecture research for: Telegram grocery price tracking bot (price-spy)*
*Researched: 2026-03-30*
