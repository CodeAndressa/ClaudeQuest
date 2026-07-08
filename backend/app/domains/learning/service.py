from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.gamification.certificates import issue_completed_track_certificates
from app.domains.gamification.quests import mark_lesson_progress_for_quests
from app.domains.gamification.repository import XpLedgerRepository
from app.domains.gamification.xp_rules import calculate_level, xp_to_next_level
from app.domains.learning.model import Lesson, School, Track
from app.domains.learning.repository import (
    LessonProgressRepository,
    LessonRepository,
    SchoolRepository,
    TrackRepository,
)
from app.domains.learning.schemas import (
    CompleteLessonResponse,
    LessonDetail,
    LevelDetail,
    ModuleDetail,
    SchoolSummary,
    TrackDetail,
    TrackSummary,
)
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
        schools: SchoolRepository,
        tracks: TrackRepository,
        lessons: LessonRepository,
        progress: LessonProgressRepository,
        xp_ledger: XpLedgerRepository,
        session: AsyncSession | None = None,
    ) -> None:
        self._schools = schools
        self._tracks = tracks
        self._lessons = lessons
        self._progress = progress
        self._xp_ledger = xp_ledger
        self._session = session if session is not None else getattr(progress, "_session", None)

    async def list_schools(self) -> list[SchoolSummary]:
        schools = await self._schools.list_active()
        return [self._build_school_summary(school) for school in schools]

    async def list_tracks(
        self, user_id: UUID, *, school_id: UUID | None = None
    ) -> list[TrackSummary]:
        tracks = await self._tracks.list_active(school_id=school_id)
        completed_lesson_ids = await self._progress.list_completed_lesson_ids_for_user(user_id)
        return [self._build_track_summary(track, completed_lesson_ids) for track in tracks]

    async def get_track_detail(self, *, track_id: UUID, user_id: UUID) -> TrackDetail:
        track = await self._tracks.get_detail_by_id(track_id)
        if track is None or not track.is_active:
            raise _TRACK_NOT_FOUND
        completed_lesson_ids = await self._progress.list_completed_lesson_ids_for_user(user_id)
        return self._build_track_detail(track, completed_lesson_ids)

    async def complete_lesson(self, *, user_id: UUID, lesson_id: UUID) -> CompleteLessonResponse:
        lesson = await self._lessons.get_by_id(lesson_id)
        if lesson is None:
            raise _LESSON_NOT_FOUND

        existing = await self._progress.get_for_user_and_lesson(
            user_id=user_id, lesson_id=lesson_id
        )
        if existing is not None:
            if self._session is not None:
                await self._issue_track_certificate_if_completed(
                    user_id=user_id,
                    lesson_id=lesson_id,
                )
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
        progress = await self._progress.create(
            user_id=user_id, lesson_id=lesson_id, xp_awarded=xp_awarded
        )
        if xp_awarded > 0:
            await self._xp_ledger.add_entry(
                user_id=user_id,
                amount=xp_awarded,
                reason=f"lesson_completed:{lesson_id}",
            )

        if self._session is not None:
            await mark_lesson_progress_for_quests(
                self._session,
                user_id=user_id,
                lesson_id=lesson_id,
                completed_at=progress.completed_at,
            )
            await self._issue_track_certificate_if_completed(
                user_id=user_id,
                lesson_id=lesson_id,
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

    async def _issue_track_certificate_if_completed(
        self, *, user_id: UUID, lesson_id: UUID
    ) -> None:
        if self._session is None:
            return

        track_id = await self._lessons.get_track_id_for_lesson(lesson_id)
        if track_id is None:
            return

        track = await self._tracks.get_detail_by_id(track_id)
        if track is None or not track.is_active:
            return

        completed_lesson_ids = await self._progress.list_completed_lesson_ids_for_user(user_id)
        total_lessons, completed_lessons, _progress_percent = self._track_progress(
            track, completed_lesson_ids
        )
        if total_lessons > 0 and completed_lessons == total_lessons:
            await issue_completed_track_certificates(
                self._session,
                user_id=user_id,
                track_id=track_id,
            )

    @staticmethod
    def _build_school_summary(school: School) -> SchoolSummary:
        return SchoolSummary(
            id=school.id,
            title=school.title,
            slug=school.slug,
            description=school.description,
            icon=school.icon,
            order=school.order,
            track_count=sum(
                1 for track in school.tracks if track.deleted_at is None and track.is_active
            ),
        )

    @staticmethod
    def _track_progress(track: Track, completed_lesson_ids: set[UUID]) -> tuple[int, int, int]:
        lessons = [
            lesson
            for module in track.modules
            for level in module.levels
            for lesson in level.lessons
        ]
        total_lessons = len(lessons)
        completed_lessons = sum(1 for lesson in lessons if lesson.id in completed_lesson_ids)
        progress_percent = (
            round((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
        )
        return total_lessons, completed_lessons, progress_percent

    def _build_track_summary(self, track: Track, completed_lesson_ids: set[UUID]) -> TrackSummary:
        total_lessons, completed_lessons, progress_percent = self._track_progress(
            track, completed_lesson_ids
        )
        return TrackSummary(
            id=track.id,
            title=track.title,
            description=track.description,
            difficulty=track.difficulty,
            estimated_hours=track.estimated_hours,
            image=track.image,
            icon=track.icon,
            order=track.order,
            total_lessons=total_lessons,
            completed_lessons=completed_lessons,
            progress_percent=progress_percent,
        )

    def _build_lesson_detail(self, lesson: Lesson, completed_lesson_ids: set[UUID]) -> LessonDetail:
        return LessonDetail(
            id=lesson.id,
            title=lesson.title,
            description=lesson.description,
            content=lesson.content,
            estimated_minutes=lesson.estimated_minutes,
            difficulty=lesson.difficulty,
            lesson_type=lesson.lesson_type,
            order=lesson.order,
            xp=lesson.xp,
            ai_corrected=lesson.ai_corrected,
            completed=lesson.id in completed_lesson_ids,
            questions=[question for question in lesson.questions],
        )

    def _build_track_detail(self, track: Track, completed_lesson_ids: set[UUID]) -> TrackDetail:
        total_lessons, completed_lessons, progress_percent = self._track_progress(
            track, completed_lesson_ids
        )
        return TrackDetail(
            id=track.id,
            title=track.title,
            description=track.description,
            difficulty=track.difficulty,
            estimated_hours=track.estimated_hours,
            image=track.image,
            icon=track.icon,
            order=track.order,
            is_active=track.is_active,
            total_lessons=total_lessons,
            completed_lessons=completed_lessons,
            progress_percent=progress_percent,
            modules=[
                ModuleDetail(
                    id=module.id,
                    title=module.title,
                    description=module.description,
                    order=module.order,
                    levels=[
                        LevelDetail(
                            id=level.id,
                            title=level.title,
                            description=level.description,
                            level_number=level.level_number,
                            estimated_minutes=level.estimated_minutes,
                            xp=level.xp,
                            stars=level.stars,
                            required_xp=level.required_xp,
                            lessons=[
                                self._build_lesson_detail(lesson, completed_lesson_ids)
                                for lesson in level.lessons
                            ],
                        )
                        for level in module.levels
                    ],
                )
                for module in track.modules
            ],
        )
