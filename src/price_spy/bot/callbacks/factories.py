from aiogram.filters.callback_data import CallbackData


class BasketCB(CallbackData, prefix="bsk"):
    """Top-level basket navigation."""

    action: str  # "list", "view", "new", "set_source"
    basket_id: int | None = None
    source: str | None = None  # "arbuz" or "magnum" for creation


class BasketActionCB(CallbackData, prefix="bact"):
    """Actions within a specific basket."""

    action: str  # "items", "prices", "charts", "add", "edit", "delete", "confirm_delete", "back"
    basket_id: int


class ItemCB(CallbackData, prefix="itm"):
    """Item-level actions."""

    action: str  # "remove", "confirm_remove", "page"
    basket_id: int
    item_id: int | None = None
    page: int = 0
