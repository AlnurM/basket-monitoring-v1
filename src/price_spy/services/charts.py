"""Chart generation service.

Generates PNG charts for basket totals and individual item price history.
Uses matplotlib with Agg backend and run_in_executor to avoid blocking
the asyncio event loop. Per CHRT-01..05.
"""

import asyncio
import datetime
from decimal import Decimal
from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # Must be before pyplot import

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from price_spy.db.repositories.basket_item import BasketItemRepository  # noqa: E402
from price_spy.db.repositories.price_history import PriceHistoryRepository  # noqa: E402

# Bilingual chart strings per D-10.
CHART_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "chart_title_basket": "Стоимость корзины: {name}",
        "chart_title_item": "Цена: {name}",
        "chart_ylabel": "Цена (₸)",
        "chart_no_data": (
            "Недостаточно данных для графика. "
            "Попробуйте после следующего парсинга."
        ),
        "chart_generating": "Генерирую график...",
    },
    "en": {
        "chart_title_basket": "Basket cost: {name}",
        "chart_title_item": "Price: {name}",
        "chart_ylabel": "Price (₸)",
        "chart_no_data": "Not enough data for chart. Try after next scrape.",
        "chart_generating": "Generating chart...",
    },
}


def _get_str(lang: str, key: str) -> str:
    """Get a chart string for the given language, falling back to English."""
    strings = CHART_STRINGS.get(lang, CHART_STRINGS["en"])
    return strings.get(key, CHART_STRINGS["en"].get(key, key))


def _tenge_formatter(x: float, _pos: int) -> str:
    """Format y-axis values as space-separated thousands with tenge symbol."""
    return f"{int(x):,} ₸".replace(",", " ")


def _generate_basket_chart_sync(
    dates: list[str],
    totals: list[float],
    title: str,
    ylabel: str,
) -> bytes:
    """Generate a basket total line chart (sync, runs in executor).

    Args:
        dates: Date labels (DD.MM format).
        totals: Basket total values per day.
        title: Chart title.
        ylabel: Y-axis label.

    Returns:
        PNG image bytes.
    """
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    try:
        ax.plot(dates, totals, marker="o", linewidth=2, color="#2196F3")
        ax.set_title(title, fontsize=14)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(FuncFormatter(_tenge_formatter))
        fig.autofmt_xdate(rotation=45)
        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        return buf.read()
    finally:
        plt.close(fig)


def _generate_item_chart_sync(
    dates: list[str],
    prices: list[float],
    original_prices: list[float | None],
    availabilities: list[bool],
    title: str,
    ylabel: str,
) -> bytes:
    """Generate an item price chart with discount/out-of-stock markers (sync).

    Args:
        dates: Date labels (DD.MM format).
        prices: Item prices over time.
        original_prices: Original prices (non-None when discounted).
        availabilities: Whether item was in stock at each point.
        title: Chart title.
        ylabel: Y-axis label.

    Returns:
        PNG image bytes.
    """
    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
    try:
        ax.plot(dates, prices, marker="o", linewidth=2, color="#2196F3")

        # Green dots for discount prices (original_price > price)
        discount_x = []
        discount_y = []
        for i, (op, p) in enumerate(zip(original_prices, prices)):
            if op is not None and op > p:
                discount_x.append(dates[i])
                discount_y.append(p)
        if discount_x:
            ax.scatter(
                discount_x, discount_y,
                color="#4CAF50", marker="o", s=80, zorder=5, label="Discount",
            )

        # Red X for out-of-stock
        oos_x = []
        oos_y = []
        for i, avail in enumerate(availabilities):
            if not avail:
                oos_x.append(dates[i])
                oos_y.append(prices[i])
        if oos_x:
            ax.scatter(
                oos_x, oos_y,
                color="#F44336", marker="x", s=100, zorder=5, label="Out of stock",
            )

        ax.set_title(title, fontsize=14)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(FuncFormatter(_tenge_formatter))
        if discount_x or oos_x:
            ax.legend()
        fig.autofmt_xdate(rotation=45)
        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        return buf.read()
    finally:
        plt.close(fig)


async def generate_basket_chart(
    session: AsyncSession,
    basket_id: int,
    basket_name: str,
    days: int = 30,
    lang: str = "en",
) -> bytes | None:
    """Generate a basket total over time chart.

    Args:
        session: Database session.
        basket_id: Basket ID.
        basket_name: Basket name (for title).
        days: Number of days to include (default 30, per D-09).
        lang: Language code.

    Returns:
        PNG bytes or None if insufficient data.
    """
    import zoneinfo

    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    start_date = now - datetime.timedelta(days=days)

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_items_by_basket(basket_id)
    if not items:
        return None

    item_ids = [item.id for item in items]
    quantities = {item.id: item.quantity for item in items}

    price_repo = PriceHistoryRepository(session)
    daily_totals = await price_repo.get_daily_basket_totals(
        item_ids, quantities, start_date, now,
    )

    if len(daily_totals) < 2:
        return None

    dates = [d.strftime("%d.%m") for d, _ in daily_totals]
    totals = [float(t) for _, t in daily_totals]

    title = _get_str(lang, "chart_title_basket").format(name=basket_name)
    ylabel = _get_str(lang, "chart_ylabel")

    loop = asyncio.get_event_loop()
    png_bytes = await loop.run_in_executor(
        None, _generate_basket_chart_sync, dates, totals, title, ylabel,
    )
    return png_bytes


async def generate_item_chart(
    session: AsyncSession,
    basket_id: int,
    item_index: int,
    days: int = 30,
    lang: str = "en",
) -> tuple[bytes | None, str | None]:
    """Generate a price chart for a single item in a basket.

    Args:
        session: Database session.
        basket_id: Basket ID.
        item_index: 1-based item index within the basket.
        days: Number of days to include (default 30).
        lang: Language code.

    Returns:
        (PNG bytes, None) on success, or (None, error_message) on failure.
    """
    import zoneinfo

    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    start_date = now - datetime.timedelta(days=days)

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_items_by_basket(basket_id)

    # Sort by created_at for consistent indexing
    items.sort(key=lambda i: i.created_at)

    if not items or item_index < 1 or item_index > len(items):
        return None, _get_str(lang, "chart_no_data")

    item = items[item_index - 1]

    price_repo = PriceHistoryRepository(session)
    records = await price_repo.get_price_range([item.id], start_date, now)

    if len(records) < 2:
        return None, _get_str(lang, "chart_no_data")

    dates = [r.scraped_at.strftime("%d.%m") for r in records]
    prices = [float(r.price) if r.price is not None else 0.0 for r in records]
    original_prices = [
        float(r.original_price) if r.original_price is not None else None
        for r in records
    ]
    availabilities = [r.is_available for r in records]

    item_name = item.name or f"Item #{item.id}"
    title = _get_str(lang, "chart_title_item").format(name=item_name)
    ylabel = _get_str(lang, "chart_ylabel")

    loop = asyncio.get_event_loop()
    png_bytes = await loop.run_in_executor(
        None,
        _generate_item_chart_sync,
        dates, prices, original_prices, availabilities, title, ylabel,
    )
    return png_bytes, None
