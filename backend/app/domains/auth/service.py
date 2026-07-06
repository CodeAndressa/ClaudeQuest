from datetime import UTC, datetime

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.domains.auth.repository import SessionRepository
from app.domains.auth.schemas import AuthenticatedUser, LoginRequest, TokenPairResponse
from app.domains.users.model import User, UserStatus
from app.domains.users.repository import UserRepository
from app.shared.errors import AppError

_INVALID_CREDENTIALS = AppError(
    code="invalid_credentials",
    message="E-mail ou senha inválidos.",
    status_code=401,
)

_INVALID_REFRESH_TOKEN = AppError(
    code="invalid_refresh_token",
    message="Sessão expirada. Faça login novamente.",
    status_code=401,
)


class AuthService:
    def __init__(self, users: UserRepository, sessions: SessionRepository) -> None:
        self._users = users
        self._sessions = sessions

    async def login(
        self,
        credentials: LoginRequest,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPairResponse:
        user = await self._users.get_by_email(credentials.email)
        if user is None or not verify_password(credentials.password, user.password_hash):
            raise _INVALID_CREDENTIALS

        self._ensure_active(user)
        await self._users.touch_last_login(user, datetime.now(UTC))

        return await self._issue_tokens(user, user_agent=user_agent, ip_address=ip_address)

    async def refresh(
        self,
        refresh_token: str | None,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPairResponse:
        if not refresh_token:
            raise _INVALID_REFRESH_TOKEN

        auth_session = await self._sessions.get_active_by_refresh_token_hash(
            hash_refresh_token(refresh_token)
        )
        if auth_session is None:
            raise _INVALID_REFRESH_TOKEN

        user = await self._users.get_by_id(auth_session.user_id)
        if user is None:
            raise _INVALID_REFRESH_TOKEN
        self._ensure_active(user)

        await self._sessions.revoke(auth_session)
        return await self._issue_tokens(user, user_agent=user_agent, ip_address=ip_address)

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        await self._sessions.revoke_by_refresh_token_hash(hash_refresh_token(refresh_token))

    def _ensure_active(self, user: User) -> None:
        if user.status != UserStatus.ACTIVE:
            raise AppError(
                code="account_not_active",
                message="Esta conta não está ativa. Fale com o administrador.",
                status_code=403,
            )

    async def _issue_tokens(
        self, user: User, *, user_agent: str | None, ip_address: str | None
    ) -> TokenPairResponse:
        access_token, expires_in = create_access_token(user.id, user.role.value)
        refresh_token, refresh_token_hash = generate_refresh_token()

        await self._sessions.create(
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            expires_at=refresh_token_expiry(),
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user=AuthenticatedUser(
                id=str(user.id),
                name=user.name,
                email=user.email,
                role=user.role.value,
            ),
        )
