# Grocery Price Tracker Bot (price-spy)

## What This Is

A Telegram bot for monitoring grocery prices across Arbuz.kz and Magnum (magnum.kz + kaspi.kz/shop) in Almaty. Users create baskets of products, the bot scrapes prices daily, and delivers analytics — daily reports, price change tracking, Arbuz vs Magnum comparison, charts, and CSV exports. Multi-user from day 1, bilingual (Russian + English).

## Core Value

Users get automated daily visibility into what their grocery basket costs across stores, so they can spot price drops, avoid overpaying, and compare where to shop.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-user Telegram bot with registration and personal baskets
- [ ] Basket management: create, delete, switch active basket, set source (arbuz/magnum)
- [ ] Add products by URL (arbuz.kz, magnum.kz, kaspi.kz/shop) with quantity
- [ ] URL validation: correct format, correct source for basket type
- [ ] Scraping: Playwright for Arbuz.kz and Magnum.kz (SPA/403), httpx+selectolax for Kaspi.kz (SSR)
- [ ] Daily automated scraping at 07:00 Asia/Almaty
- [ ] Price history storage with original/discount prices and availability
- [ ] Daily price report sent at user's preferred time
- [ ] Price change tracking (was/became over N days)
- [ ] Arbuz vs Magnum comparison (total basket cost + per-item where overlap exists)
- [ ] Inline button navigation for baskets and actions
- [ ] Price charts via matplotlib (basket total over time, individual item, comparative)
- [ ] CSV export of price history
- [ ] Configurable notification time per user
- [ ] Manual scrape trigger with rate limiting (1/hour)
- [ ] Bilingual interface (Russian + English)
- [ ] Scraper optimizations: API interception, browser reuse, parallelism, retry, stealth
- [ ] Price drop alerts (>10% decrease notification)
- [ ] Product name caching after first scrape
- [ ] Deploy on Railway with PostgreSQL

### Out of Scope

- Product search by name (without URL) — complexity of cross-site search, defer to future
- Mobile app — Telegram is the interface
- Real-time price monitoring (more than once daily) — unnecessary resource cost
- Stores beyond Arbuz and Magnum — can add later but not in this project

## Context

- **Target market:** Almaty, Kazakhstan — grocery shoppers who use Arbuz.kz and Magnum
- **Scraping validated:** Arbuz.kz and Magnum.kz confirmed scrapeable via Playwright; Kaspi.kz works with direct HTTP
- **Scale expectation:** Small (1-10 users) in first months, but architecture supports growth
- **Store model:** Arbuz baskets accept only arbuz.kz URLs; Magnum baskets accept both magnum.kz and kaspi.kz/shop URLs
- **Comparison model:** Mix of overlapping products (per-item comparison) and store-exclusive items (total cost comparison)
- **Currency:** Kazakhstani tenge (₸)
- **Timezone:** Asia/Almaty

## Constraints

- **Tech stack**: Python only — aiogram 3, Playwright, httpx, selectolax, SQLAlchemy 2, asyncpg, APScheduler, matplotlib, Pydantic Settings
- **Hosting**: Railway (Starter plan, ~$5-10/month)
- **Database**: PostgreSQL (Railway managed)
- **Scraper resources**: Playwright headless Chromium without GPU/sandbox in Railway container
- **Limits**: Max 10 baskets/user, 50 items/basket, 90-day price history retention
- **Bot detection**: playwright-stealth plugin + UA rotation required for Arbuz/Magnum

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Playwright for Arbuz + Magnum, httpx for Kaspi | Arbuz returns 403 on direct HTTP, Magnum is SPA; Kaspi is SSR with full HTML | — Pending |
| PostgreSQL over SQLite | Multi-user, Railway provides managed Postgres, APScheduler jobstore support | — Pending |
| aiogram 3 over python-telegram-bot | Async-native, better middleware system, inline keyboard support | — Pending |
| Single process (bot + scheduler) | Simpler deployment on Railway, sufficient for small scale | — Pending |
| Multi-user from day 1 | Avoids costly refactor later, architecture already supports it | — Pending |
| Bilingual (RU + EN) | Broader accessibility for Almaty's diverse population | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-30 after initialization*
