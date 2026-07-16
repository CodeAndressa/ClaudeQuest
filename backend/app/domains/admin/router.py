from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.domains.admin.repository import AdminRepository
from app.domains.admin.schemas import (
    AdminCertificateItem,
    AdminOverview,
    AdminTrackItem,
    AdminUserItem,
    CreateUserRequest,
    UpdateTrackStatusRequest,
    UpdateUserStatusRequest,
)
from app.domains.admin.service import AdminService
from app.domains.auth.dependencies import get_current_user
from app.domains.users.model import User, UserRole
from app.shared.errors import AppError
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

router = APIRouter(prefix="/admin", tags=["admin"])

_FORBIDDEN = AppError(
    code="forbidden", message="Apenas administradores podem acessar esta operação.", status_code=403
)


def get_admin_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AdminService:
    return AdminService(AdminRepository(session))


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.ADMIN:
        raise _FORBIDDEN
    return current_user


@router.get("/overview")
async def overview(
    request: Request,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> SuccessResponse[AdminOverview]:
    return success_response(request, "Visão administrativa carregada.", await service.overview())


@router.get("/users")
async def list_users(
    request: Request,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> SuccessResponse[list[AdminUserItem]]:
    return success_response(request, "Usuários listados.", await service.list_users())


@router.post("/users", status_code=201)
async def create_user(
    request: Request,
    payload: CreateUserRequest,
    admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> SuccessResponse[AdminUserItem]:
    result = await service.create_user(
        organization_id=admin.organization_id,
        name=payload.name,
        email=str(payload.email),
        password=payload.password,
        role=payload.role,
    )
    return success_response(request, "Usuário criado.", result)


@router.patch("/users/{user_id}/status")
async def update_user_status(
    request: Request,
    user_id: UUID,
    payload: UpdateUserStatusRequest,
    admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> SuccessResponse[AdminUserItem]:
    result = await service.update_user_status(
        actor_id=admin.id, user_id=user_id, status=payload.status
    )
    return success_response(request, "Status do usuário atualizado.", result)


@router.get("/tracks")
async def list_tracks(
    request: Request,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> SuccessResponse[list[AdminTrackItem]]:
    return success_response(request, "Trilhas listadas.", await service.list_tracks())


@router.patch("/tracks/{track_id}/status")
async def update_track_status(
    request: Request,
    track_id: UUID,
    payload: UpdateTrackStatusRequest,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> SuccessResponse[AdminTrackItem]:
    result = await service.update_track_status(track_id=track_id, is_active=payload.is_active)
    return success_response(request, "Publicação da trilha atualizada.", result)


@router.get("/certificates")
async def list_certificates(
    request: Request,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> SuccessResponse[list[AdminCertificateItem]]:
    return success_response(request, "Certificados listados.", await service.list_certificates())
