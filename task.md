# Grocery Price Tracker Bot — Техническое задание

## 1. Обзор проекта

**Название:** Grocery Price Tracker Bot (рабочее: `price-spy`)

**Цель:** Telegram-бот для персонального мониторинга цен на продукты в онлайн-магазинах Алматы — **Arbuz.kz** и **Magnum** (через magnum.kz и kaspi.kz/shop). Пользователь формирует корзину (список товаров × количество), бот ежедневно парсит цены и присылает аналитику.

**Стек:** Python (полностью)

**Хостинг:** Railway

---

## 2. Архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│                          Railway                                 │
│                                                                  │
│  ┌──────────────┐   ┌───────────────────────┐   ┌────────────┐  │
│  │  Telegram Bot │   │       Scraper         │   │  Scheduler │  │
│  │  (aiogram 3)  │◄─►│ Arbuz/Magnum:Playwright│◄──│  (APSched) │  │
│  └──────┬───────┘   │ Kaspi: httpx (fast)   │   └────────────┘  │
│         │           └───────────┬───────────┘                    │
│         ▼                       ▼                                │
│  ┌──────────────────────────────────────────┐                    │
│  │          PostgreSQL (Railway)            │                    │
│  └──────────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────────┘
```

### Компоненты

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Telegram Bot | aiogram 3.x | Интерфейс пользователя: управление корзинами, просмотр аналитики |
| Scraper | Playwright (async) + httpx | Парсинг цен: Arbuz.kz — Playwright (SPA, 403); Magnum.kz — Playwright (SPA); Kaspi.kz — httpx (SSR, полный HTML) |
| Scheduler | APScheduler | Ежедневный запуск парсинга по расписанию |
| Database | PostgreSQL | Хранение корзин, истории цен, настроек |
| Charts | matplotlib / plotly | Генерация графиков цен для отправки в Telegram |

---

## 3. Структура URL целевых сайтов

### Arbuz.kz

- **Формат URL товара:** `https://arbuz.kz/ru/almaty/catalog/item/{item_id}-{slug}`
- **Пример:** `https://arbuz.kz/ru/almaty/catalog/item/191336-moloko_amiran_zhivoe_3_2_0_8_l`
- **Каталог категории:** `https://arbuz.kz/ru/almaty/catalog/cat/{cat_id}-{slug}`
- **Особенности:** Сайт возвращает 403 на прямой HTTP-запрос; контент рендерится через JS → **нужен Playwright**

### Magnum (два источника ссылок)

Magnum продаёт товары как через свой сайт, так и через Kaspi Магазин. Бот принимает ссылки из обоих источников в одну корзину.

#### magnum.kz (собственный сайт)

- **Формат URL товара:** `https://magnum.kz/products/{product_id}?city=almaty`
- **Пример:** `https://magnum.kz/products/143331?city=almaty`
- **Каталог скидок:** `https://magnum.kz/catalog`
- **Особенности:** Полностью SPA (Next.js/React), сервер отдаёт пустой HTML shell → **нужен Playwright**

#### kaspi.kz/shop (маркетплейс)

- **Формат URL товара:** `https://kaspi.kz/shop/p/{slug}-{product_id}?c={city_id}`
- **Пример:** `https://kaspi.kz/shop/p/bonduelle-kukuruza-sladkaja-425-ml-100980360?c=750000000`
- **city_id для Алматы:** `750000000`
- **Особенности:** SSR — сервер отдаёт полный HTML с ценой, характеристиками, названием → **Playwright НЕ нужен**, достаточно `httpx` + `BeautifulSoup` / `selectolax`. Это быстрее и экономит ресурсы на Railway.

> **Примечание:** Оба сайта (Arbuz и Magnum через magnum.kz) могут иметь внутренние API (XHR/fetch запросы). На этапе разработки рекомендуется перехватить сетевые запросы через Playwright и, если удастся найти стабильные API-эндпоинты, переключиться на прямые HTTP-запросы для ускорения и снижения ресурсов. Для kaspi.kz это уже не нужно — он отдаёт данные в HTML напрямую.

---

## 4. Модель данных (PostgreSQL)

### 4.1. `users`

```sql
CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    telegram_id   BIGINT UNIQUE NOT NULL,
    username      TEXT,
    notify_time   TIME DEFAULT '09:00',  -- время ежедневной рассылки
    timezone      TEXT DEFAULT 'Asia/Almaty',
    created_at    TIMESTAMPTZ DEFAULT now()
);
```

