from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, telegram_id: int, username: str | None, language: str
    ) -> User:
        user = User(telegram_id=telegram_id, username=username, language=language)
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_language(self, user: User, language: str) -> User:
        user.language = language
        await self._session.flush()
        return user

    async def get_or_create(
        self, telegram_id: int, username: str | None, language: str
    ) -> tuple[User, bool]:
        """Returns (user, created) tuple."""
        existing = await self.get_by_telegram_id(telegram_id)
        if existing:
            return existing, False
        new_user = await self.create(telegram_id, username, language)
        return new_user, True
