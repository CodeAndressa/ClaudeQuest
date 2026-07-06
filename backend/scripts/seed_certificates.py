"""
Cria uma entrada de catálogo de certificado para a trilha de demonstração,
para permitir testar a emissão (POST /gamification/certificates/{id}/issue)
sem precisar de um Admin Portal (ainda não implementado — ADMIN-002).

Uso: uv run python scripts/seed_certificates.py
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.domains.gamification.certificates import Certificate, CertificateRepository
from app.domains.learning.model import Track

TRACK_TITLE = "Claude Chat"


async def seed(session: AsyncSession) -> None:
    track = await session.scalar(select(Track).where(Track.title == TRACK_TITLE))
    if track is None:
        print(f"Trilha '{TRACK_TITLE}' não encontrada — rode seed_learning_content.py primeiro.")
        return

    existing = await session.scalar(select(Certificate).where(Certificate.track_id == track.id))
    if existing is not None:
        print(f"Certificado para '{TRACK_TITLE}' já existe — nada a fazer.")
        return

    certificate = await CertificateRepository(session).create(
        track_id=track.id, title=f"Certificado {TRACK_TITLE}", hours=track.estimated_hours
    )
    await session.commit()

    print(f"Certificado criado: {certificate.title} (id={certificate.id})")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
