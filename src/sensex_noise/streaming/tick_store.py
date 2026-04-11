from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock
from typing import Any


class TickStore:
    """In-memory latest tick cache + per-token ring buffers."""

    def __init__(self, max_buffer_ticks: int = 2048) -> None:
        self.max_buffer_ticks = int(max_buffer_ticks)
        self._latest_by_token: dict[int, dict[str, Any]] = {}
        self._buffer_by_token: dict[int, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self.max_buffer_ticks)
        )
        self._token_by_symbol: dict[str, int] = {}
        self._symbol_by_token: dict[int, str] = {}
        self._lock = Lock()

    def register_symbol_token(self, symbol: str, token: int) -> None:
        with self._lock:
            self._token_by_symbol[symbol] = int(token)
            self._symbol_by_token[int(token)] = symbol

    def put(self, tick: dict[str, Any]) -> None:
        token = int(tick["instrument_token"])
        symbol = str(tick["symbol"])
        with self._lock:
            self._latest_by_token[token] = tick
            self._buffer_by_token[token].append(tick)
            self._token_by_symbol[symbol] = token
            self._symbol_by_token[token] = symbol

    def latest_by_token(self, token: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._latest_by_token.get(int(token))
            return None if row is None else dict(row)

    def latest_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        with self._lock:
            token = self._token_by_symbol.get(symbol)
            if token is None:
                return None
            row = self._latest_by_token.get(token)
            return None if row is None else dict(row)

    def token_for_symbol(self, symbol: str) -> int | None:
        with self._lock:
            token = self._token_by_symbol.get(symbol)
            return None if token is None else int(token)

    def slice_token_last_seconds(
        self,
        token: int,
        seconds: int,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        horizon_seconds = max(0, int(seconds))
        with self._lock:
            rows = list(self._buffer_by_token.get(int(token), deque()))

        if not rows:
            return []

        if now is None:
            ts = rows[-1].get("timestamp_exchange")
            now = ts if isinstance(ts, datetime) else datetime.now()

        floor = now - timedelta(seconds=horizon_seconds)
        out: list[dict[str, Any]] = []
        for row in rows:
            ts = row.get("timestamp_exchange")
            if not isinstance(ts, datetime):
                continue
            if ts >= floor:
                out.append(dict(row))
        return out

    def slice_symbols_last_seconds(
        self,
        symbols: list[str],
        seconds: int,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for symbol in symbols:
            token = self.token_for_symbol(symbol)
            if token is None:
                continue
            out.extend(self.slice_token_last_seconds(token=token, seconds=seconds, now=now))
        out.sort(key=lambda row: row.get("timestamp_exchange") or datetime.min)
        return out
