from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole
from app.domains.users.repository import UserRepository


async def _create_user(session: AsyncSession, *, email: str) -> User:
    organization = Organization(name="Org de Teste", slug=f"org-{email}", plan="internal")
    session.add(organization)
    await session.flush()

    user = User(
        organization_id=organization.id,
        name="Usuária de Teste",
        email=email,
        password_hash=hash_password("senha-forte"),
        role=UserRole.STUDENT,
    )
    session.add(user)
    await session.flush()
    return user


async def test_get_by_email_returns_none_when_not_found(db_session: AsyncSession) -> None:
    repository = UserRepository(db_session)

    result = await repository.get_by_email("inexistente@claudequest.dev")

    assert result is None


async def test_get_by_email_returns_the_matching_user(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="maria@claudequest.dev")
    repository = UserRepository(db_session)

    result = await repository.get_by_email("maria@claudequest.dev")

    assert result is not None
    assert result.id == user.id


async def test_get_by_email_ignores_soft_deleted_users(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="removida@claudequest.dev")
    user.deleted_at = datetime.now(UTC)
    await db_session.flush()
    repository = UserRepository(db_session)

    result = await repository.get_by_email("removida@claudequest.dev")

    assert result is None


async def test_touch_last_login_updates_the_timestamp(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="pedro@claudequest.dev")
    repository = UserRepository(db_session)
    when = datetime.now(UTC)

    await repository.touch_last_login(user, when)

    assert user.last_login == when
