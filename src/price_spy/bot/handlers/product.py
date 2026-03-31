from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.bot.callbacks.factories import BasketActionCB, ItemCB
from price_spy.bot.keyboards.basket import confirm_remove_item_keyboard
from price_spy.bot.keyboards.pagination import ITEMS_PER_PAGE, items_page_keyboard
from price_spy.bot.states.basket import AddProduct
from price_spy.config import settings
from price_spy.db.models.user import User
from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.db.repositories.price_history import PriceHistoryRepository
from price_spy.i18n import get_text
from price_spy.services.scraper import (
    SOURCE_TO_BASKET,
    ScraperService,
    detect_source,
    extract_product_id,
)

logger = logging.getLogger(__name__)

router = Router(name="product")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_product_lines(text: str) -> list[tuple[str, int]]:
    """Parse message text into list of (url, quantity) tuples.

    Each non-empty line is parsed as: URL [optional quantity].
    If the last token is a positive integer, it is used as quantity.
    Otherwise, the entire line is the URL and quantity defaults to 1.
    """
    results: list[tuple[str, int]] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit(None, 1)
        if len(parts) == 2:
            try:
                qty = int(parts[1])
                if qty > 0:
                    results.append((parts[0], qty))
                    continue
            except ValueError:
                pass
        results.append((line, 1))
    return results


def validate_url_for_basket(url: str, basket_source: str) -> str | None:
    """Validate that a URL is a recognized product link matching the basket source.

    Returns an i18n error key if invalid, or None if valid.
    """
    source = detect_source(url)
    if source is None:
        return "error_invalid_url"
    if SOURCE_TO_BASKET[source] != basket_source:
        return "error_source_mismatch"
    return None


async def _build_items_text(
    items: list[tuple], basket_name: str, lang: str, page: int = 0
) -> str:
    """Build formatted item list text for a given page."""
    if not items:
        return get_text("items_empty", lang)

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]

    lines = [get_text("items_title", lang, name=basket_name)]
    total = Decimal(0)

    for idx, (item, price, original_price, is_available) in enumerate(page_items, start=start + 1):
        name = item.name or item.product_url[:30]
        qty = item.quantity

        if not is_available:
            lines.append(get_text("item_line_unavailable", lang, num=idx, name=name, qty=qty))
        elif price is not None and original_price is not None and original_price != price:
            line_total = price * qty
            total += line_total
            lines.append(get_text(
                "item_line_discount", lang,
                num=idx, name=name, qty=qty,
                price=price, original=original_price, total=line_total,
            ))
        elif price is not None:
            line_total = price * qty
            total += line_total
            lines.append(get_text(
                "item_line", lang,
                num=idx, name=name, qty=qty,
                price=price, total=line_total,
            ))
        else:
            lines.append(get_text("item_line_unavailable", lang, num=idx, name=name, qty=qty))

    # Calculate full total across ALL items (not just current page) for accuracy
    full_total = Decimal(0)
    for item, price, _orig, is_available in items:
        if price is not None and is_available:
            full_total += price * item.quantity

    lines.append("")
    lines.append(get_text("basket_total", lang, total=full_total))
    return "\n".join(lines)


