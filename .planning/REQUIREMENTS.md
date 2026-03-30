# Requirements: Grocery Price Tracker Bot (price-spy)

**Defined:** 2026-03-30
**Core Value:** Users get automated daily visibility into what their grocery basket costs across stores, so they can spot price drops, avoid overpaying, and compare where to shop.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### User Management

- [x] **USER-01**: User can register via /start command in Telegram
- [ ] **USER-02**: User can select interface language (Russian or English) at registration
- [ ] **USER-03**: User can switch language at any time via settings
- [ ] **USER-04**: User can view help with available commands via /help

### Basket Management

- [ ] **BSKT-01**: User can create a basket with a name and store source (arbuz or magnum)
- [ ] **BSKT-02**: User can view all their baskets with item counts
- [ ] **BSKT-03**: User can switch active basket
- [ ] **BSKT-04**: User can delete a basket
- [ ] **BSKT-05**: User is limited to 10 baskets maximum

### Product Input

- [ ] **PROD-01**: User can add products by pasting arbuz.kz URL (for arbuz baskets)
- [ ] **PROD-02**: User can add products by pasting magnum.kz or kaspi.kz/shop URL (for magnum baskets)
- [ ] **PROD-03**: User can specify quantity when adding a product (default: 1)
- [ ] **PROD-04**: User can add multiple products at once (one URL per line)
- [ ] **PROD-05**: Bot validates URL format and rejects invalid URLs with clear error message
- [ ] **PROD-06**: Bot validates URL source matches basket type (arbuz URLs only in arbuz baskets)
- [ ] **PROD-07**: User can remove a product from their basket
- [ ] **PROD-08**: User can view basket contents with product names, quantities, and latest prices
- [ ] **PROD-09**: User is limited to 50 items per basket

### Scraping

- [ ] **SCRP-01**: Bot scrapes Arbuz.kz product pages via Playwright (handles SPA/403)
- [ ] **SCRP-02**: Bot scrapes Magnum.kz product pages via Playwright (handles SPA)
- [ ] **SCRP-03**: Bot scrapes Kaspi.kz/shop product pages via httpx + selectolax (SSR fast-path)
- [ ] **SCRP-04**: Scraper extracts: current price, original price (if discounted), product name, availability status
- [ ] **SCRP-05**: Product name is cached after first scrape (no re-extraction needed)
- [ ] **SCRP-06**: Bot attempts API interception via Playwright network events to find stable JSON endpoints
- [ ] **SCRP-07**: Scraper uses playwright-stealth and UA rotation for anti-bot evasion
- [ ] **SCRP-08**: Scraper reuses browser instance across scrape cycle with fresh contexts per store
- [ ] **SCRP-09**: Scraper runs with parallelism (semaphore: max 3 Playwright, max 10 httpx)
- [ ] **SCRP-10**: Scraper retries failed requests (3 attempts with exponential backoff)

### Price History

- [ ] **HIST-01**: Every scrape result is stored in price_history with timestamp
- [ ] **HIST-02**: Price history includes current price, original price, and availability
- [ ] **HIST-03**: Price history records older than 90 days are automatically cleaned up (monthly)

### Daily Reports

- [ ] **REPT-01**: Bot scrapes all active baskets daily at 07:00 Asia/Almaty
- [ ] **REPT-02**: Bot sends daily price report to each user at their configured notification time
- [ ] **REPT-03**: Daily report shows per-item prices with quantity totals
- [ ] **REPT-04**: Daily report shows basket total and change from previous day
- [ ] **REPT-05**: Daily report highlights items that changed price (was/became with percentage)
- [ ] **REPT-06**: Daily report flags out-of-stock items
- [ ] **REPT-07**: User can configure notification time via /notify command
- [ ] **REPT-08**: Default notification time is 09:00 Asia/Almaty

### Price Analytics

- [ ] **ANLT-01**: User can view price changes over N days via /changes command
- [ ] **ANLT-02**: Changes report groups items by: price increased, price decreased, unchanged, unavailable
- [ ] **ANLT-03**: User can compare Arbuz vs Magnum basket totals via /compare
- [ ] **ANLT-04**: Comparison shows per-item price differences where same product exists in both stores
- [ ] **ANLT-05**: Comparison shows total cost difference with percentage

### Charts

- [ ] **CHRT-01**: User can view basket total price chart over time via /chart command
- [ ] **CHRT-02**: User can view individual product price chart via /chart_item command
- [ ] **CHRT-03**: Charts default to 30-day period, user can specify custom period
- [ ] **CHRT-04**: Charts mark discount prices (green dots) and out-of-stock periods (red X)
- [ ] **CHRT-05**: Charts are generated via matplotlib and sent as Telegram photos

### Alerts

- [ ] **ALRT-01**: Bot notifies user when a product price drops by more than 10%
- [ ] **ALRT-02**: Alert includes product name, old price, new price, and percentage drop

### Export

- [ ] **EXPT-01**: User can export basket price history as CSV via /export
- [ ] **EXPT-02**: CSV includes: date, basket name, source, product, quantity, unit price, total, availability
- [ ] **EXPT-03**: CSV is UTF-8 with BOM for Excel compatibility with Cyrillic text

### Manual Scraping

- [ ] **MSCR-01**: User can trigger manual scrape via /scrape command
- [ ] **MSCR-02**: Manual scrape is rate-limited to once per hour per user
- [ ] **MSCR-03**: Bot shows progress feedback during manual scrape

### Telegram UX

