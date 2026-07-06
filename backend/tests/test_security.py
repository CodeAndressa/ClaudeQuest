import uuid
from datetime import datetime

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)


def test_hash_password_produces_a_verifiable_hash() -> None:
    password_hash = hash_password("uma-senha-forte")

    assert password_hash != "uma-senha-forte"
    assert verify_password("uma-senha-forte", password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    password_hash = hash_password("uma-senha-forte")

    assert verify_password("senha-errada", password_hash) is False


def test_create_access_token_contains_subject_and_role() -> None:
    user_id = uuid.uuid4()

    token, expires_in = create_access_token(user_id, "admin")
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"
    assert expires_in > 0


def test_create_access_token_is_unique_even_for_the_same_user_within_the_same_second() -> None:
    user_id = uuid.uuid4()

    first, _ = create_access_token(user_id, "student")
    second, _ = create_access_token(user_id, "student")

    assert first != second


def test_decode_access_token_rejects_tampered_token() -> None:
    token, _ = create_access_token(uuid.uuid4(), "student")

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token + "tampered")


def test_generate_refresh_token_returns_plain_and_hash() -> None:
    plain, hashed = generate_refresh_token()

    assert plain != hashed
    assert hash_refresh_token(plain) == hashed


def test_generate_refresh_token_is_unique_each_call() -> None:
    first, _ = generate_refresh_token()
    second, _ = generate_refresh_token()

    assert first != second


def test_refresh_token_expiry_is_in_the_future() -> None:
    assert refresh_token_expiry() > datetime.now(refresh_token_expiry().tzinfo)
