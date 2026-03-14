#!/usr/bin/env python3
"""Generate a Kite access token from request_token and optionally persist it."""

from __future__ import annotations

import sys
from pathlib import Path

import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect


def _required_env(name: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        raise ValueError(f"Missing required environment variable: {name}")
    value = raw.strip()
    if not value:
        raise ValueError(f"Environment variable {name} is empty/whitespace")
    return value


def _mask(value: str, keep: int = 8) -> str:
    clean = value.strip()
    if not clean:
        return "<empty>"
    return f"{clean[:keep]}..."


def _load_env() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    env_path = repo_root / ".env"
    load_dotenv(dotenv_path=env_path)
    return env_path


def _upsert_env_value(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    replaced = False
    new_lines: list[str] = []
    prefix = f"{key}="
    for line in lines:
        if line.startswith(prefix):
            new_lines.append(f"{key}={value}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        if new_lines and new_lines[-1] != "":
            new_lines.append("")
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        env_path = _load_env()
        api_key = _required_env("KITE_API_KEY")
        api_secret = _required_env("KITE_API_SECRET")
    except Exception as exc:
        print(f"Failed to load credentials from .env: {exc}")
        return 1

    kite = KiteConnect(api_key=api_key)
    print("Open this Kite login URL in your browser:")
    print(kite.login_url())
    print("")
    print("After login, copy request_token from the redirect URL and paste below.")

    request_token = input("request_token: ").strip()
    if not request_token:
        print("No request_token provided.")
        return 2

    try:
        session = kite.generate_session(request_token, api_secret=api_secret)
    except Exception as exc:
        print(f"Failed to generate session: {exc}")
        return 3

    access_token = str(session["access_token"]).strip()
    if not access_token:
        print("Session generated but access_token was empty.")
        return 4

    print(f"New access token generated: {_mask(access_token)}")
    choice = input("Update .env with this KITE_ACCESS_TOKEN? [y/N]: ").strip().lower()
    if choice == "y":
        _upsert_env_value(env_path=env_path, key="KITE_ACCESS_TOKEN", value=access_token)
        print(f"Updated {env_path}")
    else:
        print("Skipped .env update. Copy token manually if needed.")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
