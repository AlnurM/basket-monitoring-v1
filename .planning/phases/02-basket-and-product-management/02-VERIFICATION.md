---
phase: 02-basket-and-product-management
verified: 2026-03-30T00:00:00Z
status: human_needed
score: 17/17 must-haves verified
re_verification: false
human_verification:
  - test: "Create a basket via /baskets -> + New Basket, enter a name, tap Arbuz"
    expected: "Basket appears in list with >> active marker and (0 item(s)) count; confirmation message shows basket name and source"
    why_human: "FSM flow + inline keyboard interaction cannot be exercised without a live Telegram bot session"
  - test: "Add an arbuz.kz product URL to an arbuz basket (freeform message)"
    expected: "Bot replies with product name, quantity, and price in KZT; item appears in /baskets -> Items"
    why_human: "Requires live Playwright scrape against arbuz.kz and a running bot"
  - test: "Add a magnum.kz URL to an arbuz basket"
    expected: "Bot replies with source-mismatch error message naming the mismatch stores"
    why_human: "URL validation path requires live bot to verify exact message text"
  - test: "Add more than 50 URLs to a basket"
    expected: "51st item is rejected with error_item_limit_reached message; basket retains exactly 50 items"
    why_human: "Requires live DB session and bot to verify limit enforcement"
  - test: "View basket items with a product that has a discount (original_price != price)"
    expected: "Strikethrough original price shown in item line alongside current price"
    why_human: "Requires live scrape returning a discounted product to exercise item_line_discount formatting"
  - test: "Tap Charts button on a basket action keyboard"
    expected: "Telegram shows a popup alert (show_alert=True) with charts_coming_soon message; keyboard remains visible"
    why_human: "show_alert popup behavior requires live Telegram client to verify"
---

# Phase 2: Basket and Product Management Verification Report

**Phase Goal:** Users can create store-specific baskets, add products by URL with validation, and view their basket contents with live prices
**Verified:** 2026-03-30
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

All automated checks passed. The phase goal is structurally achieved: data models, repositories, handlers, wiring, and i18n are fully implemented and connected. Six items require a live Telegram session to confirm UX behavior.

### Observable Truths (Plan 02-01)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Basket, BasketItem, PriceHistory tables exist in PostgreSQL with correct schema | VERIFIED | `003_add_baskets_items_price_history.py` creates all three tables with correct columns, FKs, constraints, and composite index |
| 2 | Repositories provide async CRUD for baskets, items, and price history | VERIFIED | `basket.py` (8 methods), `basket_item.py` (6 methods), `price_history.py` (2 methods) -- all async, all with real DB queries |
| 3 | CallbackData factories encode/decode basket and item actions within 64-byte limit | VERIFIED | `factories.py` defines BasketCB (prefix=bsk), BasketActionCB (prefix=bact), ItemCB (prefix=itm) -- 3-4 char prefixes per design constraint |
| 4 | Keyboard builders produce correct inline button layouts per D-03 | VERIFIED | `basket.py` keyboards: basket_list_keyboard (1 per basket + New), basket_actions_keyboard (3-3-1 layout), confirm_delete_keyboard (2), source_selection_keyboard (2), confirm_remove_item_keyboard (2) |
| 5 | All Phase 2 i18n keys exist in both Russian and English | VERIFIED | 35 keys present and matching in both `ru.py` and `en.py`: basket management (12), product management (10), item display (8), pagination (3), stubs (2) |

