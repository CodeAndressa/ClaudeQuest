"""
Cria a organização demo e o usuário administrador inicial, conforme previsto em
05 - Database/Database Specification.md.md ("Seeds"). Necessário porque não existe
tela de cadastro - usuários são criados pelo Admin (ADMIN-001, ainda não implementado).

Uso: uv run python scripts/seed_demo_data.py
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.domains.organizations.model import Organization
from app.domains.users.model import User, UserRole

DEMO_ORG_SLUG = "claudequest-demo"
ADMIN_EMAIL = "admin@claudequest.dev"
ADMIN_PASSWORD = "ClaudeQuest#2026"


async def seed(session: AsyncSession) -> None:
    existing_org = await session.scalar(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    )
    if existing_org is not None:
        print("Organização demo já existe - nada a fazer.")
        return

    organization = Organization(name="ClaudeQuest Demo", slug=DEMO_ORG_SLUG, plan="internal")
    session.add(organization)
    await session.flush()

    admin = User(
        organization_id=organization.id,
        name="Administrador ClaudeQuest",
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        email_verified=True,
    )
    session.add(admin)
    await session.commit()

    print(f"Organização criada: {organization.name} ({organization.slug})")
    print(f"Admin criado: {admin.email} / senha: {ADMIN_PASSWORD}")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
