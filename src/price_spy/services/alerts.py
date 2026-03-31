"""Price drop alert service.

Detects >10% price drops after daily scrape and sends batched
per-user bilingual notifications. Per D-11, D-12, D-13 / ALRT-01..02.
"""

import asyncio
import datetime
import logging
from decimal import Decimal

from price_spy.db.engine import async_session
from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.db.repositories.price_history import PriceHistoryRepository
from price_spy.db.repositories.user import UserRepository

logger = logging.getLogger(__name__)

# Bilingual alert strings per D-12 / ALRT-02.
ALERT_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "alert_price_drop": (
            "\U0001f7e2 {name} подешевел(а) на {pct}%: {old} \u20b8 \u2192 {new} \u20b8"
        ),
        "alert_header": "\U0001f514 Уведомления о ценах",
    },
    "en": {
        "alert_price_drop": (
            "\U0001f7e2 {name} dropped by {pct}%: {old} \u20b8 \u2192 {new} \u20b8"
        ),
        "alert_header": "\U0001f514 Price alerts",
    },
}


def _get_str(lang: str, key: str) -> str:
    """Get an alert string for the given language, falling back to English."""
    strings = ALERT_STRINGS.get(lang, ALERT_STRINGS["en"])
    return strings.get(key, ALERT_STRINGS["en"].get(key, key))


def _format_number(value: Decimal | int) -> str:
    """Format a number with space as thousands separator."""
    n = int(value)
    return f"{n:,}".replace(",", " ")


async def check_and_send_alerts(bot: object) -> None:
    """Check for >10% price drops and send batched alerts per user.

    Opens its own async_session (self-managed pattern, same as daily_scrape
    and deliver_reports). Called from scheduler after daily scrape.

    Args:
        bot: aiogram Bot instance for sending messages.
    """
    import zoneinfo

    from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    today_start = datetime.datetime.combine(now.date(), datetime.time.min, tzinfo=tz)

    alert_count = 0

    async with async_session() as session:
        basket_repo = BasketRepository(session)
        item_repo = BasketItemRepository(session)
        price_repo = PriceHistoryRepository(session)
        user_repo = UserRepository(session)

        baskets = await basket_repo.get_all_active_baskets()
        if not baskets:
            logger.info("No baskets for alert check")
            return

        # Group baskets by user_id
        user_baskets: dict[int, list] = {}
        for basket in baskets:
            user_baskets.setdefault(basket.user_id, []).append(basket)

        for user_id, baskets_for_user in user_baskets.items():
            # Collect all item IDs across user's baskets
            all_items = []
            for basket in baskets_for_user:
                items = await item_repo.get_items_by_basket(basket.id)
                all_items.extend(items)

            if not all_items:
                continue

            item_ids = [item.id for item in all_items]
            item_map = {item.id: item for item in all_items}

            # Get previous prices (before today)
            previous_prices = await price_repo.get_previous_prices(
                item_ids, today_start,
            )

            # Get today's latest prices
            today_records = await price_repo.get_price_range(
                item_ids, today_start, now,
            )

            # Build today's latest price per item (last record wins)
            today_prices: dict[int, Decimal] = {}
            for rec in today_records:
                if rec.price is not None:
                    today_prices[rec.basket_item_id] = rec.price

            # Detect >10% drops (per D-11 / ALRT-01)
            alerts: list[str] = []
            # Get user language for formatting (need user object)
            # Fetch once and use for all alert lines
            user = None

            for item_id, new_price in today_prices.items():
                prev = previous_prices.get(item_id)
                if prev is None:
                    continue
                old_price, _old_available = prev
                if old_price is None or old_price == 0:
                    continue

                # Check if new price is more than 10% lower
                if new_price < old_price * Decimal("0.9"):
                    drop_pct = (
                        (old_price - new_price) / old_price * 100
                    ).quantize(Decimal("0.1"))
                    item = item_map.get(item_id)
                    item_name = (item.name if item and item.name else f"Item #{item_id}")

                    if user is None:
                        # Lazy-load user for language
                        from price_spy.db.models.user import User
                        from sqlalchemy import select

                        stmt = select(User).where(User.id == user_id)
                        result = await session.execute(stmt)
                        user = result.scalar_one_or_none()

                    lang = user.language if user else "en"
                    alert_line = _get_str(lang, "alert_price_drop").format(
                        name=item_name,
                        pct=drop_pct,
                        old=_format_number(old_price),
                        new=_format_number(new_price),
                    )
                    alerts.append(alert_line)

            if not alerts:
                continue

            # Send batched alert message
            lang = user.language if user else "en"
            header = _get_str(lang, "alert_header")
            message = header + "\n\n" + "\n".join(alerts)

            telegram_id = user.telegram_id if user else None
            if telegram_id is None:
                continue

            try:
                await bot.send_message(chat_id=telegram_id, text=message)  # type: ignore[union-attr]
                alert_count += len(alerts)
            except TelegramForbiddenError:
                logger.warning(
                    "User %d blocked bot, skipping alerts", telegram_id,
                )
            except TelegramRetryAfter as e:
                logger.warning("Rate limited, sleeping %ds", e.retry_after)
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(chat_id=telegram_id, text=message)  # type: ignore[union-attr]
                    alert_count += len(alerts)
                except Exception:
                    logger.exception(
                        "Failed to send alerts to user %d after retry",
                        telegram_id,
                    )
            except Exception:
                logger.exception(
                    "Failed to send alerts to user %d", telegram_id,
                )

            # Flood control: 1s between users (same as deliver_reports)
            await asyncio.sleep(1)

    logger.info("Alert check complete: %d alerts sent", alert_count)
