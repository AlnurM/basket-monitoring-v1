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
        "\n"
        "More commands will be available in future updates."
    ),
    # Errors
    "please_select_language": "Please select a language first.",
    "unknown_command": "Unknown command. Use /help to see available commands.",
    # Scrape errors (D-07: detailed diagnostic)
    "scrape_failed": "{product} failed: {reason} on {source}",
    "scrape_timeout": "timeout after {timeout}ms",
    "scrape_selector_not_found": "price selector not found",
}