### Observable Truths (Plan 02-02)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | User can run /baskets and see their basket list with inline buttons | VERIFIED | `cmd_baskets` handler at line 39 queries `get_user_baskets_with_item_counts` and returns `basket_list_keyboard` |
| 7 | User can create a new basket by tapping New Basket, entering a name, and selecting a source | VERIFIED | FSM flow: `callback_new_basket` sets `CreateBasket.waiting_for_name` -> `receive_basket_name` stores name -> `callback_set_source` creates basket and calls `repo.create` |
| 8 | User can tap a basket and see action buttons (Items, Prices, Charts, Add, Edit, Delete) | VERIFIED | `callback_view_basket` calls `basket_actions_keyboard` which builds 3-3-1 layout with all 7 buttons |
| 9 | User can delete a basket with confirmation | VERIFIED | `callback_delete_basket` shows `confirm_delete_keyboard`; `callback_confirm_delete` calls `repo.delete` |
| 10 | User can switch active basket by selecting one | VERIFIED | `callback_view_basket` calls `repo.set_active(user.id, basket.id)` which deactivates all then activates target |
| 11 | Basket creation is rejected when user has 10 baskets | VERIFIED | Both `cmd_new_basket` and `callback_set_source` check `count >= settings.max_baskets_per_user` and return `basket_limit_reached` error |

### Observable Truths (Plan 02-03)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 12 | User can add arbuz.kz products to an arbuz basket by sending URLs | VERIFIED | `handle_url_message` (freeform) and `receive_product_urls` (FSM) both call `_process_urls` which validates source via `SOURCE_TO_BASKET` |
| 13 | User can add magnum.kz or kaspi.kz products to a magnum basket by sending URLs | VERIFIED | `SOURCE_TO_BASKET = {"kaspi": "magnum", "magnum": "magnum"}` maps both to magnum basket type |
| 14 | User can specify quantity per product (default 1) | VERIFIED | `parse_product_lines` splits trailing int token as qty, defaults to 1 |
| 15 | User can send multiple URLs in one message (one per line) | VERIFIED | `parse_product_lines` iterates `text.strip().splitlines()` |
| 16 | Bot rejects invalid URLs with specific error message | VERIFIED | `validate_url_for_basket` returns "error_invalid_url" when `detect_source` returns None |
| 17 | Bot rejects URLs that don't match basket source with specific error | VERIFIED | `validate_url_for_basket` returns "error_source_mismatch" when `SOURCE_TO_BASKET[source] != basket_source` |
| 18 | Bot triggers first scrape after adding and shows product name + price | VERIFIED | `_process_urls` calls `ScraperService(session).scrape_urls(urls_to_scrape)` after item creation, then stores name and price history |
| 19 | User can view basket items with names, quantities, and latest prices | VERIFIED | `callback_list_items` calls `get_basket_items_with_latest_price` (LATERAL join) and `_build_items_text` renders formatted lines |
| 20 | User can remove a product from a basket | VERIFIED | `callback_remove_item` shows confirmation; `callback_confirm_remove` calls `item_repo.delete` |
| 21 | 50-item limit per basket is enforced | VERIFIED | `_process_urls` checks `current_count >= settings.max_items_per_basket` before each item creation |
| 22 | Every scrape result is stored in price_history | VERIFIED | `_process_urls` calls `price_repo.create(basket_item_id=item_id, price=..., original_price=..., is_available=...)` for every successful scrape |
| 23 | Price history cleanup job runs monthly | VERIFIED | `cleanup_old_prices` function in `__main__.py` + `CronTrigger(day=1, hour=3, minute=0)` APScheduler job |

