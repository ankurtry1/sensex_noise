from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from sensex_noise.config import Settings


ADMIN_SESSION_COOKIE = "sensex_admin_session"
ADMIN_SESSION_MAX_AGE_SECONDS = 18 * 60 * 60


def _session_secret(settings: Settings) -> str:
    return settings.admin_token.strip()


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def new_admin_session(settings: Settings, now: int | None = None) -> str:
    secret = _session_secret(settings)
    if not secret:
        raise ValueError("ADMIN_TOKEN is required for admin sessions")
    issued_at = now if now is not None else int(time.time())
    nonce = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode("ascii").rstrip("=")
    payload = f"{nonce}.{issued_at}"
    return f"{payload}.{_sign(secret, payload)}"


def valid_admin_session(settings: Settings, session: str | None, now: int | None = None) -> bool:
    secret = _session_secret(settings)
    if not secret or not session:
        return False

    parts = session.split(".")
    if len(parts) != 3:
        return False

    nonce, issued_at_raw, signature = parts
    if not nonce or not issued_at_raw or not signature:
        return False

    try:
        issued_at = int(issued_at_raw)
    except ValueError:
        return False

    current_time = now if now is not None else int(time.time())
    if issued_at > current_time + 60:
        return False
    if current_time - issued_at > ADMIN_SESSION_MAX_AGE_SECONDS:
        return False

    payload = f"{nonce}.{issued_at}"
    expected = _sign(secret, payload)
    return secrets.compare_digest(signature, expected)
