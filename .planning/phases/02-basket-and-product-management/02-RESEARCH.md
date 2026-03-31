# Phase 2: Basket and Product Management - Research

**Researched:** 2026-03-30
**Domain:** aiogram 3 inline keyboard navigation, SQLAlchemy basket/item models, URL validation, price history
**Confidence:** HIGH

## Summary

Phase 2 builds basket CRUD, product management, inline keyboard navigation, and price history storage on top of Phase 1's foundation. The existing codebase provides all necessary patterns: Router-based handlers, middleware-injected sessions, repository CRUD, i18n via `get_text`, and `ScraperService` with `URL_PATTERNS`/`detect_source`/`extract_product_id`. The main new concerns are (1) hierarchical inline button navigation using aiogram 3's `CallbackData` factory for type-safe routing, (2) three new SQLAlchemy models (`Basket`, `BasketItem`, `PriceHistory`) with a new Alembic migration (003), and (3) integrating ScraperService into the product-add flow for first-scrape.

The architecture is straightforward: new models follow `User` pattern, new repositories follow `UserRepository` pattern, new handlers follow `start.py` router pattern, and new i18n keys go into both `ru.py` and `en.py`. The main discretion area is FSM vs pure callback routing for basket creation -- recommendation below is to use FSM for the basket creation name-input step only, and `CallbackData` factories for all button navigation.

**Primary recommendation:** Use aiogram 3 `CallbackData` subclasses with prefixes for all inline button routing, and FSM `StatesGroup` only for the basket-creation name-input step (the single point where freeform text input is needed outside URL adding).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Hierarchical inline button navigation: /baskets shows list of baskets with inline buttons -> selecting a basket shows action buttons (List, Prices, Add, Delete) -> each action shows relevant content with back navigation.
- D-02: Basket list format: emoji + name + store source + item count per basket.
- D-03: Inline buttons follow the layout from task.md section 6.2.
- D-04: Users add products by sending freeform text messages containing URLs. Bot detects URLs in any message sent while a basket is active. Format: `<URL> [quantity]` per line, one or more lines per message.
- D-05: Bot auto-detects URL source (arbuz/magnum/kaspi) and validates against active basket type.
- D-06: After adding products, bot immediately triggers a first scrape to populate name and initial price.
- D-07: Basket contents show per-item: number, product name, quantity, unit price, line total.
- D-08: Out-of-stock items flagged with a red marker. Discount prices shown with original crossed out.
- D-09: Basket total displayed at bottom of item list.
- D-10: Detailed validation errors with specific reason for rejection.
- D-11: All validation messages are bilingual (use i18n get_text from Phase 1).
- D-12: Every scrape stores: basket_item_id, price, original_price, is_available, scraped_at.
- D-13: Cleanup job runs monthly (1st of month at 03:00 Asia/Almaty) deleting records older than 90 days. Uses APScheduler cron trigger.
- D-14: Limits from settings: max_baskets_per_user (10), max_items_per_basket (50).
- Carry forward: Dictionary-based i18n, User model, ScraperService, DB session middleware, ProductNameCache, InlineKeyboardBuilder, URL_PATTERNS/detect_source.

### Claude's Discretion
- Pagination approach for long basket item lists (if >10 items)
- Whether to use aiogram FSM for multi-step basket creation flow or simple callback_data routing
- Exact callback_data encoding format for inline buttons

