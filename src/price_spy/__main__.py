"""Entry point: python -m price_spy

Wires bot + browser + scheduler in a single process (INFR-01).
Startup validation fails fast if any dependency is unavailable (D-10).
"""

import asyncio
import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from price_spy.bot.create import create_bot, create_dispatcher
from price_spy.config import Settings, settings
from price_spy.db.engine import engine
from price_spy.scrapers.browser import browser_manager

logger = logging.getLogger(__name__)


async def validate_startup(cfg: Settings) -> None:
    """Fail fast if any dependency is unavailable. Per D-10."""
    from sqlalchemy import text

    # 1. DB connection test
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Startup check: DB connection OK")

    # 2. Playwright browser test
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    )
    await browser.close()
    await pw.stop()
    logger.info("Startup check: Playwright Chromium OK")

    # 3. Bot token test
    from aiogram import Bot

    bot = Bot(token=cfg.bot_token)
    me = await bot.get_me()
    await bot.session.close()
    logger.info("Startup check: Bot token OK (@%s)", me.username)


async def daily_scrape() -> None:
    """REPT-01: Scrape all active baskets daily. Per D-01, D-02."""
    from price_spy.services.daily_scrape import scrape_all_baskets

    logger.info("Daily scrape starting...")
    try:
        results = await scrape_all_baskets()
        total_items = sum(len(r) for r in results.values())
        logger.info(
            "Daily scrape complete: %d baskets, %d items",
            len(results),
            total_items,
        )
    except Exception:
        logger.exception("Daily scrape failed")


async def deliver_reports() -> None:
    """REPT-02: Check for users due for notification and send reports. Per D-09."""
    import datetime
    import zoneinfo

    from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

    from price_spy.db.engine import async_session
    from price_spy.db.repositories.user import UserRepository
    from price_spy.services.message_utils import split_message
    from price_spy.services.report import generate_user_report

    tz = zoneinfo.ZoneInfo("Asia/Almaty")
    now = datetime.datetime.now(tz)
    current_time = now.time().replace(second=0, microsecond=0)

    bot = deliver_reports._bot  # type: ignore[attr-defined]  # Set during main()

    async with async_session() as session:
        user_repo = UserRepository(session)
        users = await user_repo.get_users_by_notify_time(current_time)

        if not users:
            return

        logger.info("Delivering reports to %d user(s) at %s", len(users), current_time)

        for user in users:
            try:
                report = await generate_user_report(session, user)
                if not report:
                    continue
                parts = split_message(report)
                for part in parts:
                    await bot.send_message(chat_id=user.telegram_id, text=part)
                await asyncio.sleep(1)  # Flood control: 1s between users (Pitfall 2)
            except TelegramForbiddenError:
                logger.warning(
                    "User %d blocked bot, skipping report", user.telegram_id
                )
            except TelegramRetryAfter as e:
                logger.warning("Rate limited, sleeping %ds", e.retry_after)
                await asyncio.sleep(e.retry_after)
            except Exception:
                logger.exception(
                    "Failed to deliver report to user %d", user.telegram_id
                )


async def cleanup_old_prices() -> None:
    """HIST-03: Delete price_history records older than retention_days. Runs monthly on 1st at 03:00."""
    from price_spy.db.engine import async_session
    from price_spy.db.repositories.price_history import PriceHistoryRepository

    async with async_session() as session:
        repo = PriceHistoryRepository(session)
        count = await repo.cleanup_old_records(settings.price_history_retention_days)
        await session.commit()
        logger.info(
            "HIST-03: Cleaned up %d old price history records (>%d days)",
            count,
            settings.price_history_retention_days,
        )


async def on_startup(dispatcher: object) -> None:
    """Start browser and scheduler. Registered as aiogram startup hook."""
    # Start Playwright browser (SCRP-08: reuse browser instance)
    await browser_manager.start()
    logger.info("BrowserManager started in on_startup")

    # Initialize APScheduler with PostgreSQL jobstore (INFR-05)
    # Pitfall 3: must be inside running event loop
    # Pitfall 4: SQLAlchemyJobStore needs sync URL (APScheduler 3.x limitation)
    jobstores = {
        "default": SQLAlchemyJobStore(url=settings.database_url_sync),
    }
    scheduler = AsyncIOScheduler(timezone="Asia/Almaty", jobstores=jobstores)
    scheduler.add_job(
        daily_scrape,
        trigger=CronTrigger(hour=settings.scrape_daily_hour, minute=0),
        id="daily_scrape",
        replace_existing=True,
        misfire_grace_time=900,
        coalesce=True,
    )
    scheduler.add_job(
        deliver_reports,
        trigger=IntervalTrigger(minutes=1),
        id="deliver_reports",
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
    )
    scheduler.add_job(
        cleanup_old_prices,
        trigger=CronTrigger(day=1, hour=3, minute=0),
        id="cleanup_prices",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "APScheduler started (daily scrape at %02d:00 Asia/Almaty, "
        "report delivery every minute, monthly cleanup on 1st at 03:00)",
        settings.scrape_daily_hour,
    )

    # Store scheduler reference for shutdown access
    on_startup._scheduler = scheduler  # type: ignore[attr-defined]


async def on_shutdown(dispatcher: object) -> None:
    """Clean up browser, scheduler, and DB engine."""
    # Shut down scheduler
    scheduler = getattr(on_startup, "_scheduler", None)
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down")

    # Close browser
    await browser_manager.close()
    logger.info("BrowserManager closed in on_shutdown")

    # Dispose DB engine
    await engine.dispose()
    logger.info("DB engine disposed")


async def main() -> None:
    """Application entry point.

    Sequence: validate -> create bot/dp -> register hooks -> start polling.
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    logger.info("price-spy starting...")

    # D-10: Fail fast if any dependency is unavailable
    await validate_startup(settings)

    # Create bot and dispatcher
    bot = create_bot()
    deliver_reports._bot = bot  # type: ignore[attr-defined]
    dp = create_dispatcher()

    # Register lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling (INFR-01: single process)
    logger.info("Starting aiogram polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
