from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class EntryWindowRecord:
    timestamp: datetime
    ltp: float
    bid: float | None = None
    ask: float | None = None
    spread: float | None = None
    bid_qty: float | None = None
    ask_qty: float | None = None


def _extract_timestamp(value: dict[str, Any]) -> datetime | None:
    for key in ("timestamp_exchange", "timestamp", "last_trade_time"):
        raw = value.get(key)
        if isinstance(raw, datetime):
            return raw
    return None


def _extract_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_depth_qty(record: dict[str, Any], side: str) -> float | None:
    direct = _extract_float(record.get(f"{side}_qty"))
    if direct is not None:
        return direct

    for key in (f"{side}[5]", f"{side}5"):
        rows = record.get(key)
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            qty = _extract_float(rows[0].get("quantity"))
            if qty is not None:
                return qty

    depth = record.get("depth")
    if isinstance(depth, dict):
        side_key = "buy" if side == "bid" else "sell"
        rows = depth.get(side_key)
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            qty = _extract_float(rows[0].get("quantity"))
            if qty is not None:
                return qty

    return None


def _normalize_record(value: dict[str, Any]) -> EntryWindowRecord | None:
    timestamp = _extract_timestamp(value)
    ltp = _extract_float(value.get("ltp"))
    if timestamp is None or ltp is None:
        return None

    bid = _extract_float(value.get("best_bid"))
    if bid is None:
        bid = _extract_float(value.get("bid"))
    ask = _extract_float(value.get("best_ask"))
    if ask is None:
        ask = _extract_float(value.get("ask"))

    spread = _extract_float(value.get("spread"))
    if spread is None and bid is not None and ask is not None:
        spread = ask - bid

    return EntryWindowRecord(
        timestamp=timestamp,
        ltp=ltp,
        bid=bid,
        ask=ask,
        spread=spread,
        bid_qty=_extract_depth_qty(value, "bid"),
        ask_qty=_extract_depth_qty(value, "ask"),
    )


class EntryWindowBuffer:
    def __init__(self, max_seconds: float = 10.0) -> None:
        self.max_seconds = max(0.1, float(max_seconds))
        self._underlying: deque[EntryWindowRecord] = deque()
        self._options: dict[str, deque[EntryWindowRecord]] = defaultdict(deque)

    def add_underlying_tick(self, quote_or_tick: dict[str, Any]) -> None:
        record = _normalize_record(quote_or_tick)
        if record is None:
            return
        self._underlying.append(record)
        self._prune_deque(self._underlying, now=record.timestamp)

    def add_option_tick(self, symbol: str, quote_or_tick: dict[str, Any]) -> None:
        record = _normalize_record(quote_or_tick)
        if record is None:
            return
        bucket = self._options[str(symbol)]
        bucket.append(record)
        self._prune_deque(bucket, now=record.timestamp)

    def get_underlying_window(self, seconds: float) -> list[EntryWindowRecord]:
        return self._slice_window(self._underlying, seconds=seconds)

    def get_option_window(self, symbol: str, seconds: float) -> list[EntryWindowRecord]:
        return self._slice_window(self._options.get(str(symbol), deque()), seconds=seconds)

    def prune(self) -> None:
        now = datetime.now()
        self._prune_deque(self._underlying, now=now)
        empty_symbols: list[str] = []
        for symbol, bucket in self._options.items():
            self._prune_deque(bucket, now=now)
            if not bucket:
                empty_symbols.append(symbol)
        for symbol in empty_symbols:
            self._options.pop(symbol, None)

    def _slice_window(
        self,
        bucket: deque[EntryWindowRecord],
        *,
        seconds: float,
    ) -> list[EntryWindowRecord]:
        if not bucket:
            return []
        lookback = max(0.0, float(seconds))
        end_time = bucket[-1].timestamp
        floor = end_time - timedelta(seconds=lookback)
        return [record for record in bucket if record.timestamp >= floor]

    def _prune_deque(self, bucket: deque[EntryWindowRecord], *, now: datetime) -> None:
        floor = now - timedelta(seconds=self.max_seconds)
        while bucket and bucket[0].timestamp < floor:
            bucket.popleft()
