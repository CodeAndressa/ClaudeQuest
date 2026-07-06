from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session


async def test_get_db_session_yields_an_async_session() -> None:
    generator = get_db_session()

    session = await anext(generator)
    assert isinstance(session, AsyncSession)

    await generator.aclose()
