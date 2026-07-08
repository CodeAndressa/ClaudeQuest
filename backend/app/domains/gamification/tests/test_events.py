import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.gamification.events import (
    Event,
    EventRepository,
    EventService,
)
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole
from app.shared.errors import AppError

_NOW = datetime.now(UTC)


async def _create_user(
    session: AsyncSession, *, email: str, password: str, role: UserRole = UserRole.STUDENT
) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_event(
    session: AsyncSession,
    *,
    name: str = "Claude Week",
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    is_active: bool = True,
) -> Event:
    event = Event(
        name=name,
        starts_at=starts_at or (_NOW - timedelta(days=1)),
        ends_at=ends_at or (_NOW + timedelta(days=1)),
        is_active=is_active,
    )
    session.add(event)
    await session.flush()
    return event


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token: str = response.json()["data"]["access_token"]
    return token


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class TestEventRepository:
    async def test_create_persists_a_new_event(self, db_session: AsyncSession) -> None:
        repository = EventRepository(db_session)

        event = await repository.create(
            name="Halloween",
            starts_at=_NOW - timedelta(days=1),
            ends_at=_NOW + timedelta(days=1),
        )

        assert event.id is not None
        found = await repository.get_by_id(event.id)
        assert found is not None
        assert found.name == "Halloween"
        assert found.is_active is True

    async def test_get_by_id_returns_none_for_unknown_id(self, db_session: AsyncSession) -> None:
        repository = EventRepository(db_session)

        event = await repository.get_by_id(uuid.uuid4())

        assert event is None

    async def test_list_all_returns_created_events(self, db_session: AsyncSession) -> None:
        await _create_event(db_session, name="Black Friday")
        await _create_event(db_session, name="Natal")
        repository = EventRepository(db_session)

        events = await repository.list_all()

        names = {event.name for event in events}
        assert {"Black Friday", "Natal"} <= names

    async def test_get_active_at_returns_event_within_window(
        self, db_session: AsyncSession
    ) -> None:
        event = await _create_event(
            db_session,
            name="Hackathon",
            starts_at=_NOW - timedelta(hours=1),
            ends_at=_NOW + timedelta(hours=1),
        )
        repository = EventRepository(db_session)

        found = await repository.get_active_at(_NOW)

        assert found is not None
        assert found.id == event.id

    async def test_get_active_at_returns_none_outside_window(
        self, db_session: AsyncSession
    ) -> None:
        await _create_event(
            db_session,
            name="Semana da IA",
            starts_at=_NOW - timedelta(days=10),
            ends_at=_NOW - timedelta(days=5),
        )
        repository = EventRepository(db_session)

        found = await repository.get_active_at(_NOW)

        assert found is None

    async def test_get_active_at_returns_none_when_manually_deactivated(
        self, db_session: AsyncSession
    ) -> None:
        await _create_event(
            db_session,
            name="Claude Week",
            starts_at=_NOW - timedelta(hours=1),
            ends_at=_NOW + timedelta(hours=1),
            is_active=False,
        )
        repository = EventRepository(db_session)

        found = await repository.get_active_at(_NOW)

        assert found is None

    async def test_deactivate_flips_is_active_to_false(self, db_session: AsyncSession) -> None:
        event = await _create_event(db_session)
        repository = EventRepository(db_session)

        deactivated = await repository.deactivate(event)

        assert deactivated.is_active is False


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class TestEventService:
    async def test_create_event_persists_valid_event(self, db_session: AsyncSession) -> None:
        service = EventService(EventRepository(db_session))

        event = await service.create_event(
            name="Claude Week", starts_at=_NOW, ends_at=_NOW + timedelta(days=5)
        )

        assert event.id is not None
        assert event.name == "Claude Week"

    async def test_create_event_rejects_end_before_start(self, db_session: AsyncSession) -> None:
        service = EventService(EventRepository(db_session))

        with pytest.raises(AppError) as excinfo:
            await service.create_event(
                name="Evento Inválido",
                starts_at=_NOW,
                ends_at=_NOW - timedelta(days=1),
            )

        assert excinfo.value.code == "invalid_event_window"
        assert excinfo.value.status_code == 422

    async def test_create_event_rejects_end_equal_to_start(self, db_session: AsyncSession) -> None:
        service = EventService(EventRepository(db_session))

        with pytest.raises(AppError) as excinfo:
            await service.create_event(name="Evento Inválido", starts_at=_NOW, ends_at=_NOW)

        assert excinfo.value.code == "invalid_event_window"

    async def test_is_event_active_now_returns_event_within_window(
        self, db_session: AsyncSession
    ) -> None:
        await _create_event(db_session, name="Hackathon")
        service = EventService(EventRepository(db_session))

        active = await service.is_event_active_now()

        assert active is not None
        assert active.name == "Hackathon"

    async def test_is_event_active_now_returns_none_when_no_event_matches(
        self, db_session: AsyncSession
    ) -> None:
        await _create_event(
            db_session,
            starts_at=_NOW + timedelta(days=1),
            ends_at=_NOW + timedelta(days=5),
        )
        service = EventService(EventRepository(db_session))

        active = await service.is_event_active_now()

        assert active is None

    async def test_deactivate_event_marks_it_inactive(self, db_session: AsyncSession) -> None:
        event = await _create_event(db_session)
        service = EventService(EventRepository(db_session))

        deactivated = await service.deactivate_event(event.id)

        assert deactivated.is_active is False

    async def test_deactivate_event_raises_for_unknown_id(self, db_session: AsyncSession) -> None:
        service = EventService(EventRepository(db_session))

        with pytest.raises(AppError) as excinfo:
            await service.deactivate_event(uuid.uuid4())

        assert excinfo.value.code == "event_not_found"
        assert excinfo.value.status_code == 404


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #


