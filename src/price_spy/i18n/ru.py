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
        "/baskets - Мои корзины\n"
        "/new_basket - Создать корзину\n"
        "/list - Товары текущей корзины\n"
        "/prices - Текущие цены\n"
        "/remove - Удалить товар\n"
        "/notify - Время уведомлений\n"
        "/scrape - Ручной парсинг цен\n"
        "\n"
        "Для добавления товара отправьте ссылку на него."
    ),
    # Errors
    "please_select_language": "Пожалуйста, сначала выберите язык.",
    "unknown_command": "Неизвестная команда. Используйте /help для списка команд.",
    # Scrape errors (D-07: detailed diagnostic)
    "scrape_failed": "{product} не удалось: {reason} на {source}",
    "scrape_timeout": "таймаут после {timeout}мс",
    "scrape_selector_not_found": "селектор цены не найден",
    # Basket management
    "baskets_title": "Ваши корзины:",
    "baskets_empty": "У вас пока нет корзин. Создайте первую!",
    "basket_line": "{active}{name} ({source}) -- {count} товар(ов)",
    "btn_new_basket": "+ Новая корзина",
    "enter_basket_name": "Введите название корзины:",
    "choose_source": "Выберите магазин для корзины:",
    "basket_created": 'Корзина "{name}" ({source}) создана!',
    "basket_limit_reached": "Достигнут лимит: максимум {max} корзин.",
    "basket_deleted": 'Корзина "{name}" удалена.',
    "confirm_delete_basket": 'Удалить корзину "{name}"? Все товары и история цен будут потеряны.',
    "btn_yes_delete": "Да, удалить",
    "btn_no_cancel": "Нет, отмена",
    "basket_activated": 'Корзина "{name}" теперь активная.',
    # Basket action buttons
    "btn_list_items": "Список",
    "btn_prices": "Цены",
    "btn_charts": "Графики",
    "btn_add_item": "+ Добавить",
    "btn_edit": "Ред.",
    "btn_delete_basket": "Удалить",
    "btn_back": "< Назад",
    # Stub messages for Phase 4 features
    "charts_coming_soon": "Графики будут доступны в следующем обновлении.",
    "edit_quantity_prompt": 'Отправьте новое количество для "{name}":',
    # Product management
    "send_urls_prompt": (
        "Отправьте ссылки на товары (по одной на строку).\n"
        "Формат: URL [количество]\n"
        "Пример:\n"
        "https://arbuz.kz/ru/almaty/catalog/item/191336-moloko 2"
    ),
    "adding_products": "Добавляю товары...",
    "product_added": "{name} x{qty} -- {price} тг",
    "product_added_no_price": "{name} x{qty} -- цена недоступна",
    "product_add_failed": "Не удалось добавить: {url}\nПричина: {reason}",
    "error_invalid_url": "URL не является ссылкой на товар Arbuz, Magnum или Kaspi.",
    "error_source_mismatch": 'Эта ссылка ({source}) не подходит для корзины "{basket}" ({basket_source}).',
    "error_duplicate_item": "Этот товар уже есть в корзине.",
    "error_item_limit_reached": "Достигнут лимит: максимум {max} товаров в корзине.",
    "error_no_active_basket": "Нет активной корзины. Используйте /baskets чтобы выбрать.",
    # Item display
    "items_title": 'Товары в "{name}":',
    "items_empty": "В корзине пока нет товаров.",
    "item_line": "{num}. {name} x{qty} -- {price} тг (итого: {total} тг)",
    "item_line_discount": "{num}. {name} x{qty} -- {price} тг (<s>{original}</s>) (итого: {total} тг)",
    "item_line_unavailable": "{num}. {name} x{qty} -- недоступен",
    "basket_total": "Итого: {total} тг",
    "item_removed": 'Товар "{name}" удален.',
    "confirm_remove_item": 'Удалить "{name}" из корзины?',
    # Pagination
    "btn_prev": "< Пред.",
    "btn_next": "След. >",
    "page_indicator": "Стр. {current}/{total}",
    # Notification settings (/notify)
    "notify_current": "Текущее время уведомлений: {time}",
    "notify_updated": "Время уведомлений установлено: {time}",
    "notify_usage": "Используйте: /notify ЧЧ:ММ\nПример: /notify 08:30",
    "notify_invalid_format": "Неверный формат. Используйте ЧЧ:ММ (00:00-23:59).",
    # Manual scrape (/scrape)
    "scrape_starting": "Парсинг {count} товар(ов)...",
    "scrape_complete": "Парсинг завершён!\n\n{results}",
    "scrape_item_ok": "{name} — {price} ₸",
    "scrape_item_fail": "{name} — ошибка",
    "scrape_item_unavailable": "{name} — нет в наличии",
    "scrape_no_active_basket": "Нет активной корзины. Используйте /baskets чтобы выбрать.",
    "scrape_empty_basket": "В активной корзине нет товаров.",
    "scrape_rate_limited": "Подождите ещё {minutes} мин. перед следующим парсингом.",
}
