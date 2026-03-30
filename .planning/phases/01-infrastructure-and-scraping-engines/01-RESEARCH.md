# Phase 1: Infrastructure and Scraping Engines - Research

**Researched:** 2026-03-30
**Domain:** Python Telegram bot + Playwright web scraping + PostgreSQL + Railway deployment
**Confidence:** HIGH

## Summary

Phase 1 is a greenfield foundation phase covering project initialization, database schema, all three scraper engines (Arbuz via Playwright, Magnum via Playwright, Kaspi via httpx), a minimal Telegram bot with user registration and bilingual support, and deployment to Railway with Docker. The phase is large but well-defined by the technical specification in `task.md` and constrained by locked decisions in CONTEXT.md.

The primary technical risks are: (1) Playwright Docker configuration on Railway (the /dev/shm and Chromium memory issues documented in PITFALLS research), (2) discovering actual DOM selectors for Arbuz.kz and Magnum.kz at development time since these are unknown until live inspection, and (3) correct async lifecycle orchestration -- starting Playwright browser, DB pool, APScheduler, and aiogram polling in the right order within a single process.

**Primary recommendation:** Build bottom-up -- config, DB, scrapers, then bot -- validating each layer works on Railway before building the next. Get a trivial Playwright script running in Docker on Railway as the very first milestone.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Hybrid scraping approach from day 1 -- attempt API interception (capture XHR/fetch JSON responses during page.goto) AND have DOM selectors as fallback in the same scrape cycle. If API yields valid price data, use it; otherwise fall back to DOM extraction.
- **D-02:** Selector discovery approach is Claude's discretion -- choose multi-selector fallback or hardcoded based on what the actual site HTML looks like during development.
- **D-03:** Kaspi.kz parser choice is Claude's discretion -- selectolax (Lexbor) recommended by research but Claude may choose based on actual HTML structure.
- **D-04:** Full anti-bot evasion suite from Phase 1: playwright-stealth plugin + UA rotation + random delays between requests + viewport randomization + cookie persistence + proxy support architecture (even if no proxy is used initially).
- **D-05:** i18n library/approach is Claude's discretion -- choose the best fit for aiogram 3 (gettext, JSON dicts, or Fluent).
- **D-06:** Language selection is forced on /start -- bot asks user to choose RU or EN before proceeding with any functionality. No default language assumed.
- **D-07:** Detailed diagnostic errors to users -- when a scrape fails, show technical details: "[Product name] failed: timeout after 30s on arbuz.kz" or "[Product] failed: price selector not found on magnum.kz".
- **D-08:** Silent retries -- retry 3 times with exponential backoff silently. Only report the final failure to the user.
- **D-09:** Individual error reporting per item -- even if multiple items fail from the same source, list each failed item separately in reports and error messages.
- **D-10:** Full startup validation on boot -- verify DB connection, verify Playwright can launch Chromium, verify bot token is valid, log all results. Fail fast (crash) if any check fails. No /health endpoint needed in Phase 1.
- **D-11:** Docker base image choice is Claude's discretion -- python:3.12-slim with manual deps or Microsoft's official Playwright image. Research flagged /dev/shm as critical concern.
- **D-12:** Both local and Docker development supported -- Docker Compose for full stack (bot + PostgreSQL), but also runnable directly via `python -m bot.main` with local PostgreSQL and local Playwright for faster iteration.

