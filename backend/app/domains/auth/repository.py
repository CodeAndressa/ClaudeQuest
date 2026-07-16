from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.model import Session as AuthSession


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthSession:
        auth_session = AuthSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self._session.add(auth_session)
        await self._session.flush()
        return auth_session

    async def get_active_by_refresh_token_hash(self, refresh_token_hash: str) -> AuthSession | None:
        statement = select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke(self, auth_session: AuthSession) -> None:
        auth_session.revoked_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke_by_refresh_token_hash(self, refresh_token_hash: str) -> None:
        auth_session = await self.get_active_by_refresh_token_hash(refresh_token_hash)
        if auth_session is not None:
            await self.revoke(auth_session)

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoga todas as sessões ativas do usuário - usado no reset de senha
        (AUTH-003), para invalidar refresh tokens emitidos com a senha antiga."""
        statement = (
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.execute(statement)
        await self._session.flush()
