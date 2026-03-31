"""Report generation service.

Generates per-user daily reports matching task.md section 7.1 format.
Includes price change highlighting and out-of-stock markers.
"""

import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.basket import Basket
from price_spy.db.models.user import User
from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.db.repositories.price_history import PriceHistoryRepository

SEPARATOR = "\u2501" * 23  # "━" * 23

# Report-specific strings keyed by language.
# Defined locally to avoid touching i18n files in this plan.
REPORT_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "report_title": "\U0001f4ca \u041e\u0442\u0447\u0451\u0442 \u0437\u0430 {date}",
        "basket_header": "\U0001f6d2 {name} ({source}) \u2014 {count} \u0442\u043e\u0432\u0430\u0440(\u043e\u0432)",
        "item_price": "\U0001f4b0 {price} \u20b8 \u2192 {total} \u20b8",
        "price_decreased": "\u2b07\ufe0f -{delta} \u20b8 (\u0431\u044b\u043b\u043e {old} \u20b8)",
        "price_increased": "\u2b06\ufe0f +{delta} \u20b8 (\u0431\u044b\u043b\u043e {old} \u20b8)",
        "out_of_stock": "\U0001f534 \u041d\u0435\u0442 \u0432 \u043d\u0430\u043b\u0438\u0447\u0438\u0438!",
        "basket_total": "\U0001f4b5 \u0418\u0422\u041e\u0413\u041e: {total} \u20b8",
        "yesterday_comparison": "(\u0432\u0447\u0435\u0440\u0430: {yesterday} \u20b8, {delta})",
        "no_change": "\u0431\u0435\u0437 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439",
        "comparison_header": "\U0001f4ca \u0421\u0420\u0410\u0412\u041d\u0415\u041d\u0418\u0415:",
        "cheaper_note": "\U0001f4a1 {store} \u0434\u0435\u0448\u0435\u0432\u043b\u0435 \u043d\u0430 {delta} \u20b8 ({pct}%)",
        "same_price": "\U0001f4a1 \u0426\u0435\u043d\u044b \u043e\u0434\u0438\u043d\u0430\u043a\u043e\u0432\u044b\u0435",
    },
    "en": {
        "report_title": "\U0001f4ca Report for {date}",
        "basket_header": "\U0001f6d2 {name} ({source}) \u2014 {count} item(s)",
        "item_price": "\U0001f4b0 {price} \u20b8 \u2192 {total} \u20b8",
        "price_decreased": "\u2b07\ufe0f -{delta} \u20b8 (was {old} \u20b8)",
        "price_increased": "\u2b06\ufe0f +{delta} \u20b8 (was {old} \u20b8)",
        "out_of_stock": "\U0001f534 Out of stock!",
        "basket_total": "\U0001f4b5 TOTAL: {total} \u20b8",
        "yesterday_comparison": "(yesterday: {yesterday} \u20b8, {delta})",
        "no_change": "no change",
        "comparison_header": "\U0001f4ca COMPARISON:",
        "cheaper_note": "\U0001f4a1 {store} is cheaper by {delta} \u20b8 ({pct}%)",
        "same_price": "\U0001f4a1 Same total price",
    },
}


def _get_str(lang: str, key: str) -> str:
    """Get a report string for the given language, falling back to English."""
    strings = REPORT_STRINGS.get(lang, REPORT_STRINGS["en"])
    return strings.get(key, REPORT_STRINGS["en"].get(key, key))


def _format_number(value: Decimal | int) -> str:
    """Format a number with space as thousands separator (e.g. 28 450)."""
    n = int(value)
    return f"{n:,}".replace(",", " ")


async def generate_user_report(session: AsyncSession, user: User) -> str | None:
    """Generate a full daily report for a user.

    Returns the formatted report text, or None if the user has no baskets/items.
    """
    basket_repo = BasketRepository(session)
    baskets = await basket_repo.get_user_baskets_for_report(user.id)
    if not baskets:
        return None

    lang = user.language or "en"
    today = datetime.date.today()
    date_str = today.strftime("%d.%m.%Y")

    lines: list[str] = [_get_str(lang, "report_title").format(date=date_str), ""]

    # Track basket totals by source for comparison section
    source_totals: dict[str, Decimal] = {}
    source_names: dict[str, str] = {}
    sections_added = 0

    for basket in baskets:
        section, basket_total = await generate_basket_section(session, basket, lang)
        if section:
            lines.append(section)
            lines.append("")
            sections_added += 1
            # Track for comparison
            source_key = basket.source.lower()
            source_totals[source_key] = source_totals.get(
                source_key, Decimal(0)
            ) + basket_total
            source_names[source_key] = basket.source.capitalize()

    if sections_added == 0:
        return None

    # Comparison section if user has multiple sources
    if len(source_totals) >= 2:
        lines.append(SEPARATOR)
        lines.append(_get_str(lang, "comparison_header"))
        for source_key, total in source_totals.items():
            name = source_names[source_key]
            lines.append(f"{name}:  {_format_number(total)} \u20b8")

        sources = list(source_totals.keys())
        totals = list(source_totals.values())
        if totals[0] != totals[1]:
            cheaper_idx = 0 if totals[0] < totals[1] else 1
            more_idx = 1 - cheaper_idx
            delta = totals[more_idx] - totals[cheaper_idx]
            pct = (delta / totals[more_idx] * 100).quantize(Decimal("0.1"))
            lines.append(
                _get_str(lang, "cheaper_note").format(
                    store=source_names[sources[cheaper_idx]],
                    delta=_format_number(delta),
                    pct=pct,
                )
            )
        else:
            lines.append(_get_str(lang, "same_price"))

    return "\n".join(lines)


