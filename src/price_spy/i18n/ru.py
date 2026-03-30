STRINGS: dict[str, str] = {
    # Language selection
    "choose_language": "Please select your language / Выберите язык:",
    "btn_russian": "Русский",
    "btn_english": "English",
    # Welcome & registration
    "welcome": "Добро пожаловать в Price Spy! Я помогу отслеживать цены на продукты в Arbuz.kz и Magnum в Алматы.",
    "language_set": "Язык установлен: Русский",
    "language_switched": "Язык переключён на Русский",
    # Help
    "help": (
        "Доступные команды:\n"
        "/start - Регистрация / перезапуск\n"
        "/help - Показать справку\n"
        "/language - Сменить язык\n"
        "\n"
        "Больше команд будет доступно в будущих обновлениях."
    ),
    # Errors
    "please_select_language": "Пожалуйста, сначала выберите язык.",
    "unknown_command": "Неизвестная команда. Используйте /help для списка команд.",
    # Scrape errors (D-07: detailed diagnostic)
    "scrape_failed": "{product} не удалось: {reason} на {source}",
    "scrape_timeout": "таймаут после {timeout}мс",
    "scrape_selector_not_found": "селектор цены не найден",
}
