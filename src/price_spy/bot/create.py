from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from price_spy.bot.handlers import basket, start
from price_spy.bot.middlewares.db import DbSessionMiddleware
from price_spy.bot.middlewares.i18n import I18nMiddleware
from price_spy.config import settings


def create_bot() -> Bot:
    """Create a Bot instance with HTML parse mode."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create a Dispatcher with DB and i18n middlewares and all routers."""
    dp = Dispatcher()

    # Register middlewares (outer middleware runs first)
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(basket.router)

    return dp
