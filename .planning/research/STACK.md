# Technology Stack

**Project:** Grocery Price Tracker Bot (price-spy)
**Researched:** 2026-03-30
**Overall Confidence:** HIGH -- Stack is pre-validated in PROJECT.md; research confirms versions and fills gaps.

## Recommended Stack

### Python Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12 | Runtime | Best balance of performance, library compatibility, and Railway support. 3.13 is available but some C-extension libraries (matplotlib, selectolax) have better wheel coverage on 3.12. | HIGH |

### Telegram Bot Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| aiogram | ~=3.26 | Telegram Bot API | Async-native, excellent middleware system, inline keyboard support, actively maintained (3.26.0 released 2026-03-02 with Bot API 9.4). Superior to python-telegram-bot for async-first projects. | HIGH |
| aiohttp | (transitive) | HTTP server for aiogram | Installed as aiogram dependency. No need to pin separately. | HIGH |

### Web Scraping

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| playwright | ~=1.50 | Browser automation for Arbuz.kz, Magnum.kz | Both sites block direct HTTP (403/SPA). Playwright 1.50+ is stable. Pin to ~=1.50, not latest, because Railway Docker image must match exactly. Latest PyPI is 1.58.0 but use the version matching your Docker base image. | HIGH |
| playwright-stealth | ~=1.0.6 | Anti-detection evasion | Patches navigator.webdriver and HeadlessChrome UA. Simple, sufficient for Arbuz/Magnum (not Cloudflare-grade). If Arbuz/Magnum upgrade detection later, switch to patchright. | MEDIUM |
| httpx | ~=0.28 | Async HTTP client for Kaspi.kz | Kaspi.kz is SSR, responds to direct HTTP. httpx is async-native, supports HTTP/2, cleaner API than aiohttp for scraping. 0.28.1 is latest stable. | HIGH |
| selectolax | ~=0.4.7 | Fast HTML parsing for Kaspi responses | 20x faster than BeautifulSoup, CSS selector support. Use the **Lexbor** backend (default since 0.4.x) -- Modest is deprecated. | HIGH |

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PostgreSQL | 16 | Primary database | Railway managed Postgres. Multi-user, JSONB for flexible product metadata, good time-series query support. Railway provides PG 16 by default. | HIGH |
| SQLAlchemy | ~=2.0.48 | ORM + async engine | Mature async support via `create_async_engine`. Mapped classes with type annotations. 2.0.48 released 2026-03-02. Do NOT use 2.1 beta in production. | HIGH |
| asyncpg | ~=0.31.0 | Async PostgreSQL driver | 5x faster than psycopg3 for asyncio. 0.31.0 released 2025-11-24. Compatible with SQLAlchemy 2.0.x. | HIGH |
| alembic | ~=1.18 | Database migrations | Official SQLAlchemy migration tool. 1.18.4 released 2026-02-10. Supports async via `run_async`. Essential for schema evolution. | HIGH |

### Scheduling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| APScheduler | ~=3.11 | Cron-style job scheduling | Daily scraping at 07:00 Asia/Almaty, per-user notification times. Use `AsyncIOScheduler` with `asyncpg` jobstore. Version 3.11.2 is latest stable. Do NOT use 4.x (still alpha, unstable API). | HIGH |

### Configuration and Validation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pydantic | ~=2.12 | Data validation, models | Type-safe scraping results, API models. 2.12.5 is latest stable. Do NOT use 2.13 beta. | HIGH |
| pydantic-settings | ~=2.13 | Environment config | Reads from .env and Railway env vars. Typed settings with validation. 2.13.1 released 2026-02-19. | HIGH |

### Charting and Export

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| matplotlib | ~=3.10 | Price charts (PNG) | Basket total over time, per-item trends, comparative charts. Generates PNG buffers sent via Telegram. 3.10.8 is latest. Heavier than alternatives but most capable for customization. | HIGH |
| csv (stdlib) | -- | CSV export | Built-in. No external library needed for simple price history export. | HIGH |

### Infrastructure and DevOps

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Docker | -- | Container for Railway | Required for Playwright (Chromium needs system deps). Use `mcr.microsoft.com/playwright/python:v1.50.0-noble` as base image. | HIGH |
| Railway | Starter plan | Hosting | ~$5-10/month. Managed PostgreSQL included. Supports Docker deployments with custom Dockerfiles. | HIGH |

### Development Tools

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| uv | latest | Package manager | 10-100x faster than pip. Lockfile support. Replaces pip + pip-tools. | HIGH |
| ruff | latest | Linter + formatter | Replaces flake8 + black + isort. Single tool, extremely fast. | HIGH |
| pytest | ~=8.x | Testing | With pytest-asyncio for async test support. | HIGH |
| pytest-asyncio | ~=0.24 | Async test fixtures | Required for testing async handlers, scrapers, and DB operations. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Bot framework | aiogram 3 | python-telegram-bot | PTB's async support is bolted on (v20+). aiogram is async-native with better middleware/router architecture. |
| Bot framework | aiogram 3 | Telethon | Telethon is for userbot/MTProto. Overkill for Bot API usage. |
| HTTP client | httpx | aiohttp (direct) | aiohttp is already a transitive dep but httpx has cleaner API for scraping (auto-redirect, HTTP/2). |
| HTML parser | selectolax | BeautifulSoup4 | selectolax is 20x faster. For scraping structured product pages, CSS selectors are sufficient. |
| HTML parser | selectolax | lxml | lxml is fast but more complex to install (C deps). selectolax has easier API for this use case. |
| Stealth | playwright-stealth | patchright | patchright is more capable against advanced anti-bot but is a Playwright fork (version lag risk). playwright-stealth is sufficient for Arbuz/Magnum. Upgrade path: swap to patchright if detection occurs. |
| Stealth | playwright-stealth | undetected-playwright | Less maintained than patchright. If playwright-stealth fails, skip to patchright. |
| ORM | SQLAlchemy 2 | Tortoise ORM | SQLAlchemy has vastly larger ecosystem, better async maturity, Alembic for migrations. |
| ORM | SQLAlchemy 2 | raw asyncpg | No migration support, manual SQL. Fine for read-heavy microservices, poor for schema evolution. |
| Scheduler | APScheduler 3.11 | APScheduler 4.x | 4.x is alpha since 2023, API unstable, no production recommendation. |
| Scheduler | APScheduler 3.11 | Celery + Redis | Massive overkill for a single-process bot. Adds Redis dependency. |
| Scheduler | APScheduler 3.11 | aiocron | Less feature-rich, no persistent jobstore, no per-user scheduling. |
| Charts | matplotlib | plotly | Plotly generates interactive HTML, not static PNGs. Telegram needs images. |
| Charts | matplotlib | Pillow (manual) | Reinventing charting is wasteful when matplotlib exists. |
| Package mgr | uv | pip + pip-tools | uv is faster, has native lockfile support, and is the modern standard. |
| Package mgr | uv | poetry | poetry is slower than uv and has resolver issues with complex dependency trees. |

