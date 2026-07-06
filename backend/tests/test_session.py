import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session


async def test_get_db_session_yields_an_async_session() -> None:
    generator = get_db_session()

    session = await anext(generator)
    assert isinstance(session, AsyncSession)

    await generator.aclose()


async def test_get_db_session_commits_when_the_request_succeeds() -> None:
    generator = get_db_session()
    await anext(generator)

    with pytest.raises(StopAsyncIteration):
        await anext(generator)


async def test_get_db_session_rolls_back_and_reraises_on_error() -> None:
    generator = get_db_session()
    await anext(generator)

    with pytest.raises(ValueError, match="falha simulada"):
        await generator.athrow(ValueError("falha simulada"))