### Claude's Discretion
- Selector discovery approach (D-02)
- Kaspi.kz HTML parser choice (D-03)
- i18n library choice for aiogram 3 (D-05)
- Docker base image selection (D-11)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| USER-01 | User can register via /start command in Telegram | aiogram 3 Router + handler pattern; user model in DB |
| USER-02 | User can select interface language (RU or EN) at registration | i18n recommendation (dictionary approach); forced language selection per D-06 |
| USER-03 | User can switch language at any time via settings | i18n middleware reads user preference from DB; /settings handler updates it |
| USER-04 | User can view help with available commands via /help | Simple handler returning translated help text |
| SCRP-01 | Bot scrapes Arbuz.kz product pages via Playwright (handles SPA/403) | BrowserManager singleton + ArbuzScraper strategy class; Playwright Docker setup |
| SCRP-02 | Bot scrapes Magnum.kz product pages via Playwright (handles SPA) | BrowserManager + MagnumScraper strategy class; same Playwright infrastructure |
| SCRP-03 | Bot scrapes Kaspi.kz/shop product pages via httpx + selectolax (SSR) | KaspiScraper using httpx async client + selectolax Lexbor parser |
| SCRP-04 | Scraper extracts: current price, original price, product name, availability | PriceResult dataclass/Pydantic model with validation (price > 0, name non-empty) |
| SCRP-05 | Product name is cached after first scrape | Store name in basket_items table on first successful scrape |
| SCRP-06 | Bot attempts API interception via Playwright network events | page.on("response") pattern to capture XHR/fetch JSON; D-01 hybrid approach |
| SCRP-07 | Scraper uses playwright-stealth and UA rotation | playwright-stealth 2.x + UA rotation pool per D-04 |
| SCRP-08 | Scraper reuses browser instance across scrape cycle with fresh contexts per store | BrowserManager singleton pattern with new_context() per scrape batch |
| SCRP-09 | Scraper runs with parallelism (semaphore: max 3 Playwright, max 10 httpx) | asyncio.Semaphore for concurrency control |
| SCRP-10 | Scraper retries failed requests (3 attempts with exponential backoff) | Retry decorator/utility with exponential backoff per D-08 |
| INFR-01 | Bot runs as single process (bot + scheduler) on Railway | __main__.py orchestrating aiogram polling + APScheduler in one asyncio loop |
| INFR-02 | PostgreSQL database on Railway for all persistent data | SQLAlchemy 2 async + asyncpg + Alembic migrations |
| INFR-03 | Playwright runs headless Chromium without GPU/sandbox in Docker | Chromium launch args: --no-sandbox, --disable-gpu, --disable-dev-shm-usage |
| INFR-04 | Docker image handles Playwright system dependencies correctly (including /dev/shm) | Microsoft Playwright Docker base image (recommended) |
| INFR-05 | APScheduler uses PostgreSQL jobstore for persistent scheduled tasks | SQLAlchemyJobStore with sync DB URL (APScheduler 3.x limitation) |
| INFR-06 | Database connection pool sized for concurrent scraping + bot handlers | pool_size=5, max_overflow=5, pool_pre_ping=True |
| INFR-07 | All times handled in Asia/Almaty timezone (Railway runs UTC) | APScheduler timezone="Asia/Almaty"; all DB timestamps as TIMESTAMPTZ |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Runtime | Best wheel coverage for selectolax/matplotlib; 3.14 on dev machine but Docker pins 3.12 |
| aiogram | ~=3.26 | Telegram Bot API | Async-native, Router system, middleware injection, Bot API 9.4 |
| playwright | ~=1.50 | Browser automation | Pin to match Docker base image version exactly |
| playwright-stealth | ~=2.0.2 | Anti-detection | Latest stable; applies stealth patches to page objects via `stealth_async(page)` |
| httpx | ~=0.28 | Async HTTP client | For Kaspi.kz SSR scraping; HTTP/2 support |
| selectolax | ~=0.4.7 | Fast HTML parsing | Lexbor backend, 20x faster than BS4, CSS selector API |
| SQLAlchemy | ~=2.0.48 | Async ORM | create_async_engine + mapped classes; do NOT use 2.1 beta |
| asyncpg | ~=0.31.0 | PostgreSQL driver | 5x faster than psycopg3 for asyncio |
| alembic | ~=1.18 | DB migrations | Async support via run_async; essential from day 1 |
| APScheduler | ~=3.11 | Job scheduling | AsyncIOScheduler + SQLAlchemyJobStore; do NOT use 4.x alpha |
| pydantic | ~=2.12 | Data validation | PriceResult models, scraper output validation |
| pydantic-settings | ~=2.13 | Env config | Typed settings from Railway env vars and .env files |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uv | latest | Package manager | Project init, dependency management, lockfile |
| ruff | latest | Linter + formatter | All Python files; replaces flake8+black+isort |
| pytest | ~=8.x | Testing | Scraper validation, handler tests |
| pytest-asyncio | ~=0.24 | Async test support | Testing async scrapers, DB operations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| playwright-stealth 2.x | patchright (Playwright fork) | More evasion capability but version lag risk; upgrade path if stealth fails |
| selectolax | BeautifulSoup4 | 20x slower; use only if selectolax CSS selectors are insufficient for Kaspi HTML |
| Dictionary i18n | gettext (.po files) | Gettext is overkill for 2 languages; dictionary is simpler, faster to iterate |
| Microsoft Playwright image | python:3.12-slim + manual deps | Slim requires manual system dep installation, /dev/shm config; MS image is safer |

