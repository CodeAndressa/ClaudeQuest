"""
Cria uma entrada de catalogo de certificado para cada trilha ativa.

Uso: uv run python scripts/seed_certificates.py
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.domains.gamification.certificates import Certificate, CertificateRepository
from app.domains.learning.model import Lesson, Level, Module, Track, UserLessonProgress


async def seed(session: AsyncSession) -> None:
    result = await session.execute(
        select(Track).where(Track.is_active.is_(True), Track.deleted_at.is_(None))
    )
    tracks = list(result.scalars().all())
    if not tracks:
        print("Nenhuma trilha ativa encontrada. Rode seed_learning_content.py primeiro.")
        return

    created_count = 0
    skipped_count = 0
    issued_count = 0
    repository = CertificateRepository(session)
    for track in tracks:
        existing = await session.scalar(select(Certificate).where(Certificate.track_id == track.id))
        if existing is not None:
            skipped_count += 1
        else:
            await repository.create(
                track_id=track.id,
                title=f"Certificado {track.title}",
                hours=track.estimated_hours,
            )
            created_count += 1

        issued_count += await _backfill_completed_track_certificates(
            session,
            repository=repository,
            track=track,
        )

    await session.commit()
    print(
        "Certificados criados: "
        f"{created_count}; ja existentes: {skipped_count}; emissoes preenchidas: {issued_count}."
    )


async def _backfill_completed_track_certificates(
    session: AsyncSession,
    *,
    repository: CertificateRepository,
    track: Track,
) -> int:
    lesson_ids = list(
        (
            await session.execute(
                select(Lesson.id)
                .join(Level, Level.id == Lesson.level_id)
                .join(Module, Module.id == Level.module_id)
                .where(
                    Module.track_id == track.id,
                    Module.deleted_at.is_(None),
                    Level.deleted_at.is_(None),
                    Lesson.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    if not lesson_ids:
        return 0

    certificates = await repository.list_for_track(track.id)
    if not certificates:
        return 0

    result = await session.execute(
        select(UserLessonProgress.user_id)
        .where(
            UserLessonProgress.lesson_id.in_(lesson_ids),
            UserLessonProgress.deleted_at.is_(None),
        )
        .group_by(UserLessonProgress.user_id)
        .having(func.count(distinct(UserLessonProgress.lesson_id)) == len(lesson_ids))
    )
    completed_user_ids = list(result.scalars().all())

    issued_count = 0
    for user_id in completed_user_ids:
        for certificate in certificates:
            existing = await repository.get_issued(certificate_id=certificate.id, user_id=user_id)
            if existing is not None:
                continue
            await repository.issue(
                certificate_id=certificate.id,
                user_id=user_id,
                issued_at=datetime.now(UTC),
            )
            issued_count += 1
    return issued_count


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
