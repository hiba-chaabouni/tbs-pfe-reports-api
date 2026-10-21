"""Authentication: users, JWT creation/checking, revocation and @token_required."""
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, request
from werkzeug.security import check_password_hash

from config import (ACCESS_TOKEN_EXPIRES_SECONDS, JWT_ALGORITHM,
                    REFRESH_TOKEN_EXPIRES_SECONDS, SECRET_KEY)
from errors import ApiError

# Hard-coded users. Only password HASHES are stored (werkzeug scrypt), never plain text.
users = [
    {"username": "admin",
     "password_hash": "scrypt:32768:8:1$6R6ODp545zL8kKp5$dc81bd2bee336eb3055f6de0aaa31955635afb5da3ee868c9a23d1a584ff597f4c78c7e521007a2f322b031c4662cc64ed424e44dbce68519e9a94a3be691c73"},
    {"username": "tbs_student",
     "password_hash": "scrypt:32768:8:1$kefAXDXEppo7YhGs$a05724c0c92f594387bd7244010fe83dd436e4c02875a3326ff651d283ad381bb4b14efe092b4ae8b8a403b0e781fa1173d034f2c6f9b71a056bb430d72425e1"},
]

# In-memory blocklist: the unique id (jti) of every revoked token.
revoked_tokens = set()


def check_credentials(username, password):
    user = next((u for u in users if u["username"] == username), None)
    return user is not None and check_password_hash(user["password_hash"], password)


# ---------------------------------------------------------------------------
# Creating tokens
# ---------------------------------------------------------------------------
def _create_token(username, token_type, lifetime_seconds):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,                 # who the token belongs to
        "type": token_type,              # "access" or "refresh"
        "jti": uuid.uuid4().hex,         # unique id, used for revocation
        "iat": now,
        "exp": now + timedelta(seconds=lifetime_seconds),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_token_pair(username):
    return {
        "access_token": _create_token(username, "access", ACCESS_TOKEN_EXPIRES_SECONDS),
        "refresh_token": _create_token(username, "refresh", REFRESH_TOKEN_EXPIRES_SECONDS),
        "token_type": "Bearer",
        "access_expires_in": ACCESS_TOKEN_EXPIRES_SECONDS,
        "refresh_expires_in": REFRESH_TOKEN_EXPIRES_SECONDS,
    }


# ---------------------------------------------------------------------------
# Reading and checking tokens
# ---------------------------------------------------------------------------
def get_bearer_token():
    """Read 'Authorization: Bearer <token>' or raise 401."""
    header = request.headers.get("Authorization", "")
    if not header:
        raise ApiError(401, "Unauthorized",
                       "Missing token. Send header 'Authorization: Bearer <token>'.")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ApiError(401, "Unauthorized",
                       "Malformed Authorization header. Expected 'Bearer <token>'.")
    return parts[1]


def decode_token(token, expected_type):
    """Return the token's payload, or raise 401 with a precise reason."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM],
                             options={"require": ["exp", "sub", "type", "jti"]})
    except jwt.ExpiredSignatureError:
        if expected_type == "access":
            raise ApiError(401, "Token Expired", "Access token expired, use /auth/refresh.")
        raise ApiError(401, "Token Expired", "Refresh token expired, please log in again.")
    except jwt.InvalidTokenError:
        raise ApiError(401, "Invalid Token", "Token is malformed or its signature is invalid.")

    if payload["type"] != expected_type:
        raise ApiError(401, "Wrong Token Type",
                       f"Expected the {expected_type} token but received the {payload['type']} token.")
    if payload["jti"] in revoked_tokens:
        raise ApiError(401, "Token Revoked", f"This {expected_type} token has been revoked.")
    return payload


def revoke(payload):
    revoked_tokens.add(payload["jti"])


def token_required(view):
    """Decorator: the route runs only with a valid, non-revoked ACCESS token."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.token = decode_token(get_bearer_token(), "access")
        g.current_user = g.token["sub"]
        return view(*args, **kwargs)
    return wrapper
