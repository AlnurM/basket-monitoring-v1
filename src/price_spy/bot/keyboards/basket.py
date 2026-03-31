from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from price_spy.bot.callbacks.factories import BasketActionCB, BasketCB, ItemCB
from price_spy.i18n import get_text

if TYPE_CHECKING:
    from price_spy.db.models.basket import Basket


def basket_list_keyboard(
    baskets: list[tuple[Basket, int]], lang: str
) -> InlineKeyboardMarkup:
    """Build keyboard listing all user baskets with item counts.

    Each basket button shows: active marker + name + source + item count.
    Plus a "+ New Basket" button at the bottom.
    """
    builder = InlineKeyboardBuilder()
    for basket, item_count in baskets:
        active_marker = ">> " if basket.is_active else "   "
        label = get_text(
            "basket_line",
            lang,
            active=active_marker,
            name=basket.name,
            source=basket.source.capitalize(),
            count=item_count,
        )
        builder.button(
            text=label,
            callback_data=BasketCB(action="view", basket_id=basket.id),
        )
    builder.button(
        text=get_text("btn_new_basket", lang),
        callback_data=BasketCB(action="new"),
    )
    builder.adjust(1)
    return builder.as_markup()


def basket_actions_keyboard(
    basket_id: int, lang: str
) -> InlineKeyboardMarkup:
    """Build action buttons for a specific basket.

    Layout per D-03:
      Row 1: Items | Prices | Charts
      Row 2: Add   | Edit   | Delete
      Row 3: < Back
    """
    builder = InlineKeyboardBuilder()
    # Row 1
    builder.button(
        text=get_text("btn_list_items", lang),
        callback_data=BasketActionCB(action="items", basket_id=basket_id),
    )
    builder.button(
        text=get_text("btn_prices", lang),
        callback_data=BasketActionCB(action="prices", basket_id=basket_id),
    )
    builder.button(
        text=get_text("btn_charts", lang),
        callback_data=BasketActionCB(action="charts", basket_id=basket_id),
    )
    # Row 2
    builder.button(
        text=get_text("btn_add_item", lang),
        callback_data=BasketActionCB(action="add", basket_id=basket_id),
    )
    builder.button(
        text=get_text("btn_edit", lang),
        callback_data=BasketActionCB(action="edit", basket_id=basket_id),
    )
    builder.button(
        text=get_text("btn_delete_basket", lang),
        callback_data=BasketActionCB(action="delete", basket_id=basket_id),
    )
    # Row 3
    builder.button(
        text=get_text("btn_back", lang),
        callback_data=BasketActionCB(action="back", basket_id=basket_id),
    )
    builder.adjust(3, 3, 1)
    return builder.as_markup()


def confirm_delete_keyboard(
    basket_id: int, lang: str
) -> InlineKeyboardMarkup:
    """Yes/No confirmation for basket deletion."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_yes_delete", lang),
        callback_data=BasketActionCB(
            action="confirm_delete", basket_id=basket_id
        ),
    )
    builder.button(
        text=get_text("btn_no_cancel", lang),
        callback_data=BasketCB(action="view", basket_id=basket_id),
    )
    builder.adjust(2)
    return builder.as_markup()


def source_selection_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Two buttons: Arbuz and Magnum source selection."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Arbuz",
        callback_data=BasketCB(action="set_source", source="arbuz"),
    )
    builder.button(
        text="Magnum",
        callback_data=BasketCB(action="set_source", source="magnum"),
    )
    builder.adjust(2)
    return builder.as_markup()


def confirm_remove_item_keyboard(
    basket_id: int, item_id: int, lang: str
) -> InlineKeyboardMarkup:
    """Yes/No confirmation for item removal."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=get_text("btn_yes_delete", lang),
        callback_data=ItemCB(
            action="confirm_remove", basket_id=basket_id, item_id=item_id
        ),
    )
    builder.button(
        text=get_text("btn_no_cancel", lang),
        callback_data=BasketActionCB(action="items", basket_id=basket_id),
    )
    builder.adjust(2)
    return builder.as_markup()
