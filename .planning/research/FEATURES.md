# Feature Research

**Domain:** Grocery price tracking / comparison via Telegram bot (Almaty, Kazakhstan)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Add products by URL | Every price tracker (Pricegram, PriceTrackerBot, SuperPriceWatchdog) uses URL-based tracking as the primary input method. Users paste a link, bot tracks it. | MEDIUM | Must validate URL format and match to correct store. Arbuz URLs vs Magnum/Kaspi URLs. |
| View tracked items with current prices | All trackers show a list of what you're tracking and their latest prices. Without this, users have zero visibility. | LOW | `/list` or inline button to show basket contents with prices. |
| Price change notifications | Core value prop of every price tracker. Pricegram sends alerts on any price change; SuperPriceWatchdog sends daily alerts for deals. Users expect to be told when prices move. | MEDIUM | Both push (proactive alerts on significant drops) and pull (daily report) patterns exist. Daily report is the baseline. |
| Daily price report | SuperPriceWatchdog sends daily alerts. Grocery Dealz tracks daily. Users expect a recurring summary without having to ask. This is the core loop that keeps users engaged. | MEDIUM | Scheduled message with basket total, per-item prices, and notable changes. Configurable delivery time is expected. |
| Price history storage | SuperPriceWatchdog stores 90 days. Price Book tracks purchase history. Grocery Prices History app is literally named for this. Without history, there is no trend to show. | LOW | 90-day retention matches SuperPriceWatchdog and is sufficient for grocery cycles. Database schema concern, not UX-heavy. |
| Remove/edit tracked items | Every tracker (Pricegram `/list` with delete, PriceTrackerBot) lets users manage their tracking list. Cannot add without ability to remove. | LOW | Inline buttons for item management within baskets. |
| Basic basket management | Basket (the app) organizes items into shopping lists. Users need at minimum one named basket to group related products. Create, view, delete. | MEDIUM | Multiple baskets per user with store-type binding (arbuz vs magnum) is the project's design. |
| Original vs discount price display | Grocery shoppers care deeply about whether a price is promotional. Arbuz.kz and Magnum show both. Hiding this loses trust. | LOW | Scrape both original and discounted price. Display clearly which is which. |
| Product availability status | Pricegram tracks availability changes. Out-of-stock items in a basket affect the total cost calculation and user decisions. | LOW | Boolean available/unavailable from scrape. Flag in reports. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cross-store basket comparison (Arbuz vs Magnum) | No existing Telegram bot does side-by-side store comparison for KZ grocery stores. Basket (US app) does this for US stores. Bringing this to Almaty via Telegram is the core differentiator. | HIGH | Requires matching overlapping products across stores. Total basket cost comparison + per-item where overlap exists. Complex matching logic. |
| Price trend charts (matplotlib) | Visual price history is rare in Telegram bots. Mobile apps like Grocery Prices History and Stretch offer charts, but Telegram bots almost never do. Sends chart as image in chat. | MEDIUM | Three chart types: basket total over time, individual item history, comparative (store A vs store B). matplotlib generates PNG sent as Telegram photo. |
| Price drop alerts (threshold-based) | SuperPriceWatchdog uses statistical thresholds (1 std dev below mean). Most basic trackers alert on any change. Threshold-based alerts (>10% drop) reduce noise and surface real deals. | LOW | Simple percentage calculation against previous price. Low implementation cost, high perceived value. |
| CSV export of price history | Enterprise grocery tools export CSV/JSON. Consumer apps rarely do. Power users who want to analyze their grocery spend in spreadsheets will love this. Uncommon in bot space. | LOW | Generate CSV from price_history table, send as Telegram document. Straightforward. |
| Bilingual interface (Russian + English) | No existing grocery price bot targets the KZ market. Russian is primary language for Almaty shoppers; English broadens reach. Most Telegram bots are English-only. | MEDIUM | i18n from day 1 means every user-facing string needs two versions. Moderate ongoing cost but architectural decision that must be made early. |
| Manual scrape trigger with rate limiting | Existing bots use fixed polling intervals (Pricegram: 2hr). On-demand "check now" gives users agency. Rate limiting (1/hour) prevents abuse. | LOW | Simple command with cooldown tracking per user. |
| Configurable notification time | SuperPriceWatchdog has fixed schedule. Letting users pick their report time (morning commute, evening planning) personalizes the experience. | LOW | Store per-user timezone offset or preferred hour. APScheduler job per user. |
| Quantity tracking per item | Basket apps track quantities for shopping lists. Price trackers typically track single items. Combining both (3x milk, 2x bread) gives accurate basket total cost. | LOW | Multiply unit price by quantity for basket totals. Simple but important for accurate cost comparison. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Product search by name (without URL) | Users want to search "milk" and find it across stores | Cross-site search is a full product matching/NLP problem. Product names differ across stores. Scraping search results is fragile and expensive. Scope explosion. | Require URL input. Users browse store websites naturally and paste URLs. Clear UX guidance in onboarding. |
| Real-time price monitoring (multiple times daily) | "I want to know the instant a price changes" | Unnecessary resource cost for groceries (prices change at most daily). Scraping more than once/day risks rate limiting and bot detection. Railway resource budget is limited. | Daily scraping at 07:00 + manual trigger (1/hour max) covers all real use cases. |
| Barcode/QR scanning | Mobile price comparison apps offer this (Basket, Yuka) | Telegram bot cannot access phone camera in a useful way. Would require a separate companion app. Completely different architecture. | URL-based input is the natural Telegram interaction pattern. |
| Price prediction / AI recommendations | "Tell me when to buy" | Grocery prices are influenced by supply chains, seasons, promotions -- not predictable from 90 days of scrape data for a single city. Overpromise risk. Adds ML complexity for dubious value. | Show price history trends and let users draw their own conclusions. Statistical alerts (like SuperPriceWatchdog's std dev approach) are simpler and honest. |
| Stores beyond Arbuz and Magnum | "Add Glovo, Wolt, Small.kz" | Each store requires a new scraper with different anti-bot measures, DOM structures, and URL patterns. Maintenance multiplier. Two stores is the validated scope. | Architect scraper as pluggable modules so stores CAN be added later, but do not commit to it now. |
| Shared/collaborative baskets | "My family shares a grocery list" | Multi-user editing of shared state in Telegram is complex (conflict resolution, permissions, notification routing). Telegram group bots have different interaction patterns. | Personal baskets only. Users can share CSV exports or screenshot reports. |
| Recipe-based basket building | "Import a recipe and track ingredient prices" | Recipe parsing is its own NLP domain. Ingredient-to-product matching across stores is unsolved. Massive scope. | Out of scope entirely. Users add individual products they care about. |
| Push notifications for restocks | "Tell me when out-of-stock items come back" | Requires checking availability of items users may have forgotten about. Notification fatigue. Edge case for grocery (vs electronics). | Show availability status in daily report. Users notice when items return. |
| Voice input for adding products | Mobile apps offer voice search | Telegram voice messages would need speech-to-text + intent parsing. Over-engineered for URL input. | Text-based URL input. Simple, reliable, no ambiguity. |

## Feature Dependencies

```
[User Registration]
    +-- [Basket Management (create/delete/switch)]
    |       +-- [Add Products by URL]
    |       |       +-- [URL Validation per store type]
    |       |       +-- [Product Scraping (first scrape)]
    |       |               +-- [Product Name Caching]
    |       |               +-- [Price History Storage]
    |       |                       +-- [Daily Price Report]
    |       |                       +-- [Price Change Tracking]
    |       |                       +-- [Price Drop Alerts]
    |       |                       +-- [Price Charts (matplotlib)]
    |       |                       +-- [CSV Export]
    |       +-- [Cross-Store Comparison]
    |               requires: at least one arbuz basket + one magnum basket with overlapping products
    +-- [Notification Time Config]
    +-- [Language Preference (RU/EN)]

[Daily Automated Scraping]
    +-- requires: [Scraper Infrastructure (Playwright + httpx)]
    +-- feeds: [Price History Storage]
    +-- triggers: [Daily Price Report]
    +-- triggers: [Price Drop Alerts]

[Manual Scrape Trigger]
    +-- requires: [Scraper Infrastructure]
    +-- requires: [Rate Limiting]
```

### Dependency Notes

- **Basket Management requires User Registration:** Each user owns their baskets; user identity must exist first.
- **Add Products requires Basket:** Products belong to baskets, not floating. A basket must exist before adding products.
- **All analytics (reports, charts, CSV, alerts) require Price History:** Cannot generate insights without stored historical data. At least 2 data points needed for trends.
- **Cross-Store Comparison requires two basket types:** User needs both an Arbuz basket and a Magnum basket with some overlapping products to get per-item comparison. Total cost comparison works with any two baskets.
- **Daily Report requires Daily Scraping:** The report is generated from fresh scrape data. Scraping pipeline must run before report generation.
- **Bilingual support is cross-cutting:** Affects every user-facing string. Must be architected in from the start, not bolted on.
- **Price Charts enhance Price History:** Charts are a visualization layer on top of stored data. No new data collection needed, just rendering.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what is needed to validate the concept.

- [ ] User registration and language selection (RU/EN) -- identity is prerequisite for everything
- [ ] Basket CRUD (create with store type, delete, switch active, list) -- organizational foundation
- [ ] Add products by URL with validation -- core input mechanism
- [ ] Scraper infrastructure (Playwright for Arbuz/Magnum, httpx for Kaspi) -- data acquisition
- [ ] Price history storage (original + discount + availability) -- data foundation
- [ ] Daily automated scraping at 07:00 -- recurring data freshness
- [ ] Daily price report at configurable time -- core value delivery loop
- [ ] Price change tracking (was/became) -- users need to see what moved
- [ ] Inline button navigation -- Telegram UX standard for bot interaction

### Add After Validation (v1.x)

Features to add once core is working and at least a few users are active.

- [ ] Price drop alerts (>10% threshold) -- trigger: users asking "did anything get cheaper?"
- [ ] Cross-store comparison (Arbuz vs Magnum totals + per-item) -- trigger: users with both basket types
- [ ] Price charts via matplotlib -- trigger: users wanting visual trends
- [ ] CSV export -- trigger: power users asking for raw data
- [ ] Manual scrape trigger with rate limiting -- trigger: users wanting fresher data

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Scraper optimizations (API interception, browser reuse, parallelism, stealth enhancements) -- scale-driven; optimize when scraping load matters
- [ ] Product name caching after first scrape -- performance optimization, defer until item count is meaningful
- [ ] Additional stores -- only after current two are stable and users request specific stores
- [ ] Shared basket export/sharing features -- only if collaborative use cases emerge

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| User registration + language | HIGH | LOW | P1 |
| Basket CRUD | HIGH | MEDIUM | P1 |
| Add products by URL + validation | HIGH | MEDIUM | P1 |
| Scraper infrastructure | HIGH | HIGH | P1 |
| Price history storage | HIGH | LOW | P1 |
| Daily automated scraping | HIGH | MEDIUM | P1 |
| Daily price report | HIGH | MEDIUM | P1 |
| Price change tracking | HIGH | LOW | P1 |
| Inline button navigation | MEDIUM | MEDIUM | P1 |
| Bilingual interface (RU + EN) | MEDIUM | MEDIUM | P1 |
| Price drop alerts | HIGH | LOW | P2 |
| Cross-store comparison | HIGH | HIGH | P2 |
| Price charts (matplotlib) | MEDIUM | MEDIUM | P2 |
| CSV export | LOW | LOW | P2 |
| Manual scrape trigger | MEDIUM | LOW | P2 |
| Configurable notification time | MEDIUM | LOW | P2 |
| Scraper optimizations | LOW | HIGH | P3 |
| Product name caching | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch -- without these the bot has no value loop
- P2: Should have, add when possible -- these differentiate and delight
- P3: Nice to have, future consideration -- optimization and scale concerns

## Competitor Feature Analysis

| Feature | SuperPriceWatchdog (HK) | Pricegram (Amazon) | Basket App (US) | Grocery Dealz (US) | **price-spy (Ours)** |
|---------|------------------------|-------------------|----------------|--------------------|--------------------|
| Platform | Telegram | Telegram | Mobile app | Mobile app | Telegram |
| Add by URL | No (preset items) | Yes | No (search) | No (search) | Yes |
| Multiple baskets | No | No (flat list) | Yes | No | Yes (store-typed) |
| Cross-store comparison | No | No (single store) | Yes (multiple stores) | Yes | Yes (Arbuz vs Magnum) |
| Price history | 90 days | Unlimited | No | Yes | 90 days |
| Price charts | No | No | No | No | Yes (matplotlib) |
| Price drop alerts | Statistical (1 std dev) | Target price or any change | No | Yes | Threshold (>10%) |
| Daily report | Yes (daily alerts) | No (change-based) | No | No | Yes (configurable time) |
| CSV export | No | No | No | No | Yes |
| Bilingual | No (English) | Multi-currency | No | No | Yes (RU + EN) |
| Quantity tracking | No | No | Yes | No | Yes |
| Manual refresh | No | No | N/A | N/A | Yes (rate-limited) |

**Competitive position:** price-spy combines the best of Telegram bot simplicity (like Pricegram) with mobile app depth (like Basket). No existing Telegram bot offers basket-level grocery comparison. No existing tool targets the KZ market at all. The combination of cross-store comparison, visual charts, and bilingual Telegram delivery is unique.

## Sources

- [SuperPriceWatchdog](https://github.com/Jack-cky/SuperPriceWatchdog) -- Telegram grocery price bot for Hong Kong supermarkets
- [Pricegram](https://github.com/AleG94/Pricegram) -- Telegram Amazon price tracker with target price alerts
- [PriceTrackerBot](https://github.com/nuhmanpk/PriceTrackerBot) -- Telegram bot for Flipkart/Amazon price changes
- [Basket App](https://basketsavings.com/index.html) -- US mobile app for cross-store grocery price comparison
- [Grocery Dealz](https://www.grocerydive.com/news/new-grocery-app-launched-real-time-price-comparison-ecommerce-Grocery-Dealz/752296/) -- US real-time grocery price comparison app
- [Best Grocery Price Tracking Apps 2026](https://savingsgrove.com/blogs/guides/best-grocery-price-tracking-apps) -- Comparative review of 11 apps
- [Grocery Price Comparison App Guide](https://www.octalsoftware.com/blog/grocery-price-comparison-app) -- Feature landscape for price comparison apps
- [Price Book App](https://apps.apple.com/us/app/price-book-track-grocery-price/id1431720584) -- Personal grocery price history tracker

---
*Feature research for: Grocery price tracking Telegram bot (Almaty, KZ)*
*Researched: 2026-03-30*
