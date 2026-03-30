# Roadmap: Grocery Price Tracker Bot (price-spy)

## Overview

This roadmap delivers a Telegram bot that tracks grocery prices across Arbuz.kz and Magnum in Almaty. The build follows the natural dependency chain: infrastructure and scraping engines first (the riskiest components), then basket/product management that depends on working scrapers, then scheduled daily reports that depend on baskets with products, and finally analytics/charts/exports that depend on accumulated price history. Four phases, coarse granularity, 67 requirements.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Infrastructure and Scraping Engines** - Deployed bot skeleton on Railway with working Playwright/httpx scrapers, user registration, and bilingual support
- [ ] **Phase 2: Basket and Product Management** - Users can create baskets, add products by URL, and see scraped prices
- [ ] **Phase 3: Scheduling and Daily Reports** - Automated daily scraping and personalized price reports delivered to users
- [ ] **Phase 4: Analytics, Charts, and Export** - Cross-store comparison, price charts, drop alerts, CSV export, and manual scrape

## Phase Details

### Phase 1: Infrastructure and Scraping Engines
**Goal**: A deployed, running Telegram bot on Railway with PostgreSQL, Playwright, and all three scraper engines producing validated price data
**Depends on**: Nothing (first phase)
**Requirements**: USER-01, USER-02, USER-03, USER-04, SCRP-01, SCRP-02, SCRP-03, SCRP-04, SCRP-05, SCRP-06, SCRP-07, SCRP-08, SCRP-09, SCRP-10, INFR-01, INFR-02, INFR-03, INFR-04, INFR-05, INFR-06, INFR-07
**Success Criteria** (what must be TRUE):
  1. User can /start the bot in Telegram, select language (Russian or English), and see a welcome message in their chosen language
  2. User can /help and see available commands in their selected language
  3. User can switch interface language at any time and all subsequent messages appear in the new language
  4. Bot is deployed on Railway with PostgreSQL and Playwright running in Docker without crashing
  5. Each scraper engine (Arbuz, Magnum, Kaspi) can fetch a product URL and return a validated price result (name, current price, original price, availability)
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Project init, config, DB schema, User model, Alembic migrations, User repository
- [x] 01-02-PLAN.md — Scraper engines (Arbuz, Magnum, Kaspi) with API interception, BrowserManager, stealth, orchestration service
- [ ] 01-03-PLAN.md — Bot skeleton with i18n, /start (language selection), /help, /language handlers, middlewares
- [ ] 01-04-PLAN.md — Application entry point, startup validation, Docker/Railway infrastructure

### Phase 2: Basket and Product Management
**Goal**: Users can create store-specific baskets, add products by URL with validation, and view their basket contents with live prices
**Depends on**: Phase 1
**Requirements**: BSKT-01, BSKT-02, BSKT-03, BSKT-04, BSKT-05, PROD-01, PROD-02, PROD-03, PROD-04, PROD-05, PROD-06, PROD-07, PROD-08, PROD-09, HIST-01, HIST-02, HIST-03, TXUX-01, TXUX-02
**Success Criteria** (what must be TRUE):
  1. User can create a basket with a name and store source (arbuz or magnum), view all baskets, switch active basket, and delete a basket
  2. User can add products by pasting URLs (with quantity), and the bot validates URL format and source-basket match, rejecting invalid input with clear errors
  3. User can view basket contents showing product names, quantities, and latest scraped prices via inline keyboard navigation
  4. Price history is stored for every scrape with current price, original price, availability, and records older than 90 days are cleaned up
  5. Limits are enforced: max 10 baskets per user, max 50 items per basket
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Scheduling and Daily Reports
**Goal**: Users receive automated daily price reports at their preferred time, with price changes highlighted and out-of-stock items flagged
**Depends on**: Phase 2
**Requirements**: REPT-01, REPT-02, REPT-03, REPT-04, REPT-05, REPT-06, REPT-07, REPT-08, MSCR-01, MSCR-02, MSCR-03
**Success Criteria** (what must be TRUE):
  1. Bot automatically scrapes all active baskets daily at 07:00 Asia/Almaty without manual intervention
  2. User receives a daily report at their configured time showing per-item prices, basket total, and change from previous day
  3. Daily report highlights items that changed price (was/became with percentage) and flags out-of-stock items
  4. User can configure their notification time via /notify command (default 09:00 Asia/Almaty)
  5. User can trigger a manual scrape via /scrape with rate limiting (1/hour) and progress feedback
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Analytics, Charts, and Export
**Goal**: Users can compare stores, visualize price trends, receive price drop alerts, and export their data
**Depends on**: Phase 3
**Requirements**: ANLT-01, ANLT-02, ANLT-03, ANLT-04, ANLT-05, CHRT-01, CHRT-02, CHRT-03, CHRT-04, CHRT-05, ALRT-01, ALRT-02, EXPT-01, EXPT-02, EXPT-03, TXUX-03
**Success Criteria** (what must be TRUE):
  1. User can view price changes over N days grouped by increased, decreased, unchanged, and unavailable
  2. User can compare Arbuz vs Magnum baskets showing per-item differences and total cost comparison with percentage
  3. User can view price trend charts (basket total and individual item) as Telegram photos with discount and out-of-stock markers
  4. User receives automatic alerts when a product price drops by more than 10%, with old/new price and percentage
  5. User can export basket price history as a UTF-8 CSV (with BOM for Excel/Cyrillic) containing all required fields
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure and Scraping Engines | 0/4 | Planned | - |
| 2. Basket and Product Management | 0/3 | Not started | - |
| 3. Scheduling and Daily Reports | 0/2 | Not started | - |
| 4. Analytics, Charts, and Export | 0/3 | Not started | - |
