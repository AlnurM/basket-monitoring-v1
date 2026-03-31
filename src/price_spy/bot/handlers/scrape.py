"""Scrape handler: /scrape command for manual price scraping with rate limiting."""

import time as time_module

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.user import User
from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.i18n import get_text

router = Router(name="scrape")

# In-memory rate limiting (per D-13)
_last_scrape: dict[int, float] = {}
SCRAPE_COOLDOWN = 3600  # 1 hour in seconds


def _check_rate_limit(user_id: int) -> int | None:
    """Returns remaining minutes if rate-limited, None if allowed."""
    last = _last_scrape.get(user_id)
    if last is None:
        return None
    elapsed = time_module.time() - last
    if elapsed < SCRAPE_COOLDOWN:
        return int((SCRAPE_COOLDOWN - elapsed) / 60) + 1
    return None


def _record_scrape(user_id: int) -> None:
    _last_scrape[user_id] = time_module.time()


@router.message(Command("scrape"))
async def cmd_scrape(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """MSCR-01..03: Manual scrape with rate limiting and progress feedback."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    # Check rate limit
    remaining = _check_rate_limit(user.id)
    if remaining is not None:
        await message.answer(
            get_text("scrape_rate_limited", lang, minutes=remaining)
        )
        return

    # Get active basket
    basket_repo = BasketRepository(session)
    basket = await basket_repo.get_active_basket(user.id)
    if basket is None:
        await message.answer(get_text("scrape_no_active_basket", lang))
        return

    # Get items
    item_repo = BasketItemRepository(session)
    items = await item_repo.get_items_by_basket(basket.id)
    if not items:
        await message.answer(get_text("scrape_empty_basket", lang))
        return

    # Send progress message (D-14)
    progress_msg = await message.answer(
        get_text("scrape_starting", lang, count=len(items))
    )

    # Record scrape time (before actual scrape to prevent double-triggering)
    _record_scrape(user.id)

    # Build URL-to-name mapping for result display
    url_to_name: dict[str, str] = {}
    for item in items:
        url_to_name[item.product_url] = item.name or item.product_url[:40]

    # Scrape
    from price_spy.services.daily_scrape import scrape_single_basket

    results = await scrape_single_basket(basket.id)

    # Build results text
    result_lines: list[str] = []
    for result in results:
        name = url_to_name.get(result.url, result.url[:40])
        if result.ok and result.data is not None:
            if result.data.name:
                name = result.data.name
            if result.data.is_available:
                result_lines.append(
                    get_text(
                        "scrape_item_ok",
                        lang,
                        name=name,
                        price=result.data.price,
                    )
                )
            else:
                result_lines.append(
                    get_text("scrape_item_unavailable", lang, name=name)
                )
        else:
            result_lines.append(get_text("scrape_item_fail", lang, name=name))

    results_text = "\n".join(result_lines) if result_lines else ""

    # Edit progress message with results
    await progress_msg.edit_text(
        get_text("scrape_complete", lang, results=results_text)
    )