async def _process_urls(
    message: Message,
    session: AsyncSession,
    user: User,
    lang: str,
    basket: object,
    text: str,
) -> None:
    """Shared URL processing logic for both FSM add flow and freeform messages."""
    lines = parse_product_lines(text)
    if not lines:
        return

    status_msg = await message.answer(get_text("adding_products", lang))

    item_repo = BasketItemRepository(session)
    price_repo = PriceHistoryRepository(session)
    result_lines: list[str] = []
    added_items: list[tuple[int, str, int]] = []  # (item_id, url, qty)

    current_count = await item_repo.count_by_basket(basket.id)

    for url, qty in lines:
        # Validate URL
        error_key = validate_url_for_basket(url, basket.source)
        if error_key:
            if error_key == "error_source_mismatch":
                source = detect_source(url)
                result_lines.append(get_text(
                    error_key, lang,
                    source=source, basket=basket.name, basket_source=basket.source,
                ))
            else:
                result_lines.append(get_text(error_key, lang))
            continue

        # Check item limit
        if current_count >= settings.max_items_per_basket:
            result_lines.append(get_text(
                "error_item_limit_reached", lang, max=settings.max_items_per_basket,
            ))
            break

        source = detect_source(url)
        product_id = extract_product_id(url, source) if source else None

        # Create basket item
        try:
            item = await item_repo.create(
                basket_id=basket.id,
                product_url=url,
                product_id=product_id or "",
                url_source=source or "",
                name=None,
                quantity=qty,
            )
            added_items.append((item.id, url, qty))
            current_count += 1
        except IntegrityError:
            await session.rollback()
            result_lines.append(get_text("error_duplicate_item", lang))
            continue

    # Trigger first scrape for successfully added items
    if added_items:
        urls_to_scrape = [url for _, url, _ in added_items]
        scraper = ScraperService(session)
        try:
            scrape_results = await scraper.scrape_urls(urls_to_scrape)

            for (item_id, url, qty), result in zip(added_items, scrape_results):
                if result.ok and result.data:
                    # Update item name
                    await item_repo.update_name(item_id, result.data.name)

                    # Store price history (HIST-01, HIST-02)
                    price_decimal = Decimal(str(result.data.price)) if result.data.price else None
                    original_decimal = (
                        Decimal(str(result.data.original_price))
                        if result.data.original_price
                        else None
                    )
                    await price_repo.create(
                        basket_item_id=item_id,
                        price=price_decimal,
                        original_price=original_decimal,
                        is_available=result.data.is_available,
                    )

                    # Build confirmation line
                    if result.data.price:
                        result_lines.append(get_text(
                            "product_added", lang,
                            name=result.data.name, qty=qty, price=result.data.price,
                        ))
                    else:
                        result_lines.append(get_text(
                            "product_added_no_price", lang,
                            name=result.data.name, qty=qty,
                        ))
                elif result.error:
                    result_lines.append(get_text(
                        "product_add_failed", lang,
                        url=url, reason=result.error,
                    ))
        finally:
            await scraper.close()

    # Edit the status message with results
    if result_lines:
        await status_msg.edit_text("\n".join(result_lines))
    else:
        await status_msg.edit_text(get_text("items_empty", lang))


# ---------------------------------------------------------------------------
# Slash commands: /list, /prices, /remove
# ---------------------------------------------------------------------------


@router.message(Command("list"))
async def cmd_list(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """Show items in the user's active basket."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    basket = await BasketRepository(session).get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("error_no_active_basket", lang))
        return

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_basket_items_with_latest_price(basket.id)

    if not items:
        await message.answer(get_text("items_empty", lang))
        return

    text = await _build_items_text(items, basket.name, lang, page=0)
    item_objects = [row[0] for row in items]
    keyboard = items_page_keyboard(item_objects, basket.id, 0, lang)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("prices"))
async def cmd_prices(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """Show current prices for items in the user's active basket."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    basket = await BasketRepository(session).get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("error_no_active_basket", lang))
        return

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_basket_items_with_latest_price(basket.id)

    if not items:
        await message.answer(get_text("items_empty", lang))
        return

    text = await _build_items_text(items, basket.name, lang, page=0)
    item_objects = [row[0] for row in items]
    keyboard = items_page_keyboard(item_objects, basket.id, 0, lang)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("remove"))
async def cmd_remove(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """Remove an item by number: /remove <number>.

    Shows the item list with remove buttons if no number given.
    """
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    basket = await BasketRepository(session).get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("error_no_active_basket", lang))
        return

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_basket_items_with_latest_price(basket.id)

    if not items:
        await message.answer(get_text("items_empty", lang))
        return

    # Parse optional item number argument
    raw_text = message.text or ""
    parts = raw_text.strip().split(maxsplit=1)

    if len(parts) >= 2:
        try:
            item_index = int(parts[1])
            if item_index < 1 or item_index > len(items):
                await message.answer(get_text("remove_invalid_number", lang, max=len(items)))
                return

            item = items[item_index - 1][0]  # BasketItem from tuple
            name = item.name or item.product_url[:30]
            from price_spy.bot.keyboards.basket import confirm_remove_item_keyboard

            await message.answer(
                get_text("confirm_remove_item", lang, name=name),
                reply_markup=confirm_remove_item_keyboard(basket.id, item.id, lang),
            )
            return
        except ValueError:
            pass

    # No number given: show usage hint + item list with remove buttons
    await message.answer(get_text("remove_usage", lang))
    text = await _build_items_text(items, basket.name, lang, page=0)
    item_objects = [row[0] for row in items]
    keyboard = items_page_keyboard(item_objects, basket.id, 0, lang)
    await message.answer(text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# 1. Callback: add item prompt (enters FSM)
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "add"))
async def callback_add_item_prompt(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    session: AsyncSession,
    lang: str,
    state: FSMContext,
    **kwargs: object,
) -> None:
    item_repo = BasketItemRepository(session)
    count = await item_repo.count_by_basket(callback_data.basket_id)

    if count >= settings.max_items_per_basket:
        await callback.message.answer(
            get_text("error_item_limit_reached", lang, max=settings.max_items_per_basket)
        )
        await callback.answer()
        return

    await state.set_state(AddProduct.waiting_for_urls)
    await state.update_data(basket_id=callback_data.basket_id)
    await callback.message.answer(get_text("send_urls_prompt", lang))
    await callback.answer()


