from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db_session
from app.main import app


class _FakeSession:
    """Sessão de banco falsa usada para isolar os testes de uma instância real de Postgres."""

    async def execute(self, _statement: object) -> None:
        return None


class _FailingSession:
    async def execute(self, _statement: object) -> None:
        raise ConnectionRefusedError("banco de dados indisponível")


@pytest.fixture
def client() -> Generator[TestClient]:
    async def _override() -> Generator:
        yield _FakeSession()

    app.dependency_overrides[get_db_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_db_down() -> Generator[TestClient]:
    async def _override() -> Generator:
        yield _FailingSession()

    app.dependency_overrides[get_db_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
