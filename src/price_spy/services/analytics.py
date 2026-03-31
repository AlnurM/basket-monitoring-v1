"""Analytics service for price change tracking.

Generates /changes reports grouping items into increased/decreased/unchanged/unavailable
categories with percentage changes over a configurable number of days.
"""

import datetime
import zoneinfo
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.db.repositories.price_history import PriceHistoryRepository

ANALYTICS_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "changes_title": "\U0001f4c8 \u0418\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0446\u0435\u043d \u0437\u0430 {days} \u0434\u043d\u0435\u0439",
        "price_increased_header": "\U0001f534 \u041f\u043e\u0434\u043e\u0440\u043e\u0436\u0430\u043b\u0438:",
        "price_decreased_header": "\U0001f7e2 \u041f\u043e\u0434\u0435\u0448\u0435\u0432\u0435\u043b\u0438:",
        "unchanged_header": "\u26aa \u0411\u0435\u0437 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439: {count} \u0442\u043e\u0432\u0430\u0440\u043e\u0432",
        "unavailable_header": "\U0001f534 \u041f\u0440\u043e\u043f\u0430\u043b\u0438 \u0438\u0437 \u043d\u0430\u043b\u0438\u0447\u0438\u044f:",
        "restored_header": "\U0001f7e2 \u0412\u0435\u0440\u043d\u0443\u043b\u0438\u0441\u044c \u0432 \u043d\u0430\u043b\u0438\u0447\u0438\u0435:",
        "changes_no_baskets": "\u041d\u0435\u0442 \u043a\u043e\u0440\u0437\u0438\u043d.",
        "changes_no_data": "\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u0434\u0430\u043d\u043d\u044b\u0445.",
    },
    "en": {
        "changes_title": "\U0001f4c8 Price changes over {days} days",
        "price_increased_header": "\U0001f534 Price increased:",
        "price_decreased_header": "\U0001f7e2 Price decreased:",
        "unchanged_header": "\u26aa Unchanged: {count} items",
        "unavailable_header": "\U0001f534 Became unavailable:",
        "restored_header": "\U0001f7e2 Restored availability:",
        "changes_no_baskets": "No baskets.",
        "changes_no_data": "Not enough data.",
    },
}


def _get_str(lang: str, key: str) -> str:
    """Get an analytics string for the given language, falling back to English."""
    strings = ANALYTICS_STRINGS.get(lang, ANALYTICS_STRINGS["en"])
    return strings.get(key, ANALYTICS_STRINGS["en"].get(key, key))


def _format_number(value: Decimal | int) -> str:
    """Format a number with space as thousands separator (e.g. 28 450)."""
    n = int(value)
    return f"{n:,}".replace(",", " ")


async def generate_changes_report(
    session: AsyncSession,
    user_id: int,
    days: int,
    lang: str,
) -> str | None:
    """Generate a price changes report for the user's active basket.

    Groups items into increased/decreased/unchanged/unavailable categories
    comparing first price in range vs latest price.

    Returns formatted report string, or None if no basket/items.
    """
    basket_repo = BasketRepository(session)
    basket = await basket_repo.get_active_basket(user_id)
    if not basket:
        return None

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_items_by_basket(basket.id)
    if not items:
        return None

    item_ids = [item.id for item in items]
    item_names = {item.id: (item.name or f"Item #{item.id}") for item in items}

    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    start_date = now - datetime.timedelta(days=days)

    price_repo = PriceHistoryRepository(session)
    first_prices = await price_repo.get_first_prices_in_range(item_ids, start_date)
    latest_prices = await price_repo.get_previous_prices(item_ids, now + datetime.timedelta(seconds=1))

    if not first_prices and not latest_prices:
        return _get_str(lang, "changes_no_data")

    # Categorize items
    increased: list[tuple[str, Decimal, Decimal, Decimal]] = []  # name, old, new, pct
    decreased: list[tuple[str, Decimal, Decimal, Decimal]] = []
    unchanged: list[str] = []
    unavailable: list[str] = []
    restored: list[str] = []

    for item_id in item_ids:
        name = item_names[item_id]
        first = first_prices.get(item_id)
        latest = latest_prices.get(item_id)

        if first is None or latest is None:
            continue

        first_price, first_avail = first
        latest_price, latest_avail = latest

        # Check availability changes
        if first_avail and not latest_avail:
            unavailable.append(name)
            continue
        if not first_avail and latest_avail:
            restored.append(name)

        # Compare prices (skip if either is None)
        if first_price is None or latest_price is None:
            unchanged.append(name)
            continue

        if latest_price > first_price:
            pct = ((latest_price - first_price) / first_price * 100).quantize(Decimal("0.1"))
            increased.append((name, first_price, latest_price, pct))
        elif latest_price < first_price:
            pct = ((first_price - latest_price) / first_price * 100).quantize(Decimal("0.1"))
            decreased.append((name, first_price, latest_price, pct))
        else:
            unchanged.append(name)

    # Build report
    lines: list[str] = [_get_str(lang, "changes_title").format(days=days), ""]

    if increased:
        lines.append(_get_str(lang, "price_increased_header"))
        for name, old, new, pct in increased:
            lines.append(f"  \u2022 {name}: {_format_number(old)} \u20b8 \u2192 {_format_number(new)} \u20b8 (+{pct}%)")
        lines.append("")

    if decreased:
        lines.append(_get_str(lang, "price_decreased_header"))
        for name, old, new, pct in decreased:
            lines.append(f"  \u2022 {name}: {_format_number(old)} \u20b8 \u2192 {_format_number(new)} \u20b8 (-{pct}%)")
        lines.append("")

    if unchanged:
        lines.append(_get_str(lang, "unchanged_header").format(count=len(unchanged)))

    if unavailable:
        lines.append(_get_str(lang, "unavailable_header"))
        for name in unavailable:
            lines.append(f"  \u2022 {name}")

    if restored:
        lines.append(_get_str(lang, "restored_header"))
        for name in restored:
            lines.append(f"  \u2022 {name}")

    return "\n".join(lines)
