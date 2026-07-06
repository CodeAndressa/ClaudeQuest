import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.learning.model import Level, Module, Track
from app.domains.learning.repository import TrackRepository
from app.domains.learning.service import LearningService
from app.shared.errors import AppError


def _build_service(session: AsyncSession) -> LearningService:
    return LearningService(TrackRepository(session))


async def _create_track(session: AsyncSession, *, is_active: bool = True) -> Track:
    track = Track(
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
    service = _build_service(db_session)

    tracks = await service.list_tracks()

    assert track.id in [t.id for t in tracks]


async def test_get_track_detail_returns_the_track(db_session: AsyncSession) -> None:
    track = await _create_track(db_session)
    module = Module(track_id=track.id, title="Introdução", description="Básico", order=1)
    db_session.add(module)
    await db_session.flush()
    db_session.add(
        Level(
            module_id=module.id,
            title="Nível 1",
            description="Introdução",
            level_number=1,
        )
    )
    await db_session.flush()
    service = _build_service(db_session)

    result = await service.get_track_detail(track.id)

    assert result.id == track.id
    assert len(result.modules) == 1


async def test_get_track_detail_raises_when_not_found(db_session: AsyncSession) -> None:
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.get_track_detail(uuid.uuid4())

    assert exc_info.value.code == "track_not_found"
    assert exc_info.value.status_code == 404


async def test_get_track_detail_raises_when_inactive(db_session: AsyncSession) -> None:
    track = await _create_track(db_session, is_active=False)
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.get_track_detail(track.id)

    assert exc_info.value.code == "track_not_found"
