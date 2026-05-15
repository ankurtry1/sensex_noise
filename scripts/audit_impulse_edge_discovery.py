#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from replay_impulse_sync_edge import (  # noqa: E402
    PRIMARY_DATES,
    SECONDARY_FILTERED_DATES,
    VARIANTS,
    _compute_drawdown,
    _latest_idx_at_or_before,
    _median_window,
    _nearest_idx_within,
    _next_idx_at_or_after,
    _time_bucket,
    _value_change,
    choose_atm_symbol,
    classify_regime,
    load_option_tape,
    load_sensex_ticks,
)

EXCLUDED_DATES = {"1970-01-01", "2026-04-23", "2026-04-24", "2026-05-04"}
IMPULSE_WINDOWS = [1, 2, 3, 5]
IMPULSE_THRESHOLDS = [15, 20, 25, 30, 40]
COST_MODELS = [
    "ltp_ltp",
    "half_point_roundtrip",
    "one_point_roundtrip",
    "buy_ask_sell_bid",
    "buy_ask_plus_0_25_sell_bid_minus_0_25",
]
LATENCY_MS = [0, 250, 500, 1000, 2000]
TIME_FILTER_START = time(9, 15)
TIME_FILTER_END = time(15, 30)
FORWARD_DATE = "2026-05-05"
CALIBRATION_DATES = ["2026-04-27", "2026-04-28"]
EXPIRY_FILTERED_SAMPLE = ["2026-04-29", "2026-04-30"]


@dataclass
class DayConfig:
    date: str
    option_path: Path
    sensex_path: Path
    expiry_filter: str | None
    sample_type: str


@dataclass
class SymbolArrays:
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


@dataclass
class SignalRecord:
    date: str
    variant: str
    signal_time: datetime
    direction: str
    symbol: str
    strike: int
    expiry: str
    sensex_spot: float
    sensex_move_3s: float
    sync_passed: bool
    vacuum_available: bool
    vacuum_passed: bool
    spread_now: float | None
    median_spread_10s: float | None
    top_depth_now: float | None
    median_top_depth_10s: float | None
    option_move_1s: float | None
    option_move_3s: float | None
    nearest_option_tick_time: datetime | None
    nearest_tick_lag_ms: float | None
    entry_option_tick_time: datetime
    entry_idx: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the ATM impulse-sync replay edge.")
    parser.add_argument("--repo-root", default=".", help="Repository root")
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


def canonical_configs(repo_root: Path) -> list[DayConfig]:
    tape_root = repo_root / "data" / "tape" / "sensex_options"
    tick_root = repo_root / "logs" / "ticks"
    configs: list[DayConfig] = []
    for date_str in PRIMARY_DATES:
        option_path = tape_root / date_str / "options.jsonl"
        manifest_path = tape_root / date_str / "manifest.json"
        sensex_path = tick_root / date_str / "sensex.jsonl"
        if option_path.exists() and manifest_path.exists() and sensex_path.exists():
            configs.append(
                DayConfig(
                    date=date_str,
                    option_path=option_path,
                    sensex_path=sensex_path,
                    expiry_filter=None,
                    sample_type="primary",
                )
            )
    for date_str, expiry_filter in SECONDARY_FILTERED_DATES.items():
        option_path = tape_root / date_str / "options.jsonl"
        manifest_path = tape_root / date_str / "manifest.json"
        sensex_path = tick_root / date_str / "sensex.jsonl"
        if option_path.exists() and manifest_path.exists() and sensex_path.exists():
            configs.append(
                DayConfig(
                    date=date_str,
                    option_path=option_path,
                    sensex_path=sensex_path,
                    expiry_filter=expiry_filter,
                    sample_type="secondary_expiry_filtered",
                )
            )
    return configs


def round_to_100(value: float) -> int:
    return int(round(value / 100.0) * 100)


def top_depth_at(symbol_data: Any, idx: int) -> float | None:
    value = float(symbol_data.top_depth[idx])
    return value if np.isfinite(value) else None


def spread_at(symbol_data: Any, idx: int) -> float | None:
    value = float(symbol_data.spread[idx])
    return value if np.isfinite(value) else None


def bid_at(symbol_data: Any, idx: int) -> float | None:
    value = float(symbol_data.best_bid[idx])
    return value if np.isfinite(value) else None


def ask_at(symbol_data: Any, idx: int) -> float | None:
    value = float(symbol_data.best_ask[idx])
    return value if np.isfinite(value) else None