**Installation:**
```bash
uv init price-spy
cd price-spy
uv python pin 3.12

uv add aiogram~=3.26 \
    playwright~=1.50 \
    playwright-stealth~=2.0 \
    httpx~=0.28 \
    selectolax~=0.4.7 \
    "sqlalchemy[asyncio]~=2.0.48" \
    asyncpg~=0.31.0 \
    alembic~=1.18 \
    apscheduler~=3.11 \
    pydantic~=2.12 \
    pydantic-settings~=2.13

uv add --dev ruff pytest pytest-asyncio

# Install Playwright browsers (dev machine only)
playwright install chromium
```

**Version note:** playwright-stealth has been updated to 2.0.2 (Feb 2026), up from 1.0.6 referenced in earlier STACK research. The API remains `stealth_async(page)` but the version pin should be `~=2.0` not `~=1.0.6`.

## Project Constraints (from CLAUDE.md)

- Tech stack: Python only -- aiogram 3, Playwright, httpx, selectolax, SQLAlchemy 2, asyncpg, APScheduler, matplotlib, Pydantic Settings
- Hosting: Railway (Starter plan, ~$5-10/month)
- Database: PostgreSQL (Railway managed)
- Scraper resources: Playwright headless Chromium without GPU/sandbox in Railway container
- Limits: Max 10 baskets/user, 50 items/basket, 90-day price history retention
- Bot detection: playwright-stealth plugin + UA rotation required for Arbuz/Magnum
- GSD workflow enforcement: use `/gsd:` entry points for work

## Architecture Patterns

### Recommended Project Structure
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
│   │   └── i18n.py          # Language resolution middleware
│   └── handlers/
│       ├── __init__.py
│       └── start.py         # /start, /help, language selection
├── scrapers/
│   ├── __init__.py
│   ├── base.py              # Abstract BaseScraper interface
│   ├── arbuz.py             # ArbuzScraper (Playwright + API interception)
│   ├── magnum.py            # MagnumScraper (Playwright + API interception)
│   ├── kaspi.py             # KaspiScraper (httpx + selectolax)
│   ├── browser.py           # BrowserManager singleton
│   ├── stealth.py           # Stealth config, UA rotation pool
│   └── models.py            # PriceResult Pydantic model
├── services/
│   ├── __init__.py
│   └── scraper.py           # Scrape orchestration, concurrency, retries
├── db/
│   ├── __init__.py
│   ├── engine.py            # create_async_engine, sessionmaker
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # DeclarativeBase
│   │   └── user.py          # User model (for Phase 1)
│   └── repositories/
│       ├── __init__.py
│       └── user.py          # User CRUD
├── i18n/
│   ├── __init__.py
│   ├── core.py              # Translator class, get_text function
│   ├── ru.py                # Russian strings dictionary
│   └── en.py                # English strings dictionary
├── alembic/                 # Alembic migrations directory
│   ├── env.py
│   └── versions/
├── alembic.ini
├── Dockerfile
├── docker-compose.yml       # Local dev: bot + PostgreSQL
├── railway.toml
├── pyproject.toml
└── .env.example
```

### Pattern 1: Strategy Pattern for Scrapers
**What:** Each store gets its own scraper class implementing `BaseScraper.scrape(url) -> PriceResult`. The scraper service dispatches by URL domain.
**When to use:** Always. This is the core scraping abstraction.
**Example:**
```python
# Source: Architecture research + task.md pseudocode
from abc import ABC, abstractmethod
from pydantic import BaseModel, field_validator

class PriceResult(BaseModel):
    name: str
    price: int          # Store as integer tenge (no floating point)
    original_price: int | None
    is_available: bool

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> PriceResult:
        ...