### Deferred Ideas (OUT OF SCOPE)
None -- auto-mode discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BSKT-01 | Create basket with name + source | Basket model, BasketRepository.create(), FSM for name input, callback for source selection |
| BSKT-02 | View all baskets with item counts | BasketRepository.get_user_baskets_with_counts(), inline keyboard list |
| BSKT-03 | Switch active basket | `is_active` flag on Basket model, BasketRepository.set_active() |
| BSKT-04 | Delete a basket | BasketRepository.delete(), CASCADE deletes items and price history |
| BSKT-05 | Max 10 baskets per user | BasketRepository.count_by_user(), check before create |
| PROD-01 | Add arbuz.kz URL to arbuz basket | URL_PATTERNS["arbuz"], detect_source(), SOURCE_TO_BASKET validation |
| PROD-02 | Add magnum.kz/kaspi.kz URL to magnum basket | URL_PATTERNS["magnum"/"kaspi"], SOURCE_TO_BASKET maps both to "magnum" |
| PROD-03 | Specify quantity (default 1) | Parse `<URL> [qty]` format per line |
| PROD-04 | Add multiple products at once | Split message by newlines, process each line |
| PROD-05 | Validate URL format | detect_source() returns None for invalid URLs |
| PROD-06 | Validate URL source matches basket type | SOURCE_TO_BASKET[detected_source] must equal basket.source |
| PROD-07 | Remove product from basket | BasketItemRepository.delete(), CASCADE deletes price history |
| PROD-08 | View basket contents with names/quantities/prices | Join basket_items with latest price_history per item |
| PROD-09 | Max 50 items per basket | BasketItemRepository.count_by_basket(), check before add |
| HIST-01 | Store every scrape in price_history | PriceHistoryRepository.create() after each scrape |
| HIST-02 | Price history includes price, original_price, availability | PriceHistory model matches task.md 4.4 schema |
| HIST-03 | Auto-cleanup records >90 days monthly | APScheduler cron job on 1st of month, DELETE WHERE scraped_at < now() - 90 days |
| TXUX-01 | Inline keyboard navigation for baskets | CallbackData factories, hierarchical button flow |
| TXUX-02 | Basket list shows action buttons | Two-row layout per D-03 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- GSD workflow enforcement: use `/gsd:execute-phase` for planned phase work, not direct edits
- `commit_docs: true` in config -- commit documentation artifacts
- Mode: yolo, granularity: coarse
- No nyquist_validation (explicitly false)

## Standard Stack

No new dependencies needed for Phase 2. Everything uses the existing stack from Phase 1.

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiogram | ~=3.26 | Telegram bot: Router, CallbackData, FSM, InlineKeyboardBuilder | Already installed; provides all inline keyboard and state management needed |
| SQLAlchemy | ~=2.0.48 | ORM for Basket, BasketItem, PriceHistory models | Already installed; async mapped_column pattern established |
| alembic | ~=1.18 | Migration 003 for new tables | Already installed; migration chain at 002 |
| APScheduler | ~=3.11 | Monthly price history cleanup job | Already installed; scheduler initialized in `__main__.py` |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | ~=2.12 | Validation of parsed URL/quantity input | Already installed; use for input parsing models if needed |

## Architecture Patterns

### Recommended Project Structure (new files for Phase 2)
```
src/price_spy/
├── bot/
│   ├── handlers/
│   │   ├── basket.py           # /baskets, /new_basket, basket CRUD callbacks
│   │   └── product.py          # URL message handler, /remove, item list callbacks
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── basket.py           # Basket list, basket actions keyboards
│   │   └── pagination.py       # Generic pagination for item lists
│   ├── callbacks/
│   │   ├── __init__.py
│   │   └── factories.py        # All CallbackData subclasses
│   └── states/
│       ├── __init__.py
│       └── basket.py           # FSM states for basket creation
├── db/
│   ├── models/
│   │   ├── basket.py           # Basket model
│   │   ├── basket_item.py      # BasketItem model
│   │   └── price_history.py    # PriceHistory model
│   └── repositories/
│       ├── basket.py           # Basket CRUD + count queries
│       ├── basket_item.py      # Item CRUD + count + latest price join
│       └── price_history.py    # Price record creation + cleanup query
├── services/
│   └── basket.py               # Basket business logic (validation, limits, first-scrape orchestration)
└── i18n/
    ├── ru.py                   # Add ~30 new keys
    └── en.py                   # Add ~30 new keys
alembic/versions/
    └── 003_add_baskets_items_price_history.py
```

### Pattern 1: CallbackData Factories for Type-Safe Inline Buttons

