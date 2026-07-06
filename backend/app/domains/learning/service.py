from uuid import UUID

from app.domains.gamification.repository import XpLedgerRepository
from app.domains.gamification.xp_rules import calculate_level, xp_to_next_level
from app.domains.learning.model import Track
from app.domains.learning.repository import LessonProgressRepository, LessonRepository, TrackRepository
from app.domains.learning.schemas import CompleteLessonResponse
from app.shared.errors import AppError

_TRACK_NOT_FOUND = AppError(
    code="track_not_found",
    message="Trilha nao encontrada.",
    status_code=404,
)

_LESSON_NOT_FOUND = AppError(
    code="lesson_not_found",
    message="Missao nao encontrada.",
    status_code=404,
)


class LearningService:
    def __init__(
        self,
        tracks: TrackRepository,
        lessons: LessonRepository,
        progress: LessonProgressRepository,
        xp_ledger: XpLedgerRepository,
    ) -> None:
        self._tracks = tracks
        self._lessons = lessons
        self._progress = progress
        self._xp_ledger = xp_ledger

    async def list_tracks(self) -> list[Track]:
        return await self._tracks.list_active()

    async def get_track_detail(self, track_id: UUID) -> Track:
        track = await self._tracks.get_detail_by_id(track_id)
        if track is None or not track.is_active:
            raise _TRACK_NOT_FOUND
        return track

    async def complete_lesson(self, *, user_id: UUID, lesson_id: UUID) -> CompleteLessonResponse:
        lesson = await self._lessons.get_by_id(lesson_id)
        if lesson is None:
            raise _LESSON_NOT_FOUND

        existing = await self._progress.get_for_user_and_lesson(
            user_id=user_id, lesson_id=lesson_id
        )
        if existing is not None:
            total_xp = await self._xp_ledger.get_total_xp(user_id)
            return CompleteLessonResponse(
                lesson_id=lesson_id,
                completed=True,
                already_completed=True,
                xp_granted=0,
                total_xp=total_xp,
                level=calculate_level(total_xp),
                xp_to_next_level=xp_to_next_level(total_xp),
            )

        xp_awarded = max(lesson.xp, 0)
        await self._progress.create(user_id=user_id, lesson_id=lesson_id, xp_awarded=xp_awarded)
        if xp_awarded > 0:
            await self._xp_ledger.add_entry(
                user_id=user_id,
                amount=xp_awarded,
                reason=f"lesson_completed:{lesson_id}",
            )

        total_xp = await self._xp_ledger.get_total_xp(user_id)
        return CompleteLessonResponse(
            lesson_id=lesson_id,
            completed=True,
            already_completed=False,
            xp_granted=xp_awarded,
            total_xp=total_xp,
            level=calculate_level(total_xp),
            xp_to_next_level=xp_to_next_level(total_xp),
        )
