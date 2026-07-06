"""
Cria um conjunto inicial de badges do catálogo (GAME-002), com exemplos retirados
da seção "Badges" de G:\\Meu Drive\\Obsidian\\ClaudeLinguo\\08 - Gamification\\
Gamification.md.md.

Idempotente: badges já existentes (mesmo nome) não são recriados.

Uso: uv run python scripts/seed_badges.py
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.domains.gamification.badges import Badge, BadgeCategory

BADGES: list[dict[str, object]] = [
    {
        "name": "Primeiro Login",
        "description": "Concedido ao acessar a plataforma pela primeira vez.",
        "category": BadgeCategory.BRONZE,
    },
    {
        "name": "Primeira Missão",
        "description": "Concedido ao concluir a primeira missão da jornada.",
        "category": BadgeCategory.BRONZE,
    },
    {
        "name": "Primeiro Certificado",
        "description": "Concedido ao conquistar o primeiro certificado oficial.",
        "category": BadgeCategory.PRATA,
    },
    {
        "name": "100 Missões",
        "description": "Concedido ao concluir 100 missões na plataforma.",
        "category": BadgeCategory.OURO,
    },
    {
        "name": "Prompt Master",
        "description": "Concedido por domínio avançado de Prompt Engineering.",
        "category": BadgeCategory.PLATINA,
    },
]


async def seed(session: AsyncSession) -> None:
    for badge_data in BADGES:
        name = str(badge_data["name"])
        existing = await session.scalar(select(Badge).where(Badge.name == name))
        if existing is not None:
            print(f"Badge já existe, pulando: {name}")
            continue

        badge = Badge(
            name=name,
            description=str(badge_data["description"]),
            category=badge_data["category"],
        )
        session.add(badge)
        print(f"Badge criado: {name} ({badge_data['category']})")

    await session.commit()


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
