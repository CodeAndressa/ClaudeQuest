from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.gamification.repository import XpLedgerRepository
from app.domains.learning.repository import LessonProgressRepository, LessonRepository, TrackRepository
from app.domains.learning.schemas import CompleteLessonResponse, TrackDetail, TrackSummary
from app.domains.learning.service import LearningService
from app.domains.users.model import User
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

router = APIRouter(prefix="/learning", tags=["learning"])


def get_learning_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LearningService:
    return LearningService(
        TrackRepository(session),
        LessonRepository(session),
        LessonProgressRepository(session),
        XpLedgerRepository(session),
    )


@router.get("/tracks")
async def list_tracks(
    request: Request,
    learning_service: Annotated[LearningService, Depends(get_learning_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[list[TrackSummary]]:
    tracks = await learning_service.list_tracks(current_user.id)
    return success_response(
        request,
        "Trilhas listadas com sucesso.",
        tracks,
    )


@router.get("/tracks/{track_id}")
async def get_track_detail(
    request: Request,
    track_id: UUID,
    learning_service: Annotated[LearningService, Depends(get_learning_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[TrackDetail]:
    track = await learning_service.get_track_detail(track_id=track_id, user_id=current_user.id)
    return success_response(request, "Detalhe da trilha obtido com sucesso.", track)


@router.post("/lessons/{lesson_id}/complete")
async def complete_lesson(
    request: Request,
    lesson_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    learning_service: Annotated[LearningService, Depends(get_learning_service)],
) -> SuccessResponse[CompleteLessonResponse]:
    result = await learning_service.complete_lesson(user_id=current_user.id, lesson_id=lesson_id)
    return success_response(request, "Missao concluida com sucesso.", result)
