from uuid import UUID

from app.core.security import hash_password
from app.domains.admin.repository import AdminRepository
from app.domains.admin.schemas import (
    AdminCertificateItem,
    AdminOverview,
    AdminTrackItem,
    AdminUserItem,
)
from app.domains.gamification.badges import UserBadge
from app.domains.gamification.certificates import UserCertificate
from app.domains.learning.model import Lesson, Track, UserLessonProgress
from app.domains.users.model import User, UserRole, UserStatus
from app.shared.errors import AppError

_USER_NOT_FOUND = AppError(
    code="user_not_found", message="Usuário não encontrado.", status_code=404
)
_TRACK_NOT_FOUND = AppError(
    code="track_not_found", message="Trilha não encontrada.", status_code=404
)
_SELF_STATUS_CHANGE = AppError(
    code="self_status_change",
    message="Você não pode alterar o status da própria conta administrativa.",
    status_code=409,
)
_EMAIL_IN_USE = AppError(
    code="email_in_use", message="Já existe um usuário com este e-mail.", status_code=409
)


class AdminService:
    def __init__(self, repository: AdminRepository) -> None:
        self._repository = repository

    async def overview(self) -> AdminOverview:
        return AdminOverview(
            users=await self._repository.count(User, User.deleted_at.is_(None)),
            active_users=await self._repository.count(
                User, User.deleted_at.is_(None), User.status == UserStatus.ACTIVE
            ),
            tracks=await self._repository.count(Track, Track.deleted_at.is_(None)),
            published_tracks=await self._repository.count(
                Track, Track.deleted_at.is_(None), Track.is_active.is_(True)
            ),
            lessons=await self._repository.count(Lesson, Lesson.deleted_at.is_(None)),
            lesson_completions=await self._repository.count(
                UserLessonProgress, UserLessonProgress.deleted_at.is_(None)
            ),
            issued_certificates=await self._repository.count(
                UserCertificate, UserCertificate.deleted_at.is_(None)
            ),
            awarded_badges=await self._repository.count(UserBadge, UserBadge.deleted_at.is_(None)),
        )

    async def list_users(self) -> list[AdminUserItem]:
        users = await self._repository.list_users()
        progress, certificates = await self._repository.user_learning_counts()
        return [
            AdminUserItem(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                status=user.status,
                last_login=user.last_login,
                completed_lessons=progress.get(user.id, 0),
                certificates=certificates.get(user.id, 0),
            )
            for user in users
        ]

    async def create_user(
        self,
        *,
        organization_id: UUID,
        name: str,
        email: str,
        password: str,
        role: UserRole,
    ) -> AdminUserItem:
        normalized_email = email.strip().lower()
        if await self._repository.get_user_by_email(normalized_email) is not None:
            raise _EMAIL_IN_USE
        user = await self._repository.create_user(
            User(
                organization_id=organization_id,
                name=name.strip(),
                email=normalized_email,
                password_hash=hash_password(password),
                role=role,
                status=UserStatus.ACTIVE,
                email_verified=True,
            )
        )
        await self._repository.commit()
        return AdminUserItem(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            status=user.status,
            last_login=None,
            completed_lessons=0,
            certificates=0,
        )

    async def update_user_status(
        self, *, actor_id: UUID, user_id: UUID, status: UserStatus
    ) -> AdminUserItem:
        if actor_id == user_id:
            raise _SELF_STATUS_CHANGE
        user = await self._repository.get_user(user_id)
        if user is None:
            raise _USER_NOT_FOUND
        await self._repository.update_user_status(user, status)
        await self._repository.commit()
        progress, certificates = await self._repository.user_learning_counts()
        return AdminUserItem(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            status=user.status,
            last_login=user.last_login,
            completed_lessons=progress.get(user.id, 0),
            certificates=certificates.get(user.id, 0),
        )

    async def list_tracks(self) -> list[AdminTrackItem]:
        tracks = await self._repository.list_tracks()
        lessons, completions = await self._repository.track_counts()
        return [
            AdminTrackItem(
                id=track.id,
                title=track.title,
                difficulty=track.difficulty,
                estimated_hours=track.estimated_hours,
                is_active=track.is_active,
                lessons=lessons.get(track.id, 0),
                completions=completions.get(track.id, 0),
            )
            for track in tracks
        ]

    async def update_track_status(self, *, track_id: UUID, is_active: bool) -> AdminTrackItem:
        track = await self._repository.get_track(track_id)
        if track is None:
            raise _TRACK_NOT_FOUND
        await self._repository.update_track_status(track, is_active)
        await self._repository.commit()
        lessons, completions = await self._repository.track_counts()
        return AdminTrackItem(
            id=track.id,
            title=track.title,
            difficulty=track.difficulty,
            estimated_hours=track.estimated_hours,
            is_active=track.is_active,
            lessons=lessons.get(track.id, 0),
            completions=completions.get(track.id, 0),
        )

    async def list_certificates(self) -> list[AdminCertificateItem]:
        rows = await self._repository.list_certificates()
        return [
            AdminCertificateItem(
                id=issued.id,
                title=certificate.title,
                user_name=user.name,
                user_email=user.email,
                issued_at=issued.issued_at,
                validation_code=issued.validation_code,
            )
            for issued, certificate, user in rows
        ]
