from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.repositories.user import UserRepository


class I18nMiddleware(BaseMiddleware):
    """Load user from DB and inject language context into handler data.

    Provides ``user``, ``user_repo``, and ``lang`` keys in handler data.
    If no user exists yet (new visitor), ``user`` is None and ``lang``
    defaults to ``"en"`` for the language-selection prompt.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]
        repo = UserRepository(session)

        # Extract Telegram user from event
        telegram_user = data.get("event_from_user")
        if telegram_user is None:
            return await handler(event, data)

        user = await repo.get_by_telegram_id(telegram_user.id)
        data["user"] = user
        data["user_repo"] = repo

        if user:
            data["lang"] = user.language
        else:
            # No user in DB -- default for language-selection prompts (D-06)
            data["lang"] = "en"

        return await handler(event, data)
