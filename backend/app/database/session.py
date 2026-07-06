from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Dependency do FastAPI: fornece uma sessão de banco por requisição."""
    async with AsyncSessionLocal() as session:
        yield session