# ---------------------------------------------------------------------------
# 2. FSM: receive product URLs (AddProduct.waiting_for_urls)
# ---------------------------------------------------------------------------
@router.message(AddProduct.waiting_for_urls)
async def receive_product_urls(
    message: Message,
    session: AsyncSession,
    user: User,
    lang: str,
    state: FSMContext,
    **kwargs: object,
) -> None:
    data = await state.get_data()
    basket_id = data["basket_id"]
    await state.clear()

    basket = await BasketRepository(session).get_by_id(basket_id)
    if basket is None:
        await message.answer(get_text("error_no_active_basket", lang))
        return

    await _process_urls(message, session, user, lang, basket, message.text or "")


# ---------------------------------------------------------------------------
# 3. Freeform URL handler (catches URLs outside FSM state)
# ---------------------------------------------------------------------------
@router.message(F.text.regexp(r"https?://"))
async def handle_url_message(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    if user is None:
        return

    basket = await BasketRepository(session).get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("error_no_active_basket", lang))
        return

    await _process_urls(message, session, user, lang, basket, message.text or "")


# ---------------------------------------------------------------------------
# 4. Callback: list items
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "items"))
async def callback_list_items(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    session: AsyncSession,
    lang: str,
    **kwargs: object,
) -> None:
    basket = await BasketRepository(session).get_by_id(callback_data.basket_id)
    if basket is None:
        await callback.answer()
        return

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_basket_items_with_latest_price(callback_data.basket_id)

    if not items:
        await callback.message.edit_text(get_text("items_empty", lang))
        await callback.answer()
        return

    text = await _build_items_text(items, basket.name, lang, page=0)
    # Extract just the BasketItem objects for the keyboard
    item_objects = [row[0] for row in items]
    keyboard = items_page_keyboard(item_objects, callback_data.basket_id, 0, lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ---------------------------------------------------------------------------
# 5. Callback: prices (same display as items)
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "prices"))
async def callback_prices(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    session: AsyncSession,
    lang: str,
    **kwargs: object,
) -> None:
    basket = await BasketRepository(session).get_by_id(callback_data.basket_id)
    if basket is None:
        await callback.answer()
        return

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_basket_items_with_latest_price(callback_data.basket_id)

    if not items:
        await callback.message.edit_text(get_text("items_empty", lang))
        await callback.answer()
        return

    text = await _build_items_text(items, basket.name, lang, page=0)
    item_objects = [row[0] for row in items]
    keyboard = items_page_keyboard(item_objects, callback_data.basket_id, 0, lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ---------------------------------------------------------------------------
# 6. Callback: page navigation
# ---------------------------------------------------------------------------
@router.callback_query(ItemCB.filter(F.action == "page"))
async def callback_page(
    callback: CallbackQuery,
    callback_data: ItemCB,
    session: AsyncSession,
    lang: str,
    **kwargs: object,
) -> None:
    basket = await BasketRepository(session).get_by_id(callback_data.basket_id)
    if basket is None:
        await callback.answer()
        return

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_basket_items_with_latest_price(callback_data.basket_id)

    page = callback_data.page
    text = await _build_items_text(items, basket.name, lang, page=page)
    item_objects = [row[0] for row in items]
    keyboard = items_page_keyboard(item_objects, callback_data.basket_id, page, lang)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ---------------------------------------------------------------------------
# 7. Callback: remove item (show confirmation)
# ---------------------------------------------------------------------------
@router.callback_query(ItemCB.filter(F.action == "remove"))
async def callback_remove_item(
    callback: CallbackQuery,
    callback_data: ItemCB,
    session: AsyncSession,
    lang: str,
    **kwargs: object,
) -> None:
    item_repo = BasketItemRepository(session)
    item = await item_repo.get_by_id(callback_data.item_id)
    name = item.name if item else "Unknown"

    await callback.message.edit_text(
        get_text("confirm_remove_item", lang, name=name),
        reply_markup=confirm_remove_item_keyboard(
            callback_data.basket_id, callback_data.item_id, lang
        ),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# 8. Callback: confirm remove
# ---------------------------------------------------------------------------
@router.callback_query(ItemCB.filter(F.action == "confirm_remove"))
async def callback_confirm_remove(
    callback: CallbackQuery,
    callback_data: ItemCB,
    session: AsyncSession,
    lang: str,
    **kwargs: object,
) -> None:
    item_repo = BasketItemRepository(session)
    item = await item_repo.get_by_id(callback_data.item_id)
    name = item.name if item else "Unknown"

    await item_repo.delete(callback_data.item_id)

    await callback.message.edit_text(get_text("item_removed", lang, name=name))
    await callback.answer()
