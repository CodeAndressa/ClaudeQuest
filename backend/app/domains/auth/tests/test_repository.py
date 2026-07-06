from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.auth.repository import SessionRepository
from app.domains.organizations.model import Organization
from app.domains.users.model import User


async def _create_user(session: AsyncSession, *, email: str) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password("senha-forte"),
    )
    session.add(user)
    await session.flush()
    return user


async def test_create_persists_a_session(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="sessao1@claudequest.dev")
    repository = SessionRepository(db_session)

    session = await repository.create(
        user_id=user.id,
        refresh_token_hash="hash-1",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        user_agent="pytest",
        ip_address="127.0.0.1",
    )

    assert session.id is not None
    assert session.revoked_at is None


async def test_get_active_by_refresh_token_hash_ignores_expired_sessions(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="sessao2@claudequest.dev")
    repository = SessionRepository(db_session)
    await repository.create(
        user_id=user.id,
        refresh_token_hash="hash-expirado",
        expires_at=datetime.now(UTC) - timedelta(days=1),
        user_agent=None,
        ip_address=None,
    )

    result = await repository.get_active_by_refresh_token_hash("hash-expirado")

    assert result is None


async def test_get_active_by_refresh_token_hash_ignores_revoked_sessions(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="sessao3@claudequest.dev")
    repository = SessionRepository(db_session)
    session = await repository.create(
        user_id=user.id,
        refresh_token_hash="hash-revogado",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        user_agent=None,
        ip_address=None,
    )
    await repository.revoke(session)

    result = await repository.get_active_by_refresh_token_hash("hash-revogado")

    assert result is None


async def test_revoke_by_refresh_token_hash_is_a_no_op_when_not_found(
    db_session: AsyncSession,
) -> None:
    repository = SessionRepository(db_session)

    await repository.revoke_by_refresh_token_hash("hash-inexistente")
