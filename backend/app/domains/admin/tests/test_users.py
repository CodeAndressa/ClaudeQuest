from uuid import UUID

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole


async def _admin(session: AsyncSession) -> User:
    organization = Organization(name="Organização Admin", slug="org-admin")
    session.add(organization)
    await session.flush()
    user = User(
        organization_id=organization.id,
        name="Pessoa Administradora",
        email="admin-create@example.com",
        password_hash=hash_password("senha-admin"),
        role=UserRole.ADMIN,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_admin_creates_user_in_same_organization(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _admin(db_session)
    login = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "senha-admin"},
    )
    token = login.json()["data"]["access_token"]

    response = await client_with_db.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Nova Pessoa",
            "email": "nova@example.com",
            "password": "senha-inicial",
            "role": "student",
        },
    )

    assert response.status_code == 201
    created = response.json()["data"]
    assert created["email"] == "nova@example.com"
    assert created["status"] == "active"
    stored = await db_session.get(User, UUID(created["id"]))
    assert stored is not None
    assert stored.organization_id == admin.organization_id
    assert verify_password("senha-inicial", stored.password_hash)


@pytest.mark.asyncio
async def test_admin_cannot_create_duplicate_email(
    client_with_db: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _admin(db_session)
    login = await client_with_db.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "senha-admin"},
    )
    token = login.json()["data"]["access_token"]
    payload = {
        "name": "Pessoa Duplicada",
        "email": admin.email,
        "password": "senha-inicial",
        "role": "student",
    }

    response = await client_with_db.post(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_in_use"
