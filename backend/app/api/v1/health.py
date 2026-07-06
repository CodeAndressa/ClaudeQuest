from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.middlewares.request_context import get_execution_time_ms, get_request_id
from app.shared.errors import AppError
from app.shared.schemas import ResponseMetadata, SuccessResponse

router = APIRouter(tags=["health"])


def _envelope(
    request: Request, message: str, data: dict[str, object]
) -> SuccessResponse[dict[str, object]]:
    return SuccessResponse(
        message=message,
        data=data,
        metadata=ResponseMetadata(
            request_id=get_request_id(request),
            execution_time_ms=get_execution_time_ms(request),
        ),
    )


@router.get("/health")
async def health(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> SuccessResponse[dict[str, object]]:
    """Informações gerais de identidade do serviço."""
    return _envelope(
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
    return _envelope(request, "Processo ativo.", {"status": "ok"})


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

    return _envelope(request, "Serviço pronto para receber tráfego.", {"status": "ok"})
