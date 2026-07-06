from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class AuthenticatedUser(BaseModel):
    id: str
    name: str
    email: str
    role: str


class TokenPairResponse(BaseModel):
    """Uso interno do Service — nunca serializado diretamente numa resposta HTTP.

    O refresh_token nunca deve chegar ao corpo JSON: o Router o extrai daqui e o
    envia como cookie httpOnly (ver app/domains/auth/cookies.py).
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthenticatedUser


class SessionResponse(BaseModel):
    """Resposta pública de login/refresh — nunca inclui o refresh token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthenticatedUser

    @classmethod
    def from_token_pair(cls, tokens: TokenPairResponse) -> "SessionResponse":
        return cls(
            access_token=tokens.access_token,
            token_type=tokens.token_type,
            expires_in=tokens.expires_in,
            user=tokens.user,
        )