### 4.2. `baskets`

```sql
CREATE TABLE baskets (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,             -- "Недельная закупка", "Для дачи" и т.д.
    source      TEXT NOT NULL CHECK (source IN ('arbuz', 'magnum')),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### 4.3. `basket_items`

```sql
CREATE TABLE basket_items (
    id          BIGSERIAL PRIMARY KEY,
    basket_id   BIGINT REFERENCES baskets(id) ON DELETE CASCADE,
    product_url TEXT NOT NULL,              -- полная ссылка на товар (arbuz / magnum / kaspi)
    product_id  TEXT NOT NULL,              -- извлечённый ID (191336 / 143331 / 100980360)
    url_source  TEXT NOT NULL CHECK (url_source IN ('arbuz', 'magnum', 'kaspi')),  -- откуда ссылка
    name        TEXT,                       -- название товара (заполняется при первом парсинге)
    quantity    INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (basket_id, product_url)
);
```

### 4.4. `price_history`

```sql
CREATE TABLE price_history (
    id              BIGSERIAL PRIMARY KEY,
    basket_item_id  BIGINT REFERENCES basket_items(id) ON DELETE CASCADE,
    price           NUMERIC(12, 2),         -- цена в тенге (NULL = товар недоступен)
    original_price  NUMERIC(12, 2),         -- цена без скидки (если есть)
    is_available    BOOLEAN DEFAULT TRUE,
    scraped_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_price_history_item_date ON price_history (basket_item_id, scraped_at DESC);
```

---

## 5. Scraper (Playwright + httpx)

### 5.1. Общая стратегия

Бот использует **два метода парсинга** в зависимости от источника ссылки:

- **Playwright (headless Chromium)** — для Arbuz.kz (403 на прямой запрос) и Magnum.kz (SPA)
- **httpx + selectolax** — для Kaspi.kz (SSR, полный HTML в ответе). Быстрее, легче, не требует браузера.

```python
# Псевдокод scraper-а
async def scrape_product(url: str, url_source: str, page: Page = None) -> dict:
    if url_source == "kaspi":
        # Прямой HTTP-запрос — Playwright не нужен
        return await scrape_kaspi(url)
    
    # Для arbuz и magnum — через Playwright
    await page.goto(url, wait_until="networkidle")

    if url_source == "arbuz":
        # Селекторы для Arbuz (уточнить при разработке):
        # - Цена: '.product-price', '[data-testid="price"]'  
        # - Название: 'h1', '.product-title'
        # - Наличие: проверка наличия кнопки "В корзину"
        # - Старая цена: '.old-price', '.crossed-price'
        return await extract_arbuz_data(page)

    elif url_source == "magnum":
        # Селекторы для Magnum (уточнить при разработке):
        # - Цена: '.product-price', '[class*="price"]'
        # - Название: 'h1'
        # - Наличие: отсутствие "Нет в наличии"
        return await extract_magnum_data(page)


async def scrape_kaspi(url: str) -> dict:
    """Kaspi.kz — SSR, парсим HTML напрямую через httpx."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"User-Agent": random_ua()})
    
    tree = HTMLParser(resp.text)  # selectolax
    
    # Проверенные данные из HTML (kaspi.kz отдаёт SSR):
    # - Название: <h1> тег
    # - Характеристики: structured data в HTML
    # - Цена: ищем в мета-тегах, JSON-LD или в DOM
    # - Наличие: проверка наличия кнопки покупки / статуса
    
    return {
        "price": price,
        "original_price": original_price,
        "name": name,
        "is_available": is_available,
    }
```

### 5.2. Оптимизации

| Приём | Описание |
|-------|----------|
| **Kaspi fast-path** | Kaspi.kz парсится через `httpx` без Playwright — ~100ms вместо ~3–5s на товар |
| **API Interception** | При `page.on("response")` перехватывать XHR/fetch → если найдётся JSON API с ценой, использовать `httpx` напрямую |
| **Browser reuse** | Один экземпляр browser на весь цикл парсинга, новый context на каждый магазин |
| **Параллелизм** | `asyncio.gather` с семафором (max 3 страницы для Playwright, max 10 для httpx) |
| **Retry** | 3 попытки с экспоненциальной задержкой при ошибке загрузки |
| **User-Agent rotation** | Пул из 5–10 реальных UA для снижения вероятности блокировки |
| **Stealth** | `playwright-stealth` плагин для обхода bot-detection (Arbuz, Magnum) |

### 5.3. Порядок парсинга одной корзины

1. Разделить `basket_items` на две группы: `kaspi_items` и `browser_items` (arbuz + magnum)
2. **Kaspi-группа** (параллельно, httpx):
   - `asyncio.gather` с семафором (max 10) — прямые HTTP-запросы
   - Для каждого: GET → parse HTML → извлечь данные
3. **Browser-группа** (Playwright):
   - Запустить headless Chromium
   - Для каждого `basket_item`:
     - Перейти на `product_url`
     - Дождаться рендера (networkidle / конкретный селектор)
     - Извлечь: `price`, `original_price`, `name`, `is_available`
   - Закрыть browser
4. Если `name` у `basket_item` пустой — записать из результатов парсинга
5. Сохранить все результаты в `price_history`

---

## 6. Telegram Bot (aiogram 3)

### 6.1. Команды

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация, приветствие |
| `/help` | Список команд |
| `/baskets` | Показать мои корзины |
| `/new_basket` | Создать корзину (inline: имя → источник arbuz/magnum) |
| `/add <url> [кол-во]` | Добавить товар в активную корзину |
| `/remove <номер>` | Удалить товар из корзины |
| `/list` | Показать товары текущей корзины |
| `/prices` | Текущие цены по корзине (последний парсинг) |
| `/compare` | Сравнение итогов Arbuz vs Magnum |
| `/changes` | Изменения цен за последние N дней (было/стало) |
| `/chart <дни>` | График цен за период (по умолчанию 30 дней) |
| `/chart_item <номер> <дни>` | График цены одного товара |
| `/notify <HH:MM>` | Установить время ежедневной рассылки |
| `/scrape` | Ручной запуск парсинга (rate limit: 1 раз в час) |
| `/switch <id_корзины>` | Переключить активную корзину |
| `/delete_basket <id>` | Удалить корзину |
| `/export` | Выгрузить историю цен в CSV |

### 6.2. Inline-кнопки для навигации

```
[Мои корзины]
├── 🛒 Недельная (Arbuz) — 12 товаров
│   ├── [📋 Список]  [💰 Цены]  [📈 Графики]
│   └── [➕ Добавить] [✏️ Ред.]  [🗑 Удалить]
├── 🛒 Основная (Magnum) — 8 товаров
│   └── ...
└── [➕ Новая корзина]
```

### 6.3. Формат добавления товаров

Пользователь отправляет боту **ссылку** (или несколько ссылок, каждая с новой строки):

```
https://arbuz.kz/ru/almaty/catalog/item/233401-kukuruza_bonduelle_konservirovannaya_molodaya_425_ml 2
https://arbuz.kz/ru/almaty/catalog/item/56050-moloko_prostokvashino_2_5_950_ml 3
```

Для магнумовской корзины — ссылки с magnum.kz или kaspi.kz:

```
https://magnum.kz/products/143331?city=almaty 1
https://kaspi.kz/shop/p/bonduelle-kukuruza-sladkaja-425-ml-100980360?c=750000000 2
```

Формат: `<URL> [количество]` (количество по умолчанию = 1).

Бот валидирует:
- URL принадлежит arbuz.kz, magnum.kz или kaspi.kz/shop
- URL соответствует формату товара (не категории/главной)
- Для корзины `source=arbuz` — принимаются только ссылки arbuz.kz
- Для корзины `source=magnum` — принимаются ссылки magnum.kz **и** kaspi.kz/shop (оба допустимы в одной корзине)

### 6.4. URL-парсинг и валидация

```python
import re

URL_PATTERNS = {
    "arbuz": re.compile(
        r"https?://arbuz\.kz/ru/\w+/catalog/item/(\d+)-[\w-]+"
    ),
    "magnum": re.compile(
        r"https?://magnum\.kz/products/(\d+)"
    ),
    "kaspi": re.compile(
        r"https?://kaspi\.kz/shop/p/[\w-]+-(\d+)"
    ),
}

# Маппинг url_source → допустимый basket source
SOURCE_TO_BASKET = {
    "arbuz": "arbuz",
    "magnum": "magnum",
    "kaspi": "magnum",   # kaspi ссылки идут в магнумовскую корзину
}
```

---

## 7. Аналитика и отчёты

### 7.1. Ежедневный отчёт (автоматический)

Отправляется в `notify_time` пользователя после завершения парсинга:

```
📊 Отчёт за 30.03.2026

🛒 Недельная (Arbuz) — 12 товаров
━━━━━━━━━━━━━━━━━━━━━━━
1. Молоко Amiran 3.2% 0.8л × 2
   💰 890 ₸ → 1 780 ₸
2. Молоко Простоквашино 2.5% × 3
   💰 750 ₸ → 2 250 ₸  ⬇️ -50 ₸ (было 800 ₸)
3. Alpro миндальное 1л × 1
   💰 2 490 ₸  🔴 Нет в наличии!
...
━━━━━━━━━━━━━━━━━━━━━━━
💵 ИТОГО: 28 450 ₸ (вчера: 29 100 ₸, -650 ₸)

🛒 Основная (Magnum) — 8 товаров
━━━━━━━━━━━━━━━━━━━━━━━
...
💵 ИТОГО: 22 300 ₸ (вчера: 22 300 ₸, без изменений)

━━━━━━━━━━━━━━━━━━━━━━━
📊 СРАВНЕНИЕ:
Arbuz:  28 450 ₸
Magnum: 22 300 ₸
💡 Magnum дешевле на 6 150 ₸ (21.6%)
```

### 7.2. Отчёт об изменениях (`/changes`)

```
📈 Изменения цен за 7 дней

🔴 Подорожали:
  • Молоко Простоквашино: 700 ₸ → 800 ₸ (+14.3%)
  • Яйца 10 шт: 590 ₸ → 650 ₸ (+10.2%)

🟢 Подешевели:
  • Масло сливочное: 1200 ₸ → 990 ₸ (-17.5%)

⚪ Без изменений: 9 товаров
🔴 Пропали из наличия: 1 товар
  • Alpro миндальное 1л
```

### 7.3. Графики (`/chart`)

Генерируются через **matplotlib** и отправляются как фото:

- **Общий график корзины** — линия суммарной стоимости корзины по дням
- **График отдельного товара** — цена товара по дням (с отметками скидок)
- **Сравнительный график** — две линии: Arbuz vs Magnum (если есть корзины для обоих)

Параметры графика:
- Ось X: даты
- Ось Y: цена в тенге
- Маркеры на скидки (зелёные точки)
- Маркеры на отсутствие товара (красные X)

### 7.4. Экспорт CSV (`/export`)

```csv
date,basket,source,product,quantity,unit_price,total,available
2026-03-30,Недельная,arbuz,Молоко Amiran 3.2% 0.8л,2,890,1780,true
2026-03-30,Недельная,arbuz,Молоко Простоквашино 2.5%,3,750,2250,true
...
```

---

## 8. Scheduler

### Расписание

| Задача | Cron | Описание |
|--------|------|----------|
| `scrape_all` | `0 7 * * *` | Ежедневный парсинг всех активных корзин |
| `send_reports` | `0 9 * * *` | Отправка ежедневных отчётов (или по `notify_time` пользователя) |
| `cleanup_old` | `0 3 1 * *` | Удаление записей `price_history` старше 90 дней |

> Время парсинга (07:00) фиксировано для Алматы (`Asia/Almaty`). Отчёты отправляются после завершения парсинга.

---

## 9. Структура проекта

```
price-spy/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Точка входа, запуск бота + scheduler
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py          # /start, /help
│   │   ├── baskets.py        # /baskets, /new_basket, /switch, /delete_basket
│   │   ├── items.py          # /add, /remove, /list
│   │   ├── analytics.py      # /prices, /compare, /changes, /chart, /export
│   │   └── settings.py       # /notify
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── inline.py         # Inline-кнопки
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── auth.py           # Авто-регистрация пользователя
│   └── filters/
│       ├── __init__.py
│       └── url_filter.py     # Валидация ссылок arbuz/magnum
├── scraper/
│   ├── __init__.py
│   ├── base.py               # Базовый класс ScraperBase
│   ├── arbuz.py              # ArbuzScraper (Playwright)
│   ├── magnum.py             # MagnumScraper (Playwright)
│   ├── kaspi.py              # KaspiScraper (httpx + selectolax, без браузера)
│   ├── router.py             # Роутер: url_source → нужный scraper
│   └── stealth.py            # Playwright stealth настройки
├── analytics/
│   ├── __init__.py
│   ├── reports.py            # Формирование текстовых отчётов
│   ├── charts.py             # Генерация графиков (matplotlib)
│   ├── comparison.py         # Сравнение Arbuz vs Magnum
│   └── export.py             # CSV экспорт
├── scheduler/
│   ├── __init__.py
│   └── jobs.py               # APScheduler задачи
├── db/
│   ├── __init__.py
│   ├── models.py             # SQLAlchemy models
│   ├── repository.py         # CRUD операции
│   └── migrations/           # Alembic миграции
├── config.py                 # Pydantic Settings (env vars)
├── requirements.txt
├── Dockerfile
├── railway.toml
└── README.md
```

---

## 10. Конфигурация (env vars)

```env
# Telegram
TELEGRAM_BOT_TOKEN=...

# Database (Railway auto-provisions)
DATABASE_URL=postgresql://...

# Scraper
SCRAPE_CONCURRENCY=3         # Параллельные страницы
SCRAPE_TIMEOUT=30000         # Таймаут загрузки страницы (ms)
SCRAPE_RETRY_COUNT=3         # Количество ретраев
SCRAPE_DAILY_CRON=0 7 * * * # Время ежедневного парсинга

# Limits
MAX_BASKETS_PER_USER=10
MAX_ITEMS_PER_BASKET=50
PRICE_HISTORY_RETENTION_DAYS=90
```

---

## 11. Деплой на Railway

### Dockerfile

```dockerfile
FROM python:3.12-slim

# Playwright system dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .
CMD ["python", "-m", "bot.main"]
```

### railway.toml

```toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Ресурсы Railway

- **Web Service** — бот + scheduler (единый процесс)
- **PostgreSQL** — managed database (Railway plugin)
- **Ожидаемый расход:** ~$5–10/мес (Starter plan достаточно для одного пользователя)

---

## 12. Обработка ошибок

| Ситуация | Поведение |
|----------|-----------|
| Товар не найден (404 / пустая страница) | Записать `is_available = false`, уведомить пользователя |
| Сайт не отвечает (timeout) | 3 retry → если всё fail, пропустить товар, отправить warning |
| Изменился HTML (селекторы не найдены) | Логировать ошибку, отправить пользователю "⚠️ Не удалось получить цену для: ..." |
| Бот заблокирован пользователем | Деактивировать рассылку для этого user |
| Rate limit Telegram | Очередь отправки с задержкой между сообщениями |
| Railway container restart | APScheduler `jobstores` в PostgreSQL → задачи не теряются |

---

## 13. Безопасность и лимиты

- Бот **персональный** (single-user), но архитектура multi-user ready
- Rate limiting на `/scrape`: 1 вызов в час
- Максимум 10 корзин × 50 товаров = 500 товаров на парсинг
- Playwright запускается **без GPU, без sandbox** (Railway контейнер)
- Не хранить чувствительные данные пользователя кроме Telegram ID

---

## 14. Roadmap

### MVP (v0.1)

- [x] Создание/удаление корзин
- [x] Добавление товаров по URL
- [x] Парсинг цен Arbuz + Magnum через Playwright
- [x] Ежедневный отчёт с ценами
- [x] Деплой на Railway

### v0.2

- [ ] Изменения цен (было/стало)
- [ ] Сравнение Arbuz vs Magnum
- [ ] Inline-кнопки навигации

### v0.3

- [ ] Графики цен (matplotlib)
- [ ] CSV экспорт
- [ ] Настройка времени рассылки

### v0.4 (оптимизация)

- [ ] Переход на прямые API-запросы (если найдутся стабильные эндпоинты)
- [ ] Кэширование названий товаров
- [ ] Алерты: "Товар X подешевел на >10%!"
- [ ] Поиск товара по названию (без ссылки)

---

## 15. Зависимости (requirements.txt)

```
aiogram>=3.4
playwright>=1.40
httpx>=0.27               # Для Kaspi (SSR) — быстрый async HTTP
selectolax>=0.3           # Быстрый HTML-парсер для Kaspi
apscheduler>=3.10
sqlalchemy>=2.0
asyncpg>=0.29
alembic>=1.13
pydantic-settings>=2.0
matplotlib>=3.8
```