async def generate_basket_section(
    session: AsyncSession, basket: Basket, lang: str
) -> tuple[str, Decimal]:
    """Generate a report section for a single basket.

    Returns (section_text, basket_total). Section text is empty string if no items.
    """
    item_repo = BasketItemRepository(session)
    price_repo = PriceHistoryRepository(session)

    items_with_prices = await item_repo.get_basket_items_with_latest_price(
        basket.id
    )
    if not items_with_prices:
        return "", Decimal(0)

    # Get yesterday's prices for comparison
    item_ids = [item.id for item, *_ in items_with_prices]

    # Use start of today in user's timezone as cutoff
    import zoneinfo

    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    today_start = datetime.datetime.combine(now.date(), datetime.time.min, tzinfo=tz)

    previous_prices = await price_repo.get_previous_prices(item_ids, today_start)

    lines: list[str] = []
    item_count = len(items_with_prices)

    # Basket header
    lines.append(
        _get_str(lang, "basket_header").format(
            name=basket.name,
            source=basket.source.capitalize(),
            count=item_count,
        )
    )
    lines.append(SEPARATOR)

    basket_total = Decimal(0)
    yesterday_total = Decimal(0)
    has_yesterday = False

    for idx, (item, price, _original_price, is_available) in enumerate(
        items_with_prices, 1
    ):
        item_name = item.name or f"Item #{item.id}"
        qty = item.quantity

        # Item header: number, name x quantity
        if qty > 1:
            lines.append(f"{idx}. {item_name} \u00d7 {qty}")
        else:
            lines.append(f"{idx}. {item_name}")

        # Price line
        if price is not None:
            unit_price = price
            line_total = unit_price * qty
            basket_total += line_total

            if qty > 1:
                price_line = _get_str(lang, "item_price").format(
                    price=_format_number(unit_price),
                    total=_format_number(line_total),
                )
            else:
                price_line = f"\U0001f4b0 {_format_number(unit_price)} \u20b8"

            # Check for price change from yesterday
            prev = previous_prices.get(item.id)
            if prev is not None:
                prev_price, _prev_available = prev
                if prev_price is not None:
                    has_yesterday = True
                    yesterday_total += prev_price * qty

                    if prev_price != price:
                        delta = abs(price - prev_price)
                        if price < prev_price:
                            change_str = _get_str(lang, "price_decreased").format(
                                delta=_format_number(delta),
                                old=_format_number(prev_price),
                            )
                        else:
                            change_str = _get_str(lang, "price_increased").format(
                                delta=_format_number(delta),
                                old=_format_number(prev_price),
                            )
                        price_line += f"  {change_str}"
                else:
                    # Previous price was None (item existed but had no price)
                    yesterday_total += Decimal(0)
            else:
                # No previous data for this item -- still add current to yesterday
                # for consistent total comparison (treat as same)
                yesterday_total += line_total

            lines.append(f"   {price_line}")
        else:
            lines.append("   \U0001f4b0 \u2014 \u20b8")

        # Out of stock marker
        if not is_available:
            lines.append(f"   {_get_str(lang, 'out_of_stock')}")

    # Total line
    lines.append(SEPARATOR)
    total_line = _get_str(lang, "basket_total").format(
        total=_format_number(basket_total)
    )

    if has_yesterday and yesterday_total > 0:
        total_delta = basket_total - yesterday_total
        if total_delta == 0:
            delta_str = _get_str(lang, "no_change")
        elif total_delta < 0:
            delta_str = f"-{_format_number(abs(total_delta))} \u20b8"
        else:
            delta_str = f"+{_format_number(total_delta)} \u20b8"

        comparison = _get_str(lang, "yesterday_comparison").format(
            yesterday=_format_number(yesterday_total),
            delta=delta_str,
        )
        total_line += f" {comparison}"

    lines.append(total_line)

    return "\n".join(lines), basket_total
