from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.session import get_db_session
from app.domains.users.model import User, UserStatus
from app.domains.users.repository import UserRepository
from app.shared.errors import AppError

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = AppError(
    code="unauthorized", message="Autenticação necessária.", status_code=401
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if credentials is None:
        raise _UNAUTHORIZED

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _UNAUTHORIZED from exc

    user = await UserRepository(session).get_by_id(UUID(payload["sub"]))
    if user is None or user.status != UserStatus.ACTIVE:
        raise _UNAUTHORIZED

    return user
