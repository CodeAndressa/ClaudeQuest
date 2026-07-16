from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.database import registry  # noqa: F401 - registra os modelos em Base.metadata
from app.database.base import Base
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


@pytest_asyncio.fixture(scope="session")
async def db_engine():  # type: ignore[no-untyped-def]
    """Engine apontando para o Postgres real (docker compose up -d db)."""
    settings = get_settings()
    engine = create_async_engine(settings.test_database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession]:  # type: ignore[no-untyped-def]
    """Sessão transacional isolada: cada teste roda dentro de uma transação revertida ao final."""
    connection = await db_engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client_with_db(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient]:
    """Cliente assíncrono que reaproveita, no mesmo event loop, a sessão/transação de teste.

    Usa httpx.AsyncClient (não o TestClient síncrono) porque o TestClient roda a app numa
    thread com seu próprio event loop, o que quebra o compartilhamento de uma conexão
    asyncpg real entre o setup do teste e a requisição.
    """

    async def _override() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
