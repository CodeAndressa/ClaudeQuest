from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.domains.auth.repository import SessionRepository
from app.domains.auth.schemas import LoginRequest, TokenPairResponse
from app.domains.auth.service import AuthService
from app.domains.users.repository import UserRepository
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(UserRepository(session), SessionRepository(session))


@router.post("/login")
async def login(
    request: Request,
    credentials: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[TokenPairResponse]:
    result = await auth_service.login(
        credentials,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return success_response(request, "Login realizado com sucesso.", result)