```

### Pattern 2: Hybrid API Interception + DOM Fallback (D-01)
**What:** During Playwright page.goto, capture network responses matching JSON API patterns. If valid price data is found in an API response, use it. Otherwise fall back to DOM selector extraction.
**When to use:** For Arbuz and Magnum scrapers.
**Example:**
```python
# Source: Playwright docs (https://playwright.dev/python/docs/network)
async def scrape_with_api_interception(self, url: str) -> PriceResult:
    api_data = {}

    async def capture_response(response):
        if response.url.endswith(".json") or "api" in response.url:
            try:
                if "application/json" in (response.headers.get("content-type", "")):
                    body = await response.json()
                    # Extract price data if present
                    if "price" in str(body).lower():
                        api_data["response"] = body
            except Exception:
                pass

    async with self._browser.new_context() as ctx:
        page = await ctx.new_page()
        await stealth_async(page)
        page.on("response", capture_response)
        await page.goto(url, wait_until="networkidle")

        # Try API data first
        if api_data.get("response"):
            result = self._parse_api_response(api_data["response"])
            if result:
                return result

        # Fallback: DOM extraction
        return await self._extract_from_dom(page)
```

### Pattern 3: BrowserManager Singleton with Context Recycling
**What:** Single browser instance started at boot. Fresh browser contexts created per scrape batch, closed after use. Browser recycled every 24h or 100 pages.
**When to use:** Always for Playwright scrapers.
**Critical:** Close every page and context in try/finally. Never reuse contexts across scrape cycles.

### Pattern 4: Startup Validation Sequence (D-10)
**What:** On boot, validate all external dependencies before starting the main loop.
**When to use:** In `__main__.py` before aiogram polling starts.
**Example:**
```python
async def validate_startup(settings: Settings) -> None:
    """Fail fast if any dependency is unavailable."""
    # 1. DB connection
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("DB connection: OK")

    # 2. Playwright browser
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=[...])
    await browser.close()
    await pw.stop()
    log.info("Playwright browser: OK")

    # 3. Bot token
    from aiogram import Bot
    bot = Bot(token=settings.bot_token)
    me = await bot.get_me()
    await bot.session.close()
    log.info(f"Bot token: OK (@{me.username})")
```

### Pattern 5: Dictionary-Based i18n (D-05 Recommendation)
**What:** Simple Python dictionaries mapping string keys to translations. A middleware reads the user's language from DB and injects a translator function into handler data.
**When to use:** For this project (only 2 languages, ~50-100 strings).
**Why not gettext:** gettext requires .po/.mo compilation workflow, which is overkill for 2 languages. Dictionary approach is faster to iterate, easier to maintain, and keeps translations in Python (no external tooling).
**Example:**
```python
# i18n/ru.py
STRINGS = {
    "welcome": "Добро пожаловать! Выберите язык:",
    "help": "Доступные команды:\n/start - Начать\n/help - Помощь",
    "language_set": "Язык установлен: Русский",
    "scrape_failed": "{product} не удалось: {reason} на {source}",
}

# i18n/en.py
STRINGS = {
    "welcome": "Welcome! Please select a language:",
    "help": "Available commands:\n/start - Start\n/help - Help",
    "language_set": "Language set: English",
    "scrape_failed": "{product} failed: {reason} on {source}",
}

# i18n/core.py
from . import ru, en

_LANGS = {"ru": ru.STRINGS, "en": en.STRINGS}

def get_text(key: str, lang: str = "en", **kwargs) -> str:
    template = _LANGS.get(lang, _LANGS["en"]).get(key, key)
    return template.format(**kwargs) if kwargs else template
