from __future__ import annotations

import math
from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from price_spy.bot.callbacks.factories import BasketActionCB, ItemCB
from price_spy.i18n import get_text

if TYPE_CHECKING:
    from price_spy.db.models.basket_item import BasketItem

ITEMS_PER_PAGE = 10


def items_page_keyboard(
    items: list[BasketItem],
    basket_id: int,
    page: int,
    lang: str,
) -> InlineKeyboardMarkup:
    """Build paginated item list with remove buttons and navigation.

    Shows up to ITEMS_PER_PAGE items per page with a remove button each,
    plus prev/next navigation and a back-to-basket button.
    """
    total_pages = max(1, math.ceil(len(items) / ITEMS_PER_PAGE))
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]

    builder = InlineKeyboardBuilder()

    # Item remove buttons (one per row)
    for item in page_items:
        label = item.name or item.product_url[:30]
        builder.button(
            text=f"X  {label}",
            callback_data=ItemCB(
                action="remove", basket_id=basket_id, item_id=item.id
            ),
        )

    # Navigation row
    nav_buttons = 0
    if page > 0:
        builder.button(
            text=get_text("btn_prev", lang),
            callback_data=ItemCB(
                action="page", basket_id=basket_id, page=page - 1
            ),
        )
        nav_buttons += 1

    if total_pages > 1:
        builder.button(
            text=get_text("page_indicator", lang, current=page + 1, total=total_pages),
            callback_data=ItemCB(
                action="page", basket_id=basket_id, page=page
            ),
        )
        nav_buttons += 1

    if page < total_pages - 1:
        builder.button(
            text=get_text("btn_next", lang),
            callback_data=ItemCB(
                action="page", basket_id=basket_id, page=page + 1
            ),
        )
        nav_buttons += 1

    # Back button
    builder.button(
        text=get_text("btn_back", lang),
        callback_data=BasketActionCB(action="back", basket_id=basket_id),
    )

    # Adjust: one button per item row, then nav row, then back row
    row_sizes = [1] * len(page_items)
    if nav_buttons > 0:
        row_sizes.append(nav_buttons)
    row_sizes.append(1)  # back button
    builder.adjust(*row_sizes)

    return builder.as_markup()