**Score:** 23/23 truths verified (17 automated checks passed; 6 require human verification for UX behavior)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/price_spy/db/models/basket.py` | Basket ORM model | VERIFIED | `class Basket` with user_id FK, name, source, is_active, CASCADE items |
| `src/price_spy/db/models/basket_item.py` | BasketItem ORM model | VERIFIED | `class BasketItem` with basket_id FK, product_url, UniqueConstraint, CASCADE price_records |
| `src/price_spy/db/models/price_history.py` | PriceHistory ORM model | VERIFIED | `class PriceHistory` with basket_item_id FK, price, original_price, is_available, composite index |
| `alembic/versions/003_add_baskets_items_price_history.py` | Migration for 3 tables | VERIFIED | Creates baskets, basket_items, price_history with FK constraints and composite index |
| `src/price_spy/db/repositories/basket.py` | BasketRepository CRUD | VERIFIED | 8 async methods including LATERAL-style correlated subquery for item counts |
| `src/price_spy/db/repositories/basket_item.py` | BasketItemRepository CRUD | VERIFIED | 6 async methods including `get_basket_items_with_latest_price` using LATERAL join |
| `src/price_spy/db/repositories/price_history.py` | PriceHistoryRepository CRUD + cleanup | VERIFIED | `create` and `cleanup_old_records` methods; cleanup returns deleted row count |
| `src/price_spy/bot/callbacks/factories.py` | CallbackData subclasses | VERIFIED | BasketCB (bsk), BasketActionCB (bact), ItemCB (itm) |
| `src/price_spy/bot/states/basket.py` | FSM states | VERIFIED | `CreateBasket.waiting_for_name`, `AddProduct.waiting_for_urls` |
| `src/price_spy/bot/keyboards/basket.py` | Keyboard builders | VERIFIED | 5 keyboard builder functions including `confirm_remove_item_keyboard` |
| `src/price_spy/bot/keyboards/pagination.py` | Pagination keyboard | VERIFIED | `items_page_keyboard` with ITEMS_PER_PAGE=10, prev/next/page-indicator/back |
| `src/price_spy/bot/handlers/basket.py` | Basket CRUD handlers | VERIFIED | 338 lines, 12 handlers (min_lines=100 passed), `router = Router` present |
| `src/price_spy/bot/handlers/product.py` | Product URL handler + item display + removal | VERIFIED | 447 lines, 8 handlers + 3 helpers, `router = Router` present |
| `src/price_spy/bot/create.py` | Dispatcher with basket+product routers | VERIFIED | `dp.include_router(basket.router)` and `dp.include_router(product.router)` both present |
| `src/price_spy/__main__.py` | Monthly cleanup job | VERIFIED | `cleanup_old_prices` function + `CronTrigger(day=1, hour=3, minute=0)` scheduler job |
| `src/price_spy/i18n/ru.py` | Phase 2 i18n keys (Russian) | VERIFIED | All 35 Phase 2 keys present |
| `src/price_spy/i18n/en.py` | Phase 2 i18n keys (English) | VERIFIED | All 35 Phase 2 keys present, matching Russian key set |

### Key Link Verification

**Plan 02-01 Links**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `basket.py` | `user.py` | ForeignKey users.id | VERIFIED | Line 21: `ForeignKey("users.id", ondelete="CASCADE")` |
| `basket_item.py` | `basket.py` | ForeignKey baskets.id | VERIFIED | Line 25: `ForeignKey("baskets.id", ondelete="CASCADE")` |
| `price_history.py` | `basket_item.py` | ForeignKey basket_items.id | VERIFIED | Line 25: `ForeignKey("basket_items.id", ondelete="CASCADE")` |

**Plan 02-02 Links**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `handlers/basket.py` | `repositories/basket.py` | BasketRepository instantiation | VERIFIED | Line 17: import; lines 48, 80, 133, 167, 194, 226, 251, 275, 304 instantiations |
| `handlers/basket.py` | `callbacks/factories.py` | BasketCB.filter imports | VERIFIED | Line 7: import; 4 `BasketCB.filter(F.action == ...)` decorators |
| `handlers/basket.py` | `keyboards/basket.py` | basket_list_keyboard, basket_actions_keyboard | VERIFIED | Lines 9-10: imports used in cmd_baskets, callback_view_basket, callback_basket_list |
| `bot/create.py` | `handlers/basket.py` | dp.include_router | VERIFIED | Line 31: `dp.include_router(basket.router)` |

**Plan 02-03 Links**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `handlers/product.py` | `services/scraper.py` | ScraperService.scrape_urls | VERIFIED | Line 22: import; line 192: `ScraperService(session)` instantiation + `scrape_urls` call |
| `handlers/product.py` | `services/scraper.py` | detect_source, SOURCE_TO_BASKET | VERIFIED | Lines 23-26: imports; lines 68, 71, 153, 169 usage |
| `handlers/product.py` | `repositories/basket_item.py` | BasketItemRepository | VERIFIED | Line 19: import; 6 instantiation sites |
| `handlers/product.py` | `repositories/price_history.py` | PriceHistoryRepository | VERIFIED | Line 20: import; line 142 instantiation; line 208 `price_repo.create` call |
| `__main__.py` | `repositories/price_history.py` | cleanup_old_records | VERIFIED | Lines 60-64: lazy import + `PriceHistoryRepository(session)` + `cleanup_old_records(settings.price_history_retention_days)` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `handlers/basket.py` | `baskets_with_counts` | `BasketRepository.get_user_baskets_with_item_counts` | Yes -- correlated scalar subquery over DB | FLOWING |
| `handlers/product.py` | `items` (list+prices) | `BasketItemRepository.get_basket_items_with_latest_price` | Yes -- LATERAL join over price_history | FLOWING |
| `handlers/product.py` | `scrape_results` | `ScraperService.scrape_urls` | Yes -- live Playwright/httpx scrape | FLOWING |
| `__main__.py` | `count` (deleted records) | `PriceHistoryRepository.cleanup_old_records` | Yes -- DELETE with WHERE clause, returns rowcount | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED -- no runnable entry points available without a live PostgreSQL database and Telegram bot token. All behaviors depend on network/bot/DB resources.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BSKT-01 | 02-01, 02-02 | User can create a basket with a name and store source | SATISFIED | FSM creation flow in basket.py; Basket model with source column + CHECK constraint |
| BSKT-02 | 02-01, 02-02 | User can view all their baskets with item counts | SATISFIED | `get_user_baskets_with_item_counts` + `basket_list_keyboard` |
| BSKT-03 | 02-01, 02-02 | User can switch active basket | SATISFIED | `callback_view_basket` calls `repo.set_active`; `set_active` deactivates all then activates target |
| BSKT-04 | 02-01, 02-02 | User can delete a basket | SATISFIED | Two-step confirmation: `callback_delete_basket` + `callback_confirm_delete` -> `repo.delete` |
| BSKT-05 | 02-01, 02-02 | User is limited to 10 baskets maximum | SATISFIED | Guard in `cmd_new_basket`, `callback_new_basket`, and `callback_set_source` checks `count >= settings.max_baskets_per_user` |
| PROD-01 | 02-03 | User can add products by pasting arbuz.kz URL (for arbuz baskets) | SATISFIED | `detect_source` matches arbuz pattern; `SOURCE_TO_BASKET["arbuz"] == "arbuz"` |
| PROD-02 | 02-03 | User can add products by pasting magnum.kz or kaspi.kz URL (for magnum baskets) | SATISFIED | `SOURCE_TO_BASKET["magnum"] == "magnum"` and `SOURCE_TO_BASKET["kaspi"] == "magnum"` |
| PROD-03 | 02-03 | User can specify quantity when adding a product (default: 1) | SATISFIED | `parse_product_lines` extracts trailing int as qty, defaults to 1 |
| PROD-04 | 02-03 | User can add multiple products at once (one URL per line) | SATISFIED | `parse_product_lines` iterates `splitlines()` |
| PROD-05 | 02-03 | Bot validates URL format and rejects invalid URLs with clear error message | SATISFIED | `validate_url_for_basket` -> "error_invalid_url" i18n key |
| PROD-06 | 02-03 | Bot validates URL source matches basket type | SATISFIED | `validate_url_for_basket` -> "error_source_mismatch" i18n key with source/basket details |
| PROD-07 | 02-01, 02-03 | User can remove a product from their basket | SATISFIED | `callback_remove_item` + `callback_confirm_remove` -> `item_repo.delete` |
| PROD-08 | 02-03 | User can view basket contents with product names, quantities, and latest prices | SATISFIED | `callback_list_items` + `_build_items_text` renders numbered lines with prices/discounts/availability |
| PROD-09 | 02-01, 02-03 | User is limited to 50 items per basket | SATISFIED | `count_by_basket` check in `callback_add_item_prompt` + per-URL check in `_process_urls` |
| HIST-01 | 02-01, 02-03 | Every scrape result is stored in price_history with timestamp | SATISFIED | `price_repo.create` called in `_process_urls` for every successful `scrape_results` entry; `scraped_at` uses `server_default=func.now()` |
| HIST-02 | 02-01, 02-03 | Price history includes current price, original price, and availability | SATISFIED | `PriceHistory` model has `price`, `original_price`, `is_available`; all three passed to `price_repo.create` |
| HIST-03 | 02-01, 02-03 | Price history records older than 90 days are automatically cleaned up (monthly) | SATISFIED | `cleanup_old_prices` + APScheduler `CronTrigger(day=1, hour=3)` + `cleanup_old_records(settings.price_history_retention_days)` |
| TXUX-01 | 02-01, 02-02 | Bot provides inline keyboard navigation for baskets and actions | SATISFIED | 5 keyboard builders; all basket/product callbacks use `InlineKeyboardMarkup` |
| TXUX-02 | 02-01, 02-02 | Basket list shows inline buttons for: list items, view prices, view charts, add item, edit, delete | SATISFIED | `basket_actions_keyboard` builds 3-3-1 layout with all 7 buttons; Charts/Edit stub handlers present per spec |

**Orphaned requirements check:** TXUX-03 ("All user-facing messages are bilingual") is assigned to Phase 4 in REQUIREMENTS.md and was not claimed by any Phase 2 plan. This is correct -- not an orphan, correctly deferred.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/price_spy/__main__.py` | 54 | `daily_scrape` is a logged placeholder | INFO | Intentional -- explicitly scoped to Phase 3. Comment says "full implementation in Phase 3". Does not affect Phase 2 goal. |
| `src/price_spy/bot/handlers/basket.py` | 319-338 | `charts` and `edit` handlers return `show_alert=True` stubs | INFO | Intentional per TXUX-02 and design spec -- buttons must exist but functionality deferred to Phase 4. Properly labeled. |