def replay_trade_detailed(symbol_data: Any, entry_idx: int, entry_time: datetime, args: argparse.Namespace) -> dict[str, Any] | None:
    entry_ns = int(symbol_data.times_ns[entry_idx])
    entry_price = float(symbol_data.ltp[entry_idx])
    target_price = entry_price + float(args.target_points)
    stop_price = entry_price - float(args.stop_points)
    deadline_ns = entry_ns + int(args.max_hold_seconds * 1_000_000_000)
    one_sec_ns = entry_ns + 1_000_000_000
    three_sec_ns = entry_ns + 3_000_000_000
    mfe = 0.0
    mae = 0.0
    exit_idx = len(symbol_data.times_ns) - 1
    exit_reason = "MAX_HOLD"
    one_done = False
    three_done = False

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

    exit_time = pd.Timestamp(symbol_data.times[exit_idx]).to_pydatetime()
    exit_price = float(symbol_data.ltp[exit_idx])
    points = exit_price - entry_price
    return {
        "entry_idx": entry_idx,
        "exit_idx": exit_idx,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "points": points,
        "gross_pnl": points * int(args.qty),
        "net_pnl": points * int(args.qty) - float(args.charges_per_trade),
        "exit_reason": exit_reason,
        "hold_seconds": max(0.0, (exit_time - entry_time).total_seconds()),
        "mfe": mfe,
        "mae": mae,
    }


def compute_vacuum(symbol_data: Any, t0_ns: int, nearest_idx: int) -> tuple[bool, bool, float | None, float | None, float | None, float | None]:
    spread_now = spread_at(symbol_data, nearest_idx)
    top_depth_now = top_depth_at(symbol_data, nearest_idx)
    median_spread_10s = _median_window(symbol_data.spread, symbol_data.times_ns, t0_ns, 10.0)
    median_top_depth_10s = _median_window(symbol_data.top_depth, symbol_data.times_ns, t0_ns, 10.0)
    vacuum_available = all(
        value is not None and np.isfinite(value)
        for value in (spread_now, top_depth_now, median_spread_10s, median_top_depth_10s)
    )
    vacuum_passed = False
    if vacuum_available:
        vacuum_passed = bool(
            float(spread_now) >= 1.5 * float(median_spread_10s)
            or float(top_depth_now) <= 0.5 * float(median_top_depth_10s)
        )
    return vacuum_available, vacuum_passed, spread_now, median_spread_10s, top_depth_now, median_top_depth_10s


