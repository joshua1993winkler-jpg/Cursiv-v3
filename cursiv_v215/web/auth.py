"""
Auth helpers — bcrypt password hashing + JWT session tokens.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

_SECRET = os.environ.get("CURSIV_BOARD_SECRET", "change-me-in-production-env")
_ALG    = "HS256"
_TTL_H  = 72


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: str, username: str) -> str:
    exp = datetime.utcnow() + timedelta(hours=_TTL_H)
    return jwt.encode(
        {"sub": user_id, "username": username, "exp": exp},
        _SECRET, algorithm=_ALG,
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALG])
    except JWTError:
        return None
