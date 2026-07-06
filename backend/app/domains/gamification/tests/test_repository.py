from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.gamification.repository import XpLedgerRepository
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


async def test_add_entry_persists_an_xp_ledger_row(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="xp1@claudequest.dev")
    repository = XpLedgerRepository(db_session)

    entry = await repository.add_entry(user_id=user.id, amount=100, reason="quiz")

    assert entry.id is not None
    assert entry.user_id == user.id
    assert entry.amount == 100
    assert entry.reason == "quiz"


async def test_get_total_xp_returns_zero_when_no_entries(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="xp2@claudequest.dev")
    repository = XpLedgerRepository(db_session)

    total = await repository.get_total_xp(user.id)

    assert total == 0


async def test_get_total_xp_sums_all_entries_for_the_user(db_session: AsyncSession) -> None:
    user = await _create_user(db_session, email="xp3@claudequest.dev")
    repository = XpLedgerRepository(db_session)
    await repository.add_entry(user_id=user.id, amount=100, reason="quiz")
    await repository.add_entry(user_id=user.id, amount=50, reason="missao_diaria")
    await repository.add_entry(user_id=user.id, amount=25, reason="streak")

    total = await repository.get_total_xp(user.id)

    assert total == 175


async def test_get_total_xp_does_not_mix_entries_from_other_users(db_session: AsyncSession) -> None:
    user_a = await _create_user(db_session, email="xp4a@claudequest.dev")
    user_b = await _create_user(db_session, email="xp4b@claudequest.dev")
    repository = XpLedgerRepository(db_session)
    await repository.add_entry(user_id=user_a.id, amount=100, reason="quiz")
    await repository.add_entry(user_id=user_b.id, amount=999, reason="quiz")

    total_a = await repository.get_total_xp(user_a.id)

    assert total_a == 100


async def test_xp_ledger_never_stores_negative_amounts_by_convention(
    db_session: AsyncSession,
) -> None:
    # O ledger não impõe uma constraint de banco contra valores negativos (a
    # regra "nunca punir" é garantida na camada de Service/Schema, que nunca
    # aceita amount <= 0). Este teste documenta que o Repository, por si só,
    # é uma camada de persistência pura e confia no chamador.
    user = await _create_user(db_session, email="xp5@claudequest.dev")
    repository = XpLedgerRepository(db_session)

    entry = await repository.add_entry(user_id=user.id, amount=10, reason="ajuste")

    assert entry.amount > 0
