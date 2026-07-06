from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.domains.auth.dependencies import get_current_user
from app.domains.dashboard.repository import DashboardRepository
from app.domains.dashboard.schemas import DashboardResponse
from app.domains.dashboard.service import DashboardService
from app.domains.users.model import User
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardService:
    return DashboardService(DashboardRepository(session))


@router.get("/me")
async def get_my_dashboard(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> SuccessResponse[DashboardResponse]:
    summary = await dashboard_service.get_summary(current_user.id)
    return success_response(request, "Resumo do dashboard recuperado com sucesso.", summary)
