"""Testes de service e repository do fluxo de recuperação de senha (AUTH-003)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.domains.auth.model import Session as AuthSession
from app.domains.auth.password_reset import (
    ForgotPasswordRequest,
    PasswordResetRepository,
    PasswordResetService,
    PasswordResetToken,
    ResetPasswordRequest,
    generate_reset_token,
    hash_reset_token,
)
from app.domains.auth.repository import SessionRepository
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserStatus
from app.domains.users.repository import UserRepository
from app.shared.errors import AppError


async def _create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str = "senha-antiga",
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password(password),
        status=status,
    )
    session.add(user)
    await session.flush()
    return user


def _build_service(session: AsyncSession) -> PasswordResetService:
    return PasswordResetService(
        UserRepository(session), PasswordResetRepository(session), SessionRepository(session)
    )


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


async def test_repository_create_persists_a_token(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="repo1@claudequest.dev")
    repository = PasswordResetRepository(db_session)

    token = await repository.create(
        user_id=user.id,
        token_hash="hash-1",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )

    assert token.id is not None
    assert token.used_at is None


async def test_repository_get_valid_by_token_hash_ignores_expired(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="repo2@claudequest.dev")
    repository = PasswordResetRepository(db_session)
    await repository.create(
        user_id=user.id,
        token_hash="hash-expirado",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    result = await repository.get_valid_by_token_hash("hash-expirado")

    assert result is None


async def test_repository_get_valid_by_token_hash_ignores_used(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="repo3@claudequest.dev")
    repository = PasswordResetRepository(db_session)
    token = await repository.create(
        user_id=user.id,
        token_hash="hash-usado",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    await repository.mark_used(token)

    result = await repository.get_valid_by_token_hash("hash-usado")

    assert result is None


async def test_repository_get_valid_by_token_hash_returns_valid_token(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="repo4@claudequest.dev")
    repository = PasswordResetRepository(db_session)
    await repository.create(
        user_id=user.id,
        token_hash="hash-valido",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )

    result = await repository.get_valid_by_token_hash("hash-valido")

    assert result is not None
    assert result.user_id == user.id


async def test_generate_reset_token_returns_matching_pair() -> None:
    token, token_hash = generate_reset_token()

    assert token
    assert token_hash == hash_reset_token(token)


# --------------------------------------------------------------------------- #
# Service — forgot_password
# --------------------------------------------------------------------------- #


async def test_forgot_password_creates_a_token_for_existing_active_user(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="esqueci1@claudequest.dev")
    service = _build_service(db_session)

    await service.forgot_password(ForgotPasswordRequest(email="esqueci1@claudequest.dev"))

    tokens = (await db_session.execute(select(PasswordResetToken))).scalars().all()
    assert len(tokens) == 1
    assert tokens[0].user_id == user.id


async def test_forgot_password_does_nothing_for_unknown_email(db_session: AsyncSession) -> None:
    service = _build_service(db_session)

    await service.forgot_password(ForgotPasswordRequest(email="ninguem@claudequest.dev"))

    tokens = (await db_session.execute(select(PasswordResetToken))).scalars().all()
    assert len(tokens) == 0


async def test_forgot_password_does_nothing_for_inactive_user(db_session: AsyncSession) -> None:
    await _create_user(db_session, email="inativa@claudequest.dev", status=UserStatus.INACTIVE)
    service = _build_service(db_session)

    await service.forgot_password(ForgotPasswordRequest(email="inativa@claudequest.dev"))

    tokens = (await db_session.execute(select(PasswordResetToken))).scalars().all()
    assert len(tokens) == 0


# --------------------------------------------------------------------------- #
# Service — reset_password
# --------------------------------------------------------------------------- #


async def test_reset_password_happy_path_changes_password_and_revokes_sessions(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="reset1@claudequest.dev", password="senha-antiga")
    sessions = SessionRepository(db_session)
    await sessions.create(
        user_id=user.id,
        refresh_token_hash="hash-sessao-antiga",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        user_agent=None,
        ip_address=None,
    )

    reset_repo = PasswordResetRepository(db_session)
    token, token_hash = generate_reset_token()
    await reset_repo.create(
        user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(minutes=30)
    )

    service = _build_service(db_session)
    await service.reset_password(ResetPasswordRequest(token=token, new_password="senha-nova-123"))

    assert verify_password("senha-nova-123", user.password_hash)
    assert not verify_password("senha-antiga", user.password_hash)

    used_token = await reset_repo.get_valid_by_token_hash(token_hash)
    assert used_token is None

    active_sessions = (
        (
            await db_session.execute(
                select(AuthSession).where(
                    AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(active_sessions) == 0


async def test_reset_password_rejects_unknown_token(db_session: AsyncSession) -> None:
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.reset_password(
            ResetPasswordRequest(token="token-inexistente", new_password="senha-nova-123")
        )

    assert exc_info.value.code == "invalid_reset_token"
    assert exc_info.value.status_code == 400


async def test_reset_password_rejects_expired_token(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="reset-expirado@claudequest.dev")
    reset_repo = PasswordResetRepository(db_session)
    token, token_hash = generate_reset_token()
    await reset_repo.create(
        user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.reset_password(
            ResetPasswordRequest(token=token, new_password="senha-nova-123")
        )

    assert exc_info.value.code == "invalid_reset_token"


async def test_reset_password_rejects_token_whose_user_was_deleted(
    db_session: AsyncSession,
) -> None:
    user = await _create_user(db_session, email="reset-usuario-excluido@claudequest.dev")
    reset_repo = PasswordResetRepository(db_session)
    token, token_hash = generate_reset_token()
    await reset_repo.create(
        user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(minutes=30)
    )
    user.deleted_at = datetime.now(UTC)
    await db_session.flush()
    service = _build_service(db_session)

    with pytest.raises(AppError) as exc_info:
        await service.reset_password(
            ResetPasswordRequest(token=token, new_password="senha-nova-123")
        )

    assert exc_info.value.code == "invalid_reset_token"


async def test_reset_password_rejects_already_used_token(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="reset-usado@claudequest.dev")
    reset_repo = PasswordResetRepository(db_session)
    token, token_hash = generate_reset_token()
    await reset_repo.create(
        user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(minutes=30)
    )
    service = _build_service(db_session)
    await service.reset_password(ResetPasswordRequest(token=token, new_password="senha-nova-123"))

    with pytest.raises(AppError) as exc_info:
        await service.reset_password(
            ResetPasswordRequest(token=token, new_password="outra-senha-456")
        )

    assert exc_info.value.code == "invalid_reset_token"
