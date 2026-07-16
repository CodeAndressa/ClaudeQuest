from fastapi import Response

from app.core.config import get_settings

REFRESH_TOKEN_COOKIE_NAME = "refresh_token"  # nosec B105 - nome do cookie, não um segredo
REFRESH_TOKEN_COOKIE_PATH = "/api/v1/auth"  # nosec B105 - path do cookie, não um segredo


def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.jwt_refresh_expire_days * 24 * 60 * 60,
        path=REFRESH_TOKEN_COOKIE_PATH,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE_NAME, path=REFRESH_TOKEN_COOKIE_PATH)
