import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Atribui um request_id a cada requisição, mede o tempo de execução e loga o acesso."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        request.state.start_time = start_time

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        structlog.contextvars.clear_contextvars()
        return response


def get_execution_time_ms(request: Request) -> float:
    start_time: float = getattr(request.state, "start_time", time.perf_counter())
    return round((time.perf_counter() - start_time) * 1000, 2)


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid.uuid4()))