- [ ] **TXUX-01**: Bot provides inline keyboard navigation for baskets and actions
- [ ] **TXUX-02**: Basket list shows inline buttons for: list items, view prices, view charts, add item, edit, delete
- [ ] **TXUX-03**: All user-facing messages are bilingual (Russian and English based on user preference)

### Infrastructure

- [ ] **INFR-01**: Bot runs as single process (bot + scheduler) on Railway
- [x] **INFR-02**: PostgreSQL database on Railway for all persistent data
- [ ] **INFR-03**: Playwright runs headless Chromium without GPU/sandbox in Docker container
- [ ] **INFR-04**: Docker image handles Playwright system dependencies correctly (including /dev/shm)
- [ ] **INFR-05**: APScheduler uses PostgreSQL jobstore for persistent scheduled tasks
- [x] **INFR-06**: Database connection pool is sized to handle concurrent scraping + bot handlers
- [x] **INFR-07**: All times handled in Asia/Almaty timezone (Railway runs UTC)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extended Stores

- **STOR-01**: Support for additional Almaty stores (e.g., Small.kz, Glovo grocery)
- **STOR-02**: Pluggable scraper architecture for easy store additions

### Product Discovery

- **DISC-01**: Search products by name within a store
- **DISC-02**: Browse store categories to find products

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Product search by name (without URL) | Cross-site search is a full NLP/matching problem; URL input is the natural Telegram pattern |
| Real-time price monitoring (>1x daily) | Grocery prices change at most daily; wastes Railway resources and risks bot detection |
| Barcode/QR scanning | Telegram cannot access phone camera usefully; different architecture entirely |
| Price prediction / AI recommendations | Insufficient data from 90 days of single-city scraping; overpromise risk |
| Shared/collaborative baskets | Multi-user editing in Telegram is complex (conflicts, permissions); personal baskets only |
| Recipe-based basket building | Recipe parsing + ingredient matching is its own NLP domain; massive scope |
| Mobile app | Telegram is the interface; no native app needed |
| Voice input | Over-engineered for URL input; text-based is simple and reliable |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| USER-01 | Phase 1 | Complete |
| USER-02 | Phase 1 | Pending |
| USER-03 | Phase 1 | Pending |
| USER-04 | Phase 1 | Pending |
| SCRP-01 | Phase 1 | Pending |
| SCRP-02 | Phase 1 | Pending |
| SCRP-03 | Phase 1 | Pending |
| SCRP-04 | Phase 1 | Pending |
| SCRP-05 | Phase 1 | Pending |
| SCRP-06 | Phase 1 | Pending |
| SCRP-07 | Phase 1 | Pending |
| SCRP-08 | Phase 1 | Pending |
| SCRP-09 | Phase 1 | Pending |
| SCRP-10 | Phase 1 | Pending |
| INFR-01 | Phase 1 | Pending |
| INFR-02 | Phase 1 | Complete |
| INFR-03 | Phase 1 | Pending |
| INFR-04 | Phase 1 | Pending |
| INFR-05 | Phase 1 | Pending |
| INFR-06 | Phase 1 | Complete |
| INFR-07 | Phase 1 | Complete |
| BSKT-01 | Phase 2 | Pending |
| BSKT-02 | Phase 2 | Pending |
| BSKT-03 | Phase 2 | Pending |
| BSKT-04 | Phase 2 | Pending |
| BSKT-05 | Phase 2 | Pending |
| PROD-01 | Phase 2 | Pending |
| PROD-02 | Phase 2 | Pending |
| PROD-03 | Phase 2 | Pending |
| PROD-04 | Phase 2 | Pending |
| PROD-05 | Phase 2 | Pending |
| PROD-06 | Phase 2 | Pending |
| PROD-07 | Phase 2 | Pending |
| PROD-08 | Phase 2 | Pending |
| PROD-09 | Phase 2 | Pending |
| HIST-01 | Phase 2 | Pending |
| HIST-02 | Phase 2 | Pending |
| HIST-03 | Phase 2 | Pending |
| TXUX-01 | Phase 2 | Pending |
| TXUX-02 | Phase 2 | Pending |
| REPT-01 | Phase 3 | Pending |
| REPT-02 | Phase 3 | Pending |
| REPT-03 | Phase 3 | Pending |
| REPT-04 | Phase 3 | Pending |
| REPT-05 | Phase 3 | Pending |
| REPT-06 | Phase 3 | Pending |
| REPT-07 | Phase 3 | Pending |
| REPT-08 | Phase 3 | Pending |
| MSCR-01 | Phase 3 | Pending |
| MSCR-02 | Phase 3 | Pending |
| MSCR-03 | Phase 3 | Pending |
| ANLT-01 | Phase 4 | Pending |
| ANLT-02 | Phase 4 | Pending |
| ANLT-03 | Phase 4 | Pending |
| ANLT-04 | Phase 4 | Pending |
| ANLT-05 | Phase 4 | Pending |
| CHRT-01 | Phase 4 | Pending |
| CHRT-02 | Phase 4 | Pending |
| CHRT-03 | Phase 4 | Pending |
| CHRT-04 | Phase 4 | Pending |
| CHRT-05 | Phase 4 | Pending |
| ALRT-01 | Phase 4 | Pending |
| ALRT-02 | Phase 4 | Pending |
| EXPT-01 | Phase 4 | Pending |
| EXPT-02 | Phase 4 | Pending |
| EXPT-03 | Phase 4 | Pending |
| TXUX-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 67 total
- Mapped to phases: 67
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after roadmap creation*
