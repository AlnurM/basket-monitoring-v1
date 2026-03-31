"""Settings handlers: /notify command for notification time management."""

import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.user import User
from price_spy.i18n import get_text

router = Router(name="settings")


@router.message(Command("notify"))
async def cmd_notify(
    message: Message,
    session: AsyncSession,
    user: User | None,
    lang: str,
    **kwargs: object,
) -> None:
    """REPT-07/REPT-08: Set or display notification time."""
    if user is None:
        await message.answer(get_text("please_select_language", lang))
        return

    # Parse argument from /notify HH:MM
    raw_text = message.text or ""
    parts = raw_text.strip().split(maxsplit=1)

    if len(parts) < 2:
        # No argument: show current time + usage
        current = user.notify_time.strftime("%H:%M") if user.notify_time else "09:00"
        await message.answer(
            get_text("notify_current", lang, time=current)
            + "\n\n"
            + get_text("notify_usage", lang)
        )
        return

    time_str = parts[1].strip()

    # Validate HH:MM format
    time_parts = time_str.split(":")
    if len(time_parts) != 2:
        await message.answer(get_text("notify_invalid_format", lang))
        return

    try:
        hour = int(time_parts[0])
        minute = int(time_parts[1])
    except ValueError:
        await message.answer(get_text("notify_invalid_format", lang))
        return

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await message.answer(get_text("notify_invalid_format", lang))
        return

    new_time = datetime.time(hour, minute)
    user.notify_time = new_time
    await session.flush()

    await message.answer(
        get_text("notify_updated", lang, time=new_time.strftime("%H:%M"))
    )
