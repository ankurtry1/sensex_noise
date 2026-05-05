#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PRIMARY_DATES = [
    "2026-04-27",
    "2026-04-28",
    "2026-05-05",
]
SECONDARY_FILTERED_DATES = {
    "2026-04-29": "2026-04-30",
    "2026-04-30": "2026-04-30",
}
EXCLUDED_DATES = {
    "1970-01-01",
    "2026-04-23",
    "2026-04-24",
    "2026-05-04",
}
OPTION_TS_KEYS = ("timestamp_exchange", "exchange_timestamp", "timestamp", "ts")
PRICE_KEYS = ("last_price", "ltp", "price")
SYMBOL_KEYS = ("symbol", "tradingsymbol", "instrument")
TIME_BUCKETS = [
    (time(9, 15), time(10, 0), "09:15-10:00"),
    (time(10, 0), time(11, 0), "10:00-11:00"),
    (time(11, 0), time(12, 0), "11:00-12:00"),
    (time(12, 0), time(13, 0), "12:00-13:00"),
    (time(13, 0), time(14, 0), "13:00-14:00"),
    (time(14, 0), time(15, 0), "14:00-15:00"),
    (time(15, 0), time(15, 30), "15:00-15:30"),
]
OPTION_SYMBOL_RE = re.compile(r"(?P<strike>\d+)(?P<option_type>CE|PE)$")


@dataclass(frozen=True)
class Variant:
    name: str
    require_sync: bool
    require_vacuum: bool


VARIANTS = [
    Variant(name="A_impulse_only", require_sync=False, require_vacuum=False),
    Variant(name="B_impulse_plus_option_sync", require_sync=True, require_vacuum=False),
    Variant(name="C_impulse_plus_sync_plus_liquidity_vacuum", require_sync=True, require_vacuum=True),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay ATM impulse-synchronization edge on option tape.")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--impulse-points", type=float, default=25.0)
    parser.add_argument("--impulse-window-seconds", type=float, default=3.0)
    parser.add_argument("--sync-window-ms", type=int, default=500)
    parser.add_argument("--target-points", type=float, default=3.0)
    parser.add_argument("--stop-points", type=float, default=3.0)
    parser.add_argument("--max-hold-seconds", type=float, default=10.0)
    parser.add_argument("--cooldown-seconds", type=float, default=15.0)
    parser.add_argument("--qty", type=int, default=500)
    parser.add_argument("--charges-per-trade", type=float, default=0.0)
    return parser.parse_args()


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _detect_timestamp(row: dict[str, Any]) -> str | None:
    for key in OPTION_TS_KEYS:
        raw = row.get(key)
        if isinstance(raw, str) and raw:
            try:
                datetime.fromisoformat(raw)
            except ValueError:
                continue
            return raw
    return None


def _detect_price(row: dict[str, Any]) -> float | None:
    for key in PRICE_KEYS:
        raw = row.get(key)
        value = _safe_float(raw)
        if value is not None:
            return value
    return None


def _detect_symbol(row: dict[str, Any]) -> str | None:
    for key in SYMBOL_KEYS:
        raw = row.get(key)
        if isinstance(raw, str) and raw:
            return raw
    return None


def _parse_symbol(symbol: str) -> tuple[int | None, str | None]:
    plain = symbol.split(":", 1)[-1]
    match = OPTION_SYMBOL_RE.search(plain)
    if not match:
        return None, None
    return _safe_int(match.group("strike")), match.group("option_type")


def _top_depth_from_row(row: dict[str, Any]) -> float | None:
    bid = row.get("bid[5]")
    ask = row.get("ask[5]")
    if not isinstance(bid, list) or not isinstance(ask, list) or not bid or not ask:
        return None
    bid_qty = _safe_float((bid[0] or {}).get("quantity")) if isinstance(bid[0], dict) else None
    ask_qty = _safe_float((ask[0] or {}).get("quantity")) if isinstance(ask[0], dict) else None
    if bid_qty is None or ask_qty is None:
        return None
    return float(bid_qty + ask_qty)


