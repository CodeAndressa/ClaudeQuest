from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.shared.errors import AppError
from app.shared.response import success_response
from app.shared.schemas import SuccessResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> SuccessResponse[dict[str, object]]:
    """Informações gerais de identidade do serviço."""
    return success_response(
        request,
        "Serviço operacional.",
        {
            "app": settings.app_name,
            "environment": settings.environment,
            "status": "ok",
        },
    )


@router.get("/live")
async def live(request: Request) -> SuccessResponse[dict[str, object]]:
    """Liveness probe: o processo está de pé."""
    return success_response(request, "Processo ativo.", {"status": "ok"})


@router.get("/ready")
async def ready(
    request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> SuccessResponse[dict[str, object]]:
    """Readiness probe: o serviço consegue falar com o banco de dados."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError(
            code="database_unavailable",
            message="Não foi possível conectar ao banco de dados.",
            status_code=503,
        ) from exc

    return success_response(request, "Serviço pronto para receber tráfego.", {"status": "ok"})
