import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.learning.model import (
    Alternative,
    Lesson,
    Level,
    Module,
    Question,
    Track,
)
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole


async def _create_user_and_login(
    client: httpx.AsyncClient, session: AsyncSession, *, email: str
) -> str:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    password = "senha-correta"
    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password(password),
        role=UserRole.STUDENT,
    )
    session.add(user)
    await session.flush()

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token: str = login_response.json()["data"]["access_token"]
    return token


async def _create_track_with_hierarchy(session: AsyncSession) -> Track:
    track = Track(
        title="Claude Chat",
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
    )
    session.add(level)
    await session.flush()

    lesson = Lesson(
        level_id=level.id,
        title="Missão 1",
        description="Primeira missão",
        content="Conteúdo da missão",
        order=1,
    )
    session.add(lesson)
    await session.flush()

    question = Question(lesson_id=lesson.id, question="Pergunta?", order=1)
    session.add(question)
    await session.flush()

    session.add(
        Alternative(question_id=question.id, text="Resposta certa", is_correct=True, order=1)
    )
    await session.flush()

    return track


async def test_list_tracks_requires_authentication(client_with_db: httpx.AsyncClient) -> None:
    response = await client_with_db.get("/api/v1/learning/tracks")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_list_tracks_returns_active_tracks(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    track = await _create_track_with_hierarchy(db_session)
    token = await _create_user_and_login(
        client_with_db, db_session, email="learner1@claudequest.dev"
    )

    response = await client_with_db.get(
        "/api/v1/learning/tracks", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    titles = [item["title"] for item in body["data"]]
    assert "Claude Chat" in titles
    assert str(track.id) in [item["id"] for item in body["data"]]


async def test_get_track_detail_requires_authentication(client_with_db: httpx.AsyncClient) -> None:
    response = await client_with_db.get(f"/api/v1/learning/tracks/{uuid.uuid4()}")

    assert response.status_code == 401


async def test_get_track_detail_returns_full_hierarchy(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    track = await _create_track_with_hierarchy(db_session)
    token = await _create_user_and_login(
        client_with_db, db_session, email="learner2@claudequest.dev"
    )

    response = await client_with_db.get(
        f"/api/v1/learning/tracks/{track.id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(track.id)
    assert len(data["modules"]) == 1
    assert len(data["modules"][0]["levels"]) == 1
    assert len(data["modules"][0]["levels"][0]["lessons"]) == 1
    lesson = data["modules"][0]["levels"][0]["lessons"][0]
    assert len(lesson["questions"]) == 1
    assert len(lesson["questions"][0]["alternatives"]) == 1


async def test_get_track_detail_returns_404_when_not_found(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    token = await _create_user_and_login(
        client_with_db, db_session, email="learner3@claudequest.dev"
    )

    response = await client_with_db.get(
        f"/api/v1/learning/tracks/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "track_not_found"