**What:** Define `CallbackData` subclasses with typed fields. Use as `callback_data` in `InlineKeyboardBuilder.button()`. Filter handlers with `MyCallback.filter(F.action == "something")`.

**When to use:** All inline button interactions in the basket navigation hierarchy.

**Example:**
```python
# bot/callbacks/factories.py
from aiogram.filters.callback_data import CallbackData

class BasketCB(CallbackData, prefix="bsk"):
    action: str  # "list", "view", "delete", "new", "set_source"
    basket_id: int | None = None
    source: str | None = None  # "arbuz" or "magnum" (for creation)

class BasketActionCB(CallbackData, prefix="bact"):
    action: str  # "items", "prices", "add", "edit", "delete", "back"
    basket_id: int

class ItemCB(CallbackData, prefix="itm"):
    action: str  # "remove", "page"
    basket_id: int
    item_id: int | None = None
    page: int = 0
```

**Handler registration:**
```python
# bot/handlers/basket.py
from aiogram import F, Router
from price_spy.bot.callbacks.factories import BasketCB, BasketActionCB

router = Router(name="basket")

@router.callback_query(BasketCB.filter(F.action == "view"))
async def view_basket(
    callback: CallbackQuery,
    callback_data: BasketCB,
    session: AsyncSession,
    user: User,
    lang: str,
    **kwargs: object,
) -> None:
    basket_id = callback_data.basket_id
    # ... build action keyboard for this basket
```