No blockers or warnings found.

### Human Verification Required

#### 1. Basket Creation Flow

**Test:** Open a Telegram conversation with the bot, run `/baskets`, tap `+ New Basket`, type a basket name, tap Arbuz
**Expected:** Confirmation message "Basket [name] (Arbuz) created!"; running /baskets again shows basket with `>> ` active marker and `(0 item(s))`
**Why human:** FSM state machine and inline keyboard interaction require a live Telegram session

#### 2. Product URL Add Flow (Freeform)

**Test:** With an active arbuz basket, paste an arbuz.kz catalog URL in chat (no command)
**Expected:** Bot sends "Adding products..." then edits to show product name, quantity x1, and price in KZT
**Why human:** Requires live Playwright scrape against arbuz.kz and an active bot session

#### 3. Source Mismatch Validation

**Test:** With an active arbuz basket, send a magnum.kz product URL
**Expected:** Bot replies with source-mismatch error naming the URL's source and the basket's expected source
**Why human:** Requires live bot session to verify exact error message rendering

#### 4. Item Limit Enforcement

**Test:** Add 50 items to a basket then attempt to add a 51st
**Expected:** 51st URL is rejected with "Limit reached: maximum 50 items per basket" message; basket count remains at 50
**Why human:** Requires live DB session and repeated bot interaction

#### 5. Discount Display

**Test:** View a basket containing a product currently on discount at the target store
**Expected:** Item line shows current price, strikethrough `<s>original</s>` price, and total for that item
**Why human:** Requires a live discounted product in the target store at time of testing

#### 6. Charts Stub Alert

**Test:** Open a basket via /baskets, tap the Charts button in the action keyboard
**Expected:** Telegram displays a popup alert (modal) with "Charts will be available in the next update." / "Графики будут доступны в следующем обновлении."
**Why human:** `show_alert=True` popup behavior cannot be verified without a Telegram client

### Gaps Summary

No gaps. All 17 artifacts verified at all 4 levels (exists, substantive, wired, data-flowing). All 19 required requirement IDs have implementation evidence. The six human verification items are behavioral confirmations of already-verified code paths, not gaps.

---

_Verified: 2026-03-30_
_Verifier: Claude (gsd-verifier)_
