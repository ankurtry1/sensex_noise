#!/usr/bin/env python3
"""Run the market-day worker with today's Kite access token from token store."""

from __future__ import annotations

import fcntl
import os
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Iterator, TextIO

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sensex_noise.auth.token_store import TokenStore
from sensex_noise.config import load_settings
from sensex_noise.services.engine import StrategyEngine


class MarketWorkerAlreadyRunning(RuntimeError):
    pass


@contextmanager
def _worker_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as fp:
        try:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise MarketWorkerAlreadyRunning(f"Another market worker is already running: {lock_path}") from exc
        _write_lock_metadata(fp)
        try:
            yield
        finally:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


def _write_lock_metadata(fp: TextIO) -> None:
    fp.seek(0)
    fp.truncate()
    fp.write(f"pid={os.getpid()}\n")
    fp.flush()


def main() -> int:
    settings = load_settings()
    token_record = TokenStore(settings.token_store_path).read_today()
    if token_record is None:
        print(
            "Missing today's Kite access token. Complete daily Kite authentication "
            f"and store the token at {settings.token_store_path}."
        )
        return 2

    effective_settings = replace(settings, kite_access_token=token_record.access_token)
    lock_path = effective_settings.runtime_dir / "market_worker.lock"

    try:
        with _worker_lock(lock_path):
            StrategyEngine(settings=effective_settings).run()
    except MarketWorkerAlreadyRunning as exc:
        print(str(exc))
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
