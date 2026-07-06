from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.gamification.model import XpLedger


class XpLedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_entry(self, *, user_id: UUID, amount: int, reason: str) -> XpLedger:
        entry = XpLedger(user_id=user_id, amount=amount, reason=reason)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_total_xp(self, user_id: UUID) -> int:
        statement = select(func.coalesce(func.sum(XpLedger.amount), 0)).where(
            XpLedger.user_id == user_id
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())
