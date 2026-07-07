import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.gamification.repository import XpLedgerRepository
from app.domains.learning.model import Lesson, Level, Module, School, Track
from app.domains.learning.repository import (
    LessonProgressRepository,
    LessonRepository,
    SchoolRepository,
    TrackRepository,
)
from app.domains.learning.service import LearningService
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole
from app.shared.errors import AppError


def _build_service(session: AsyncSession) -> LearningService:
    return LearningService(
        SchoolRepository(session),
        TrackRepository(session),
        LessonRepository(session),
        LessonProgressRepository(session),
        XpLedgerRepository(session),
    )



async def _create_user(
    session: AsyncSession, *, email: str = "learner-service@claudequest.dev"
) -> User:
    organization = Organization(name="Org Learning", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()
    user = User(
        organization_id=organization.id,
        name="Learner",
        email=email,
        password_hash="hash-for-service-test",
        role=UserRole.STUDENT,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_school(session: AsyncSession, *, title: str = "Claude Academy") -> School:
    school = School(
        title=title,
        slug=f"{title.lower().replace(' ', '-')}-{uuid.uuid4()}",
        description="Escola de IA aplicada.",
        order=1,
        is_active=True,
    )
    session.add(school)
    await session.flush()
    return school


async def _create_track(session: AsyncSession, *, is_active: bool = True) -> Track:
    school = await _create_school(session)
    track = Track(
        school_id=school.id,
        title="Claude Code",
        description="Especialista em desenvolvimento assistido por IA.",
        difficulty="advanced",
        estimated_hours=8,
        order=2,
        is_active=is_active,
    )
    session.add(track)
    await session.flush()
    return track


async def test_list_tracks_returns_active_tracks(db_session: AsyncSession) -> None:
    track = await _create_track(db_session)
    user = await _create_user(db_session)
    service = _build_service(db_session)

    tracks = await service.list_tracks(user.id)

    assert track.id in [t.id for t in tracks]
    result = next(t for t in tracks if t.id == track.id)
    assert result.total_lessons == 0
    assert result.completed_lessons == 0
    assert result.progress_percent == 0


async def test_list_schools_returns_active_schools_with_track_count(
    db_session: AsyncSession,
) -> None:
    track = await _create_track(db_session)
    service = _build_service(db_session)

    schools = await service.list_schools()

    result = next(school for school in schools if school.id == track.school_id)
    assert result.title == "Claude Academy"
    assert result.track_count == 1


async def test_get_track_detail_returns_the_track(db_session: AsyncSession) -> None:
    track = await _create_track(db_session)
    module = Module(track_id=track.id, title="IntroduÃ§Ã£o", description="BÃ¡sico", order=1)
    db_session.add(module)
    await db_session.flush()
    db_session.add(
        Level(
            module_id=module.id,
            title="NÃ­vel 1",
            description="IntroduÃ§Ã£o",
            level_number=1,
        )
    )
    await db_session.flush()
    user = await _create_user(db_session)
    service = _build_service(db_session)

    result = await service.get_track_detail(track_id=track.id, user_id=user.id)

    assert result.id == track.id
    assert len(result.modules) == 1
    assert result.total_lessons == 0
    assert result.completed_lessons == 0
    assert result.progress_percent == 0


async def test_get_track_detail_raises_when_not_found(db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.get_track_detail(track_id=uuid.uuid4(), user_id=user.id)

    assert exc_info.value.code == "track_not_found"
    assert exc_info.value.status_code == 404


async def test_get_track_detail_raises_when_inactive(db_session: AsyncSession) -> None:
    track = await _create_track(db_session, is_active=False)
    user = await _create_user(db_session)
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.get_track_detail(track_id=track.id, user_id=user.id)

    assert exc_info.value.code == "track_not_found"


async def test_complete_lesson_awards_xp_once(db_session: AsyncSession) -> None:
    track = await _create_track(db_session)
    module = Module(track_id=track.id, title="Interface", description="Basico", order=1)
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="Nivel 1", description="Intro", level_number=1)
    db_session.add(level)
    await db_session.flush()
    lesson = Lesson(
        level_id=level.id,
        title="Missao 1",
        description="Primeira missao",
        content="Conteudo",
        order=1,
        xp=35,
    )
    db_session.add(lesson)
    await db_session.flush()
    service = _build_service(db_session)
    user = await _create_user(db_session)

    first = await service.complete_lesson(user_id=user.id, lesson_id=lesson.id)
    second = await service.complete_lesson(user_id=user.id, lesson_id=lesson.id)
    track_detail = await service.get_track_detail(track_id=track.id, user_id=user.id)
    track_summaries = await service.list_tracks(user.id)
    track_summary = next(item for item in track_summaries if item.id == track.id)

    assert first.completed is True
    assert first.already_completed is False
    assert first.xp_granted == 35
    assert first.total_xp == 35
    assert second.completed is True
    assert second.already_completed is True
    assert second.xp_granted == 0
    assert second.total_xp == 35
    assert track_detail.completed_lessons == 1
    assert track_detail.progress_percent == 100
    assert track_detail.modules[0].levels[0].lessons[0].completed is True
    assert track_summary.completed_lessons == 1
    assert track_summary.progress_percent == 100


async def test_complete_lesson_raises_when_not_found(db_session: AsyncSession) -> None:
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.complete_lesson(user_id=uuid.uuid4(), lesson_id=uuid.uuid4())

    assert exc_info.value.code == "lesson_not_found"
    assert exc_info.value.status_code == 404
