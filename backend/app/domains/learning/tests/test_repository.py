from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.learning.model import (
    Alternative,
    Lesson,
    Level,
    Module,
    Question,
    QuestionType,
    School,
    Track,
)
from app.domains.learning.repository import SchoolRepository, TrackRepository


async def _create_school(session: AsyncSession, *, title: str = "Claude Academy") -> School:
    school = School(
        title=title,
        slug=title.lower().replace(" ", "-"),
        description="Escola de IA aplicada.",
        order=1,
        is_active=True,
    )
    session.add(school)
    await session.flush()
    return school


async def _create_full_track(session: AsyncSession, *, title: str = "Claude Chat") -> Track:
    school = await _create_school(session, title=f"Escola {title}")
    track = Track(
        school_id=school.id,
        title=title,
        description="Domine completamente o Claude Chat.",
        difficulty="beginner",
        estimated_hours=4,
        order=1,
    )
    session.add(track)
    await session.flush()

    module = Module(
        track_id=track.id, title="Interface", description="Conheça a interface.", order=1
    )
    session.add(module)
    await session.flush()

    level = Level(
        module_id=module.id,
        title="Nível 1",
        description="Introdução",
        level_number=1,
        estimated_minutes=10,
        xp=10,
    )
    session.add(level)
    await session.flush()

    lesson = Lesson(
        level_id=level.id,
        title="Missão 1",
        description="Primeira missão",
        content="Conteúdo da missão",
        order=1,
        xp=5,
    )
    session.add(lesson)
    await session.flush()

    question = Question(
        lesson_id=lesson.id,
        question="Qual o objetivo do Claude Chat?",
        question_type=QuestionType.MULTIPLE_CHOICE,
        order=1,
    )
    session.add(question)
    await session.flush()

    session.add_all(
        [
            Alternative(
                question_id=question.id, text="Conversar com Claude", is_correct=True, order=1
            ),
            Alternative(
                question_id=question.id, text="Editar planilhas", is_correct=False, order=2
            ),
        ]
    )
    await session.flush()

    return track


async def test_list_active_returns_only_active_tracks_ordered(db_session: AsyncSession) -> None:
    active_track = await _create_full_track(db_session, title="Claude Chat")
    inactive_school = await _create_school(db_session, title="Escola Inativa")
    inactive_track = Track(
        school_id=inactive_school.id,
        title="Trilha Inativa",
        description="Não deve aparecer.",
        difficulty="beginner",
        estimated_hours=1,
        order=0,
        is_active=False,
    )
    db_session.add(inactive_track)
    await db_session.flush()

    repository = TrackRepository(db_session)
    tracks = await repository.list_active()

    ids = [track.id for track in tracks]
    assert active_track.id in ids
    assert inactive_track.id not in ids


async def test_list_active_filters_tracks_by_school(db_session: AsyncSession) -> None:
    first_track = await _create_full_track(db_session, title="Claude Chat")
    second_track = await _create_full_track(db_session, title="Claude Code")

    repository = TrackRepository(db_session)
    tracks = await repository.list_active(school_id=first_track.school_id)

    assert [track.id for track in tracks] == [first_track.id]
    assert second_track.id not in [track.id for track in tracks]


async def test_list_schools_returns_active_schools_ordered(db_session: AsyncSession) -> None:
    await _create_school(db_session, title="Escola B")
    first = await _create_school(db_session, title="Escola A")
    first.order = 0
    inactive = await _create_school(db_session, title="Escola Inativa")
    inactive.is_active = False
    await db_session.flush()

    repository = SchoolRepository(db_session)
    schools = await repository.list_active()

    assert [school.title for school in schools] == ["Escola A", "Escola B"]
    assert inactive.id not in [school.id for school in schools]


async def test_list_active_excludes_soft_deleted_tracks(db_session: AsyncSession) -> None:
    from datetime import UTC, datetime

    track = await _create_full_track(db_session, title="Trilha Deletada")
    track.deleted_at = datetime.now(UTC)
    await db_session.flush()

    repository = TrackRepository(db_session)
    tracks = await repository.list_active()

    assert track.id not in [t.id for t in tracks]


async def test_get_detail_by_id_returns_full_hierarchy(db_session: AsyncSession) -> None:
    track = await _create_full_track(db_session)
    repository = TrackRepository(db_session)

    result = await repository.get_detail_by_id(track.id)

    assert result is not None
    assert len(result.modules) == 1
    assert len(result.modules[0].levels) == 1
    assert len(result.modules[0].levels[0].lessons) == 1
    assert len(result.modules[0].levels[0].lessons[0].questions) == 1
    assert len(result.modules[0].levels[0].lessons[0].questions[0].alternatives) == 2


async def test_get_detail_by_id_returns_none_when_not_found(db_session: AsyncSession) -> None:
    import uuid

    repository = TrackRepository(db_session)

    result = await repository.get_detail_by_id(uuid.uuid4())

    assert result is None


async def test_get_detail_by_id_returns_none_when_soft_deleted(db_session: AsyncSession) -> None:
    from datetime import UTC, datetime

    track = await _create_full_track(db_session, title="Trilha Deletada Detalhe")
    track.deleted_at = datetime.now(UTC)
    await db_session.flush()

    repository = TrackRepository(db_session)
    result = await repository.get_detail_by_id(track.id)

    assert result is None
