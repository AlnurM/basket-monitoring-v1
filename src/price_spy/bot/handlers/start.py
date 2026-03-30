from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.user import User
from price_spy.db.repositories.user import UserRepository
from price_spy.i18n import get_text

router = Router(name="start")


def _language_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский", callback_data="lang:ru")
    builder.button(text="English", callback_data="lang:en")
    builder.adjust(2)
    return builder


@router.message(Command("start"))
async def cmd_start(message: Message, user: User | None, lang: str, **kwargs: object) -> None:
    """D-06: Always show language selection on /start. If user exists, this re-shows it."""
    kb = _language_keyboard()
    await message.answer(
        get_text("choose_language", lang),
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def callback_language(
    callback: CallbackQuery,
    user: User | None,
    user_repo: UserRepository,
    session: AsyncSession,
    **kwargs: object,
) -> None:
    """Handle language selection. Creates user if new, updates if existing."""
    lang_code = callback.data.split(":")[1]  # "ru" or "en"

    if user is None:
        # New user registration (USER-01 + USER-02)
        user, _ = await user_repo.get_or_create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            language=lang_code,
        )
        await callback.message.edit_text(get_text("language_set", lang_code))
        await callback.message.answer(get_text("welcome", lang_code))
    else:
        # Existing user switching language (USER-03)
        await user_repo.update_language(user, lang_code)
        await callback.message.edit_text(get_text("language_switched", lang_code))

    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, user: User | None, lang: str, **kwargs: object) -> None:
    """USER-04: Show available commands in user's language."""
    if user is None:
        # D-06: force language selection first
        kb = _language_keyboard()
        await message.answer(get_text("choose_language", lang), reply_markup=kb.as_markup())
        return
    await message.answer(get_text("help", lang))


@router.message(Command("language"))
async def cmd_language(message: Message, lang: str, **kwargs: object) -> None:
    """USER-03: Show language selection keyboard."""
    kb = _language_keyboard()
    await message.answer(get_text("choose_language", lang), reply_markup=kb.as_markup())
