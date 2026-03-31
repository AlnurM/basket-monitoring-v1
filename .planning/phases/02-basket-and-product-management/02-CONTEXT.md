# Phase 2: Basket and Product Management - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Source:** Auto-mode (recommended defaults selected)

<domain>
## Phase Boundary

Users can create store-specific baskets (arbuz/magnum), add products by URL with validation, view basket contents with live scraped prices via inline keyboard navigation. Includes price history storage, 90-day cleanup, and enforced limits (10 baskets/user, 50 items/basket).

</domain>

<decisions>
## Implementation Decisions

### Inline Keyboard UX (TXUX-01, TXUX-02)
- **D-01:** Hierarchical inline button navigation: /baskets shows list of baskets with inline buttons → selecting a basket shows action buttons (List, Prices, Add, Delete) → each action shows relevant content with back navigation.
- **D-02:** Basket list format: emoji + name + store source + item count per basket. Example: "🛒 Недельная (Arbuz) — 12 товаров"
- **D-03:** Inline buttons follow the layout from task.md section 6.2: [📋 Список] [💰 Цены] [📈 Графики] / [➕ Добавить] [✏️ Ред.] [🗑 Удалить]

### URL Input Flow (PROD-01 through PROD-06)
- **D-04:** Users add products by sending freeform text messages containing URLs. Bot detects URLs in any message sent while a basket is active. Format: `<URL> [quantity]` per line, one or more lines per message.
- **D-05:** Bot auto-detects URL source (arbuz/magnum/kaspi) and validates against active basket type. Arbuz URLs only in arbuz baskets; magnum.kz AND kaspi.kz URLs accepted in magnum baskets.
- **D-06:** After adding products, bot immediately triggers a first scrape to populate name and initial price. User sees confirmation with scraped product name and price.

### Price Display (PROD-08)
- **D-07:** Basket contents show per-item: number, product name, quantity, unit price, line total. Format consistent with daily report from task.md section 7.1.
- **D-08:** Out-of-stock items flagged with 🔴 marker. Discount prices shown with original crossed out.
- **D-09:** Basket total displayed at bottom of item list.

### Validation Errors (PROD-05, PROD-06)
- **D-10:** Detailed validation errors consistent with D-07 (Phase 1 error approach). Specific reason for rejection: "URL is not a valid Arbuz product link", "Kaspi URLs can only be added to Magnum baskets", "Maximum 50 items per basket reached".
- **D-11:** All validation messages are bilingual (use i18n get_text from Phase 1).

### Price History (HIST-01 through HIST-03)
- **D-12:** Every scrape stores: basket_item_id, price, original_price, is_available, scraped_at. Schema matches task.md section 4.4.
- **D-13:** Cleanup job runs monthly (1st of month at 03:00 Asia/Almaty) deleting records older than 90 days. Uses APScheduler cron trigger.

### Limits
- **D-14:** Basket creation checks user's basket count against max_baskets_per_user (10). Item addition checks basket's item count against max_items_per_basket (50). Both from settings.

### Carrying Forward from Phase 1
- Dictionary-based i18n (get_text) — all new messages need RU + EN translations
- User model with telegram_id, language, timezone — baskets reference user.id
- ScraperService with concurrency control — used for first-scrape on item add
- DB session middleware provides AsyncSession to handlers
- ProductNameCache — first scrape populates cache, subsequent scrapes use it
- Inline keyboard pattern from start.py (InlineKeyboardBuilder)
- URL patterns and source detection from services/scraper.py

### Claude's Discretion
- Pagination approach for long basket item lists (if >10 items)
- Whether to use aiogram FSM for multi-step basket creation flow or simple callback_data routing
- Exact callback_data encoding format for inline buttons

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specification
- `task.md` — Sections 4 (DB schema for baskets, basket_items, price_history), 6.1-6.4 (bot commands, inline buttons, URL format, validation patterns)

### Phase 1 Code (reusable patterns)
- `src/price_spy/bot/handlers/start.py` — Handler pattern with Router, InlineKeyboardBuilder, user/lang injection
- `src/price_spy/bot/middlewares/db.py` — DB session middleware pattern
- `src/price_spy/bot/middlewares/i18n.py` — i18n middleware pattern
- `src/price_spy/db/models/user.py` — SQLAlchemy model pattern with mapped_column
- `src/price_spy/db/repositories/user.py` — Repository CRUD pattern
- `src/price_spy/services/scraper.py` — ScraperService, URL_PATTERNS, detect_source, extract_product_id
- `src/price_spy/i18n/core.py` — get_text function, translation dict structure
- `src/price_spy/i18n/ru.py` — Russian translations (add new keys here)
- `src/price_spy/i18n/en.py` — English translations (add new keys here)

### Research
- `.planning/research/FEATURES.md` — Feature dependencies and MVP definition
- `.planning/research/ARCHITECTURE.md` — Component boundaries and data flow

### Project Context
- `.planning/PROJECT.md` — Project vision, constraints
- `.planning/REQUIREMENTS.md` — Phase 2 requirements: BSKT-01..05, PROD-01..09, HIST-01..03, TXUX-01..02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `InlineKeyboardBuilder` pattern from `start.py` — extend for basket navigation
- `UserRepository` CRUD pattern — replicate for BasketRepository, BasketItemRepository
- `ScraperService.scrape_urls()` — call on item addition for first price fetch
- `URL_PATTERNS` and `detect_source()` in `services/scraper.py` — reuse for URL validation
- `ProductCacheRepository` — already caches product names from scraping
- `Base` declarative base for new models
- Alembic migration chain (001 → 002) — extend with 003 for baskets/items/price_history

### Established Patterns
- Router-based handler organization (one Router per handler module)
- Dependency injection via middleware (session, user, lang available in handler kwargs)
- Repository pattern for DB operations (session-scoped, async)
- Dictionary-based i18n with get_text(key, lang, **kwargs)

### Integration Points
- New handlers register on Dispatcher via `dp.include_router(router)` in `bot/create.py`
- New models import in `db/models/__init__.py` for Alembic discovery
- New i18n keys added to both `i18n/ru.py` and `i18n/en.py`
- APScheduler in `__main__.py` for monthly cleanup job

</code_context>

<specifics>
## Specific Ideas

- task.md section 4 has complete SQL schemas for baskets, basket_items, price_history — follow these exactly
- task.md section 6.2 has the exact inline button layout for basket navigation
- task.md section 6.3 specifies the URL input format: `<URL> [quantity]` per line
- task.md section 6.4 has the regex patterns and SOURCE_TO_BASKET mapping (already in scraper.py)
- Magnum baskets accept both magnum.kz and kaspi.kz URLs in the same basket

</specifics>

<deferred>
## Deferred Ideas

None — auto-mode discussion stayed within phase scope

</deferred>

---

*Phase: 02-basket-and-product-management*
*Context gathered: 2026-03-31 via auto-mode*