```

### Anti-Patterns to Avoid
- **Browser per scrape:** Launch cost is 2-5s + 150MB. Use singleton BrowserManager.
- **Storing prices as floats:** Use integer tenge. Kazakhstan grocery prices do not use tiyn.
- **No Alembic from day 1:** Use Alembic migrations from the very first schema. No raw CREATE TABLE.
- **APScheduler init at module level:** Must initialize AFTER the asyncio event loop starts (in on_startup hook).
- **Blocking matplotlib in async:** Use `asyncio.to_thread()` for chart generation (Phase 4 concern, but pattern matters now).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Anti-bot evasion | Custom navigator patches | playwright-stealth 2.x | Covers webdriver flag, Chrome properties, WebGL fingerprint |
| HTML parsing (Kaspi) | Regex on HTML strings | selectolax (Lexbor) | CSS selectors, 20x faster than BS4, handles malformed HTML |
| DB migrations | CREATE TABLE scripts | Alembic | Schema evolution without data loss; async support |
| Env config | os.environ dict parsing | pydantic-settings | Type validation, .env file support, Railway env var injection |
| Retry logic | Nested try/except loops | tenacity or custom decorator | Exponential backoff, configurable attempts, clean separation |
| URL validation | Manual string matching | Compiled regex patterns | task.md provides exact URL patterns for all 3 stores |

**Key insight:** The task.md specification contains detailed URL regex patterns, DB schema SQL, scraper pseudocode, and project structure. Follow these closely rather than designing from scratch -- they represent validated decisions.

## Common Pitfalls

### Pitfall 1: Playwright Chromium OOM in Railway Container
**What goes wrong:** Chromium crashes silently, scraping returns empty results or container restarts.
**Why it happens:** Docker defaults /dev/shm to 64MB; Chromium needs more for rendering.
**How to avoid:** Use Microsoft Playwright Docker base image (has correct /dev/shm). Launch with `--disable-dev-shm-usage`, `--no-sandbox`, `--disable-gpu`. Keep Railway memory at 512MB minimum.
**Warning signs:** Intermittent None prices locally vs Railway; SIGKILL without Python traceback.

### Pitfall 2: Playwright + Docker Version Mismatch
**What goes wrong:** "Browser executable not found" on Railway despite working locally.
**Why it happens:** Playwright Python package version must exactly match the Docker base image browser version.
**How to avoid:** Pin `playwright==1.50.0` in pyproject.toml to match `mcr.microsoft.com/playwright/python:v1.50.0-noble`.

### Pitfall 3: APScheduler Init Order with aiogram
**What goes wrong:** Scheduler silently fails to fire jobs. No errors, no logs.
**Why it happens:** AsyncIOScheduler initialized before asyncio event loop starts.
**How to avoid:** Initialize scheduler in aiogram's `on_startup` hook, not at module level. Start scheduler AFTER dispatcher is running.

### Pitfall 4: APScheduler SQLAlchemyJobStore Needs Sync URL
**What goes wrong:** SQLAlchemyJobStore fails with async engine errors.
**Why it happens:** APScheduler 3.x SQLAlchemyJobStore uses synchronous SQLAlchemy internally.
**How to avoid:** Provide a sync DATABASE_URL (`postgresql://...`) not async (`postgresql+asyncpg://...`). Derive sync URL from async URL by stripping the `+asyncpg` part.

### Pitfall 5: asyncpg Connection Pool Exhaustion
**What goes wrong:** Bot becomes unresponsive during scraping; DB queries hang.
**Why it happens:** Concurrent scrapers + bot handlers exceed pool limits.
**How to avoid:** Configure `pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`. Use semaphore (max 3 Playwright concurrent) matching pool availability.

### Pitfall 6: Browser Context Memory Leaks
**What goes wrong:** Memory grows over days, eventually OOM.
**Why it happens:** Reusing browser contexts accumulates cached responses and DOM state.
**How to avoid:** Create fresh context per scrape batch. Close every page in try/finally. Recycle browser instance every 24h.

### Pitfall 7: Railway Container Restarts Losing Scheduler Jobs
**What goes wrong:** Daily scrape stops firing after a deploy/restart.
**Why it happens:** Default MemoryJobStore loses all jobs on restart.
**How to avoid:** Use SQLAlchemyJobStore with PostgreSQL. Set `misfire_grace_time=900` (15 min). Set `coalesce=True`. Alternative: reconstruct fixed jobs (daily scrape) from code on startup, only persist user-specific jobs.

### Pitfall 8: Forced Language Selection Flow
**What goes wrong:** User sends commands before selecting language; bot responds in wrong language or crashes.
**Why it happens:** D-06 requires language selection before any functionality.
**How to avoid:** Check user exists in DB (with language set) as first step in all handlers. If no language set, redirect to language selection flow. Use aiogram middleware to inject user language or redirect.

## Code Examples