def _time_bucket(ts: datetime) -> str:
    value = ts.time()
    for start, end, label in TIME_BUCKETS:
        if start <= value < end or (label == "15:00-15:30" and value <= end):
            return label
    return "outside_session"


def _compute_drawdown(net_pnls: list[float]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in net_pnls:
        cumulative += pnl
        peak = max(peak, cumulative)
        max_dd = min(max_dd, cumulative - peak)
    return float(max_dd)


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def discover_dates(repo_root: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    tape_root = repo_root / "data" / "tape" / "sensex_options"
    tick_root = repo_root / "logs" / "ticks"
    discovered = sorted({p.name for p in tape_root.iterdir() if p.is_dir()} | {p.name for p in tick_root.iterdir() if p.is_dir()})
    records: list[dict[str, Any]] = []
    usable_configs: list[dict[str, Any]] = []
    for date_str in discovered:
        option_path = tape_root / date_str / "options.jsonl"
        manifest_path = tape_root / date_str / "manifest.json"
        sensex_path = tick_root / date_str / "sensex.jsonl"
        has_option_tape = option_path.exists()
        has_manifest = manifest_path.exists()
        has_sensex_ticks = sensex_path.exists()
        option_rows = 0
        option_symbols: set[str] = set()
        option_start_time: str | None = None
        option_end_time: str | None = None
        if has_option_tape:
            option_rows = 0
            min_ts: datetime | None = None
            max_ts: datetime | None = None
            with option_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    option_rows += 1
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    symbol = _detect_symbol(row)
                    if symbol:
                        option_symbols.add(symbol)
                    ts_raw = _detect_timestamp(row)
                    if ts_raw:
                        ts = datetime.fromisoformat(ts_raw)
                        if min_ts is None or ts < min_ts:
                            min_ts = ts
                        if max_ts is None or ts > max_ts:
                            max_ts = ts
            option_start_time = min_ts.isoformat() if min_ts else None
            option_end_time = max_ts.isoformat() if max_ts else None
        sensex_rows = _line_count(sensex_path) if has_sensex_ticks else 0
        usable = False
        expiry_filter = None
        sample_type = None
        if date_str in PRIMARY_DATES:
            usable = has_option_tape and has_manifest and has_sensex_ticks
            sample_type = "primary"
        elif date_str in SECONDARY_FILTERED_DATES:
            usable = has_option_tape and has_manifest and has_sensex_ticks
            expiry_filter = SECONDARY_FILTERED_DATES[date_str]
            sample_type = "secondary_expiry_filtered"
        elif date_str in EXCLUDED_DATES:
            usable = False
            sample_type = "excluded"
        record = {
            "date": date_str,
            "has_sensex_ticks": has_sensex_ticks,
            "has_option_tape": has_option_tape,
            "has_manifest": has_manifest,
            "sensex_rows": sensex_rows,
            "option_rows": option_rows,
            "option_symbols": len(option_symbols),
            "option_start_time": option_start_time,
            "option_end_time": option_end_time,
            "usable": usable,
        }
        records.append(record)
        if usable:
            usable_configs.append({
                "date": date_str,
                "expiry_filter": expiry_filter,
                "sample_type": sample_type,
                "option_path": option_path,
                "sensex_path": sensex_path,
            })
    coverage = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    return coverage, usable_configs


def load_sensex_ticks(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_raw = _detect_timestamp(row)
            price = _detect_price(row)
            if ts_raw is None or price is None:
                continue
            rows.append({"ts": datetime.fromisoformat(ts_raw), "ltp": float(price)})
    df = pd.DataFrame(rows).drop_duplicates(subset=["ts", "ltp"]).sort_values("ts").reset_index(drop=True)
    if df.empty:
        return df
    times_ns = df["ts"].astype("int64").to_numpy()
    ltp = df["ltp"].to_numpy(dtype=float)
    df["ts_ns"] = times_ns
    for seconds in (1, 2, 3, 5, 60):
        prev_idx = np.searchsorted(times_ns, times_ns - int(seconds * 1_000_000_000), side="right") - 1
        move = np.full(len(df), np.nan)
        valid = prev_idx >= 0
        move[valid] = ltp[valid] - ltp[prev_idx[valid]]
        df[f"move_{seconds}s"] = move
    return df


@dataclass
class SymbolData:
    symbol: str
    strike: int
    expiry: str
    option_type: str
    times_ns: np.ndarray
    times: np.ndarray
    ltp: np.ndarray
    spread: np.ndarray
    top_depth: np.ndarray
    best_bid: np.ndarray
    best_ask: np.ndarray


def load_option_tape(path: Path, expiry_filter: str | None = None) -> tuple[dict[str, SymbolData], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    symbol_rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_raw = _detect_timestamp(row)
            symbol = _detect_symbol(row)
            ltp = _detect_price(row)
            if ts_raw is None or symbol is None or ltp is None:
                continue
            expiry = row.get("expiry")
            if expiry_filter is not None and expiry != expiry_filter:
                continue
            strike = _safe_int(row.get("strike"))
            option_type = row.get("option_type")
            if strike is None or not isinstance(option_type, str) or option_type.upper() not in {"CE", "PE"}:
                parsed_strike, parsed_type = _parse_symbol(symbol)
                strike = strike if strike is not None else parsed_strike
                option_type = option_type if isinstance(option_type, str) and option_type else parsed_type
            if strike is None or option_type is None:
                continue
            best_bid = _safe_float(row.get("best_bid"))
            best_ask = _safe_float(row.get("best_ask"))
            spread = _safe_float(row.get("spread"))
            if spread is None and best_bid is not None and best_ask is not None:
                spread = best_ask - best_bid
            top_depth = _top_depth_from_row(row)
            bucket = symbol_rows.setdefault(symbol, {
                "strike": int(strike),
                "expiry": str(expiry) if expiry is not None else "",
                "option_type": str(option_type).upper(),
                "ts": [],
                "ts_ns": [],
                "ltp": [],
                "spread": [],
                "top_depth": [],
                "best_bid": [],
                "best_ask": [],
            })
            dt = datetime.fromisoformat(ts_raw)
            bucket["ts"].append(dt)
            bucket["ts_ns"].append(int(dt.timestamp() * 1_000_000_000))
            bucket["ltp"].append(float(ltp))
            bucket["spread"].append(float(spread) if spread is not None else np.nan)
            bucket["top_depth"].append(float(top_depth) if top_depth is not None else np.nan)
            bucket["best_bid"].append(float(best_bid) if best_bid is not None else np.nan)
            bucket["best_ask"].append(float(best_ask) if best_ask is not None else np.nan)
    symbol_map: dict[str, SymbolData] = {}
    meta_rows: list[dict[str, Any]] = []
    meta_by_type: dict[str, list[dict[str, Any]]] = {"CE": [], "PE": []}
    for symbol, bucket in symbol_rows.items():
        order = np.argsort(np.asarray(bucket["ts_ns"], dtype=np.int64), kind="stable")
        times_ns = np.asarray(bucket["ts_ns"], dtype=np.int64)[order]
        times = np.asarray(bucket["ts"], dtype="datetime64[ns]")[order]
        ltp = np.asarray(bucket["ltp"], dtype=float)[order]
        spread = np.asarray(bucket["spread"], dtype=float)[order]
        top_depth = np.asarray(bucket["top_depth"], dtype=float)[order]
        best_bid = np.asarray(bucket["best_bid"], dtype=float)[order]
        best_ask = np.asarray(bucket["best_ask"], dtype=float)[order]
        data = SymbolData(
            symbol=symbol,
            strike=int(bucket["strike"]),
            expiry=str(bucket["expiry"]),
            option_type=str(bucket["option_type"]),
            times_ns=times_ns,
            times=times,
            ltp=ltp,
            spread=spread,
            top_depth=top_depth,
            best_bid=best_bid,
            best_ask=best_ask,
        )
        symbol_map[symbol] = data
        meta_row = {
            "symbol": symbol,
            "strike": int(bucket["strike"]),
            "expiry": str(bucket["expiry"]),
            "option_type": str(bucket["option_type"]),
        }
        meta_rows.append(meta_row)
        meta_by_type[str(bucket["option_type"])].append(meta_row)
    meta_rows.sort(key=lambda r: (r["expiry"], r["strike"], r["symbol"]))
    for option_type in meta_by_type:
        meta_by_type[option_type].sort(key=lambda r: (r["strike"], r["expiry"], r["symbol"]))
    return symbol_map, meta_rows, meta_by_type


def _latest_idx_at_or_before(times_ns: np.ndarray, target_ns: int) -> int | None:
    idx = int(np.searchsorted(times_ns, target_ns, side="right") - 1)
    return idx if idx >= 0 else None


def _next_idx_at_or_after(times_ns: np.ndarray, target_ns: int) -> int | None:
    idx = int(np.searchsorted(times_ns, target_ns, side="left"))
    return idx if idx < len(times_ns) else None


def _nearest_idx_within(times_ns: np.ndarray, target_ns: int, window_ns: int) -> int | None:
    idx = int(np.searchsorted(times_ns, target_ns, side="left"))
    candidates = []
    for j in (idx - 1, idx):
        if 0 <= j < len(times_ns):
            diff = abs(int(times_ns[j] - target_ns))
            if diff <= window_ns:
                candidates.append((diff, j))
    if not candidates:
        return None
    candidates.sort()
    return int(candidates[0][1])


def _value_change(symbol_data: SymbolData, end_ns: int, seconds_back: float) -> float | None:
    end_idx = _latest_idx_at_or_before(symbol_data.times_ns, end_ns)
    prev_idx = _latest_idx_at_or_before(symbol_data.times_ns, end_ns - int(seconds_back * 1_000_000_000))
    if end_idx is None or prev_idx is None:
        return None
    return float(symbol_data.ltp[end_idx] - symbol_data.ltp[prev_idx])


def _median_window(values: np.ndarray, times_ns: np.ndarray, end_ns: int, lookback_seconds: float) -> float | None:
    start_ns = end_ns - int(lookback_seconds * 1_000_000_000)
    left = int(np.searchsorted(times_ns, start_ns, side="left"))
    right = int(np.searchsorted(times_ns, end_ns, side="right"))
    if right <= left:
        return None
    window = values[left:right]
    window = window[np.isfinite(window)]
    if window.size == 0:
        return None
    return float(np.nanmedian(window))


def choose_atm_symbol(meta_by_type: dict[str, list[dict[str, Any]]], option_type: str, spot: float) -> dict[str, Any] | None:
    candidates = meta_by_type.get(option_type, [])
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda row: (abs(float(row["strike"]) - float(spot)), str(row["expiry"]), float(row["strike"]), str(row["symbol"])),
    )


def classify_regime(sensex_df: pd.DataFrame, entry_idx: int, entry_time: datetime, vacuum_passed: bool) -> str:
    if vacuum_passed:
        return "liquidity_vacuum_impulse"
    current_ns = int(sensex_df.iloc[entry_idx]["ts_ns"])
    left = int(np.searchsorted(sensex_df["ts_ns"].to_numpy(dtype=np.int64), current_ns - 60_000_000_000, side="left"))
    window = sensex_df.iloc[left : entry_idx + 1]
    if window.empty:
        return "calm_impulse"
    prices = window["ltp"].to_numpy(dtype=float)
    net_move_60s = abs(float(prices[-1] - prices[0]))
    diffs = np.diff(prices)
    path_movement_60s = float(np.abs(diffs).sum())
    efficiency = net_move_60s / path_movement_60s if path_movement_60s > 0 else 0.0
    if efficiency >= 0.55:
        return "clean_trend_impulse"
    if efficiency <= 0.30:
        return "choppy_fake_impulse"
    if entry_time.time() >= time(14, 30):
        return "late_session_impulse"
    return "calm_impulse"


def replay_trade(
    symbol_data: SymbolData,
    entry_idx: int,
    entry_time: datetime,
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    entry_ns = int(symbol_data.times_ns[entry_idx])
    entry_price = float(symbol_data.ltp[entry_idx])
    target_price = entry_price + float(args.target_points)
    stop_price = entry_price - float(args.stop_points)
    deadline_ns = entry_ns + int(args.max_hold_seconds * 1_000_000_000)
    one_sec_ns = entry_ns + 1_000_000_000
    three_sec_ns = entry_ns + 3_000_000_000
    end_idx = _next_idx_at_or_after(symbol_data.times_ns, deadline_ns)
    if end_idx is None:
        end_idx = len(symbol_data.times_ns) - 1
    mfe = 0.0
    mae = 0.0
    one_done = False
    three_done = False
    exit_idx = end_idx
    exit_reason = "MAX_HOLD"
    for idx in range(entry_idx + 1, len(symbol_data.times_ns)):
        ts_ns = int(symbol_data.times_ns[idx])
        ltp = float(symbol_data.ltp[idx])
        points = ltp - entry_price
        mfe = max(mfe, points)
        mae = min(mae, points)
        if ltp >= target_price:
            exit_idx = idx
            exit_reason = "TARGET_HIT"
            break
        if ltp <= stop_price:
            exit_idx = idx
            exit_reason = "STOP_HIT"
            break
        if not one_done and ts_ns >= one_sec_ns:
            one_done = True
            if points <= 0 and mfe < 1.0:
                exit_idx = idx
                exit_reason = "KILL_1S"
                break
        if not three_done and ts_ns >= three_sec_ns:
            three_done = True
            if points < 1.0 and mfe < 2.0:
                exit_idx = idx
                exit_reason = "KILL_3S"
                break
        if ts_ns >= deadline_ns:
            exit_idx = idx
            exit_reason = "MAX_HOLD"
            break
    if exit_idx < entry_idx:
        return None
    exit_price = float(symbol_data.ltp[exit_idx])
    exit_time = pd.Timestamp(symbol_data.times[exit_idx]).to_pydatetime()
    points = exit_price - entry_price
    gross_pnl = points * int(args.qty)
    net_pnl = gross_pnl - float(args.charges_per_trade)
    return {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "points": points,
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "exit_reason": exit_reason,
        "hold_seconds": max(0.0, (exit_time - entry_time).total_seconds()),
        "mfe": mfe,
        "mae": mae,
        "exit_time": exit_time,
    }


def simulate_day(
    date_str: str,
    sensex_df: pd.DataFrame,
    symbol_map: dict[str, SymbolData],
    meta_rows: list[dict[str, Any]],
    meta_by_type: dict[str, list[dict[str, Any]]],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    if sensex_df.empty or not meta_rows:
        return trades
    sensex_df = sensex_df.copy()
    session_mask = (
        (sensex_df["ts"].dt.time >= time(9, 15))
        & (sensex_df["ts"].dt.time <= time(15, 30))
    )
    session_df = sensex_df.loc[session_mask].reset_index(drop=True)
    if session_df.empty:
        return trades
    session_times = session_df["ts_ns"].to_numpy(dtype=np.int64)
    session_ltps = session_df["ltp"].to_numpy(dtype=float)
    move_3s = session_df[f"move_{int(args.impulse_window_seconds)}s"].to_numpy(dtype=float)
    for variant in VARIANTS:
        next_allowed_ns = -1
        i = 0
        while i < len(session_df):
            row = session_df.iloc[i]
            t0 = row["ts"]
            t0_ns = int(row["ts_ns"])
            if t0_ns < next_allowed_ns:
                i += 1
                continue
            move = move_3s[i]
            if np.isnan(move):
                i += 1
                continue
            direction = None
            option_type = None
            if move >= float(args.impulse_points):
                direction = "CE"
                option_type = "CE"
            elif move <= -float(args.impulse_points):
                direction = "PE"
                option_type = "PE"
            if direction is None:
                i += 1
                continue
            selection = choose_atm_symbol(meta_by_type, option_type=option_type, spot=float(row["ltp"]))
            if selection is None:
                i += 1
                continue
            symbol = str(selection["symbol"])
            symbol_data = symbol_map.get(symbol)
            if symbol_data is None:
                i += 1
                continue
            nearest_idx = _nearest_idx_within(symbol_data.times_ns, t0_ns, int(args.sync_window_ms) * 1_000_000)
            if nearest_idx is None:
                i += 1
                continue
            entry_idx = _next_idx_at_or_after(symbol_data.times_ns, t0_ns)
            if entry_idx is None:
                i += 1
                continue
            option_move_1s = _value_change(symbol_data, t0_ns, 1.0)
            option_move_3s = _value_change(symbol_data, t0_ns, 3.0)
            sync_passed = bool(option_move_1s is not None and option_move_1s > 0)
            spread_now = float(symbol_data.spread[nearest_idx]) if np.isfinite(symbol_data.spread[nearest_idx]) else np.nan
            top_depth_now = float(symbol_data.top_depth[nearest_idx]) if np.isfinite(symbol_data.top_depth[nearest_idx]) else np.nan
            median_spread_10s = _median_window(symbol_data.spread, symbol_data.times_ns, t0_ns, 10.0)
            median_top_depth_10s = _median_window(symbol_data.top_depth, symbol_data.times_ns, t0_ns, 10.0)
            vacuum_available = all(
                value is not None and np.isfinite(value)
                for value in (spread_now, top_depth_now, median_spread_10s, median_top_depth_10s)
            )
            vacuum_passed = False
            if vacuum_available:
                vacuum_passed = bool(
                    spread_now >= 1.5 * float(median_spread_10s)
                    or top_depth_now <= 0.5 * float(median_top_depth_10s)
                )
            if variant.require_sync and not sync_passed:
                i += 1
                continue
            if variant.require_vacuum and not (vacuum_available and vacuum_passed):
                i += 1
                continue
            replay = replay_trade(symbol_data, entry_idx, pd.Timestamp(symbol_data.times[entry_idx]).to_pydatetime(), args)
            if replay is None:
                i += 1
                continue
            entry_time = pd.Timestamp(symbol_data.times[entry_idx]).to_pydatetime()
            sensex_entry_idx = int(np.searchsorted(session_times, int(entry_time.timestamp() * 1_000_000_000), side="right") - 1)
            if sensex_entry_idx < 0:
                sensex_entry_idx = i
            regime = classify_regime(session_df, sensex_entry_idx, entry_time, vacuum_passed)
            trade = {
                "date": date_str,
                "variant": variant.name,
                "entry_time": entry_time.isoformat(),
                "exit_time": replay["exit_time"].isoformat(),
                "direction": direction,
                "symbol": symbol,
                "strike": int(selection["strike"]),
                "expiry": str(selection["expiry"]),
                "sensex_at_entry": float(session_ltps[sensex_entry_idx]),
                "sensex_move_3s": float(move),
                "entry_price": replay["entry_price"],
                "exit_price": replay["exit_price"],
                "points": replay["points"],
                "gross_pnl": replay["gross_pnl"],
                "net_pnl": replay["net_pnl"],
                "exit_reason": replay["exit_reason"],
                "hold_seconds": replay["hold_seconds"],
                "mfe": replay["mfe"],
                "mae": replay["mae"],
                "option_move_1s": option_move_1s,
                "option_move_3s": option_move_3s,
                "sync_passed": sync_passed,
                "vacuum_available": vacuum_available,
                "vacuum_passed": vacuum_passed,
                "spread_now": spread_now,
                "median_spread_10s": median_spread_10s,
                "top_depth_now": top_depth_now,
                "median_top_depth_10s": median_top_depth_10s,
                "time_bucket": _time_bucket(entry_time),
                "regime": regime,
            }
            trades.append(trade)
            next_allowed_ns = max(
                int(entry_time.timestamp() * 1_000_000_000) + int(args.cooldown_seconds * 1_000_000_000),
                int(replay["exit_time"].timestamp() * 1_000_000_000),
            )
            i = int(np.searchsorted(session_times, next_allowed_ns, side="left"))
        
    return trades


def summarize_day(trades_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (date_str, variant), group in trades_df.groupby(["date", "variant"]):
        wins = group[group["net_pnl"] > 0]
        losses = group[group["net_pnl"] < 0]
        rows.append({
            "date": date_str,
            "variant": variant,
            "trades": int(len(group)),
            "gross_pnl": float(group["gross_pnl"].sum()),
            "net_pnl": float(group["net_pnl"].sum()),
            "win_rate": float((group["net_pnl"] > 0).mean()) if len(group) else 0.0,
            "avg_win": float(wins["net_pnl"].mean()) if not wins.empty else 0.0,
            "avg_loss": float(losses["net_pnl"].mean()) if not losses.empty else 0.0,
            "profit_factor": float(wins["net_pnl"].sum() / abs(losses["net_pnl"].sum())) if not losses.empty and losses["net_pnl"].sum() != 0 else (float("inf") if not wins.empty else 0.0),
            "max_intraday_drawdown": _compute_drawdown(group.sort_values("exit_time")["net_pnl"].tolist()),
        })
    return pd.DataFrame(rows).sort_values(["date", "variant"]).reset_index(drop=True)


def summarize_time_bucket(trades_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (date_str, variant, bucket), group in trades_df.groupby(["date", "variant", "time_bucket"]):
        wins = group[group["net_pnl"] > 0]
        losses = group[group["net_pnl"] < 0]
        rows.append({
            "date": date_str,
            "variant": variant,
            "time_bucket": bucket,
            "trades": int(len(group)),
            "net_pnl": float(group["net_pnl"].sum()),
            "win_rate": float((group["net_pnl"] > 0).mean()) if len(group) else 0.0,
            "avg_hold_seconds": float(group["hold_seconds"].mean()),
            "avg_sensex_move_3s": float(group["sensex_move_3s"].mean()),
            "avg_option_move_3s": float(group["option_move_3s"].dropna().mean()) if group["option_move_3s"].notna().any() else np.nan,
            "profit_factor": float(wins["net_pnl"].sum() / abs(losses["net_pnl"].sum())) if not losses.empty and losses["net_pnl"].sum() != 0 else (float("inf") if not wins.empty else 0.0),
        })
    return pd.DataFrame(rows).sort_values(["date", "variant", "time_bucket"]).reset_index(drop=True)


def summarize_regime(trades_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (date_str, variant, regime), group in trades_df.groupby(["date", "variant", "regime"]):
        wins = group[group["net_pnl"] > 0]
        losses = group[group["net_pnl"] < 0]
        rows.append({
            "date": date_str,
            "variant": variant,
            "regime": regime,
            "trades": int(len(group)),
            "net_pnl": float(group["net_pnl"].sum()),
            "win_rate": float((group["net_pnl"] > 0).mean()) if len(group) else 0.0,
            "avg_points": float(group["points"].mean()),
            "profit_factor": float(wins["net_pnl"].sum() / abs(losses["net_pnl"].sum())) if not losses.empty and losses["net_pnl"].sum() != 0 else (float("inf") if not wins.empty else 0.0),
        })
    return pd.DataFrame(rows).sort_values(["date", "variant", "regime"]).reset_index(drop=True)


def summarize_forward_test(trades_df: pd.DataFrame) -> pd.DataFrame:
    sample_groups = {
        "calibration": ["2026-04-27", "2026-04-28"],
        "forward_test": ["2026-05-05"],
        "expiry_filtered_sample": ["2026-04-29", "2026-04-30"],
    }
    rows = []
    for sample_type, dates in sample_groups.items():
        sample = trades_df[trades_df["date"].isin(dates)]
        for variant, group in sample.groupby("variant"):
            wins = group[group["net_pnl"] > 0]
            losses = group[group["net_pnl"] < 0]
            rows.append({
                "sample_type": sample_type,
                "dates": ",".join(dates),
                "variant": variant,
                "trades": int(len(group)),
                "net_pnl": float(group["net_pnl"].sum()),
                "win_rate": float((group["net_pnl"] > 0).mean()) if len(group) else 0.0,
                "profit_factor": float(wins["net_pnl"].sum() / abs(losses["net_pnl"].sum())) if not losses.empty and losses["net_pnl"].sum() != 0 else (float("inf") if not wins.empty else 0.0),
                "max_intraday_drawdown": _compute_drawdown(group.sort_values("exit_time")["net_pnl"].tolist()),
            })
    return pd.DataFrame(rows).sort_values(["sample_type", "variant"]).reset_index(drop=True)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = repo_root / "analysis" / "impulse_sync_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    coverage_df, usable_configs = discover_dates(repo_root)
    coverage_path = out_dir / "date_coverage.csv"
    coverage_df.to_csv(coverage_path, index=False)

    usable_dates = [cfg["date"] for cfg in usable_configs]
    all_trades: list[dict[str, Any]] = []
    print("Usable dates:", ", ".join(usable_dates) if usable_dates else "none", flush=True)
    if "2026-05-05" not in usable_dates:
        print("WARNING: 2026-05-05 is missing or unusable.", flush=True)
    print("Coverage:", flush=True)
    print(coverage_df.to_string(index=False), flush=True)

    for cfg in usable_configs:
        date_str = cfg["date"]
        print(f"\nReplaying {date_str}...", flush=True)
        sensex_df = load_sensex_ticks(cfg["sensex_path"])
        symbol_map, meta_rows, meta_by_type = load_option_tape(cfg["option_path"], expiry_filter=cfg["expiry_filter"])
        trades = simulate_day(date_str=date_str, sensex_df=sensex_df, symbol_map=symbol_map, meta_rows=meta_rows, meta_by_type=meta_by_type, args=args)
        print(f"  trades: {len(trades)} | symbols: {len(symbol_map)} | expiry_filter: {cfg['expiry_filter']}", flush=True)
        all_trades.extend(trades)

    trades_df = pd.DataFrame(all_trades)
    if trades_df.empty:
        print("No trades generated.")
        trades_df.to_csv(out_dir / "trades.csv", index=False)
        return 1

    day_summary = summarize_day(trades_df)
    time_summary = summarize_time_bucket(trades_df)
    regime_summary = summarize_regime(trades_df)
    forward_summary = summarize_forward_test(trades_df)

    trades_path = out_dir / "trades.csv"
    day_path = out_dir / "day_summary.csv"
    time_path = out_dir / "time_bucket_summary.csv"
    regime_path = out_dir / "regime_summary.csv"
    forward_path = out_dir / "forward_test_summary.csv"
    trades_df.to_csv(trades_path, index=False)
    day_summary.to_csv(day_path, index=False)
    time_summary.to_csv(time_path, index=False)
    regime_summary.to_csv(regime_path, index=False)
    forward_summary.to_csv(forward_path, index=False)

    variant_compare = day_summary.groupby("variant", as_index=False).agg(
        trades=("trades", "sum"),
        gross_pnl=("gross_pnl", "sum"),
        net_pnl=("net_pnl", "sum"),
        avg_win_rate=("win_rate", "mean"),
        worst_day_pnl=("net_pnl", "min"),
        best_day_pnl=("net_pnl", "max"),
    )
    overall_time = time_summary.groupby(["variant", "time_bucket"], as_index=False).agg(
        trades=("trades", "sum"),
        net_pnl=("net_pnl", "sum"),
        win_rate=("win_rate", "mean"),
    )
    overall_regime = regime_summary.groupby(["variant", "regime"], as_index=False).agg(
        trades=("trades", "sum"),
        net_pnl=("net_pnl", "sum"),
        win_rate=("win_rate", "mean"),
    )

    print("\nDay summary:")
    print(day_summary.to_string(index=False))
    print("\nTime bucket summary:")
    print(time_summary.to_string(index=False))
    print("\nRegime summary:")
    print(regime_summary.to_string(index=False))
    print("\nForward-test summary:")
    print(forward_summary.to_string(index=False))
    print("\nVariant comparison A vs B vs C:")
    print(variant_compare.to_string(index=False))

    if not overall_time.empty:
        best_time = overall_time.sort_values("net_pnl", ascending=False).iloc[0]
        worst_time = overall_time.sort_values("net_pnl", ascending=True).iloc[0]
        print("\nBest time bucket:")
        print(best_time.to_string())
        print("\nWorst time bucket:")
        print(worst_time.to_string())
    if not overall_regime.empty:
        best_regime = overall_regime.sort_values("net_pnl", ascending=False).iloc[0]
        worst_regime = overall_regime.sort_values("net_pnl", ascending=True).iloc[0]
        print("\nBest regime:")
        print(best_regime.to_string())
        print("\nWorst regime:")
        print(worst_regime.to_string())

    print(f"\nSaved outputs to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
