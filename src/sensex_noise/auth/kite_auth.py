from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kiteconnect import KiteConnect


@dataclass(frozen=True)
class KiteSession:
    access_token: str
    user_id: str | None = None
    raw_metadata: dict[str, Any] | None = None

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "has_access_token": bool(self.access_token.strip()),
        }


def build_login_url(api_key: str) -> str:
    kite = KiteConnect(api_key=api_key)
    return str(kite.login_url())


def exchange_request_token(
    *,
    api_key: str,
    api_secret: str,
    request_token: str,
) -> KiteSession:
    clean_request_token = request_token.strip()
    if not clean_request_token:
        raise ValueError("request_token cannot be empty")

    kite = KiteConnect(api_key=api_key)
    session = kite.generate_session(clean_request_token, api_secret=api_secret)
    access_token = str(session.get("access_token") or "").strip()
    if not access_token:
        raise ValueError("Kite session did not include an access token")

    user_id = session.get("user_id")
    return KiteSession(
        access_token=access_token,
        user_id=str(user_id).strip() if user_id else None,
        raw_metadata=dict(session),
    )