### Chromium Launch Args for Railway Docker
```python
# Source: PITFALLS research + Playwright Docker docs
CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--single-process",
]

browser = await playwright.chromium.launch(
    headless=True,
    args=CHROMIUM_ARGS,
)
```

### Pydantic Settings Configuration
```python
# Source: task.md env vars section
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bot_token: str
    database_url: str  # postgresql+asyncpg://...

    scrape_concurrency: int = 3
    scrape_timeout: int = 30000
    scrape_retry_count: int = 3
    scrape_daily_hour: int = 7

    max_baskets_per_user: int = 10
    max_items_per_basket: int = 50
    price_history_retention_days: int = 90

    log_level: str = "INFO"

    @property
    def database_url_sync(self) -> str:
        """Sync URL for APScheduler jobstore."""
        return self.database_url.replace("+asyncpg", "")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

### DB Engine Setup with Pool Configuration
```python
# Source: PITFALLS research (Pitfall 7: pool exhaustion)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)
```

### APScheduler Setup in on_startup
```python
# Source: PITFALLS research (Pitfall 4: init order)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

async def on_startup(bot: Bot) -> None:
    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.database_url_sync)
    }
    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone="Asia/Almaty",
    )
    scheduler.add_job(
        daily_scrape,
        "cron",
        hour=7,
        minute=0,
        id="daily_scrape",
        replace_existing=True,
        misfire_grace_time=900,
        coalesce=True,
    )
    scheduler.start()
```

### URL Validation Patterns
```python
# Source: task.md section 6.4
import re

URL_PATTERNS = {
    "arbuz": re.compile(
        r"https?://arbuz\.kz/ru/\w+/catalog/item/(\d+)-[\w-]+"
    ),
    "magnum": re.compile(
        r"https?://magnum\.kz/products/(\d+)"
    ),
    "kaspi": re.compile(
        r"https?://kaspi\.kz/shop/p/[\w-]+-(\d+)"
    ),
}

SOURCE_TO_BASKET = {
    "arbuz": "arbuz",
    "magnum": "magnum",
    "kaspi": "magnum",   # kaspi links go into magnum baskets
}
```

### Retry with Exponential Backoff (D-08)
```python
import asyncio
import random
from functools import wraps

