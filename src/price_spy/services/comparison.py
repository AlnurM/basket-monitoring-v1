"""Comparison service for cross-store price analysis.

Generates /compare reports with store totals, percentage difference,
and fuzzy-matched per-item comparison between Arbuz and Magnum baskets.
"""

import difflib
import re
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository

COMPARISON_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "compare_title": "\U0001f4ca \u0421\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 Arbuz vs Magnum",
        "compare_difference": "\U0001f4a1 {store} \u0434\u0435\u0448\u0435\u0432\u043b\u0435 \u043d\u0430 {delta} \u20b8 ({pct}%)",
        "compare_same_price": "\U0001f4a1 \u0426\u0435\u043d\u044b \u043e\u0434\u0438\u043d\u0430\u043a\u043e\u0432\u044b\u0435",
        "compare_need_both": "\u0414\u043b\u044f \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u044f \u043d\u0443\u0436\u043d\u044b \u043a\u043e\u0440\u0437\u0438\u043d\u044b \u0438\u0437 Arbuz \u0438 Magnum.",
        "compare_matched_header": "\U0001f50d \u0421\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0449\u0438\u0435 \u0442\u043e\u0432\u0430\u0440\u044b:",
        "compare_no_matches": "\u0421\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0449\u0438\u0445 \u0442\u043e\u0432\u0430\u0440\u043e\u0432 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.",
    },
    "en": {
        "compare_title": "\U0001f4ca Arbuz vs Magnum Comparison",
        "compare_difference": "\U0001f4a1 {store} is cheaper by {delta} \u20b8 ({pct}%)",
        "compare_same_price": "\U0001f4a1 Same total price",
        "compare_need_both": "Need baskets from both Arbuz and Magnum to compare.",
        "compare_matched_header": "\U0001f50d Matched products:",
        "compare_no_matches": "No matching products found.",
    },
}

# Regex to strip weight/volume suffixes for name normalization
_SUFFIX_RE = re.compile(r"\s*\d+\s*(?:\u043b|\u043c\u043b|\u043a\u0433|\u0433|\u0448\u0442|l|ml|kg|g|pcs)\.?\s*$", re.IGNORECASE)


def _get_str(lang: str, key: str) -> str:
    """Get a comparison string for the given language, falling back to English."""
    strings = COMPARISON_STRINGS.get(lang, COMPARISON_STRINGS["en"])
    return strings.get(key, COMPARISON_STRINGS["en"].get(key, key))


def _format_number(value: Decimal | int) -> str:
    """Format a number with space as thousands separator (e.g. 28 450)."""
    n = int(value)
    return f"{n:,}".replace(",", " ")


def _normalize_name(name: str) -> str:
    """Normalize product name for fuzzy matching.

    Lowercases and strips weight/volume suffixes (digits + l/ml/kg/g/sht).
    """
    normalized = name.lower().strip()
    normalized = _SUFFIX_RE.sub("", normalized)
    return normalized.strip()


