from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.domains.auth.cookies import clear_refresh_token_cookie, set_refresh_token_cookie
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.password_reset import (
    ForgotPasswordRequest,
    PasswordResetRepository,
    PasswordResetService,
    ResetPasswordRequest,
)
from app.domains.auth.repository import SessionRepository
from app.domains.auth.schemas import AuthenticatedUser, LoginRequest, SessionResponse
from app.domains.auth.service import AuthService
from app.domains.users.model import User
from app.domains.users.repository import UserRepository
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(UserRepository(session), SessionRepository(session))


def get_password_reset_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PasswordResetService:
    return PasswordResetService(
        UserRepository(session), PasswordResetRepository(session), SessionRepository(session)
    )


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SuccessResponse[SessionResponse]:
    tokens = await auth_service.login(
        credentials,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    set_refresh_token_cookie(response, tokens.refresh_token)
    return success_response(
        request, "Login realizado com sucesso.", SessionResponse.from_token_pair(tokens)
    )


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> SuccessResponse[SessionResponse]:
    tokens = await auth_service.refresh(
        refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    set_refresh_token_cookie(response, tokens.refresh_token)
    return success_response(
        request, "Sessão renovada com sucesso.", SessionResponse.from_token_pair(tokens)
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> SuccessResponse[dict[str, object]]:
    await auth_service.logout(refresh_token)
    clear_refresh_token_cookie(response)
    return success_response(request, "Logout realizado com sucesso.", {"status": "ok"})


@router.get("/me")
async def me(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SuccessResponse[AuthenticatedUser]:
    return success_response(
        request,
        "Usuário autenticado.",
        AuthenticatedUser(
            id=str(current_user.id),
            name=current_user.name,
            email=current_user.email,
            role=current_user.role.value,
        ),
    )


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    password_reset_service: Annotated[PasswordResetService, Depends(get_password_reset_service)],
) -> SuccessResponse[dict[str, object]]:
    await password_reset_service.forgot_password(payload)
    return success_response(
        request,
        "Se o e-mail informado estiver cadastrado, enviaremos instruções de recuperação.",
        {"status": "ok"},
    )


@router.post("/reset-password")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    password_reset_service: Annotated[PasswordResetService, Depends(get_password_reset_service)],
) -> SuccessResponse[dict[str, object]]:
    await password_reset_service.reset_password(payload)
    return success_response(request, "Senha alterada com sucesso.", {"status": "ok"})