**Source:** [aiogram 3 CallbackData documentation](https://docs.aiogram.dev/en/latest/dispatcher/filters/callback_data.html), [mastergroosha guide](https://mastergroosha.github.io/aiogram-3-guide/buttons/)

### Pattern 2: FSM for Basket Creation Name Input

**What:** Use `StatesGroup` with a single state for collecting basket name via freeform text. After name is received, show source selection via inline buttons (no FSM needed for that step).

**When to use:** Only for basket creation -- the one flow requiring freeform text input that is NOT a URL.

**Example:**
```python
# bot/states/basket.py
from aiogram.fsm.state import State, StatesGroup

class CreateBasket(StatesGroup):
    waiting_for_name = State()

# In handler:
@router.callback_query(BasketCB.filter(F.action == "new"))
async def start_create_basket(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str,
    **kwargs: object,
) -> None:
    await state.set_state(CreateBasket.waiting_for_name)
    await callback.message.answer(get_text("enter_basket_name", lang))

@router.message(CreateBasket.waiting_for_name)
async def receive_basket_name(
    message: Message,
    state: FSMContext,
    lang: str,
    **kwargs: object,
) -> None:
    await state.update_data(name=message.text.strip())
    # Show source selection inline buttons
    builder = InlineKeyboardBuilder()
    builder.button(text="Arbuz", callback_data=BasketCB(action="set_source", source="arbuz"))
    builder.button(text="Magnum", callback_data=BasketCB(action="set_source", source="magnum"))
    await message.answer(get_text("choose_source", lang), reply_markup=builder.as_markup())
    await state.clear()  # No more FSM needed; source selection is via callback
```

**Source:** [aiogram 3 FSM documentation](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html)

### Pattern 3: URL Detection in Freeform Messages

**What:** Register a message handler with NO command filter that checks for URLs in message text. Only active when user has a selected basket (check via DB, not FSM). Parse each line as `<URL> [quantity]`.

**When to use:** For the D-04 product-adding flow.

**Example:**
```python
# bot/handlers/product.py
import re

router = Router(name="product")

URL_LINE_PATTERN = re.compile(
    r"(https?://(?:arbuz\.kz|magnum\.kz|kaspi\.kz)/\S+)"
    r"(?:\s+(\d+))?",
    re.IGNORECASE,
)

@router.message(F.text.regexp(r"https?://"))
async def handle_url_message(
    message: Message,
    session: AsyncSession,
    user: User,
    lang: str,
    **kwargs: object,
) -> None:
    # Find active basket for user
    # Parse each line for URL + optional quantity
    # Validate each URL source against basket.source
    # Add items, trigger first scrape, reply with confirmation
    ...
```

**Important:** This handler must be registered AFTER FSM state handlers to avoid capturing basket-name text as URLs. The `F.text.regexp(r"https?://")` filter ensures only messages containing URLs trigger this handler.

### Pattern 4: Pagination for Item Lists

**What:** For baskets with >10 items, paginate the display. Use `ItemCB(action="page", basket_id=X, page=N)` callbacks. Show "< Prev | Page X/Y | Next >" buttons.

**Recommendation:** 10 items per page. Each page shows items N*10+1 through (N+1)*10 with standard back/next navigation buttons.

### Anti-Patterns to Avoid
- **Storing active basket in FSM state:** FSM state is volatile (memory-based by default). Store `is_active` in the database `baskets` table so it persists across restarts.
- **String callback_data parsing:** Use `CallbackData` factories, not manual `f"basket:{id}:action"` strings. Factories are type-safe and self-parsing.
- **Blocking first-scrape in handler:** The first scrape on product add uses Playwright (2-5s). Run it asynchronously and `await` it, but be aware of Telegram's callback timeout (30s for messages). For single items this is fine; for bulk adds (D-04), consider sending a "processing..." message first then editing it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Callback data encoding/parsing | Custom `f"prefix:{id}:{action}"` + split | aiogram `CallbackData` subclass | Type-safe, auto-packing, auto-filtering, no off-by-one in splits |
| URL source detection | New regex matching | `detect_source()` from `services/scraper.py` | Already implemented and tested in Phase 1 |
| Product ID extraction | Custom parsing | `extract_product_id()` from `services/scraper.py` | Already implemented in Phase 1 |
| Source-to-basket validation | Custom mapping | `SOURCE_TO_BASKET` dict from `services/scraper.py` | Already defined: arbuz->arbuz, magnum->magnum, kaspi->magnum |
| First scrape orchestration | Direct scraper calls | `ScraperService.scrape_urls()` | Handles concurrency, retries, name caching |
| Inline keyboard building | Manual InlineKeyboardMarkup | `InlineKeyboardBuilder` from aiogram.utils.keyboard | Cleaner API, accepts CallbackData directly |

**Key insight:** Phase 1 already implemented the hardest parts (scraping, URL validation, name caching). Phase 2 wires those into the basket management UI.

## Common Pitfalls

### Pitfall 1: Telegram Callback Data 64-byte Limit
**What goes wrong:** Callback data strings exceed 64 bytes and Telegram silently rejects the button or throws an error.
**Why it happens:** Stuffing too many fields or long strings into callback_data.
**How to avoid:** Keep `CallbackData` prefixes short (3-4 chars). Use integer IDs, not names. The `BasketCB(prefix="bsk")` with an int `basket_id` and short `action` string stays well under 64 bytes.
**Warning signs:** Buttons that don't respond when tapped, or `BadRequest` errors in logs.

### Pitfall 2: Race Condition on Basket Item Count Check
**What goes wrong:** Two rapid "add" requests both pass the 50-item limit check, resulting in 51+ items.
**Why it happens:** Check-then-act without locking.
**How to avoid:** Use `SELECT COUNT(*) ... FOR UPDATE` or a database-level constraint. Since this is a single-user Telegram bot (one user sends messages sequentially), the practical risk is very low. A simple count check before insert is sufficient.
**Warning signs:** Item count exceeding max_items_per_basket.

### Pitfall 3: N+1 Query When Displaying Basket Items with Prices
**What goes wrong:** Loading basket items, then separately querying latest price for each item.
**Why it happens:** Naive repository implementation.
**How to avoid:** Use a single query with a lateral join or subquery to get the latest price_history record per basket_item. Example:
```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

# Subquery for latest price per item
latest_price = (
    select(PriceHistory)
    .where(PriceHistory.basket_item_id == BasketItem.id)
    .order_by(PriceHistory.scraped_at.desc())
    .limit(1)
    .correlate(BasketItem)
    .lateral("latest_price")
)
```
**Warning signs:** Slow basket display, many small queries in logs.

### Pitfall 4: Editing Messages After Callback Without answer()
**What goes wrong:** Telegram shows a spinner on the button indefinitely.
**Why it happens:** Not calling `callback.answer()` (acknowledging the callback query).
**How to avoid:** Always call `await callback.answer()` at the end of every callback handler, even if you also edit the message.
**Warning signs:** Permanent loading indicator on buttons.

### Pitfall 5: FSM State Conflicts with URL Message Handler
**What goes wrong:** User is in `CreateBasket.waiting_for_name` state and sends a URL -- the URL handler fires instead of the FSM name handler.
**Why it happens:** Handler registration order matters. If the URL message handler is registered before the FSM handler, it catches URLs first.
**How to avoid:** Register the basket creation FSM handler on the basket router. Register the URL handler on the product router. Include both routers in the dispatcher with basket router FIRST. The FSM state filter (`CreateBasket.waiting_for_name`) takes priority over the URL regex filter when state is active.
**Warning signs:** Basket names that look like URLs, or URLs rejected during basket creation.

### Pitfall 6: Missing Cascade Delete for Price History
**What goes wrong:** Deleting a basket item leaves orphaned price_history records.
**Why it happens:** Forgetting `ON DELETE CASCADE` on foreign keys.
**How to avoid:** Define foreign keys with `ondelete="CASCADE"` in SQLAlchemy models. This is specified in task.md section 4 schemas.
**Warning signs:** Growing price_history table with no corresponding basket_items.

## Code Examples

### Model: Basket
```python
# db/models/basket.py
from __future__ import annotations
import datetime
from sqlalchemy import BigInteger, Boolean, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Basket(Base):
    __tablename__ = "baskets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # "arbuz" or "magnum"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    items: Mapped[list["BasketItem"]] = relationship(
        back_populates="basket", cascade="all, delete-orphan"
    )
```
Source: task.md section 4.2 + existing User model pattern

### Model: BasketItem
```python
# db/models/basket_item.py
from __future__ import annotations
import datetime
from sqlalchemy import BigInteger, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class BasketItem(Base):
    __tablename__ = "basket_items"
    __table_args__ = (
        UniqueConstraint("basket_id", "product_url", name="uq_basket_item_url"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    basket_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("baskets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[str] = mapped_column(Text, nullable=False)
    url_source: Mapped[str] = mapped_column(Text, nullable=False)  # "arbuz", "magnum", "kaspi"
    name: Mapped[str | None] = mapped_column(Text, nullable=True)  # Populated on first scrape
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    basket: Mapped["Basket"] = relationship(back_populates="items")
    price_records: Mapped[list["PriceHistory"]] = relationship(
        back_populates="basket_item", cascade="all, delete-orphan"
    )
```
Source: task.md section 4.3

### Model: PriceHistory
```python
# db/models/price_history.py
from __future__ import annotations
import datetime
from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        Index("idx_price_history_item_date", "basket_item_id", "scraped_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    basket_item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("basket_items.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[int | None] = mapped_column(Numeric(12, 2), nullable=True)
    original_price: Mapped[int | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    basket_item: Mapped["BasketItem"] = relationship(back_populates="price_records")
```
Source: task.md section 4.4

### Repository: BasketRepository (key methods)
```python
# db/repositories/basket.py
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from price_spy.db.models.basket import Basket

class BasketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_baskets(self, user_id: int) -> list[Basket]:
        stmt = select(Basket).where(Basket.user_id == user_id).order_by(Basket.created_at)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(Basket).where(Basket.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, user_id: int, name: str, source: str) -> Basket:
        basket = Basket(user_id=user_id, name=name, source=source)
        self._session.add(basket)
        await self._session.flush()
        return basket

    async def get_active_basket(self, user_id: int) -> Basket | None:
        stmt = select(Basket).where(Basket.user_id == user_id, Basket.is_active.is_(True)).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_active(self, user_id: int, basket_id: int) -> None:
        # Deactivate all, then activate the target
        from sqlalchemy import update
        await self._session.execute(
            update(Basket).where(Basket.user_id == user_id).values(is_active=False)
        )
        await self._session.execute(
            update(Basket).where(Basket.id == basket_id).values(is_active=True)
        )
        await self._session.flush()

    async def delete(self, basket_id: int) -> None:
        basket = await self._session.get(Basket, basket_id)
        if basket:
            await self._session.delete(basket)
            await self._session.flush()
```
Source: UserRepository pattern from Phase 1

### Alembic Migration 003
```python
# alembic/versions/003_add_baskets_items_price_history.py
revision: str = "003"
down_revision: str = "002"

def upgrade() -> None:
    op.create_table(
        "baskets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("source IN ('arbuz', 'magnum')", name="ck_baskets_source"),
    )
    op.create_table(
        "basket_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("basket_id", sa.BigInteger(), sa.ForeignKey("baskets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_url", sa.Text(), nullable=False),
        sa.Column("product_id", sa.Text(), nullable=False),
        sa.Column("url_source", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("basket_id", "product_url", name="uq_basket_item_url"),
        sa.CheckConstraint("url_source IN ('arbuz', 'magnum', 'kaspi')", name="ck_items_url_source"),
    )
    op.create_table(
        "price_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("basket_item_id", sa.BigInteger(), sa.ForeignKey("basket_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("original_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_price_history_item_date", "price_history", ["basket_item_id", sa.text("scraped_at DESC")])
```

### Inline Keyboard: Basket List
```python
# bot/keyboards/basket.py
from aiogram.utils.keyboard import InlineKeyboardBuilder
from price_spy.bot.callbacks.factories import BasketCB, BasketActionCB

def basket_list_keyboard(baskets: list, item_counts: dict, lang: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for b in baskets:
        count = item_counts.get(b.id, 0)
        label = f"{'*' if b.is_active else ''} {b.name} ({b.source.capitalize()}) -- {count} items"
        builder.button(text=label, callback_data=BasketCB(action="view", basket_id=b.id))
    builder.button(text="+ New Basket", callback_data=BasketCB(action="new"))
    builder.adjust(1)  # One basket per row
    return builder

def basket_actions_keyboard(basket_id: int, lang: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    # Row 1: View actions
    builder.button(text="List", callback_data=BasketActionCB(action="items", basket_id=basket_id))
    builder.button(text="Prices", callback_data=BasketActionCB(action="prices", basket_id=basket_id))
    # Row 2: Modify actions
    builder.button(text="+ Add", callback_data=BasketActionCB(action="add", basket_id=basket_id))
    builder.button(text="Delete", callback_data=BasketActionCB(action="delete", basket_id=basket_id))
    # Row 3: Back
    builder.button(text="< Back", callback_data=BasketCB(action="list"))
    builder.adjust(2, 2, 1)
    return builder
```

### URL Parsing Logic
```python
# In bot/handlers/product.py or services/basket.py
import re
from price_spy.services.scraper import detect_source, extract_product_id, SOURCE_TO_BASKET

def parse_product_lines(text: str) -> list[tuple[str, int]]:
    """Parse message text into list of (url, quantity) tuples."""
    results = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit(None, 1)  # Split from right to get URL and optional qty
        url = parts[0]
        qty = 1
        if len(parts) == 2:
            try:
                qty = int(parts[1])
                if qty < 1:
                    qty = 1
            except ValueError:
                # Not a number -- entire line is the URL
                url = line
        results.append((url, qty))
    return results

def validate_url_for_basket(url: str, basket_source: str) -> str | None:
    """Returns error message key or None if valid."""
    source = detect_source(url)
    if source is None:
        return "error_invalid_url"
    expected_basket = SOURCE_TO_BASKET.get(source)
    if expected_basket != basket_source:
        return "error_source_mismatch"
    return None
```

### Monthly Cleanup Job
```python
# In __main__.py, add alongside daily_scrape job:
async def cleanup_old_prices() -> None:
    """HIST-03: Delete price_history records older than 90 days."""
    from sqlalchemy import delete, text
    from price_spy.db.engine import async_session
    from price_spy.db.models.price_history import PriceHistory

    async with async_session() as session:
        cutoff = func.now() - datetime.timedelta(days=settings.price_history_retention_days)
        stmt = delete(PriceHistory).where(PriceHistory.scraped_at < cutoff)
        result = await session.execute(stmt)
        await session.commit()
        logger.info("Cleaned up %d old price history records", result.rowcount)

# Register in on_startup:
scheduler.add_job(
    cleanup_old_prices,
    trigger=CronTrigger(day=1, hour=3, minute=0),
    id="cleanup_prices",
    replace_existing=True,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual callback_data string parsing | `CallbackData` factory subclasses | aiogram 3.0 (2023) | Type-safe, auto-pack/unpack, filter integration |
| `InlineKeyboardMarkup` manual construction | `InlineKeyboardBuilder` with `.button()` + `.adjust()` | aiogram 3.0 (2023) | Cleaner API, accepts CallbackData directly |
| `MemoryStorage` for FSM | Still default but `RedisStorage` / custom available | aiogram 3.0+ | For this bot, `MemoryStorage` is fine (single process, only basket creation uses FSM briefly) |

## Open Questions

1. **Price type: Integer vs Numeric(12,2)**
   - What we know: task.md section 4.4 uses `NUMERIC(12,2)` for price columns. But `PriceResult` model uses `int` (integer tenge, no tiyn).
   - What's unclear: Whether to store as integer tenge in the app layer and NUMERIC in DB, or use Decimal throughout.
   - Recommendation: Use `Numeric(12,2)` in the database as specified in task.md. Convert `PriceResult.price` (int) to Decimal when storing. This preserves flexibility if sub-tenge precision is ever needed while matching the spec exactly.

2. **Handling duplicate URLs in same basket**
   - What we know: `UNIQUE(basket_id, product_url)` constraint in DB schema.
   - What's unclear: UX when user tries to add duplicate.
   - Recommendation: Catch `IntegrityError` on duplicate and return a friendly "item already in basket" message. Optionally update quantity instead of rejecting.

## Sources

### Primary (HIGH confidence)
- task.md sections 4.2-4.4, 6.1-6.4 -- Complete DB schemas, command list, URL patterns, validation rules
- `src/price_spy/services/scraper.py` -- Existing URL_PATTERNS, detect_source, SOURCE_TO_BASKET, ScraperService
- `src/price_spy/bot/handlers/start.py` -- Existing handler pattern (Router, InlineKeyboardBuilder, middleware injection)
- `src/price_spy/db/models/user.py` -- Existing model pattern (mapped_column, Base)
- `src/price_spy/db/repositories/user.py` -- Existing repository pattern (session-based, async)
- `src/price_spy/config.py` -- Settings with max_baskets_per_user, max_items_per_basket, price_history_retention_days

### Secondary (MEDIUM confidence)
- [aiogram 3 CallbackData factory docs](https://docs.aiogram.dev/en/latest/dispatcher/filters/callback_data.html) -- CallbackData subclass pattern (verified via mastergroosha guide)
- [aiogram 3 FSM docs](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/index.html) -- StatesGroup usage
- [mastergroosha aiogram 3 buttons guide](https://mastergroosha.github.io/aiogram-3-guide/buttons/) -- CallbackData factory examples verified

### Tertiary (LOW confidence)
- None -- all patterns verified against existing codebase and official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies; all from Phase 1
- Architecture: HIGH -- All patterns directly extend existing Phase 1 code
- Pitfalls: HIGH -- Based on known Telegram Bot API limits and SQLAlchemy patterns
- Code examples: HIGH -- Modeled directly on existing codebase files

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no fast-moving dependencies)
