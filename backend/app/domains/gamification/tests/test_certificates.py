from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.gamification.certificates import (
    Certificate,
    CertificateRepository,
    UserCertificate,
    generate_validation_code,
)
from app.domains.learning.model import Track
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole


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


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token: str = response.json()["data"]["access_token"]
    return token


async def _create_track(session: AsyncSession, *, title: str = "Claude Chat") -> Track:
    track = Track(
        title=title,
        description="Domine completamente o Claude Chat.",
        difficulty="beginner",
        estimated_hours=4,
        order=1,
    )
    session.add(track)
    await session.flush()
    return track


async def _create_certificate(
    session: AsyncSession, *, track: Track, title: str = "Certificado Claude Chat", hours: int = 4
) -> Certificate:
    certificate = Certificate(track_id=track.id, title=title, hours=hours)
    session.add(certificate)
    await session.flush()
    return certificate


class TestCertificateRepositoryCreate:
    async def test_create_persists_a_catalog_entry(self, db_session: AsyncSession) -> None:
        track = await _create_track(db_session, title="Trilha para Catálogo")
        repository = CertificateRepository(db_session)

        certificate = await repository.create(
            track_id=track.id, title="Certificado de Catálogo", hours=6
        )

        assert certificate.id is not None
        found = await repository.get_by_id(certificate.id)
        assert found is not None
        assert found.title == "Certificado de Catálogo"
        assert found.hours == 6


class TestIssueCertificate:
    async def test_admin_can_issue_certificate_to_a_user(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session, email="cert-admin1@claudequest.dev", password="senha-forte",
            role=UserRole.ADMIN,
        )
        student = await _create_user(
            db_session, email="cert-student1@claudequest.dev", password="senha-forte"
        )
        track = await _create_track(db_session)
        certificate = await _create_certificate(db_session, track=track)
        admin_token = await _login(
            client_with_db, email=admin.email, password="senha-forte"
        )

        response = await client_with_db.post(
            f"/api/v1/gamification/certificates/{certificate.id}/issue",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": str(student.id)},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["certificate_id"] == str(certificate.id)
        assert data["title"] == certificate.title
        assert data["hours"] == certificate.hours
        assert data["pdf_url"] is None
        assert isinstance(data["validation_code"], str)
        assert len(data["validation_code"]) > 0

    async def test_non_admin_is_forbidden_from_issuing(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="cert-student2@claudequest.dev", password="senha-forte"
        )
        other_student = await _create_user(
            db_session, email="cert-student3@claudequest.dev", password="senha-forte"
        )
        track = await _create_track(db_session)
        certificate = await _create_certificate(db_session, track=track)
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.post(
            f"/api/v1/gamification/certificates/{certificate.id}/issue",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(other_student.id)},
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_returns_404_for_unknown_certificate(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        admin = await _create_user(
            db_session, email="cert-admin2@claudequest.dev", password="senha-forte",
            role=UserRole.ADMIN,
        )
        student = await _create_user(
            db_session, email="cert-student4@claudequest.dev", password="senha-forte"
        )
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")

        response = await client_with_db.post(
            "/api/v1/gamification/certificates/00000000-0000-0000-0000-000000000000/issue",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": str(student.id)},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "certificate_not_found"

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        track = await _create_track(db_session)
        certificate = await _create_certificate(db_session, track=track)

        response = await client_with_db.post(
            f"/api/v1/gamification/certificates/{certificate.id}/issue",
            json={"user_id": "00000000-0000-0000-0000-000000000000"},
        )

        assert response.status_code == 401


class TestListMyCertificates:
    async def test_lists_certificates_issued_to_the_logged_in_user(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="cert-student5@claudequest.dev", password="senha-forte"
        )
        track = await _create_track(db_session)
        certificate = await _create_certificate(db_session, track=track)
        user_certificate = UserCertificate(
            certificate_id=certificate.id,
            user_id=student.id,
            validation_code=generate_validation_code(),
            issued_at=datetime.now(UTC),
            pdf_url=None,
        )
        db_session.add(user_certificate)
        await db_session.flush()

        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.get(
            "/api/v1/gamification/me/certificates",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["certificate_id"] == str(certificate.id)
        assert data[0]["validation_code"] == user_certificate.validation_code

    async def test_returns_empty_list_when_user_has_no_certificates(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="cert-student6@claudequest.dev", password="senha-forte"
        )
        token = await _login(client_with_db, email=student.email, password="senha-forte")

        response = await client_with_db.get(
            "/api/v1/gamification/me/certificates",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    async def test_returns_401_without_authorization(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.get("/api/v1/gamification/me/certificates")

        assert response.status_code == 401


class TestValidateCertificate:
    async def test_validates_an_existing_code_publicly_without_authentication(
        self, client_with_db: httpx.AsyncClient, db_session: AsyncSession
    ) -> None:
        student = await _create_user(
            db_session, email="cert-student7@claudequest.dev", password="senha-forte"
        )
        track = await _create_track(db_session)
        certificate = await _create_certificate(db_session, track=track)
        admin = await _create_user(
            db_session, email="cert-admin3@claudequest.dev", password="senha-forte",
            role=UserRole.ADMIN,
        )
        admin_token = await _login(client_with_db, email=admin.email, password="senha-forte")
        issue_response = await client_with_db.post(
            f"/api/v1/gamification/certificates/{certificate.id}/issue",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": str(student.id)},
        )
        validation_code = issue_response.json()["data"]["validation_code"]

        # Sem header de Authorization: validação pública, para terceiros.
        response = await client_with_db.get(
            f"/api/v1/gamification/certificates/validate/{validation_code}"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["valid"] is True
        assert data["user_name"] == student.name
        assert data["title"] == certificate.title
        assert data["hours"] == certificate.hours

    async def test_returns_404_for_unknown_validation_code(
        self, client_with_db: httpx.AsyncClient
    ) -> None:
        response = await client_with_db.get(
            "/api/v1/gamification/certificates/validate/codigo-inexistente"
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "invalid_validation_code"
