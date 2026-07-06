from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.learning.model import Alternative, Lesson, Level, Module, Question, Track


class TrackRepository:
    """Repositório somente-leitura de trilhas (CRUD de escrita fica para o Admin Portal)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[Track]:
        statement = (
            select(Track)
            .where(Track.is_active.is_(True), Track.deleted_at.is_(None))
            .order_by(Track.order)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_detail_by_id(self, track_id: UUID) -> Track | None:
        statement = (
            select(Track)
            .where(Track.id == track_id, Track.deleted_at.is_(None))
            .options(
                selectinload(Track.modules.and_(Module.deleted_at.is_(None)))
                .selectinload(Module.levels.and_(Level.deleted_at.is_(None)))
                .selectinload(Level.lessons.and_(Lesson.deleted_at.is_(None)))
                .selectinload(Lesson.questions.and_(Question.deleted_at.is_(None)))
                .selectinload(Question.alternatives.and_(Alternative.deleted_at.is_(None)))
            )
        )
        result = await self._session.execute(statement)
        return result.unique().scalar_one_or_none()
