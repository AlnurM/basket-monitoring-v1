STRINGS: dict[str, str] = {
    # Language selection (shown before user has a language)
    "choose_language": "Please select your language / Выберите язык:",
    "btn_russian": "Русский",
    "btn_english": "English",
    # Welcome & registration
    "welcome": "Welcome to Price Spy! I'll help you track grocery prices across Arbuz.kz and Magnum in Almaty.",
    "language_set": "Language set: English",
    "language_switched": "Language switched to English",
    # Help
    "help": (
        "Available commands:\n"
        "/start - Register / restart\n"
        "/help - Show this help message\n"
        "/language - Change language\n"
        "/baskets - My baskets\n"
        "/new_basket - Create a basket\n"
        "/list - Items in current basket\n"
        "/prices - Current prices\n"
        "/remove - Remove an item\n"
        "/notify - Notification time\n"
        "/scrape - Manual price scrape\n"
        "\n"
        "To add a product, just send its URL."
    ),
    # Errors
    "please_select_language": "Please select a language first.",
    "unknown_command": "Unknown command. Use /help to see available commands.",
    # Scrape errors (D-07: detailed diagnostic)
    "scrape_failed": "{product} failed: {reason} on {source}",
    "scrape_timeout": "timeout after {timeout}ms",
    "scrape_selector_not_found": "price selector not found",
    # Basket management
    "baskets_title": "Your baskets:",
    "baskets_empty": "You don't have any baskets yet. Create your first one!",
    "basket_line": "{active}{name} ({source}) -- {count} item(s)",
    "btn_new_basket": "+ New Basket",
    "enter_basket_name": "Enter a name for your basket:",
    "choose_source": "Choose a store for your basket:",
    "basket_created": 'Basket "{name}" ({source}) created!',
    "basket_limit_reached": "Limit reached: maximum {max} baskets.",
    "basket_deleted": 'Basket "{name}" deleted.',
    "confirm_delete_basket": 'Delete basket "{name}"? All items and price history will be lost.',
    "btn_yes_delete": "Yes, delete",
    "btn_no_cancel": "No, cancel",
    "basket_activated": 'Basket "{name}" is now active.',
    # Basket action buttons
    "btn_list_items": "Items",
    "btn_prices": "Prices",
    "btn_charts": "Charts",
    "btn_add_item": "+ Add",
    "btn_edit": "Edit",
    "btn_delete_basket": "Delete",
    "btn_back": "< Back",
    # Stub messages for Phase 4 features
    "charts_coming_soon": "Charts will be available in the next update.",
    "edit_quantity_prompt": 'Send the new quantity for "{name}":',
    # Product management
    "send_urls_prompt": (
        "Send product URLs (one per line).\n"
        "Format: URL [quantity]\n"
        "Example:\n"
        "https://arbuz.kz/ru/almaty/catalog/item/191336-moloko 2"
    ),
    "adding_products": "Adding products...",
    "product_added": "{name} x{qty} -- {price} KZT",
    "product_added_no_price": "{name} x{qty} -- price unavailable",
    "product_add_failed": "Failed to add: {url}\nReason: {reason}",
    "error_invalid_url": "URL is not a valid Arbuz, Magnum, or Kaspi product link.",
    "error_source_mismatch": 'This link ({source}) doesn\'t match basket "{basket}" ({basket_source}).',
    "error_duplicate_item": "This product is already in the basket.",
    "error_item_limit_reached": "Limit reached: maximum {max} items per basket.",
    "error_no_active_basket": "No active basket. Use /baskets to select one.",
    # Item display
    "items_title": 'Items in "{name}":',
    "items_empty": "No items in this basket yet.",
    "item_line": "{num}. {name} x{qty} -- {price} KZT (total: {total} KZT)",
    "item_line_discount": "{num}. {name} x{qty} -- {price} KZT (<s>{original}</s>) (total: {total} KZT)",
    "item_line_unavailable": "{num}. {name} x{qty} -- unavailable",
    "basket_total": "Total: {total} KZT",
    "item_removed": 'Item "{name}" removed.',
    "confirm_remove_item": 'Remove "{name}" from basket?',
    # Pagination
    "btn_prev": "< Prev",
    "btn_next": "Next >",
    "page_indicator": "Page {current}/{total}",
    # Notification settings (/notify)
    "notify_current": "Current notification time: {time}",
    "notify_updated": "Notification time set to: {time}",
    "notify_usage": "Usage: /notify HH:MM\nExample: /notify 08:30",
    "notify_invalid_format": "Invalid format. Use HH:MM (00:00-23:59).",
    # Manual scrape (/scrape)
    "scrape_starting": "Scraping {count} item(s)...",
    "scrape_complete": "Scrape complete!\n\n{results}",
    "scrape_item_ok": "{name} — {price} ₸",
    "scrape_item_fail": "{name} — error",
    "scrape_item_unavailable": "{name} — out of stock",
    "scrape_no_active_basket": "No active basket. Use /baskets to select one.",
    "scrape_empty_basket": "No items in the active basket.",
    "scrape_rate_limited": "Please wait {minutes} more min. before next scrape.",
}
