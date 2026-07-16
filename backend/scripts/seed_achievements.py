"""
Cria o catálogo inicial de achievements (GAME-003), para permitir testar a
avaliação/concessão automática (GET /gamification/me/achievements) sem
precisar de um Admin Portal (ainda não implementado - ADMIN-002).

Uso: uv run python scripts/seed_achievements.py
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.domains.gamification.achievements import (
    Achievement,
    AchievementMetric,
    AchievementRepository,
)

ACHIEVEMENTS = [
    {
        "name": "Primeira Missão",
        "description": "Concluiu sua primeira lição na Claude Academy.",
        "icon": "footprints",
        "metric": AchievementMetric.LESSONS_COMPLETED,
        "threshold": 1,
    },
    {
        "name": "Maratonista",
        "description": "Concluiu 50 lições.",
        "icon": "medal",
        "metric": AchievementMetric.LESSONS_COMPLETED,
        "threshold": 50,
    },
    {
        "name": "Streak de Ferro",
        "description": "Manteve uma sequência de 30 dias consecutivos de estudo.",
        "icon": "flame",
        "metric": AchievementMetric.STREAK_DAYS,
        "threshold": 30,
    },
    {
        "name": "Colecionador",
        "description": "Conquistou 10 badges.",
        "icon": "gem",
        "metric": AchievementMetric.BADGES_COUNT,
        "threshold": 10,
    },
    {
        "name": "Lenda",
        "description": "Acumulou 5000 pontos de XP.",
        "icon": "crown",
        "metric": AchievementMetric.TOTAL_XP,
        "threshold": 5000,
    },
]


async def seed(session: AsyncSession) -> None:
    repository = AchievementRepository(session)

    for item in ACHIEVEMENTS:
        existing = await session.scalar(select(Achievement).where(Achievement.name == item["name"]))
        if existing is not None:
            print(f"Achievement '{item['name']}' já existe - nada a fazer.")
            continue

        achievement = await repository.create(
            name=item["name"],
            description=item["description"],
            icon=item["icon"],
            metric=item["metric"],
            threshold=item["threshold"],
        )
        print(f"Achievement criado: {achievement.name} (id={achievement.id})")

    await session.commit()


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
