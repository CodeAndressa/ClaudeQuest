from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.gamification.repository import XpLedgerRepository
from app.domains.gamification.schemas import (
    GamificationProfileResponse,
    GrantXpRequest,
    GrantXpResponse,
)
from app.domains.gamification.service import GamificationService
from app.domains.users.model import User
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

router = APIRouter(prefix="/gamification", tags=["gamification"])


def get_gamification_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GamificationService:
    return GamificationService(XpLedgerRepository(session))


@router.get("/me")
async def get_my_profile(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    gamification_service: Annotated[GamificationService, Depends(get_gamification_service)],
) -> SuccessResponse[GamificationProfileResponse]:
    profile = await gamification_service.get_profile(current_user.id)
    return success_response(request, "Perfil de gamificação recuperado com sucesso.", profile)


@router.post("/xp")
async def grant_xp(
    request: Request,
    payload: GrantXpRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    gamification_service: Annotated[GamificationService, Depends(get_gamification_service)],
) -> SuccessResponse[GrantXpResponse]:
    result = await gamification_service.grant_xp(current_user.id, payload)
    return success_response(request, "XP concedido com sucesso.", result)