## Key Version Pins and Compatibility Notes

### Critical: Playwright + Docker Version Match
The Playwright Python package version **must exactly match** the Docker base image version. If you use `mcr.microsoft.com/playwright/python:v1.50.0-noble`, pin `playwright==1.50.0` in requirements. Mismatches cause "browser executable not found" errors on Railway.

### Critical: asyncpg + SQLAlchemy Compatibility
asyncpg 0.31.0 works with SQLAlchemy 2.0.48. Earlier SQLAlchemy versions had issues with asyncpg >=0.29.0. Keep both updated together.

### APScheduler AsyncIOScheduler Setup
Use `AsyncIOScheduler` (not `BackgroundScheduler`). For persistence, use the PostgreSQL jobstore via SQLAlchemy:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url=DATABASE_URL_SYNC)  # Note: sync URL for jobstore
}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="Asia/Almaty")
```

### Playwright on Railway: Docker Requirements
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# Railway sets PORT env var
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Browsers already installed in base image
CMD ["python", "-m", "bot"]
```

**Important flags for headless Chromium on Railway:**
```python
browser = await playwright.chromium.launch(
    headless=True,
    args=[
        "--no-sandbox",           # Required in Docker
        "--disable-gpu",          # No GPU on Railway
        "--disable-dev-shm-usage", # Prevent /dev/shm OOM
    ]
)
```

## Installation

```bash
# Initialize project with uv
uv init price-spy
cd price-spy

# Core dependencies
uv add aiogram~=3.26 \
    playwright~=1.50 \
    playwright-stealth~=1.0.6 \
    httpx~=0.28 \
    selectolax~=0.4.7 \
    sqlalchemy[asyncio]~=2.0.48 \
    asyncpg~=0.31.0 \
    alembic~=1.18 \
    apscheduler~=3.11 \
    pydantic~=2.12 \
    pydantic-settings~=2.13 \
    matplotlib~=3.10

# Dev dependencies
uv add --dev ruff pytest pytest-asyncio

# Install Playwright browsers (dev machine)
playwright install chromium
```

## Python Version Constraint

```toml
# pyproject.toml
[project]
requires-python = ">=3.12,<3.14"
```

## Environment Variables (Railway)

```bash
# Required
BOT_TOKEN=           # Telegram bot token from @BotFather
DATABASE_URL=        # Railway provides this automatically (postgresql+asyncpg://...)
RAILWAY_ENVIRONMENT= # Set by Railway

# Optional
LOG_LEVEL=INFO
SCRAPE_HOUR=7        # 07:00 Asia/Almaty
MAX_BASKETS=10
MAX_ITEMS_PER_BASKET=50
PRICE_HISTORY_DAYS=90
```

## Sources

- [aiogram 3.26.0 on PyPI](https://pypi.org/project/aiogram/) -- confirmed 2026-03-02 release
- [aiogram documentation](https://docs.aiogram.dev/)
- [Playwright Python on PyPI](https://pypi.org/project/playwright/) -- 1.58.0 latest, pin to Docker match
- [Playwright Docker docs](https://playwright.dev/python/docs/docker)
- [playwright-stealth on PyPI](https://pypi.org/project/playwright-stealth/)
- [patchright on GitHub](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) -- upgrade path if stealth fails
- [httpx on PyPI](https://pypi.org/project/httpx/) -- 0.28.1 latest
- [selectolax on PyPI](https://pypi.org/project/selectolax/) -- 0.4.7 latest, use Lexbor backend
- [SQLAlchemy 2.0 async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLAlchemy on PyPI](https://pypi.org/project/SQLAlchemy/) -- 2.0.48 latest stable
- [asyncpg on PyPI](https://pypi.org/project/asyncpg/) -- 0.31.0 latest
- [Alembic on PyPI](https://pypi.org/project/alembic/) -- 1.18.4 latest
- [APScheduler on PyPI](https://pypi.org/project/APScheduler/) -- 3.11.2 stable, 4.x is alpha
- [matplotlib on PyPI](https://pypi.org/project/matplotlib/) -- 3.10.8 latest
- [pydantic on PyPI](https://pypi.org/project/pydantic/) -- 2.12.5 stable
- [pydantic-settings on PyPI](https://pypi.org/project/pydantic-settings/) -- 2.13.1 latest
- [Railway Playwright example](https://github.com/brody192/playwright-example-python)
- [Railway Help: Playwright in Docker](https://station.railway.com/questions/worker-timeouts-and-playwright-browser-e-d6499ade)
