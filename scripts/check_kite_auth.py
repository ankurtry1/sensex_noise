#!/usr/bin/env python3
"""Validate Kite API credentials and today's stored access token."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException

from sensex_noise.auth.token_store import TokenStore
from sensex_noise.config import load_settings


def _mask(value: str, keep: int) -> str:
    clean = value.strip()
    if not clean:
        return "<empty>"
    return f"{clean[:keep]}..."


def main() -> int:
    try:
        settings = load_settings()
    except Exception as exc:
        print(f"[FAIL] Settings loaded: {exc}")
        return 1

    token_record = TokenStore(settings.token_store_path).read_today()
    if token_record is None:
        print(f"[FAIL] No token for today in token store: {settings.token_store_path}")
        return 2

    print("[PASS] Settings loaded")
    print(f"  KITE_API_KEY={_mask(settings.kite_api_key, keep=4)}")
    print(f"  token_store={settings.token_store_path}")
    print(f"  trading_date={token_record.trading_date}")

    kite = KiteConnect(api_key=settings.kite_api_key)
    kite.set_access_token(token_record.access_token)

    try:
        profile = kite.profile()
        user_id = profile.get("user_id", "<unknown>")
        print(f"[PASS] profile() success: user_id={user_id}")
    except TokenException as exc:
        print(f"[FAIL] profile() TokenException: {exc}")
        print("Likely causes: stale token, api_key/access_token mismatch, or wrong token store.")
        return 3
    except Exception as exc:
        print(f"[FAIL] profile() failed: {exc}")
        return 4

    try:
        ltp = kite.ltp(["BSE:SENSEX"])
        if "BSE:SENSEX" not in ltp:
            print("[FAIL] ltp() failed: BSE:SENSEX missing in response")
            return 5
        last_price = ltp["BSE:SENSEX"].get("last_price")
        print(f"[PASS] ltp() success: BSE:SENSEX last_price={last_price}")
    except TokenException as exc:
        print(f"[FAIL] ltp() TokenException: {exc}")
        print("Likely causes: stale token, api_key/access_token mismatch, or wrong token store.")
        return 6
    except Exception as exc:
        print(f"[FAIL] ltp() failed: {exc}")
        return 7

    print("[PASS] Kite auth checks completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
