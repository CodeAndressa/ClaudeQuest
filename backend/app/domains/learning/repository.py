from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.learning.model import (
    Alternative,
    Lesson,
    Level,
    Module,
    Question,
    Track,
    UserLessonProgress,
)


class TrackRepository:
    """Repositorio de trilhas (CRUD de escrita fica para o Admin Portal)."""

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


class LessonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lesson_id: UUID) -> Lesson | None:
        statement = select(Lesson).where(Lesson.id == lesson_id, Lesson.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()


class LessonProgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user_and_lesson(
        self, *, user_id: UUID, lesson_id: UUID
    ) -> UserLessonProgress | None:
        statement = select(UserLessonProgress).where(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
            UserLessonProgress.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self, *, user_id: UUID, lesson_id: UUID, xp_awarded: int
    ) -> UserLessonProgress:
        progress = UserLessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            completed_at=datetime.now(UTC),
            xp_awarded=xp_awarded,
        )
        self._session.add(progress)
        await self._session.flush()
        return progress
