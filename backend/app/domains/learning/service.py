from uuid import UUID

from app.domains.learning.model import Track
from app.domains.learning.repository import TrackRepository
from app.shared.errors import AppError

_TRACK_NOT_FOUND = AppError(
    code="track_not_found",
    message="Trilha não encontrada.",
    status_code=404,
)


class LearningService:
    def __init__(self, tracks: TrackRepository) -> None:
        self._tracks = tracks

    async def list_tracks(self) -> list[Track]:
        return await self._tracks.list_active()

    async def get_track_detail(self, track_id: UUID) -> Track:
        track = await self._tracks.get_detail_by_id(track_id)
        if track is None or not track.is_active:
            raise _TRACK_NOT_FOUND
        return track
