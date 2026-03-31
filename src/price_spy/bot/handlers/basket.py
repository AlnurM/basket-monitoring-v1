from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.bot.callbacks.factories import BasketActionCB, BasketCB
from price_spy.bot.keyboards.basket import (
    basket_actions_keyboard,
    basket_list_keyboard,
    confirm_delete_keyboard,
    source_selection_keyboard,
)
from price_spy.bot.states.basket import CreateBasket
from price_spy.config import settings
from price_spy.db.models.user import User
from price_spy.db.repositories.basket import BasketRepository
from price_spy.i18n import get_text

router = Router(name="basket")

MAX_BASKET_NAME_LEN = 50


def _language_keyboard():  # type: ignore[no-untyped-def]
    """Inline language selection (mirrors start.py helper)."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="Русский", callback_data="lang:ru")
    builder.button(text="English", callback_data="lang:en")
    builder.adjust(2)
    return builder


# ---------------------------------------------------------------------------
# 1. /baskets command
# ---------------------------------------------------------------------------
@router.message(Command("baskets"))
async def cmd_baskets(
    message: Message, session: AsyncSession, user: User | None, lang: str, **kwargs: object
) -> None:
    if user is None:
        kb = _language_keyboard()
        await message.answer(get_text("choose_language", lang), reply_markup=kb.as_markup())
        return

    repo = BasketRepository(session)
    baskets_with_counts = await repo.get_user_baskets_with_item_counts(user.id)

    if not baskets_with_counts:
        await message.answer(
            get_text("baskets_empty", lang),
            reply_markup=basket_list_keyboard([], lang),
        )
    else:
        await message.answer(
            get_text("baskets_title", lang),
            reply_markup=basket_list_keyboard(baskets_with_counts, lang),
        )


# ---------------------------------------------------------------------------
# 2. /new_basket command
# ---------------------------------------------------------------------------
@router.message(Command("new_basket"))
async def cmd_new_basket(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    state: FSMContext,
    **kwargs: object,
) -> None:
    if user is None:
        kb = _language_keyboard()
        await message.answer(get_text("choose_language", lang), reply_markup=kb.as_markup())
        return

    repo = BasketRepository(session)
    count = await repo.count_by_user(user.id)
    if count >= settings.max_baskets_per_user:
        await message.answer(
            get_text("basket_limit_reached", lang, max=settings.max_baskets_per_user)
        )
        return

    await state.set_state(CreateBasket.waiting_for_name)
    await message.answer(get_text("enter_basket_name", lang))


# ---------------------------------------------------------------------------
# 3. FSM: receive basket name
# ---------------------------------------------------------------------------
@router.message(CreateBasket.waiting_for_name)
async def receive_basket_name(
    message: Message, lang: str, state: FSMContext, **kwargs: object
) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > MAX_BASKET_NAME_LEN:
        await message.answer(get_text("enter_basket_name", lang))
        return

    await state.update_data(name=name)
    await message.answer(
        get_text("choose_source", lang),
        reply_markup=source_selection_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# 4. Callback: set source (completes basket creation)
# ---------------------------------------------------------------------------
@router.callback_query(BasketCB.filter(F.action == "set_source"))
async def callback_set_source(
    callback: CallbackQuery,
    callback_data: BasketCB,
    session: AsyncSession,
    user: User | None,
    lang: str,
    state: FSMContext,
    **kwargs: object,
) -> None:
    source = callback_data.source
    data = await state.get_data()
    name = data.get("name")
    await state.clear()

    if not name or user is None:
        await callback.answer(get_text("please_select_language", lang), show_alert=True)
        return

    repo = BasketRepository(session)
    count = await repo.count_by_user(user.id)
    if count >= settings.max_baskets_per_user:
        await callback.answer(
            get_text("basket_limit_reached", lang, max=settings.max_baskets_per_user),
            show_alert=True,
        )
        return

    basket = await repo.create(user.id, name, source)
    await repo.set_active(user.id, basket.id)

    await callback.message.edit_text(
        get_text("basket_created", lang, name=name, source=source.capitalize())
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# 5. Callback: basket list (inline refresh)
# ---------------------------------------------------------------------------
@router.callback_query(BasketCB.filter(F.action == "list"))
async def callback_basket_list(
    callback: CallbackQuery,
    callback_data: BasketCB,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    if user is None:
        await callback.answer()
        return

    repo = BasketRepository(session)
    baskets_with_counts = await repo.get_user_baskets_with_item_counts(user.id)

    text = get_text("baskets_empty", lang) if not baskets_with_counts else get_text("baskets_title", lang)
    await callback.message.edit_text(
        text,
        reply_markup=basket_list_keyboard(baskets_with_counts, lang),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# 6. Callback: view basket (sets active + shows action buttons)
# ---------------------------------------------------------------------------
@router.callback_query(BasketCB.filter(F.action == "view"))
async def callback_view_basket(
    callback: CallbackQuery,
    callback_data: BasketCB,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    if user is None:
        await callback.answer()
        return

    repo = BasketRepository(session)
    basket = await repo.get_by_id(callback_data.basket_id)
    if basket is None:
        await callback.answer(get_text("baskets_empty", lang), show_alert=True)
        return

    await repo.set_active(user.id, basket.id)

    await callback.message.edit_text(
        get_text("basket_activated", lang, name=basket.name),
        reply_markup=basket_actions_keyboard(basket.id, lang),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# 7. Callback: new basket (inline button version)
# ---------------------------------------------------------------------------
@router.callback_query(BasketCB.filter(F.action == "new"))
async def callback_new_basket(
    callback: CallbackQuery,
    callback_data: BasketCB,
    session: AsyncSession,
    user: User | None,
    lang: str,
    state: FSMContext,
    **kwargs: object,
) -> None:
    if user is None:
        await callback.answer()
        return

    repo = BasketRepository(session)
    count = await repo.count_by_user(user.id)
    if count >= settings.max_baskets_per_user:
        await callback.answer(
            get_text("basket_limit_reached", lang, max=settings.max_baskets_per_user),
            show_alert=True,
        )
        return

    await state.set_state(CreateBasket.waiting_for_name)
    await callback.message.answer(get_text("enter_basket_name", lang))
    await callback.answer()


# ---------------------------------------------------------------------------
# 8. Callback: delete basket (show confirmation)
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "delete"))
async def callback_delete_basket(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    session: AsyncSession,
    lang: str,
    **kwargs: object,
) -> None:
    repo = BasketRepository(session)
    basket = await repo.get_by_id(callback_data.basket_id)
    if basket is None:
        await callback.answer(get_text("baskets_empty", lang), show_alert=True)
        return

    await callback.message.edit_text(
        get_text("confirm_delete_basket", lang, name=basket.name),
        reply_markup=confirm_delete_keyboard(basket.id, lang),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# 9. Callback: confirm delete
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "confirm_delete"))
async def callback_confirm_delete(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    session: AsyncSession,
    lang: str,
    **kwargs: object,
) -> None:
    repo = BasketRepository(session)
    basket = await repo.get_by_id(callback_data.basket_id)
    if basket is None:
        await callback.answer(get_text("baskets_empty", lang), show_alert=True)
        return

    basket_name = basket.name
    await repo.delete(basket.id)

    await callback.message.edit_text(get_text("basket_deleted", lang, name=basket_name))
    await callback.answer()


# ---------------------------------------------------------------------------
# 10. Callback: back to basket list
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "back"))
async def callback_basket_back(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    if user is None:
        await callback.answer()
        return

    repo = BasketRepository(session)
    baskets_with_counts = await repo.get_user_baskets_with_item_counts(user.id)

    text = get_text("baskets_empty", lang) if not baskets_with_counts else get_text("baskets_title", lang)
    await callback.message.edit_text(
        text,
        reply_markup=basket_list_keyboard(baskets_with_counts, lang),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# 11. Callback: charts stub (Phase 4)
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "charts"))
async def callback_charts_stub(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    lang: str,
    **kwargs: object,
) -> None:
    await callback.answer(get_text("charts_coming_soon", lang), show_alert=True)


# ---------------------------------------------------------------------------
# 12. Callback: edit stub
# ---------------------------------------------------------------------------
@router.callback_query(BasketActionCB.filter(F.action == "edit"))
async def callback_edit_stub(
    callback: CallbackQuery,
    callback_data: BasketActionCB,
    lang: str,
    **kwargs: object,
) -> None:
    await callback.answer(get_text("edit_quantity_prompt", lang, name="..."), show_alert=True)
