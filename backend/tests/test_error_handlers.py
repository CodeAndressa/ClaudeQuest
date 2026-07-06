import json

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.middlewares.error_handler import (
    handle_app_error,
    handle_unexpected_error,
    handle_validation_error,
)
from app.shared.errors import AppError


def _fake_request() -> Request:
    return Request(scope={"type": "http", "headers": [], "method": "GET", "path": "/"})


@pytest.mark.asyncio
async def test_handle_app_error_builds_standard_envelope() -> None:
    exc = AppError(code="not_found", message="Recurso não encontrado.", status_code=404)

    response = await handle_app_error(_fake_request(), exc)

    body = json.loads(response.body)
    assert response.status_code == 404
    assert body["success"] is False
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "Recurso não encontrado."
    assert "trace_id" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_handle_validation_error_returns_422() -> None:
    exc = RequestValidationError(
        errors=[{"loc": ("body", "email"), "msg": "campo obrigatório", "type": "missing"}]
    )

    response = await handle_validation_error(_fake_request(), exc)

    body = json.loads(response.body)
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]["errors"][0]["loc"] == ["body", "email"]


@pytest.mark.asyncio
async def test_handle_unexpected_error_never_leaks_internals() -> None:
    exc = RuntimeError("segredo interno: senha=hunter2")

    response = await handle_unexpected_error(_fake_request(), exc)

    body = json.loads(response.body)
    assert response.status_code == 500
    assert body["error"]["code"] == "internal_error"
    assert "senha" not in json.dumps(body)
    assert "trace_id" in body
