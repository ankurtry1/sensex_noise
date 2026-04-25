from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import iter_jsonl, parse_timestamp


@dataclass
class TradePathContext:
    trade_id: str
    date: str
    entry_time: datetime
    exit_time: datetime
    symbol: str | None
    option_ticks: pd.DataFrame
    index_ticks: pd.DataFrame
    futures_ticks: pd.DataFrame
    has_trade_ticks: bool
    has_underlying_ticks: bool
    has_futures_ticks: bool
    has_depth: bool
    has_subsecond_time: bool
    fill_method: str


class TradePathLoader:
    def __init__(self, logs_dir: Path, warnings: list[str] | None = None) -> None:
        self.logs_dir = logs_dir
        self.warnings = warnings if warnings is not None else []
        self._day_tick_cache: dict[tuple[str, str], pd.DataFrame] = {}

    def _load_jsonl_ticks(self, path: Path) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        if not path.exists():
            return pd.DataFrame()
        for obj in iter_jsonl(path, warnings=self.warnings):
            ts = parse_timestamp(obj.get("timestamp_exchange") or obj.get("timestamp"))
            if ts is None:
                continue
            row = {
                "timestamp_exchange": ts,
                "timestamp_receive": parse_timestamp(obj.get("timestamp_receive")),
                "symbol": obj.get("symbol"),
                "instrument_token": obj.get("instrument_token"),
                "ltp": obj.get("ltp"),
                "best_bid": obj.get("best_bid"),
                "best_ask": obj.get("best_ask"),
                "spread": obj.get("spread"),
                "bid5": obj.get("bid[5]", []),
                "ask5": obj.get("ask[5]", []),
                "source": obj.get("source"),
                "phase": obj.get("phase"),
                "trade_id": obj.get("trade_id"),
            }
            rows.append(row)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows).sort_values("timestamp_exchange").reset_index(drop=True)
        for col in ("ltp", "best_bid", "best_ask", "spread"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _day_ticks(self, date: str, source: str) -> pd.DataFrame:
        key = (date, source)
        if key in self._day_tick_cache:
            return self._day_tick_cache[key]

        path = self.logs_dir / "ticks" / date / f"{source}.jsonl"
        df = self._load_jsonl_ticks(path)
        self._day_tick_cache[key] = df
        return df

    def _slice_window(self, df: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
        if df.empty:
            return df
        out = df[(df["timestamp_exchange"] >= start) & (df["timestamp_exchange"] <= end)].copy()
        return out.reset_index(drop=True)

    def load_trade_context(self, row: dict[str, Any]) -> TradePathContext | None:
        trade_id = str(row.get("trade_id"))
        date = str(row.get("date"))
        symbol = row.get("symbol")
        entry_time = parse_timestamp(row.get("entry_time"))
        exit_time = parse_timestamp(row.get("exit_time"))
        if entry_time is None or exit_time is None:
            return None

        window_start = entry_time - timedelta(seconds=5)
        window_end = exit_time + timedelta(seconds=15)

        has_subsecond = False
        has_depth = False
        fill_method = "trade_scoped"

        option_ticks = pd.DataFrame()
        index_ticks = pd.DataFrame()
        futures_ticks = pd.DataFrame()

        # Primary: trade-scoped tape path if present.
        tick_path_raw = row.get("trade_tick_path")
        tick_path = Path(tick_path_raw) if isinstance(tick_path_raw, str) and tick_path_raw else None
        if tick_path and tick_path.exists():
            tape = self._load_jsonl_ticks(tick_path)
            if not tape.empty:
                tape = self._slice_window(tape, window_start, window_end)
                option_ticks = tape[tape["source"].astype(str).str.lower() == "option"].copy()
                index_ticks = tape[tape["source"].astype(str).str.lower() == "index"].copy()
                futures_ticks = tape[tape["source"].astype(str).str.lower() == "future"].copy()
                has_depth = bool(
                    (option_ticks["best_bid"].notna().any() if "best_bid" in option_ticks else False)
                    or (option_ticks["bid5"].astype(str) != "[]").any()
                )
                has_subsecond = any(ts.microsecond > 0 for ts in tape["timestamp_exchange"]) if not tape.empty else False

        # Fallback path for options if trade tape missing.
        if option_ticks.empty:
            full_opts = self._day_ticks(date, "options")
            if not full_opts.empty and symbol:
                fill_method = "full_day_options_fallback"
                opt = full_opts[full_opts["symbol"] == symbol].copy()
                option_ticks = self._slice_window(opt, window_start, window_end)
                has_depth = has_depth or bool(option_ticks["best_bid"].notna().any()) if not option_ticks.empty else has_depth
                has_subsecond = has_subsecond or any(ts.microsecond > 0 for ts in option_ticks["timestamp_exchange"]) if not option_ticks.empty else has_subsecond

        # Underlying always from daily files when available.
        if index_ticks.empty:
            index_ticks = self._slice_window(self._day_ticks(date, "sensex"), window_start, window_end)
        if futures_ticks.empty:
            futures_ticks = self._slice_window(self._day_ticks(date, "futures"), window_start, window_end)

        has_trade_ticks = not option_ticks.empty
        has_underlying = not index_ticks.empty
        has_futures = not futures_ticks.empty

        return TradePathContext(
            trade_id=trade_id,
            date=date,
            entry_time=entry_time,
            exit_time=exit_time,
            symbol=symbol,
            option_ticks=option_ticks,
            index_ticks=index_ticks,
            futures_ticks=futures_ticks,
            has_trade_ticks=has_trade_ticks,
            has_underlying_ticks=has_underlying,
            has_futures_ticks=has_futures,
            has_depth=has_depth,
            has_subsecond_time=has_subsecond,
            fill_method=fill_method,
        )