def find_matching_products(
    arbuz_items: list[tuple[str, Decimal | None]],
    magnum_items: list[tuple[str, Decimal | None]],
    threshold: float = 0.6,
) -> list[tuple[str, str, Decimal | None, Decimal | None]]:
    """Find matching products between Arbuz and Magnum using fuzzy matching.

    Args:
        arbuz_items: list of (name, price) from Arbuz baskets
        magnum_items: list of (name, price) from Magnum baskets
        threshold: minimum similarity ratio (0.0 to 1.0)

    Returns:
        list of (arbuz_name, magnum_name, arbuz_price, magnum_price) for matched pairs
    """
    matched: list[tuple[str, str, Decimal | None, Decimal | None]] = []
    used_magnum: set[int] = set()

    for a_name, a_price in arbuz_items:
        a_norm = _normalize_name(a_name)
        best_ratio = 0.0
        best_idx = -1

        for m_idx, (m_name, _m_price) in enumerate(magnum_items):
            if m_idx in used_magnum:
                continue
            m_norm = _normalize_name(m_name)
            ratio = difflib.SequenceMatcher(None, a_norm, m_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = m_idx

        if best_ratio >= threshold and best_idx >= 0:
            m_name, m_price = magnum_items[best_idx]
            matched.append((a_name, m_name, a_price, m_price))
            used_magnum.add(best_idx)

    return matched


async def generate_comparison_report(
    session: AsyncSession,
    user_id: int,
    lang: str,
) -> str | None:
    """Generate a cross-store comparison report.

    Compares total basket costs between Arbuz and Magnum stores,
    then shows fuzzy-matched per-item price differences.

    Returns formatted report string, or None if user has no baskets.
    """
    basket_repo = BasketRepository(session)
    baskets = await basket_repo.get_user_baskets(user_id)
    if not baskets:
        return None

    # Split baskets by source
    arbuz_baskets = [b for b in baskets if b.source.lower() == "arbuz"]
    magnum_baskets = [b for b in baskets if b.source.lower() == "magnum"]

    if not arbuz_baskets or not magnum_baskets:
        return _get_str(lang, "compare_need_both")

    item_repo = BasketItemRepository(session)

    # Collect items and totals for each store
    arbuz_total = Decimal(0)
    arbuz_products: list[tuple[str, Decimal | None]] = []

    for basket in arbuz_baskets:
        items_with_prices = await item_repo.get_basket_items_with_latest_price(basket.id)
        for item, price, _original_price, is_available in items_with_prices:
            name = item.name or f"Item #{item.id}"
            arbuz_products.append((name, price))
            if price is not None and is_available:
                arbuz_total += price * item.quantity

    magnum_total = Decimal(0)
    magnum_products: list[tuple[str, Decimal | None]] = []

    for basket in magnum_baskets:
        items_with_prices = await item_repo.get_basket_items_with_latest_price(basket.id)
        for item, price, _original_price, is_available in items_with_prices:
            name = item.name or f"Item #{item.id}"
            magnum_products.append((name, price))
            if price is not None and is_available:
                magnum_total += price * item.quantity

    # Build report
    lines: list[str] = [_get_str(lang, "compare_title"), ""]

    # Store totals
    lines.append(f"\U0001f6d2 Arbuz: {_format_number(arbuz_total)} \u20b8")
    lines.append(f"\U0001f6d2 Magnum: {_format_number(magnum_total)} \u20b8")
    lines.append("")

    # Difference
    if arbuz_total != magnum_total:
        if arbuz_total < magnum_total:
            delta = magnum_total - arbuz_total
            pct = (delta / magnum_total * 100).quantize(Decimal("0.1"))
            lines.append(_get_str(lang, "compare_difference").format(
                store="Arbuz", delta=_format_number(delta), pct=pct,
            ))
        else:
            delta = arbuz_total - magnum_total
            pct = (delta / arbuz_total * 100).quantize(Decimal("0.1"))
            lines.append(_get_str(lang, "compare_difference").format(
                store="Magnum", delta=_format_number(delta), pct=pct,
            ))
    else:
        lines.append(_get_str(lang, "compare_same_price"))

    lines.append("")

    # Fuzzy matched products
    matched = find_matching_products(arbuz_products, magnum_products)

    if matched:
        lines.append(_get_str(lang, "compare_matched_header"))
        for a_name, _m_name, a_price, m_price in matched:
            if a_price is not None and m_price is not None:
                diff = a_price - m_price
                if diff > 0:
                    diff_str = f"+{_format_number(diff)} \u20b8"
                elif diff < 0:
                    diff_str = f"-{_format_number(abs(diff))} \u20b8"
                else:
                    diff_str = "="
                lines.append(
                    f"  \u2022 {a_name}: {_format_number(a_price)} \u20b8 vs {_format_number(m_price)} \u20b8 ({diff_str})"
                )
            else:
                a_str = f"{_format_number(a_price)} \u20b8" if a_price is not None else "\u2014"
                m_str = f"{_format_number(m_price)} \u20b8" if m_price is not None else "\u2014"
                lines.append(f"  \u2022 {a_name}: {a_str} vs {m_str}")
    else:
        lines.append(_get_str(lang, "compare_no_matches"))

    return "\n".join(lines)
