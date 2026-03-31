"""Analytics handlers: /changes, /compare, /chart, /chart_item, /export commands."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.user import User
from price_spy.db.repositories.basket import BasketRepository
from price_spy.i18n import get_text
from price_spy.services.message_utils import split_message

logger = logging.getLogger(__name__)

router = Router(name="analytics")


@router.message(Command("changes"))
async def cmd_changes(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """ANLT-01: Price changes report over N days."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    # Parse optional days argument (default 7, clamp 1-90)
    days = 7
    raw_text = message.text or ""
    parts = raw_text.strip().split(maxsplit=1)
    if len(parts) > 1:
        try:
            days = int(parts[1])
            if days < 1 or days > 90:
                days = max(1, min(90, days))
        except ValueError:
            await message.answer(get_text("changes_invalid_days", lang))
            return

    from price_spy.services.analytics import generate_changes_report

    report = await generate_changes_report(session, user.id, days, lang)
    if report is None:
        await message.answer(get_text("changes_no_data", lang))
        return

    for part in split_message(report):
        await message.answer(part)


@router.message(Command("compare"))
async def cmd_compare(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """ANLT-03: Cross-store comparison report."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    from price_spy.services.comparison import generate_comparison_report

    report = await generate_comparison_report(session, user.id, lang)
    if report is None:
        await message.answer(get_text("compare_no_data", lang))
        return

    for part in split_message(report):
        await message.answer(part)


@router.message(Command("chart"))
async def cmd_chart(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """CHRT-01: Basket total price chart."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    basket_repo = BasketRepository(session)
    basket = await basket_repo.get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("chart_no_active_basket", lang))
        return

    # Parse optional days argument (default 30, clamp 7-90)
    days = 30
    raw_text = message.text or ""
    parts = raw_text.strip().split(maxsplit=1)
    if len(parts) > 1:
        try:
            days = int(parts[1])
            days = max(7, min(90, days))
        except ValueError:
            pass

    await message.answer(get_text("chart_generating", lang))

    from price_spy.services.charts import generate_basket_chart

    chart_bytes = await generate_basket_chart(
        session, basket.id, basket.name, days, lang
    )
    if chart_bytes is None:
        await message.answer(get_text("chart_no_data", lang))
        return

    photo = BufferedInputFile(chart_bytes, filename="chart.png")
    await message.answer_photo(photo=photo)


@router.message(Command("chart_item"))
async def cmd_chart_item(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """CHRT-02: Individual item price chart."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    basket_repo = BasketRepository(session)
    basket = await basket_repo.get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("chart_no_active_basket", lang))
        return

    # Parse args: first arg is item index (required, 1-based), second is days (optional)
    raw_text = message.text or ""
    parts = raw_text.strip().split()
    # parts[0] is "/chart_item", parts[1] is index, parts[2] is optional days

    if len(parts) < 2:
        await message.answer(get_text("chart_item_usage", lang))
        return

    try:
        item_index = int(parts[1])
        if item_index < 1:
            await message.answer(get_text("chart_item_invalid", lang))
            return
    except ValueError:
        await message.answer(get_text("chart_item_invalid", lang))
        return

    days = 30
    if len(parts) >= 3:
        try:
            days = int(parts[2])
            days = max(7, min(90, days))
        except ValueError:
            pass

    await message.answer(get_text("chart_generating", lang))

    from price_spy.services.charts import generate_item_chart

    chart_bytes, error_msg = await generate_item_chart(
        session, basket.id, item_index, days, lang
    )
    if chart_bytes is None:
        await message.answer(error_msg or get_text("chart_no_data", lang))
        return

    photo = BufferedInputFile(chart_bytes, filename="chart_item.png")
    await message.answer_photo(photo=photo)


@router.message(Command("export"))
async def cmd_export(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """EXPT-01: CSV export of basket price history."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    basket_repo = BasketRepository(session)
    basket = await basket_repo.get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("chart_no_active_basket", lang))
        return

    await message.answer(get_text("export_generating", lang))

    from price_spy.services.export import generate_export

    csv_bytes = await generate_export(
        session, basket.id, basket.name, basket.source, lang
    )
    if csv_bytes is None:
        await message.answer(get_text("export_no_data", lang))
        return

    doc = BufferedInputFile(csv_bytes, filename=f"{basket.name}_prices.csv")
    await message.answer_document(document=doc)
