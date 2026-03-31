"""CSV export service.

Generates CSV files with UTF-8 BOM for Excel/Cyrillic compatibility.
Per D-14, D-15, D-16 / EXPT-01..03.
"""

import csv
import datetime
import io
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.db.repositories.price_history import PriceHistoryRepository

# Bilingual export strings.
EXPORT_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "export_no_data": "Нет данных для экспорта.",
        "export_generating": "Генерирую CSV...",
    },
    "en": {
        "export_no_data": "No data to export.",
        "export_generating": "Generating CSV...",
    },
}

# CSV header per D-15 / EXPT-02.
CSV_HEADER = [
    "date", "basket", "source", "product",
    "quantity", "unit_price", "total", "available",
]


def _get_str(lang: str, key: str) -> str:
    """Get an export string for the given language, falling back to English."""
    strings = EXPORT_STRINGS.get(lang, EXPORT_STRINGS["en"])
    return strings.get(key, EXPORT_STRINGS["en"].get(key, key))


def _format_number(value: Decimal | int) -> str:
    """Format a number with space as thousands separator."""
    n = int(value)
    return f"{n:,}".replace(",", " ")


def generate_csv_bytes(
    rows: list,
    basket_name: str,
    source: str,
) -> bytes:
    """Generate CSV bytes with UTF-8 BOM.

    Args:
        rows: List of dicts with keys matching CSV_HEADER fields.
            Each dict should have: date, product, quantity, unit_price, available.
        basket_name: Basket name for the "basket" column.
        source: Source store name for the "source" column.

    Returns:
        UTF-8 encoded bytes with BOM prefix.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADER)

    for row in rows:
        unit_price = row.get("unit_price", Decimal(0))
        quantity = row.get("quantity", 1)
        total = unit_price * quantity if unit_price is not None else Decimal(0)

        writer.writerow([
            row.get("date", ""),
            basket_name,
            source,
            row.get("product", ""),
            quantity,
            str(unit_price) if unit_price is not None else "",
            str(total),
            "true" if row.get("available", True) else "false",
        ])

    # Prepend UTF-8 BOM per D-16 / EXPT-03.
    csv_text = output.getvalue()
    return b"\xef\xbb\xbf" + csv_text.encode("utf-8")


async def generate_export(
    session: AsyncSession,
    basket_id: int,
    basket_name: str,
    source: str,
    lang: str = "en",
) -> bytes | None:
    """Generate a CSV export for a basket's price history.

    Args:
        session: Database session.
        basket_id: Basket ID.
        basket_name: Basket name.
        source: Store source (arbuz/magnum).
        lang: Language code.

    Returns:
        CSV bytes or None if no data.
    """
    import zoneinfo

    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    start_date = now - datetime.timedelta(days=90)

    item_repo = BasketItemRepository(session)
    items = await item_repo.get_items_by_basket(basket_id)
    if not items:
        return None

    item_ids = [item.id for item in items]

    price_repo = PriceHistoryRepository(session)
    records = await price_repo.get_export_data(item_ids, start_date, now)
    if not records:
        return None

    rows = []
    for rec in records:
        bi = rec.basket_item
        rows.append({
            "date": rec.scraped_at.strftime("%Y-%m-%d"),
            "product": bi.name or f"Item #{bi.id}",
            "quantity": bi.quantity,
            "unit_price": rec.price,
            "available": rec.is_available,
        })

    return generate_csv_bytes(rows, basket_name, source)
