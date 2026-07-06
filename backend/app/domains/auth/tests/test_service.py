from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.auth.model import Session as AuthSession
from app.domains.auth.repository import SessionRepository
from app.domains.auth.schemas import LoginRequest
from app.domains.auth.service import AuthService
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole, UserStatus
from app.domains.users.repository import UserRepository
from app.shared.errors import AppError


async def _create_user(
    session: AsyncSession, *, email: str, password: str, status: UserStatus = UserStatus.ACTIVE
) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password(password),
        role=UserRole.STUDENT,
        status=status,
    )
    session.add(user)
    await session.flush()
    return user


def _build_service(session: AsyncSession) -> AuthService:
    return AuthService(UserRepository(session), SessionRepository(session))


async def test_login_succeeds_with_correct_credentials(db_session: AsyncSession) -> None:
    await _create_user(db_session, email="joao@claudequest.dev", password="senha-correta")
    service = _build_service(db_session)

    result = await service.login(
        LoginRequest(email="joao@claudequest.dev", password="senha-correta"),
        user_agent="pytest",
        ip_address="127.0.0.1",
    )

    assert result.access_token
    assert result.refresh_token
    assert result.user.email == "joao@claudequest.dev"


async def test_login_persists_an_auditable_session(db_session: AsyncSession) -> None:
    await _create_user(db_session, email="ana@claudequest.dev", password="senha-correta")
    service = _build_service(db_session)

    await service.login(
        LoginRequest(email="ana@claudequest.dev", password="senha-correta"),
        user_agent="pytest-agent",
        ip_address="10.0.0.1",
    )

    sessions = (await db_session.execute(select(AuthSession))).scalars().all()
    assert len(sessions) == 1
    assert sessions[0].user_agent == "pytest-agent"
    assert sessions[0].ip_address == "10.0.0.1"


async def test_login_updates_last_login(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="carla@claudequest.dev", password="senha-correta")
    service = _build_service(db_session)
    assert user.last_login is None

    await service.login(
        LoginRequest(email="carla@claudequest.dev", password="senha-correta"),
        user_agent=None,
        ip_address=None,
    )

    assert user.last_login is not None


async def test_login_rejects_wrong_password(db_session: AsyncSession) -> None:
    await _create_user(db_session, email="lucas@claudequest.dev", password="senha-correta")
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.login(
            LoginRequest(email="lucas@claudequest.dev", password="senha-errada"),
            user_agent=None,
            ip_address=None,
        )

    assert exc_info.value.code == "invalid_credentials"
    assert exc_info.value.status_code == 401


async def test_login_rejects_unknown_email_with_the_same_generic_error(
    db_session: AsyncSession,
) -> None:
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.login(
            LoginRequest(email="ninguem@claudequest.dev", password="qualquer-senha"),
            user_agent=None,
            ip_address=None,
        )

    assert exc_info.value.code == "invalid_credentials"


async def test_login_rejects_inactive_account(db_session: AsyncSession) -> None:
    await _create_user(
        db_session,
        email="bloqueada@claudequest.dev",
        password="senha-correta",
        status=UserStatus.BLOCKED,
    )
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.login(
            LoginRequest(email="bloqueada@claudequest.dev", password="senha-correta"),
            user_agent=None,
            ip_address=None,
        )

    assert exc_info.value.code == "account_not_active"
    assert exc_info.value.status_code == 403


async def test_refresh_issues_new_tokens_and_revokes_the_old_session(
    db_session: AsyncSession,
) -> None:
    await _create_user(db_session, email="refresh-svc@claudequest.dev", password="senha-correta")
    service = _build_service(db_session)
    login_result = await service.login(
        LoginRequest(email="refresh-svc@claudequest.dev", password="senha-correta"),
        user_agent=None,
        ip_address=None,
    )

    refreshed = await service.refresh(
        login_result.refresh_token, user_agent="pytest", ip_address="127.0.0.1"
    )

    assert refreshed.access_token != login_result.access_token
    assert refreshed.refresh_token != login_result.refresh_token

    sessions = (await db_session.execute(select(AuthSession))).scalars().all()
    assert len(sessions) == 2
    revoked = [s for s in sessions if s.revoked_at is not None]
    assert len(revoked) == 1


async def test_refresh_rejects_none_token(db_session: AsyncSession) -> None:
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.refresh(None, user_agent=None, ip_address=None)

    assert exc_info.value.code == "invalid_refresh_token"


async def test_refresh_rejects_unknown_token(db_session: AsyncSession) -> None:
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.refresh("token-que-nao-existe", user_agent=None, ip_address=None)

    assert exc_info.value.code == "invalid_refresh_token"


async def test_refresh_rejects_inactive_account(db_session: AsyncSession) -> None:
    user = await _create_user(
        db_session, email="refresh-inactive@claudequest.dev", password="senha-correta"
    )
    service = _build_service(db_session)
    login_result = await service.login(
        LoginRequest(email="refresh-inactive@claudequest.dev", password="senha-correta"),
        user_agent=None,
        ip_address=None,
    )
    user.status = UserStatus.BLOCKED
    await db_session.flush()

    with pytest.raises(AppError) as exc_info:
        await service.refresh(login_result.refresh_token, user_agent=None, ip_address=None)

    assert exc_info.value.code == "account_not_active"


async def test_refresh_rejects_a_session_whose_user_was_deleted(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(
        db_session, email="refresh-deleted@claudequest.dev", password="senha-correta"
    )
    service = _build_service(db_session)
    login_result = await service.login(
        LoginRequest(email="refresh-deleted@claudequest.dev", password="senha-correta"),
        user_agent=None,
        ip_address=None,
    )
    user.deleted_at = datetime.now(UTC)
    await db_session.flush()

    with pytest.raises(AppError) as exc_info:
        await service.refresh(login_result.refresh_token, user_agent=None, ip_address=None)

    assert exc_info.value.code == "invalid_refresh_token"


async def test_logout_revokes_the_session(db_session: AsyncSession) -> None:
    await _create_user(db_session, email="logout-svc@claudequest.dev", password="senha-correta")
    service = _build_service(db_session)
    login_result = await service.login(
        LoginRequest(email="logout-svc@claudequest.dev", password="senha-correta"),
        user_agent=None,
        ip_address=None,
    )

    await service.logout(login_result.refresh_token)

    with pytest.raises(AppError) as exc_info:
        await service.refresh(login_result.refresh_token, user_agent=None, ip_address=None)
    assert exc_info.value.code == "invalid_refresh_token"


async def test_logout_without_a_token_does_nothing(db_session: AsyncSession) -> None:
    service = _build_service(db_session)

    await service.logout(None)
