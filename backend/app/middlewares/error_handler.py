import uuid
from datetime import UTC, datetime
from typing import cast

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.middlewares.request_context import get_request_id
from app.shared.errors import AppError

logger = structlog.get_logger("errors")


def _error_body(
    code: str, message: str, details: dict[str, object], trace_id: str
) -> dict[str, object]:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
        "trace_id": trace_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    exc = cast(AppError, exc)
    trace_id = get_request_id(request)
    logger.warning("app_error", code=exc.code, message=exc.message, trace_id=trace_id)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details, trace_id),
    )


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    exc = cast(RequestValidationError, exc)
    trace_id = get_request_id(request)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            "validation_error",
            "Dados de entrada inválidos.",
            {"errors": exc.errors()},
            trace_id,
        ),
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    trace_id = get_request_id(request) or str(uuid.uuid4())
    logger.error("unhandled_error", error=str(exc), trace_id=trace_id, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            "internal_error",
            "Ocorreu um erro inesperado. Nossa equipe já foi notificada.",
            {},
            trace_id,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Ponto único de tratamento de erros. Nenhum outro local deve capturar Exception."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
