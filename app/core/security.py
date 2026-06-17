from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import os
import secrets

pwd_context = None

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "change-me"


def hash_password(password: str):
    if pwd_context:
        try:
            return pwd_context.hash(password)
        except Exception:
            pass

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, hashed: str):
    if pwd_context:
        try:
            return pwd_context.verify(password, hashed)
        except Exception:
            pass

    if not hashed.startswith("pbkdf2_sha256$"):
        return False

    _, salt, expected = hashed.split("$", 2)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100_000,
    ).hex()
    return hmac.compare_digest(digest, expected)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _create_token(data: dict, token_type: str, expires_minutes: int):
    payload = data.copy()
    payload["type"] = token_type
    payload["exp"] = int(
        (datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)).timestamp()
    )

    body = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(
        SECRET_KEY.encode(),
        body.encode(),
        hashlib.sha256,
    ).digest()

    return f"{body}.{_b64_encode(signature)}"


def create_access_token(data: dict, expires_minutes=1440):
    return _create_token(data, "access", expires_minutes)


def create_refresh_token(data: dict, expires_minutes=60 * 24 * 7):
    return _create_token(data, "refresh", expires_minutes)


def decode_token(token: str):
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        raise ValueError("Invalid token")

    expected = hmac.new(
        SECRET_KEY.encode(),
        body.encode(),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_b64_decode(signature), expected):
        raise ValueError("Invalid token")

    payload = json.loads(_b64_decode(body))
    if payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("Token expired")

    return payload