def build_signal_and_trade_records(
    day: DayConfig,
    sensex_df: pd.DataFrame,
    symbol_map: dict[str, Any],
    meta_by_type: dict[str, list[dict[str, Any]]],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[SignalRecord]]:
    trades: list[dict[str, Any]] = []
    signals: list[SignalRecord] = []
    if sensex_df.empty:
        return trades, signals
    session_mask = (sensex_df["ts"].dt.time >= TIME_FILTER_START) & (sensex_df["ts"].dt.time <= TIME_FILTER_END)
    session_df = sensex_df.loc[session_mask].reset_index(drop=True)
    session_times = session_df["ts_ns"].to_numpy(dtype=np.int64)
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
            vacuum_available, vacuum_passed, spread_now, median_spread_10s, top_depth_now, median_top_depth_10s = compute_vacuum(symbol_data, t0_ns, nearest_idx)
            if variant.require_sync and not sync_passed:
                i += 1
                continue
            if variant.require_vacuum and not (vacuum_available and vacuum_passed):
                i += 1
                continue
            entry_time_ns = int(symbol_data.times_ns[entry_idx])
            entry_time = pd.Timestamp(symbol_data.times[entry_idx]).to_pydatetime()
            trade = replay_trade_detailed(symbol_data, entry_idx, entry_time, args)
            if trade is None:
                i += 1
                continue
            sensex_entry_idx = int(np.searchsorted(session_times, entry_time_ns, side="right") - 1)
            if sensex_entry_idx < 0:
                sensex_entry_idx = i
            regime = classify_regime(session_df, sensex_entry_idx, entry_time, vacuum_passed)
            signal = SignalRecord(
                date=day.date,
                variant=variant.name,
                signal_time=t0,
                direction=direction,
                symbol=symbol,
                strike=int(selection["strike"]),
                expiry=str(selection["expiry"]),
                sensex_spot=float(row["ltp"]),
                sensex_move_3s=float(move),
                sync_passed=sync_passed,
                vacuum_available=vacuum_available,
                vacuum_passed=vacuum_passed,
                spread_now=spread_now,
                median_spread_10s=median_spread_10s,
                top_depth_now=top_depth_now,
                median_top_depth_10s=median_top_depth_10s,
                option_move_1s=option_move_1s,
                option_move_3s=option_move_3s,
                nearest_option_tick_time=pd.Timestamp(symbol_data.times[nearest_idx]).to_pydatetime(),
                nearest_tick_lag_ms=(int(symbol_data.times_ns[nearest_idx] - t0_ns) / 1_000_000.0),
                entry_option_tick_time=entry_time,
                entry_idx=entry_idx,
            )
            signals.append(signal)
            entry_bid = bid_at(symbol_data, entry_idx)
            entry_ask = ask_at(symbol_data, entry_idx)
            entry_top_depth = top_depth_at(symbol_data, entry_idx)
            atm_distance_points = int(selection["strike"]) - round_to_100(float(row["ltp"]))
            entry_prev_idx = entry_idx - 1 if entry_idx > 0 else None
            entry_next_idx = entry_idx + 1 if entry_idx + 1 < len(symbol_data.times_ns) else None
            trades.append(
                {
                    "date": day.date,
                    "variant": variant.name,
                    "signal_time": t0.isoformat(),
                    "nearest_option_tick_time": signal.nearest_option_tick_time.isoformat() if signal.nearest_option_tick_time else None,
                    "entry_option_tick_time": entry_time.isoformat(),
                    "signal_to_entry_ms": (entry_time_ns - t0_ns) / 1_000_000.0,
                    "nearest_tick_lag_ms": signal.nearest_tick_lag_ms,
                    "option_tick_gap_before_entry_ms": (int(symbol_data.times_ns[entry_idx] - symbol_data.times_ns[entry_prev_idx]) / 1_000_000.0) if entry_prev_idx is not None else np.nan,
                    "option_tick_gap_after_entry_ms": (int(symbol_data.times_ns[entry_next_idx] - symbol_data.times_ns[entry_idx]) / 1_000_000.0) if entry_next_idx is not None else np.nan,
                    "selected_expiry": signal.expiry,
                    "selected_strike": signal.strike,
                    "atm_distance_points": atm_distance_points,
                    "spread_at_entry": spread_at(symbol_data, entry_idx),
                    "bid_at_entry": entry_bid,
                    "ask_at_entry": entry_ask,
                    "ltp_at_entry": float(symbol_data.ltp[entry_idx]),
                    "top_depth_at_entry": entry_top_depth,
                    "direction": direction,
                    "symbol": symbol,
                    "entry_time": entry_time.isoformat(),
                    "exit_time": trade["exit_time"].isoformat(),
                    "entry_price": trade["entry_price"],
                    "exit_price": trade["exit_price"],
                    "points": trade["points"],
                    "gross_pnl": trade["gross_pnl"],
                    "net_pnl": trade["net_pnl"],
                    "exit_reason": trade["exit_reason"],
                    "hold_seconds": trade["hold_seconds"],
                    "mfe": trade["mfe"],
                    "mae": trade["mae"],
                    "sensex_at_entry": float(session_df.iloc[sensex_entry_idx]["ltp"]),
                    "sensex_move_3s": float(move),
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
            )
            next_allowed_ns = entry_time_ns + int(args.cooldown_seconds * 1_000_000_000)
            i = int(np.searchsorted(session_times, next_allowed_ns, side="left"))
    return trades, signals


def execution_prices(symbol_data: Any, entry_idx: int, exit_idx: int, cost_model: str) -> tuple[float, float]:
    entry_ltp = float(symbol_data.ltp[entry_idx])
    exit_ltp = float(symbol_data.ltp[exit_idx])
    entry_ask = ask_at(symbol_data, entry_idx)
    exit_bid = bid_at(symbol_data, exit_idx)
    if cost_model == "ltp_ltp":
        return entry_ltp, exit_ltp
    if cost_model == "half_point_roundtrip":
        return entry_ltp + 0.25, exit_ltp - 0.25
    if cost_model == "one_point_roundtrip":
        return entry_ltp + 0.5, exit_ltp - 0.5
    if cost_model == "buy_ask_sell_bid":
        return (entry_ask if entry_ask is not None else entry_ltp), (exit_bid if exit_bid is not None else exit_ltp)
    if cost_model == "buy_ask_plus_0_25_sell_bid_minus_0_25":
        entry_exec = (entry_ask if entry_ask is not None else entry_ltp) + 0.25
        exit_exec = (exit_bid if exit_bid is not None else exit_ltp) - 0.25
        return entry_exec, exit_exec
    raise ValueError(f"Unknown cost model: {cost_model}")


def generate_cost_latency_rows(signal: SignalRecord, symbol_data: Any, args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    signal_ns = int(pd.Timestamp(signal.signal_time).value)
    for latency_ms in LATENCY_MS:
        delayed_ns = signal_ns + latency_ms * 1_000_000
        entry_idx = _next_idx_at_or_after(symbol_data.times_ns, delayed_ns)
        if entry_idx is None:
            continue
        entry_time = pd.Timestamp(symbol_data.times[entry_idx]).to_pydatetime()
        replay = replay_trade_detailed(symbol_data, entry_idx, entry_time, args)
        if replay is None:
            continue
        for cost_model in COST_MODELS:
            entry_exec, exit_exec = execution_prices(symbol_data, replay["entry_idx"], replay["exit_idx"], cost_model)
            points = exit_exec - entry_exec
            gross_pnl = points * int(args.qty)
            net_pnl = gross_pnl - float(args.charges_per_trade)
            rows.append(
                {
                    "date": signal.date,
                    "variant": signal.variant,
                    "cost_model": cost_model,
                    "latency_ms": latency_ms,
                    "entry_time": entry_time.isoformat(),
                    "exit_time": replay["exit_time"].isoformat(),
                    "net_pnl": net_pnl,
                    "gross_pnl": gross_pnl,
                    "points": points,
                    "exit_reason": replay["exit_reason"],
                }
            )
    return rows


def compute_tick_rate(symbol_data: Any, end_ns: int, lookback_seconds: float) -> int:
    start_ns = end_ns - int(lookback_seconds * 1_000_000_000)
    left = int(np.searchsorted(symbol_data.times_ns, start_ns, side="left"))
    right = int(np.searchsorted(symbol_data.times_ns, end_ns, side="right"))
    return max(0, right - left)


def compute_forward_stats(symbol_data: Any, entry_idx: int, horizon_seconds: float) -> tuple[float | None, float | None]:
    if entry_idx is None or entry_idx >= len(symbol_data.times_ns):
        return None, None
    entry_ns = int(symbol_data.times_ns[entry_idx])
    end_ns = entry_ns + int(horizon_seconds * 1_000_000_000)
    right = int(np.searchsorted(symbol_data.times_ns, end_ns, side="right"))
    if right <= entry_idx:
        return None, None
    window = symbol_data.ltp[entry_idx:right]
    entry_price = float(symbol_data.ltp[entry_idx])
    mfe = float(np.max(window) - entry_price)
    mae = float(np.min(window) - entry_price)
    return mfe, mae


def hit_condition(symbol_data: Any, entry_idx: int, plus: float, minus: float, horizon_seconds: float = 10.0) -> bool:
    entry_ns = int(symbol_data.times_ns[entry_idx])
    end_ns = entry_ns + int(horizon_seconds * 1_000_000_000)
    right = int(np.searchsorted(symbol_data.times_ns, end_ns, side="right"))
    if right <= entry_idx:
        return False
    entry_price = float(symbol_data.ltp[entry_idx])
    for idx in range(entry_idx + 1, right):
        delta = float(symbol_data.ltp[idx] - entry_price)
        if delta >= plus:
            return True
        if delta <= -minus:
            return False
    return False


def infer_event_regime(sensex_df: pd.DataFrame, event_idx: int, event_time: datetime, vacuum_passed: bool) -> str:
    if vacuum_passed:
        return "liquidity_vacuum_impulse"
    current_ns = int(sensex_df.iloc[event_idx]["ts_ns"])
    left = int(np.searchsorted(sensex_df["ts_ns"].to_numpy(dtype=np.int64), current_ns - 60_000_000_000, side="left"))
    window = sensex_df.iloc[left : event_idx + 1]
    if window.empty:
        return "calm_impulse"
    prices = window["ltp"].to_numpy(dtype=float)
    diffs = np.diff(prices)
    net_move = abs(float(prices[-1] - prices[0]))
    path = float(np.abs(diffs).sum())
    efficiency = net_move / path if path > 0 else 0.0
    if efficiency >= 0.55:
        return "clean_trend_impulse"
    if efficiency <= 0.30:
        return "choppy_fake_impulse"
    if event_time.time() >= time(14, 30):
        return "late_session_impulse"
    return "calm_impulse"


def build_impulse_events_for_day(day: DayConfig, sensex_df: pd.DataFrame, symbol_map: dict[str, Any], meta_by_type: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    session_mask = (sensex_df["ts"].dt.time >= TIME_FILTER_START) & (sensex_df["ts"].dt.time <= TIME_FILTER_END)
    df = sensex_df.loc[session_mask].reset_index(drop=True)
    times_ns = df["ts_ns"].to_numpy(dtype=np.int64)
    for window in IMPULSE_WINDOWS:
        move_col = f"move_{window}s"
        if move_col not in df.columns:
            continue
        moves = df[move_col].to_numpy(dtype=float)
        for threshold in IMPULSE_THRESHOLDS:
            prev_dir = None
            for i, move in enumerate(moves):
                if np.isnan(move):
                    prev_dir = None
                    continue
                direction = None
                option_type = None
                if move >= threshold:
                    direction = "UP"
                    option_type = "CE"
                elif move <= -threshold:
                    direction = "DOWN"
                    option_type = "PE"
                if direction is None:
                    prev_dir = None
                    continue
                if prev_dir == direction:
                    continue
                prev_dir = direction
                event_time = df.iloc[i]["ts"]
                event_ns = int(df.iloc[i]["ts_ns"])
                selection = choose_atm_symbol(meta_by_type, option_type=option_type, spot=float(df.iloc[i]["ltp"]))
                if selection is None:
                    continue
                symbol = str(selection["symbol"])
                symbol_data = symbol_map.get(symbol)
                if symbol_data is None:
                    continue
                signal_idx = _nearest_idx_within(symbol_data.times_ns, event_ns, 500_000_000)
                entry_idx = _next_idx_at_or_after(symbol_data.times_ns, event_ns)
                if entry_idx is None:
                    continue
                option_ltp_at_signal = float(symbol_data.ltp[signal_idx]) if signal_idx is not None else np.nan
                option_move_pre_1s = _value_change(symbol_data, event_ns, 1.0)
                option_move_pre_3s = _value_change(symbol_data, event_ns, 3.0)
                spread_now = float(symbol_data.spread[signal_idx]) if signal_idx is not None and np.isfinite(symbol_data.spread[signal_idx]) else np.nan
                top_depth_now = float(symbol_data.top_depth[signal_idx]) if signal_idx is not None and np.isfinite(symbol_data.top_depth[signal_idx]) else np.nan
                tick_rate_last_5s = compute_tick_rate(symbol_data, event_ns, 5.0)
                vacuum_available, vacuum_passed, _, _, _, _ = compute_vacuum(symbol_data, event_ns, signal_idx if signal_idx is not None else entry_idx)
                mfe_1, mae_1 = compute_forward_stats(symbol_data, entry_idx, 1.0)
                mfe_3, mae_3 = compute_forward_stats(symbol_data, entry_idx, 3.0)
                mfe_5, mae_5 = compute_forward_stats(symbol_data, entry_idx, 5.0)
                mfe_10, mae_10 = compute_forward_stats(symbol_data, entry_idx, 10.0)
                hit_1 = hit_condition(symbol_data, entry_idx, plus=1.0, minus=1.0)
                hit_2 = hit_condition(symbol_data, entry_idx, plus=2.0, minus=1.0)
                hit_3 = hit_condition(symbol_data, entry_idx, plus=3.0, minus=2.0)
                tradable = bool(hit_3 and mfe_10 is not None and mfe_10 >= 3.5)
                acceleration = np.nan
                prev_idx = i - 1
                if prev_idx >= 0 and not np.isnan(df.iloc[prev_idx][move_col]):
                    acceleration = float(move - df.iloc[prev_idx][move_col])
                rows.append(
                    {
                        "date": day.date,
                        "sample_type": day.sample_type,
                        "impulse_window": window,
                        "impulse_threshold": threshold,
                        "event_time": event_time.isoformat(),
                        "direction": direction,
                        "sensex_move_1s": df.iloc[i].get("move_1s"),
                        "sensex_move_2s": df.iloc[i].get("move_2s"),
                        "sensex_move_3s": df.iloc[i].get("move_3s"),
                        "sensex_move_5s": df.iloc[i].get("move_5s"),
                        "sensex_acceleration": acceleration,
                        "time_bucket": _time_bucket(event_time),
                        "regime": infer_event_regime(df, i, event_time, vacuum_passed),
                        "selected_atm_symbol": symbol,
                        "selected_strike": int(selection["strike"]),
                        "selected_expiry": str(selection["expiry"]),
                        "option_ltp_at_signal": option_ltp_at_signal,
                        "option_move_pre_1s": option_move_pre_1s,
                        "option_move_pre_3s": option_move_pre_3s,
                        "spread": spread_now,
                        "top_depth": top_depth_now,
                        "tick_rate_last_5s": tick_rate_last_5s,
                        "MFE_1s": mfe_1,
                        "MAE_1s": mae_1,
                        "MFE_3s": mfe_3,
                        "MAE_3s": mae_3,
                        "MFE_5s": mfe_5,
                        "MAE_5s": mae_5,
                        "MFE_10s": mfe_10,
                        "MAE_10s": mae_10,
                        "hit_plus_1_before_minus_1": hit_1,
                        "hit_plus_2_before_minus_1": hit_2,
                        "hit_plus_3_before_minus_2": hit_3,
                        "tradable_after_cost_0_5pt": tradable,
                    }
                )
    return rows


def profit_factor(series: pd.Series) -> float:
    wins = series[series > 0].sum()
    losses = series[series < 0].sum()
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return float(wins / abs(losses))


def summarize_cost_latency(rows_df: pd.DataFrame) -> pd.DataFrame:
    summary_rows = []
    for (variant, cost_model, latency_ms), group in rows_df.groupby(["variant", "cost_model", "latency_ms"]):
        ordered = group.sort_values(["date", "exit_time"])
        summary_rows.append(
            {
                "variant": variant,
                "cost_model": cost_model,
                "latency_ms": latency_ms,
                "trades": int(len(group)),
                "net_pnl": float(group["net_pnl"].sum()),
                "win_rate": float((group["net_pnl"] > 0).mean()) if len(group) else 0.0,
                "profit_factor": profit_factor(group["net_pnl"]),
                "max_dd": _compute_drawdown(ordered["net_pnl"].tolist()),
                "avg_pnl_per_trade": float(group["net_pnl"].mean()) if len(group) else 0.0,
            }
        )
    return pd.DataFrame(summary_rows).sort_values(["variant", "cost_model", "latency_ms"]).reset_index(drop=True)


def build_feature_deciles(events_df: pd.DataFrame) -> pd.DataFrame:
    features = [
        "sensex_move_3s",
        "option_move_pre_1s",
        "spread",
        "top_depth",
        "tick_rate_last_5s",
    ]
    rows = []
    for feature in features:
        subset = events_df[[feature, "MFE_3s", "MAE_3s", "MFE_10s", "hit_plus_3_before_minus_2", "tradable_after_cost_0_5pt"]].dropna()
        if subset.empty or subset[feature].nunique() < 3:
            continue
        try:
            deciles = pd.qcut(subset[feature], 10, labels=False, duplicates="drop")
        except ValueError:
            continue
        subset = subset.assign(decile=deciles)
        for decile, group in subset.groupby("decile"):
            rows.append(
                {
                    "feature": feature,
                    "decile": int(decile),
                    "events": int(len(group)),
                    "avg_MFE_3s": float(group["MFE_3s"].mean()),
                    "avg_MAE_3s": float(group["MAE_3s"].mean()),
                    "avg_MFE_10s": float(group["MFE_10s"].mean()),
                    "hit_plus_3_rate": float(group["hit_plus_3_before_minus_2"].mean()),
                    "tradable_after_cost_0_5pt_rate": float(group["tradable_after_cost_0_5pt"].mean()),
                }
            )
    return pd.DataFrame(rows).sort_values(["feature", "decile"]).reset_index(drop=True)


def build_best_edge_candidates(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame()
    df = events_df.copy()
    df["proxy_points_cost_0_5"] = np.where(
        df["tradable_after_cost_0_5pt"],
        2.5,
        np.where(df["MAE_10s"].fillna(0) <= -2.0, -2.0, 0.0),
    )
    rows = []
    group_cols = ["impulse_window", "impulse_threshold", "direction", "time_bucket", "regime"]
    for keys, group in df.groupby(group_cols):
        total_events = len(group)
        if total_events < 20:
            continue
        calibration = group[group["date"].isin(CALIBRATION_DATES)]
        forward = group[group["date"] == FORWARD_DATE]
        if forward.empty:
            continue
        total_proxy = float(group["proxy_points_cost_0_5"].sum())
        forward_proxy = float(forward["proxy_points_cost_0_5"].sum())
        if total_proxy <= 0 or forward_proxy < 0:
            continue
        per_day = group.groupby("date")["proxy_points_cost_0_5"].sum()
        worst_day = float(per_day.min()) if not per_day.empty else 0.0
        max_dd = _compute_drawdown(group.sort_values("event_time")["proxy_points_cost_0_5"].tolist())
        if worst_day < -5.0 or max_dd < -10.0:
            continue
        rows.append(
            {
                "impulse_window": keys[0],
                "impulse_threshold": keys[1],
                "direction": keys[2],
                "time_bucket": keys[3],
                "regime": keys[4],
                "events": total_events,
                "calibration_events": int(len(calibration)),
                "forward_events": int(len(forward)),
                "avg_MFE_3s": float(group["MFE_3s"].mean()),
                "avg_MAE_3s": float(group["MAE_3s"].mean()),
                "hit_plus_3_rate": float(group["hit_plus_3_before_minus_2"].mean()),
                "tradable_after_cost_0_5pt_rate": float(group["tradable_after_cost_0_5pt"].mean()),
                "proxy_total_points": total_proxy,
                "proxy_forward_points": forward_proxy,
                "worst_day_proxy_points": worst_day,
                "max_dd_proxy_points": max_dd,
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["proxy_forward_points", "tradable_after_cost_0_5pt_rate", "events"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = repo_root / "analysis" / "impulse_edge_audit"
    out_dir.mkdir(parents=True, exist_ok=True)

    configs = canonical_configs(repo_root)
    print("Canonical replay dates:", ", ".join(cfg.date for cfg in configs), flush=True)

    baseline_trades_path = repo_root / "analysis" / "impulse_sync_results" / "trades.csv"
    baseline_trades = pd.read_csv(baseline_trades_path)

    integrity_rows: list[dict[str, Any]] = []
    cost_latency_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []

    for cfg in configs:
        print(f"Auditing {cfg.date}...", flush=True)
        sensex_df = load_sensex_ticks(cfg.sensex_path)
        symbol_map, _meta_rows, meta_by_type = load_option_tape(cfg.option_path, expiry_filter=cfg.expiry_filter)
        detailed_trades, signals = build_signal_and_trade_records(cfg, sensex_df, symbol_map, meta_by_type, args)
        integrity_rows.extend(detailed_trades)
        for signal in signals:
            symbol_data = symbol_map[signal.symbol]
            cost_latency_rows.extend(generate_cost_latency_rows(signal, symbol_data, args))
        event_rows.extend(build_impulse_events_for_day(cfg, sensex_df, symbol_map, meta_by_type))
        print(
            f"  detailed trades={len(detailed_trades)} | signals={len(signals)} | events={len(event_rows)} cumulative",
            flush=True,
        )

    integrity_df = pd.DataFrame(integrity_rows)
    if integrity_df.empty:
        raise RuntimeError("No integrity rows produced.")
    baseline_keys = set(
        baseline_trades.assign(key=lambda df: df["date"] + "|" + df["variant"] + "|" + df["entry_time"] + "|" + df["symbol"])["key"]
    )
    integrity_keys = set(
        integrity_df.assign(key=lambda df: df["date"] + "|" + df["variant"] + "|" + df["entry_time"] + "|" + df["symbol"])["key"]
    )
    if baseline_keys != integrity_keys:
        print(f"WARNING: integrity replay key mismatch | baseline={len(baseline_keys)} | audit={len(integrity_keys)}", flush=True)

    cost_latency_df = pd.DataFrame(cost_latency_rows)
    events_df = pd.DataFrame(event_rows)

    threshold_window_summary = (
        events_df.groupby(["impulse_window", "impulse_threshold", "direction", "time_bucket"], dropna=False)
        .agg(
            events=("date", "size"),
            avg_MFE_3s=("MFE_3s", "mean"),
            avg_MAE_3s=("MAE_3s", "mean"),
            hit_plus_3_rate=("hit_plus_3_before_minus_2", "mean"),
            tradable_after_cost_0_5pt_rate=("tradable_after_cost_0_5pt", "mean"),
        )
        .reset_index()
        .sort_values(["tradable_after_cost_0_5pt_rate", "events"], ascending=[False, False])
    )
    regime_edge_summary = (
        events_df.groupby(["regime", "time_bucket", "direction"], dropna=False)
        .agg(
            events=("date", "size"),
            avg_MFE_3s=("MFE_3s", "mean"),
            avg_MAE_3s=("MAE_3s", "mean"),
            avg_MFE_10s=("MFE_10s", "mean"),
            hit_plus_3_rate=("hit_plus_3_before_minus_2", "mean"),
            tradable_after_cost_0_5pt_rate=("tradable_after_cost_0_5pt", "mean"),
        )
        .reset_index()
        .sort_values(["tradable_after_cost_0_5pt_rate", "events"], ascending=[False, False])
    )
    feature_decile_summary = build_feature_deciles(events_df)
    best_edge_candidates = build_best_edge_candidates(events_df)
    cost_latency_summary = summarize_cost_latency(cost_latency_df)

    integrity_path = out_dir / "trade_integrity_audit.csv"
    cost_latency_path = out_dir / "cost_latency_sensitivity.csv"
    event_universe_path = out_dir / "impulse_event_universe.csv"
    threshold_summary_path = out_dir / "threshold_window_summary.csv"
    regime_summary_path = out_dir / "regime_edge_summary.csv"
    feature_decile_path = out_dir / "feature_decile_summary.csv"
    best_candidates_path = out_dir / "best_edge_candidates.csv"

    integrity_df.to_csv(integrity_path, index=False)
    cost_latency_summary.to_csv(cost_latency_path, index=False)
    events_df.to_csv(event_universe_path, index=False)
    threshold_window_summary.to_csv(threshold_summary_path, index=False)
    regime_edge_summary.to_csv(regime_summary_path, index=False)
    feature_decile_summary.to_csv(feature_decile_path, index=False)
    best_edge_candidates.to_csv(best_candidates_path, index=False)

    print("\nCurrent A/B/C cost sensitivity (0ms latency):", flush=True)
    zero_latency = cost_latency_summary[cost_latency_summary["latency_ms"] == 0]
    print(zero_latency.to_string(index=False), flush=True)

    realistic = cost_latency_summary[
        (cost_latency_summary["latency_ms"] == 500)
        & (cost_latency_summary["cost_model"] == "buy_ask_sell_bid")
    ]
    print("\nRealistic cost view (buy_ask_sell_bid, 500ms):", flush=True)
    print(realistic.to_string(index=False), flush=True)

    best_threshold = threshold_window_summary[threshold_window_summary["events"] >= 20].head(1)
    best_regime = regime_edge_summary[regime_edge_summary["events"] >= 20].head(1)
    if not best_threshold.empty:
        print("\nBest threshold/time-bucket evidence:", flush=True)
        print(best_threshold.to_string(index=False), flush=True)
    if not best_regime.empty:
        print("\nBest regime evidence:", flush=True)
        print(best_regime.to_string(index=False), flush=True)

    if not best_edge_candidates.empty:
        print("\nStable edge candidates:", flush=True)
        print(best_edge_candidates.head(10).to_string(index=False), flush=True)
    else:
        print("\nStable edge candidates: none met the stability filters.", flush=True)

    a_realistic = realistic[realistic["variant"] == "A_impulse_only"]
    b_realistic = realistic[realistic["variant"] == "B_impulse_plus_option_sync"]
    c_realistic = realistic[realistic["variant"] == "C_impulse_plus_sync_plus_liquidity_vacuum"]
    print("\nAssessment:", flush=True)
    if not a_realistic.empty and a_realistic.iloc[0]["net_pnl"] <= 0 and not b_realistic.empty and b_realistic.iloc[0]["net_pnl"] <= 0:
        print("- The earlier positive replay was likely helped materially by cost omission.", flush=True)
    else:
        print("- At least one baseline variant remains positive under realistic execution assumptions.", flush=True)
    if not best_edge_candidates.empty and (best_edge_candidates["proxy_forward_points"] > 0).any():
        print("- There is some repeatable event-level structure beyond a single day, but it is narrow.", flush=True)
    else:
        print("- The edge looks fragile and may still be dominated by a small subset of sessions or conditions.", flush=True)

    print(f"\nSaved outputs to: {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
