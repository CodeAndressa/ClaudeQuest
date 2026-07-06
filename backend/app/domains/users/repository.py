from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.model import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def touch_last_login(self, user: User, when: datetime) -> None:
        user.last_login = when
        await self._session.flush()
