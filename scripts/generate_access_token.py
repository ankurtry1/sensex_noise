#!/usr/bin/env python3
"""Generate and store today's Kite access token outside .env."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sensex_noise.auth.kite_auth import build_login_url, exchange_request_token
from sensex_noise.auth.token_store import TokenStore
from sensex_noise.config import load_settings


def main() -> int:
    try:
        settings = load_settings()
    except Exception as exc:
        print(f"Failed to load settings: {exc}")
        return 1

    print("Open this Kite login URL in your browser:")
    print(build_login_url(settings.kite_api_key))
    print("")
    print("After login, copy request_token from the redirect URL and paste below.")

    request_token = input("request_token: ").strip()
    if not request_token:
        print("No request_token provided.")
        return 2

    try:
        session = exchange_request_token(
            api_key=settings.kite_api_key,
            api_secret=settings.kite_api_secret,
            request_token=request_token,
        )
    except Exception as exc:
        print(f"Failed to generate Kite session: {exc}")
        return 3

    record = TokenStore(settings.token_store_path).save(
        access_token=session.access_token,
        api_key=settings.kite_api_key,
        user_id=session.user_id,
    )
    metadata = record.safe_metadata()
    print(
        "Stored today's Kite access token "
        f"for trading_date={metadata['trading_date']} at {settings.token_store_path}"
    )
    if metadata.get("user_id"):
        print(f"Kite user_id={metadata['user_id']}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
