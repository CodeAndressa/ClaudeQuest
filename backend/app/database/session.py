from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Dependency do FastAPI: fornece uma sessão de banco por requisição.

    Commita ao final se a requisição for concluída sem exceções; desfaz em caso de erro.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