def retry_scrape(max_attempts: int = 3, base_delay: float = 2.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(delay)
            raise last_error
        return wrapper
    return decorator
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| playwright-stealth 1.0.6 | playwright-stealth 2.0.2 | Feb 2026 | API surface cleaned up; pin ~=2.0 not ~=1.0.6 |
| APScheduler 4.x hype | APScheduler 3.11.2 stable | Ongoing | 4.x remains alpha since 2023; do NOT use |
| python:3.12-slim for Playwright | mcr.microsoft.com/playwright/python | Playwright docs | MS image avoids manual system dep management |
| gettext for small bots | Dictionary-based i18n | Community trend | Simpler for 2-language bots; no .po compilation needed |

**Deprecated/outdated:**
- selectolax Modest backend: deprecated, use Lexbor (default since 0.4.x)
- APScheduler 4.x: still alpha, not for production
- SQLAlchemy 2.1 beta: not for production, stick with 2.0.48

## Discretion Recommendations

### D-02: Selector Discovery -- Use Multi-Selector Fallback
**Recommendation:** Implement a list of candidate selectors per field (price, name, availability) and try each in order. Since Arbuz and Magnum are SPAs with build-tool-generated class names, selectors will break. A fallback list buys time.
**Confidence:** MEDIUM (actual selectors unknown until live inspection)

### D-03: Kaspi.kz Parser -- Use selectolax (Lexbor)
**Recommendation:** selectolax with Lexbor backend. Kaspi.kz is SSR with well-formed HTML. selectolax CSS selectors are sufficient and 20x faster than BeautifulSoup.
**Confidence:** HIGH

### D-05: i18n -- Use Dictionary Approach
**Recommendation:** Simple Python dictionaries (one per language) with a `get_text(key, lang, **kwargs)` function. An aiogram middleware reads the user's language from DB and injects the translator. This is simpler than gettext (no .po compilation), lighter than Fluent, and perfectly adequate for 2 languages with ~50-100 strings.
**Confidence:** HIGH

### D-11: Docker Base Image -- Use Microsoft Playwright Image
**Recommendation:** `mcr.microsoft.com/playwright/python:v1.50.0-noble`. This image has all Chromium system dependencies pre-installed, correct /dev/shm configuration, and eliminates the most common Railway deployment failure mode. Pin the Playwright Python package to match exactly: `playwright==1.50.0`.
**Confidence:** HIGH

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | Downloadable via uv | 3.12.12 | uv python install 3.12 |
| uv | Package management | Yes | 0.9.24 | -- |
| Docker | Railway deployment | Yes | 24.0.2 | -- |
| PostgreSQL | Data storage | Via Docker Compose (local) | Railway provides | docker-compose.yml with postgres:16 |
| Playwright browsers | Scraping | Install via `playwright install chromium` | Matches package version | -- |

**Missing dependencies with no fallback:** None -- all tools available or installable.

**Missing dependencies with fallback:**
- Python 3.12 not the system default (3.14 installed) -- use `uv python pin 3.12` to set project Python version.

## Open Questions

1. **Arbuz.kz DOM selectors**
   - What we know: Site returns 403 on direct HTTP; it is an SPA. Exact HTML structure and CSS classes are unknown.
   - What is unclear: What selectors extract price, name, availability. Whether an internal JSON API exists.
   - Recommendation: First task for Arbuz scraper should be live inspection -- navigate in Playwright, capture network traffic, identify API endpoints or stable DOM selectors. Document findings before writing extraction logic.

2. **Magnum.kz DOM selectors**
   - What we know: Next.js SPA with dynamic rendering. Exact structure unknown.
   - What is unclear: Same as Arbuz -- selectors and API endpoints.
   - Recommendation: Same live inspection approach.

3. **playwright-stealth 2.x breaking changes**
   - What we know: Version 2.0.2 released Feb 2026. The API function `stealth_async(page)` appears unchanged. Package docs say "breaking changes" but specifics are not documented in available sources.
   - What is unclear: Whether any configuration options or behavior changed.
   - Recommendation: Use 2.0.2 (latest stable). Test that `stealth_async(page)` works with Playwright 1.50. LOW risk since the core API pattern appears stable.

4. **APScheduler jobstore vs reconstruct-on-startup**
   - What we know: SQLAlchemyJobStore persists jobs but uses sync DB. Architecture research suggests reconstructing fixed jobs (daily scrape) from code on startup may be simpler.
   - What is unclear: Whether to persist or reconstruct.
   - Recommendation: For Phase 1, reconstruct the daily scrape job from code on startup (it is a fixed schedule). Reserve SQLAlchemyJobStore for Phase 3 when per-user notification times need persistence. This avoids the sync URL complexity in Phase 1.

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` -- Validated technology versions, installation commands, compatibility notes
- `.planning/research/ARCHITECTURE.md` -- Component boundaries, project structure, build order
- `.planning/research/PITFALLS.md` -- 7 critical pitfalls with prevention strategies
- `task.md` -- Full technical specification with DB schema, URL patterns, scraper pseudocode
- [Playwright Python Network docs](https://playwright.dev/python/docs/network) -- API interception patterns
- [APScheduler 3.11 User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) -- AsyncIOScheduler, jobstores

### Secondary (MEDIUM confidence)
- [playwright-stealth 2.0.2 on PyPI](https://pypi.org/project/playwright-stealth/) -- Latest version confirmed
- [aiogram i18n docs](https://docs.aiogram.dev/en/latest/utils/i18n.html) -- Built-in middleware options (Cloudflare blocked full read)
- [APScheduler SQLAlchemyJobStore docs](https://apscheduler.readthedocs.io/en/3.x/modules/jobstores/sqlalchemy.html) -- Sync-only limitation confirmed

### Tertiary (LOW confidence)
- playwright-stealth 2.x breaking changes -- specific changes not documented in available sources; needs validation during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified by prior STACK research, playwright-stealth version updated
- Architecture: HIGH -- patterns well-established in prior ARCHITECTURE research, aligned with task.md spec
- Pitfalls: HIGH -- 7 pitfalls documented with multiple sources in PITFALLS research
- Discretion items: MEDIUM -- i18n and Docker image recommendations are well-founded; selector approach is inherently uncertain

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stack is stable; Playwright version pins prevent drift)