class TestCreateEvent:
    async def test_admin_can_create_an_event(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="event-create-admin1@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.post(
            "/api/v1/gamification/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Claude Week",
                "starts_at": _NOW.isoformat(),
                "ends_at": (_NOW + timedelta(days=5)).isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Claude Week"
        assert data["is_active"] is True

    async def test_rejects_end_before_start_with_422(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="event-create-admin2@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.post(
            "/api/v1/gamification/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Evento Inválido",
                "starts_at": _NOW.isoformat(),
                "ends_at": (_NOW - timedelta(days=1)).isoformat(),
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_event_window"

    async def test_non_admin_is_forbidden_from_creating(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="event-create-student1@claudequest.dev", password="senha-forte"
        )
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.post(
            "/api/v1/gamification/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Claude Week",
                "starts_at": _NOW.isoformat(),
                "ends_at": (_NOW + timedelta(days=5)).isoformat(),
            },
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.post(
            "/api/v1/gamification/events",
            json={
                "name": "Claude Week",
                "starts_at": _NOW.isoformat(),
                "ends_at": (_NOW + timedelta(days=5)).isoformat(),
            },
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


class TestListEvents:
    async def test_admin_can_list_all_events(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="event-list-admin1@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        await _create_event(db_session, name="Halloween")
        await _create_event(db_session, name="Natal")
        token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.get(
            "/api/v1/gamification/events", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        names = {item["name"] for item in response.json()["data"]}
        assert {"Halloween", "Natal"} <= names

    async def test_non_admin_is_forbidden_from_listing(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="event-list-student1@claudequest.dev", password="senha-forte"
        )
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.get(
            "/api/v1/gamification/events", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.get("/api/v1/gamification/events")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


class TestGetActiveEvent:
    async def test_any_authenticated_user_can_see_the_active_event(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="event-active-student1@claudequest.dev", password="senha-forte"
        )
        await _create_event(db_session, name="Hackathon")
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.get(
            "/api/v1/gamification/events/active",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Hackathon"

    async def test_returns_null_when_no_event_is_active(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="event-active-student2@claudequest.dev", password="senha-forte"
        )
        await _create_event(
            db_session,
            starts_at=_NOW + timedelta(days=1),
            ends_at=_NOW + timedelta(days=5),
        )
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.get(
            "/api/v1/gamification/events/active",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["data"] is None

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.get("/api/v1/gamification/events/active")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


class TestDeactivateEvent:
    async def test_admin_can_deactivate_an_event_before_its_end_date(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="event-deactivate-admin1@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        event = await _create_event(db_session, name="Claude Week")
        token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.patch(
            f"/api/v1/gamification/events/{event.id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    async def test_deactivated_event_is_not_returned_as_active(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="event-deactivate-admin2@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        event = await _create_event(db_session, name="Claude Week")
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")

        await client_with_db.patch(
            f"/api/v1/gamification/events/{event.id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        response = await client_with_db.get(
            "/api/v1/gamification/events/active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        assert response.json()["data"] is None

    async def test_returns_404_for_unknown_event(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session,
            email="event-deactivate-admin3@claudequest.dev",
            password="senha-forte",
            role=UserRole.ADMIN,
        )
        token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.patch(
            f"/api/v1/gamification/events/{uuid.uuid4()}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "event_not_found"

    async def test_non_admin_is_forbidden_from_deactivating(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="event-deactivate-student1@claudequest.dev", password="senha-forte"
        )
        event = await _create_event(db_session)
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.patch(
            f"/api/v1/gamification/events/{event.id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        event = await _create_event(db_session)

        response = await client_with_db.patch(f"/api/v1/gamification/events/{event.id}/deactivate")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
