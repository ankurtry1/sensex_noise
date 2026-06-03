from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from kiteconnect.exceptions import KiteException

from sensex_noise.auth.kite_auth import build_login_url, exchange_request_token
from sensex_noise.auth.token_store import TokenStore
from sensex_noise.config import Settings, load_settings


router = APIRouter(prefix="/kite", tags=["kite"])

_STATE_COOKIE = "kite_auth_state"
_STATE_MAX_AGE_SECONDS = 15 * 60


def get_settings() -> Settings:
    return load_settings()


def _state_secret(settings: Settings) -> str:
    return settings.admin_token or settings.kite_api_secret


def _sign_state(secret: str, payload: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _new_state(settings: Settings, now: int | None = None) -> str:
    issued_at = now if now is not None else int(time.time())
    nonce = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode("ascii").rstrip("=")
    payload = f"{nonce}.{issued_at}"
    return f"{payload}.{_sign_state(_state_secret(settings), payload)}"


def _valid_state(settings: Settings, state: str, now: int | None = None) -> bool:
    parts = state.split(".")
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
    if current_time - issued_at > _STATE_MAX_AGE_SECONDS:
        return False

    payload = f"{nonce}.{issued_at}"
    expected = _sign_state(_state_secret(settings), payload)
    return secrets.compare_digest(signature, expected)


def _with_state(url: str, state_value: str) -> str:
    parsed = urlsplit(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("state", state_value))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


@router.get("/login")
def kite_login(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    state_value = _new_state(settings)
    login_url = _with_state(build_login_url(settings.kite_api_key), state_value)
    response = RedirectResponse(login_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.set_cookie(
        _STATE_COOKIE,
        state_value,
        max_age=_STATE_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.app_base_url.startswith("https://"),
        samesite="lax",
    )
    return response


@router.get("/callback")
def kite_callback(
    request_token: str = Query(..., min_length=1),
    state: str | None = None,
    kite_auth_state: str | None = Cookie(default=None, alias=_STATE_COOKIE),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    if kite_auth_state is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Kite auth state")
    if state is not None and not secrets.compare_digest(state, kite_auth_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kite auth state mismatch")
    if not _valid_state(settings, kite_auth_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired Kite auth state")

    try:
        session = exchange_request_token(
            api_key=settings.kite_api_key,
            api_secret=settings.kite_api_secret,
            request_token=request_token,
        )
    except (KiteException, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kite token exchange failed") from exc

    record = TokenStore(settings.token_store_path).save(
        access_token=session.access_token,
        api_key=settings.kite_api_key,
        user_id=session.user_id,
    )
    response = JSONResponse(
        {
            "status": "ok",
            "token_store": {
                "has_today_token": True,
                "metadata": record.safe_metadata(),
            },
        }
    )
    response.delete_cookie(
        _STATE_COOKIE,
        secure=settings.app_base_url.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    return response
