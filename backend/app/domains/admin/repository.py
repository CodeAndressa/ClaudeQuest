from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.gamification.certificates import Certificate, UserCertificate
from app.domains.learning.model import Lesson, Level, Module, Track, UserLessonProgress
from app.domains.users.model import User, UserStatus


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count(self, model: type[Any], *conditions: ColumnElement[bool]) -> int:
        statement = select(func.count()).select_from(model).where(*conditions)
        value = await self._session.scalar(statement)
        return int(value or 0)

    async def list_users(self) -> list[User]:
        result = await self._session.execute(
            select(User).where(User.deleted_at.is_(None)).order_by(User.name, User.email)
        )
        return list(result.scalars().all())

    async def get_user(self, user_id: UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_user_status(self, user: User, status: UserStatus) -> None:
        user.status = status
        await self._session.flush()

    async def user_learning_counts(self) -> tuple[dict[UUID, int], dict[UUID, int]]:
        progress_rows = await self._session.execute(
            select(UserLessonProgress.user_id, func.count(UserLessonProgress.id))
            .where(UserLessonProgress.deleted_at.is_(None))
            .group_by(UserLessonProgress.user_id)
        )
        certificate_rows = await self._session.execute(
            select(UserCertificate.user_id, func.count(UserCertificate.id))
            .where(UserCertificate.deleted_at.is_(None))
            .group_by(UserCertificate.user_id)
        )
        return (
            {user_id: int(total) for user_id, total in progress_rows.all()},
            {user_id: int(total) for user_id, total in certificate_rows.all()},
        )

    async def list_tracks(self) -> list[Track]:
        result = await self._session.execute(
            select(Track).where(Track.deleted_at.is_(None)).order_by(Track.order)
        )
        return list(result.scalars().all())

    async def get_track(self, track_id: UUID) -> Track | None:
        result = await self._session.execute(
            select(Track).where(Track.id == track_id, Track.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def update_track_status(self, track: Track, is_active: bool) -> None:
        track.is_active = is_active
        await self._session.flush()

    async def track_counts(self) -> tuple[dict[UUID, int], dict[UUID, int]]:
        lesson_rows = await self._session.execute(
            select(Module.track_id, func.count(Lesson.id))
            .join(Level, Level.module_id == Module.id)
            .join(Lesson, Lesson.level_id == Level.id)
            .where(
                Module.deleted_at.is_(None),
                Level.deleted_at.is_(None),
                Lesson.deleted_at.is_(None),
            )
            .group_by(Module.track_id)
        )
        completion_rows = await self._session.execute(
            select(Module.track_id, func.count(UserLessonProgress.id))
            .join(Level, Level.module_id == Module.id)
            .join(Lesson, Lesson.level_id == Level.id)
            .join(UserLessonProgress, UserLessonProgress.lesson_id == Lesson.id)
            .where(UserLessonProgress.deleted_at.is_(None))
            .group_by(Module.track_id)
        )
        return (
            {track_id: int(total) for track_id, total in lesson_rows.all()},
            {track_id: int(total) for track_id, total in completion_rows.all()},
        )

    async def list_certificates(
        self,
    ) -> list[tuple[UserCertificate, Certificate, User]]:
        result = await self._session.execute(
            select(UserCertificate, Certificate, User)
            .join(Certificate, Certificate.id == UserCertificate.certificate_id)
            .join(User, User.id == UserCertificate.user_id)
            .where(
                UserCertificate.deleted_at.is_(None),
                Certificate.deleted_at.is_(None),
                User.deleted_at.is_(None),
            )
            .order_by(UserCertificate.issued_at.desc())
        )
        return [(row.UserCertificate, row.Certificate, row.User) for row in result]

    async def commit(self) -> None:
        await self._session.commit()
