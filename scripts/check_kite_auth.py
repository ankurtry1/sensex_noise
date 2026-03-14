#!/usr/bin/env python3
"""Validate Kite API credentials from .env without printing secrets."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException

import os


def _mask(value: str, keep: int) -> str:
    clean = value.strip()
    if not clean:
        return "<empty>"
    return f"{clean[:keep]}..."


def _required_env(name: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        raise ValueError(f"Missing required environment variable: {name}")
    value = raw.strip()
    if not value:
        raise ValueError(f"Environment variable {name} is empty/whitespace")
    return value


def _load_env() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"
    load_dotenv(dotenv_path=env_path)
    return env_path


def main() -> int:
    try:
        env_path = _load_env()
        api_key = _required_env("KITE_API_KEY")
        _required_env("KITE_API_SECRET")
        access_token = _required_env("KITE_ACCESS_TOKEN")
    except Exception as exc:
        print(f"[FAIL] ENV loaded: {exc}")
        return 1

    print(f"[PASS] ENV loaded from: {env_path}")
    print(f"  KITE_API_KEY={_mask(api_key, keep=4)}")
    print(f"  KITE_ACCESS_TOKEN={_mask(access_token, keep=8)}")

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    try:
        profile = kite.profile()
        user_id = profile.get("user_id", "<unknown>")
        print(f"[PASS] profile() success: user_id={user_id}")
    except TokenException as exc:
        print(f"[FAIL] profile() TokenException: {exc}")
        print("Likely causes: stale access token, api_key/access_token mismatch, or wrong .env file loaded.")
        return 2
    except Exception as exc:
        print(f"[FAIL] profile() failed: {exc}")
        return 3

    try:
        ltp = kite.ltp(["BSE:SENSEX"])
        if "BSE:SENSEX" not in ltp:
            print("[FAIL] ltp() failed: BSE:SENSEX missing in response")
            return 4
        last_price = ltp["BSE:SENSEX"].get("last_price")
        print(f"[PASS] ltp() success: BSE:SENSEX last_price={last_price}")
    except TokenException as exc:
        print(f"[FAIL] ltp() TokenException: {exc}")
        print("Likely causes: stale access token, api_key/access_token mismatch, or wrong .env file loaded.")
        return 5
    except Exception as exc:
        print(f"[FAIL] ltp() failed: {exc}")
        return 6

    print("[PASS] Kite auth checks completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
