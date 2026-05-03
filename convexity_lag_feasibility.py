from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import burst_onset_research as bor
import strategy_audit as audit_mod
import tradable_expansion_edge_hunt as teh

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "convexity_lag_feasibility_results"
CHARTS_DIR = OUTPUT_DIR / "charts"
RAW_BURST_CANDIDATES_PATH = REPO_ROOT / "tradable_expansion_edge_results" / "tradable_expansion_candidates.csv"

STRIKE_STEP = 100
MAIN_BUCKETS = ["ATM", "ATM_100", "ATM_200"]
ENTRY_LAGS = [0, 1, 2, 3]
HOLD_HORIZONS = [1, 2, 3, 5, 10, 15]
MAIN_EVENT_COOLDOWN = "cd10"
TRADABLE_SPREAD_ABS = 2.0
TRADABLE_SPREAD_PCT = 0.015
TRADABLE_DEPTH = 250.0
TRADABLE_FRESHNESS = 1.0
FIXED_QTY = 500
TARGET_POINTS = 3.0
STOP_POINTS = 3.0
MAX_TRADE_HOLDS = [5, 10]
TRADE_COOLDOWNS = [30, 60]
RANDOM_CONTROL_SEEDS = [11, 23, 37, 47, 59]

TIME_BUCKETS = [
    ("09:15-09:30", "09:15:00", "09:30:00"),
    ("09:30-10:30", "09:30:00", "10:30:00"),
    ("10:30-12:00", "10:30:00", "12:00:00"),
    ("12:00-13:30", "12:00:00", "13:30:00"),
    ("13:30-14:45", "13:30:00", "14:45:00"),
    ("14:45-15:15", "14:45:00", "15:15:01"),
]

IMPULSE_DEFS = [
    {"name": "U_1S_10PTS", "horizon": 1, "threshold": 10.0},
    {"name": "U_1S_15PTS", "horizon": 1, "threshold": 15.0},
    {"name": "U_1S_20PTS", "horizon": 1, "threshold": 20.0},
    {"name": "U_2S_15PTS", "horizon": 2, "threshold": 15.0},
    {"name": "U_2S_20PTS", "horizon": 2, "threshold": 20.0},
    {"name": "U_2S_25PTS", "horizon": 2, "threshold": 25.0},
    {"name": "U_3S_20PTS", "horizon": 3, "threshold": 20.0},
    {"name": "U_3S_30PTS", "horizon": 3, "threshold": 30.0},
    {"name": "U_3S_40PTS", "horizon": 3, "threshold": 40.0},
    {"name": "U_5S_30PTS", "horizon": 5, "threshold": 30.0},
    {"name": "ACCEL_SPIKE", "horizon": 3, "threshold": 20.0, "accel": True},
]


@dataclass(frozen=True)
class TradeVariant:
    name: str
    entry_lag_seconds: int
    max_hold_seconds: int
    cooldown_seconds: int
    require_not_exhausted: bool = False
    exhaustion_limit: float = 3.0
    require_light_confirm: bool = False


def build_trade_variants() -> list[TradeVariant]:
    base_defs = [
        ("IMPULSE_ENTRY_0S", 0, False, None, False),
        ("IMPULSE_ENTRY_1S", 1, False, None, False),
        ("IMPULSE_ENTRY_1S_NOT_EXHAUSTED", 1, True, 3.0, False),
        ("IMPULSE_ENTRY_1S_LIGHT_CONFIRM", 1, False, None, True),
        ("IMPULSE_ENTRY_2S_NOT_EXHAUSTED", 2, True, 3.0, False),
    ]
    out: list[TradeVariant] = []
    for base_name, lag, not_exhausted, limit, light in base_defs:
        for hold in MAX_TRADE_HOLDS:
            for cooldown in TRADE_COOLDOWNS:
                out.append(
                    TradeVariant(
                        name=f"{base_name}_H{hold}_CD{cooldown}",
                        entry_lag_seconds=lag,
                        max_hold_seconds=hold,
                        cooldown_seconds=cooldown,
                        require_not_exhausted=not_exhausted,
                        exhaustion_limit=float(limit or 3.0),
                        require_light_confirm=light,
                    )
                )
    return out


TRADE_VARIANTS = build_trade_variants()


def safe_float(value: Any) -> float | None:
    return bor.safe_float(value)


def parse_dt(value: Any) -> pd.Timestamp | pd.NaT:
    return bor.parse_dt(value)


def round_to_strike(value: float, step: int = STRIKE_STEP) -> int:
    return int(round(float(value) / float(step)) * step)


def exact_bucket(distance_abs: int) -> str:
    if distance_abs == 0:
        return "ATM"
    if distance_abs == 100:
        return "ATM_100"
    if distance_abs == 200:
        return "ATM_200"
    return "FAR"


def time_bucket(ts: pd.Timestamp) -> str:
    if pd.isna(ts):
        return "unknown"
    t = ts.time()
    for name, start_s, end_s in TIME_BUCKETS:
        start = pd.Timestamp(f"2000-01-01 {start_s}").time()
        end = pd.Timestamp(f"2000-01-01 {end_s}").time()
        if start <= t < end:
            return name
    return "outside"


def premium_bucket(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return "unknown"
    if value < 50:
        return "<50"
    if value < 80:
        return "50-80"
    if value < 150:
        return "80-150"
    if value < 300:
        return "150-300"
    if value < 500:
        return "300-500"
    return ">500"


def spread_bucket(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return "unknown"
    if value <= 0.005:
        return "<=0.5%"
    if value <= 0.010:
        return "0.5-1.0%"
    if value <= 0.015:
        return "1.0-1.5%"
    return ">1.5%"


def depth_bucket(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return "unknown"
    if value < 250:
        return "<250"
    if value < 500:
        return "250-500"
    if value < 1000:
        return "500-1000"
    return ">=1000"


def discover_usable_dates() -> list[str]:
    tape_root = REPO_ROOT / "data" / "tape" / "sensex_options"
    if not tape_root.exists():
        return []
    dates = []
    for path in sorted([p for p in tape_root.iterdir() if p.is_dir()]):
        if not (path / "options.jsonl").exists():
            continue
        if not (REPO_ROOT / "logs" / "ticks" / path.name / "sensex.jsonl").exists():
            continue
        dates.append(path.name)
    return dates


def prepare_underlying_features(series: pd.Series, date: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = pd.DataFrame({"sensex_ltp": series.astype(float)})
    for h in [1, 2, 3, 5, 10]:
        df[f"underlying_move_{h}s"] = df["sensex_ltp"] - df["sensex_ltp"].shift(h)
    df["underlying_abs_move_20s"] = df["sensex_ltp"].diff().abs().rolling(20, min_periods=1).sum()
    ret1 = df["sensex_ltp"].diff()
    df["underlying_realized_vol_1m"] = ret1.rolling(60, min_periods=10).std().fillna(0.0)
    abs_5m = ret1.abs().rolling(300, min_periods=20).sum()
    net_5m = (df["sensex_ltp"] - df["sensex_ltp"].shift(300)).abs()
    df["underlying_trend_score_5m"] = (net_5m / abs_5m.replace(0.0, np.nan)).clip(upper=1.0).fillna(0.0)
    df["time_bucket"] = [time_bucket(ts) for ts in df.index]
    day_net_move = float(df["sensex_ltp"].iloc[-1] - df["sensex_ltp"].iloc[0]) if len(df) else 0.0
    total_abs_intraday_move = float(ret1.abs().sum()) if not ret1.empty else 0.0
    trend_ratio = abs(day_net_move) / total_abs_intraday_move if total_abs_intraday_move > 0 else 0.0
    day_stats = {
        "date": date,
        "underlying_first": df.index.min() if not df.empty else None,
        "underlying_last": df.index.max() if not df.empty else None,
        "underlying_seconds": int(len(df)),
        "day_net_move": day_net_move,
        "total_abs_intraday_move": total_abs_intraday_move,
        "trend_ratio": trend_ratio,
        "avg_realized_vol_1m": float(df["underlying_realized_vol_1m"].mean()) if not df.empty else np.nan,
    }
    return df, day_stats


def build_symbol_snapshot_series(rows: list[dict[str, Any]], full_index: pd.DatetimeIndex) -> pd.DataFrame:
    df = pd.DataFrame(rows).sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    df = df.set_index("timestamp")
    out = df.reindex(full_index).ffill()
    out["updated"] = False
    aligned_updates = df.index.intersection(out.index)
    out.loc[aligned_updates, "updated"] = True
    out["mid_price"] = (out["best_bid"].astype(float) + out["best_ask"].astype(float)) / 2.0
    out.loc[(out["best_bid"].isna()) | (out["best_ask"].isna()), "mid_price"] = np.nan
    out["spread_pct"] = out["spread"].astype(float) / out["ltp"].replace(0.0, np.nan).astype(float)
    out["depth_min_qty"] = np.minimum(out["bid_qty"].astype(float), out["ask_qty"].astype(float))
    idx_pos = np.arange(len(out), dtype=float)
    last_update_pos = pd.Series(np.where(out["updated"].to_numpy(), idx_pos, np.nan), index=out.index).ffill()
    out["seconds_since_symbol_update"] = idx_pos - last_update_pos.to_numpy()
    out.loc[last_update_pos.isna(), "seconds_since_symbol_update"] = np.nan
    out["update_count_5s"] = out["updated"].astype(int).rolling(5, min_periods=1).sum()
    out.index.name = "timestamp"
    return out


def load_day_context(date: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, Any], dict[str, Any]]:
    underlying = audit_mod.load_underlying_second_series(date)
    option_rows, option_quality = bor.load_option_second_rows_with_quality(date)
    if underlying.empty or not option_rows:
        return pd.DataFrame(), {}, option_quality, {"date": date, "usable": False}
    under_df, day_stats = prepare_underlying_features(underlying, date)
    full_index = under_df.index
    series_by_symbol: dict[str, pd.DataFrame] = {}
    meta_rows: list[dict[str, Any]] = []
    for symbol, rows in option_rows.items():
        if not rows:
            continue
        series = build_symbol_snapshot_series(rows, full_index)
        series_by_symbol[symbol] = series
        first = rows[0]
        strike = safe_float(first.get("strike"))
        opt_type = str(first.get("option_type") or "").upper()
        if strike is None or opt_type not in {"CE", "PE"}:
            continue
        meta_rows.append(
            {
                "symbol": symbol,
                "strike": int(round(strike)),
                "option_type": opt_type,
                "side": "CALL" if opt_type == "CE" else "PUT",
                "expiry": first.get("expiry"),
                "lot_size": int(first.get("lot_size") or 0),
            }
        )
    meta_df = pd.DataFrame(meta_rows)
    if meta_df.empty:
        return pd.DataFrame(), {}, option_quality, {**day_stats, "usable": False}
    day_stats.update(
        {
            "date": date,
            "usable": True,
            "option_symbols": int(meta_df["symbol"].nunique()),
            "option_strikes": int(meta_df["strike"].nunique()),
            "option_first_timestamp": option_quality.get("first_timestamp"),
            "option_last_timestamp": option_quality.get("last_timestamp"),
            "option_raw_rows": option_quality.get("raw_rows"),
        }
    )
    return under_df, series_by_symbol, {"meta": meta_df, "quality": option_quality}, day_stats


def event_direction(value: float | None) -> str | None:
    if value is None or not np.isfinite(value) or value == 0:
        return None
    return "UP" if value > 0 else "DOWN"


def build_raw_impulse_candidates(under_df: pd.DataFrame, date: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    prev_3s = under_df["underlying_move_3s"].shift(3)
    for ts, row in under_df.iterrows():
        current_3s = safe_float(row.get("underlying_move_3s"))
        prior_3s = safe_float(prev_3s.loc[ts]) if ts in prev_3s.index else None
        for imp in IMPULSE_DEFS:
            name = imp["name"]
            if name == "ACCEL_SPIKE":
                if current_3s is None or abs(current_3s) < float(imp["threshold"]):
                    continue
                if prior_3s is None or abs(current_3s) < abs(prior_3s) + 10.0:
                    continue
                move = current_3s
                accel = current_3s - (prior_3s or 0.0)
            else:
                h = int(imp["horizon"])
                move = safe_float(row.get(f"underlying_move_{h}s"))
                if move is None or abs(move) < float(imp["threshold"]):
                    continue
                prior_move = safe_float((under_df["sensex_ltp"].shift(h) - under_df["sensex_ltp"].shift(2 * h)).loc[ts]) if 2 * h < len(under_df) else None
                accel = move - (prior_move or 0.0)
            direction = event_direction(move)
            if direction is None:
                continue
            rows.append(
                {
                    "date": date,
                    "event_time": ts,
                    "impulse_type": name,
                    "direction": direction,
                    "underlying_move_1s": safe_float(row.get("underlying_move_1s")),
                    "underlying_move_2s": safe_float(row.get("underlying_move_2s")),
                    "underlying_move_3s": safe_float(row.get("underlying_move_3s")),
                    "underlying_move_5s": safe_float(row.get("underlying_move_5s")),
                    "underlying_move_10s": safe_float(row.get("underlying_move_10s")),
                    "underlying_acceleration": accel,
                    "pre_event_move_10s": safe_float(row.get("underlying_move_10s")),
                    "pre_event_abs_chop_20s": safe_float(row.get("underlying_abs_move_20s")),
                    "underlying_realized_vol_1m": safe_float(row.get("underlying_realized_vol_1m")),
                    "underlying_trend_score_5m": safe_float(row.get("underlying_trend_score_5m")),
                    "time_bucket": row.get("time_bucket"),
                    "underlying_ltp": safe_float(row.get("sensex_ltp")),
                }
            )
    return pd.DataFrame(rows).sort_values(["impulse_type", "direction", "event_time"]).reset_index(drop=True) if rows else pd.DataFrame()


def dedupe_impulses(raw_df: pd.DataFrame, cooldown_seconds: int) -> pd.DataFrame:
    if raw_df.empty:
        return raw_df.copy()
    keep_rows: list[dict[str, Any]] = []
    for (impulse_type, direction), g in raw_df.groupby(["impulse_type", "direction"]):
        last_kept: pd.Timestamp | None = None
        for row in g.sort_values("event_time").to_dict(orient="records"):
            ts = pd.Timestamp(row["event_time"])
            if last_kept is not None and (ts - last_kept).total_seconds() < cooldown_seconds:
                continue
            keep_rows.append(row)
            last_kept = ts
    out = pd.DataFrame(keep_rows)
    if out.empty:
        return out
    out = out.sort_values(["event_time", "impulse_type", "direction"]).reset_index(drop=True)
    return out


def attach_day_regimes(events_df: pd.DataFrame, day_stats_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return events_df
    out = events_df.merge(day_stats_df, on="date", how="left", suffixes=("", "_day"))
    trend_med = float(day_stats_df["trend_ratio"].median()) if not day_stats_df.empty else 0.0
    vol_med = float(day_stats_df["avg_realized_vol_1m"].median()) if not day_stats_df.empty else 0.0
    out["trend_regime"] = np.where(out["trend_ratio"] >= trend_med, "trending", "choppy")
    out["day_vol_regime"] = np.where(out["avg_realized_vol_1m"] >= vol_med, "high_vol", "low_vol")
    return out


def build_event_lookup(events_df: pd.DataFrame) -> dict[tuple[str, str], list[pd.Timestamp]]:
    lookup: dict[tuple[str, str], list[pd.Timestamp]] = {}
    if events_df.empty:
        return lookup
    for (date, direction), g in events_df.groupby(["date", "direction"]):
        lookup[(str(date), str(direction))] = list(pd.to_datetime(g["event_time"]).sort_values())
    return lookup


def has_recent_impulse(lookup: dict[tuple[str, str], list[pd.Timestamp]], date: str, direction: str, ts: pd.Timestamp, seconds: int) -> bool:
    arr = lookup.get((date, direction), [])
    if not arr:
        return False
    left = ts - pd.Timedelta(seconds=seconds)
    for t in reversed(arr):
        if t > ts:
            continue
        if t < left:
            break
        return True
    return False


def score_option_for_event(series: pd.DataFrame, ts: pd.Timestamp, strike: int, atm_strike: int, event_ltp: float | None = None) -> tuple[float, dict[str, Any]] | None:
    if ts not in series.index:
        return None
    row = series.loc[ts]
    ltp = safe_float(row.get("ltp"))
    spread_pct = safe_float(row.get("spread_pct"))
    spread = safe_float(row.get("spread"))
    depth = safe_float(row.get("depth_min_qty"))
    freshness = safe_float(row.get("seconds_since_symbol_update"))
    if ltp is None or spread_pct is None or spread is None or depth is None or freshness is None:
        return None
    dist_abs = abs(int(strike) - int(atm_strike))
    event_to_entry_move = None
    if event_ltp is not None:
        event_to_entry_move = ltp - event_ltp
    premium_penalty = 0.0
    if ltp < 80:
        premium_penalty += (80.0 - ltp) / 20.0
    elif ltp > 300:
        premium_penalty += (ltp - 300.0) / 50.0
    score = (
        -10.0 * dist_abs
        - 500.0 * spread_pct
        - 5.0 * spread
        + 0.01 * depth
        - 2.0 * freshness
        - 5.0 * premium_penalty
    )
    if event_to_entry_move is not None and event_to_entry_move > 0:
        score -= event_to_entry_move
    meta = {
        "ltp": ltp,
        "spread": spread,
        "spread_pct": spread_pct,
        "depth_min_qty": depth,
        "seconds_since_update": freshness,
        "event_to_entry_move": event_to_entry_move,
        "atm_distance_abs": dist_abs,
        "tradable_flag": bool(
            spread <= TRADABLE_SPREAD_ABS
            and spread_pct <= TRADABLE_SPREAD_PCT
            and depth >= TRADABLE_DEPTH
            and freshness <= TRADABLE_FRESHNESS
        ),
    }
    return score, meta


def response_metrics_from_path(path: pd.DataFrame, entry_price: float, target_points: Iterable[int] = (1, 2, 3, 5)) -> dict[str, Any]:
    ltp = path["ltp"].astype(float)
    max_ltp = float(ltp.max())
    min_ltp = float(ltp.min())
    mfe = max_ltp - entry_price
    mae = min_ltp - entry_price
    out: dict[str, Any] = {
        "max_ltp_after_entry_within_horizon": max_ltp,
        "min_ltp_after_entry_within_horizon": min_ltp,
        "mfe_points": mfe,
        "mae_points": mae,
    }
    for k in target_points:
        hit_mask = ltp >= entry_price + float(k)
        hit = bool(hit_mask.any())
        out[f"target_{k}_hit"] = hit
        if hit:
            first_ts = ltp.index[hit_mask.argmax()]
            out[f"time_to_plus_{k}"] = float((first_ts - path.index[0]).total_seconds())
        else:
            out[f"time_to_plus_{k}"] = np.nan
    minus2_mask = ltp <= entry_price - 2.0
    minus3_mask = ltp <= entry_price - 3.0
    plus3_mask = ltp >= entry_price + 3.0
    t_plus3 = ltp.index[plus3_mask.argmax()] if plus3_mask.any() else None
    t_minus2 = ltp.index[minus2_mask.argmax()] if minus2_mask.any() else None
    t_minus3 = ltp.index[minus3_mask.argmax()] if minus3_mask.any() else None
    out["harvest_3_before_minus2"] = bool(t_plus3 is not None and (t_minus2 is None or t_plus3 <= t_minus2))
    out["harvest_3_before_minus3"] = bool(t_plus3 is not None and (t_minus3 is None or t_plus3 <= t_minus3))
    return out


def build_option_response_rows_for_event(
    event: dict[str, Any],
    meta_df: pd.DataFrame,
    series_by_symbol: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    event_time = pd.Timestamp(event["event_time"])
    atm_strike = int(event["atm_strike"])
    side = "CALL" if event["direction"] == "UP" else "PUT"
    option_type = "CE" if side == "CALL" else "PE"
    candidates = meta_df[meta_df["option_type"] == option_type].copy()
    if candidates.empty:
        return rows
    candidates["atm_distance_abs"] = (candidates["strike"].astype(int) - atm_strike).abs()
    candidates = candidates[candidates["atm_distance_abs"] <= 200].copy()
    if candidates.empty:
        return rows
    candidates["atm_bucket"] = candidates["atm_distance_abs"].map(exact_bucket)
    candidates = candidates[candidates["atm_bucket"].isin(MAIN_BUCKETS)]
    for cand in candidates.to_dict(orient="records"):
        symbol = str(cand["symbol"])
        series = series_by_symbol.get(symbol)
        if series is None or event_time not in series.index:
            continue
        event_row = series.loc[event_time]
        event_ltp = safe_float(event_row.get("ltp"))
        if event_ltp is None or not np.isfinite(event_ltp):
            continue
        for lag in ENTRY_LAGS:
            entry_time = event_time + pd.Timedelta(seconds=lag)
            if entry_time not in series.index:
                continue
            entry_row = series.loc[entry_time]
            entry_ltp = safe_float(entry_row.get("ltp"))
            if entry_ltp is None or not np.isfinite(entry_ltp):
                continue
            spread_at_entry = safe_float(entry_row.get("spread"))
            spread_pct_at_entry = safe_float(entry_row.get("spread_pct"))
            depth_at_entry = safe_float(entry_row.get("depth_min_qty"))
            freshness = safe_float(entry_row.get("seconds_since_symbol_update"))
            update_count_5s = safe_float(entry_row.get("update_count_5s"))
            event_to_entry_move = entry_ltp - event_ltp
            rank_info = score_option_for_event(series, entry_time, int(cand["strike"]), atm_strike, event_ltp)
            entry_rank_score = rank_info[0] if rank_info is not None else np.nan
            for hold in HOLD_HORIZONS:
                exit_time = entry_time + pd.Timedelta(seconds=hold)
                if exit_time not in series.index:
                    continue
                path = series.loc[entry_time:exit_time]
                if path.empty:
                    continue
                metrics = response_metrics_from_path(path, entry_ltp)
                exit_ltp = safe_float(path.iloc[-1].get("ltp"))
                if exit_ltp is None:
                    continue
                rows.append(
                    {
                        "date": event["date"],
                        "event_id": event["event_id"],
                        "cooldown_mode": event["cooldown_mode"],
                        "event_time": event_time,
                        "impulse_type": event["impulse_type"],
                        "direction": event["direction"],
                        "option_symbol": symbol,
                        "option_type": option_type,
                        "strike": int(cand["strike"]),
                        "atm_strike": atm_strike,
                        "atm_distance_abs": int(cand["atm_distance_abs"]),
                        "atm_bucket": cand["atm_bucket"],
                        "entry_lag_seconds": lag,
                        "holding_horizon_seconds": hold,
                        "entry_time": entry_time,
                        "exit_time": exit_time,
                        "event_ltp": event_ltp,
                        "entry_ltp": entry_ltp,
                        "exit_ltp": exit_ltp,
                        "gross_points": exit_ltp - entry_ltp,
                        "spread_at_entry": spread_at_entry,
                        "spread_pct_at_entry": spread_pct_at_entry,
                        "depth_min_qty_at_entry": depth_at_entry,
                        "seconds_since_update_at_entry": freshness,
                        "update_count_5s_at_entry": update_count_5s,
                        "tradable_spread_depth_flag": bool(
                            spread_at_entry is not None and spread_at_entry <= TRADABLE_SPREAD_ABS
                            and spread_pct_at_entry is not None and spread_pct_at_entry <= TRADABLE_SPREAD_PCT
                            and depth_at_entry is not None and depth_at_entry >= TRADABLE_DEPTH
                            and freshness is not None and freshness <= TRADABLE_FRESHNESS
                        ),
                        "entry_rank_score": entry_rank_score,
                        "event_to_entry_move_points": event_to_entry_move,
                        "time_bucket": event["time_bucket"],
                        "underlying_realized_vol_1m": event.get("underlying_realized_vol_1m"),
                        "underlying_trend_score_5m": event.get("underlying_trend_score_5m"),
                        "premium_bucket": premium_bucket(entry_ltp),
                        "spread_bucket": spread_bucket(spread_pct_at_entry),
                        "depth_bucket": depth_bucket(depth_at_entry),
                        **metrics,
                    }
                )
    return rows


def compute_cross_correlation_rows(date: str, under_df: pd.DataFrame, meta_df: pd.DataFrame, series_by_symbol: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    under_ret = under_df["sensex_ltp"].diff().fillna(0.0)
    atm_series = under_df["sensex_ltp"].apply(round_to_strike)
    for side, option_type in [("CALL", "CE"), ("PUT", "PE")]:
        signed_under = under_ret if side == "CALL" else -under_ret
        agg: dict[str, pd.DataFrame] = {}
        for bucket in MAIN_BUCKETS:
            agg[bucket] = pd.DataFrame({"sum": np.zeros(len(under_df)), "count": np.zeros(len(under_df))}, index=under_df.index)
        meta_side = meta_df[meta_df["option_type"] == option_type]
        for rec in meta_side.to_dict(orient="records"):
            sym = str(rec["symbol"])
            strike = int(rec["strike"])
            series = series_by_symbol.get(sym)
            if series is None:
                continue
            ret = series["ltp"].astype(float).diff().fillna(0.0)
            dist = (strike - atm_series).abs()
            for bucket, want in [("ATM", 0), ("ATM_100", 100), ("ATM_200", 200)]:
                mask = dist == want
                if not mask.any():
                    continue
                agg[bucket].loc[mask, "sum"] += ret.loc[mask].to_numpy()
                agg[bucket].loc[mask, "count"] += 1.0
        for bucket, g in agg.items():
            count = g["count"]
            valid = count > 0
            if not valid.any():
                continue
            opt_ret = pd.Series(np.where(valid, g["sum"] / count.replace(0.0, np.nan), np.nan), index=g.index)
            for lag in range(-10, 11):
                shifted = opt_ret.shift(-lag)
                aligned = pd.concat([signed_under, shifted], axis=1, join="inner").dropna()
                if len(aligned) < 30:
                    corr = np.nan
                else:
                    corr = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
                rows.append(
                    {
                        "date": date,
                        "side": side,
                        "atm_bucket": bucket,
                        "lag_seconds": lag,
                        "correlation": corr,
                        "sample_count": int(len(aligned)),
                    }
                )
    return rows


def get_impulse_definition_map() -> dict[str, tuple[int, float]]:
    out: dict[str, tuple[int, float]] = {}
    for item in IMPULSE_DEFS:
        if item["name"] == "ACCEL_SPIKE":
            out[item["name"]] = (3, 20.0)
        else:
            out[item["name"]] = (int(item["horizon"]), float(item["threshold"]))
    return out


def pick_best_option_for_event(event: dict[str, Any], meta_df: pd.DataFrame, series_by_symbol: dict[str, pd.DataFrame], side_override: str | None = None) -> dict[str, Any] | None:
    event_time = pd.Timestamp(event["event_time"])
    atm_strike_value = event.get("atm_strike")
    if atm_strike_value is None or (isinstance(atm_strike_value, float) and not np.isfinite(atm_strike_value)):
        underlying_ltp = safe_float(event.get("underlying_ltp"))
        if underlying_ltp is None:
            return None
        atm_strike = round_to_strike(underlying_ltp)
    else:
        atm_strike = int(atm_strike_value)
    side = side_override or ("CALL" if event["direction"] == "UP" else "PUT")
    option_type = "CE" if side == "CALL" else "PE"
    candidates = meta_df[meta_df["option_type"] == option_type].copy()
    if candidates.empty:
        return None
    candidates["atm_distance_abs"] = (candidates["strike"].astype(int) - atm_strike).abs()
    candidates = candidates[candidates["atm_distance_abs"] <= 200].copy()
    if candidates.empty:
        return None
    scored: list[dict[str, Any]] = []
    for cand in candidates.to_dict(orient="records"):
        sym = str(cand["symbol"])
        series = series_by_symbol.get(sym)
        if series is None:
            continue
        scored_info = score_option_for_event(series, event_time, int(cand["strike"]), atm_strike)
        if scored_info is None:
            continue
        score, meta = scored_info
        scored.append({**cand, **meta, "rank_score": score, "option_symbol": sym, "side": side, "option_type": option_type})
    if not scored:
        return None
    scored.sort(key=lambda x: (x["rank_score"], -x["depth_min_qty"], -float(200 - x["atm_distance_abs"])), reverse=True)
    return scored[0]


def simulate_impulse_trade(series: pd.DataFrame, entry_time: pd.Timestamp, max_hold_seconds: int) -> dict[str, Any] | None:
    if entry_time not in series.index:
        return None
    entry_price = safe_float(series.loc[entry_time, "ltp"])
    if entry_price is None:
        return None
    window = series.loc[entry_time: entry_time + pd.Timedelta(seconds=max_hold_seconds)]
    if window.empty:
        return None
    runup = 0.0
    drawdown = 0.0
    exit_reason = None
    exit_time = entry_time
    exit_price = entry_price
    for now, row in window.iterrows():
        ltp = safe_float(row.get("ltp"))
        if ltp is None:
            continue
        pnl = ltp - entry_price
        runup = max(runup, pnl)
        drawdown = min(drawdown, pnl)
        if pnl >= TARGET_POINTS:
            exit_reason = "TARGET_HIT"
            exit_time = now
            exit_price = ltp
            break
        if pnl <= -STOP_POINTS:
            exit_reason = "STOP_HIT"
            exit_time = now
            exit_price = ltp
            break
    if exit_reason is None:
        last = window.iloc[-1]
        exit_reason = f"TIMEOUT_{max_hold_seconds}S"
        exit_time = window.index[-1]
        exit_price = float(last["ltp"])
    return {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "holding_seconds": float((exit_time - entry_time).total_seconds()),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "points_pnl": exit_price - entry_price,
        "gross_pnl": (exit_price - entry_price) * FIXED_QTY,
        "net_pnl": (exit_price - entry_price) * FIXED_QTY,
        "runup_points": runup,
        "drawdown_points": drawdown,
        "exit_reason": exit_reason,
        "quantity": FIXED_QTY,
        "quantity_source": "fixed_500",
    }


def build_candidate_trades_for_variant(
    events_df: pd.DataFrame,
    variant: TradeVariant,
    meta_df: pd.DataFrame,
    series_by_symbol: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    next_free_time: pd.Timestamp | None = None
    for event in events_df.sort_values("event_time").to_dict(orient="records"):
        event_time = pd.Timestamp(event["event_time"])
        if next_free_time is not None and event_time < next_free_time:
            continue
        choice = pick_best_option_for_event(event, meta_df, series_by_symbol)
        if choice is None:
            continue
        sym = str(choice["option_symbol"])
        series = series_by_symbol.get(sym)
        if series is None:
            continue
        entry_time = event_time + pd.Timedelta(seconds=variant.entry_lag_seconds)
        if entry_time not in series.index:
            continue
        event_ltp = safe_float(series.loc[event_time, "ltp"]) if event_time in series.index else None
        entry_ltp = safe_float(series.loc[entry_time, "ltp"])
        if entry_ltp is None:
            continue
        move_from_event = None if event_ltp is None else entry_ltp - event_ltp
        if variant.require_not_exhausted and move_from_event is not None and move_from_event > variant.exhaustion_limit:
            continue
        if variant.require_light_confirm:
            if move_from_event is None or move_from_event < 0.0 or move_from_event > 1.5:
                continue
        result = simulate_impulse_trade(series, entry_time, variant.max_hold_seconds)
        if result is None:
            continue
        trade = {
            **event,
            **choice,
            **result,
            "variant_name": variant.name,
            "atm_bucket": exact_bucket(int(choice["atm_distance_abs"])),
            "entry_lag_seconds": variant.entry_lag_seconds,
            "max_hold_seconds": variant.max_hold_seconds,
            "cooldown_seconds": variant.cooldown_seconds,
            "event_to_entry_move_points": move_from_event,
            "tradable_entry_flag": bool(
                choice["spread"] <= TRADABLE_SPREAD_ABS
                and choice["spread_pct"] <= TRADABLE_SPREAD_PCT
                and choice["depth_min_qty"] >= TRADABLE_DEPTH
                and choice["seconds_since_update"] <= TRADABLE_FRESHNESS
            ),
        }
        trades.append(trade)
        next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
    return trades


def summarize_trades(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (impulse_type, variant_name), g in trades_df.groupby(["impulse_type", "variant_name"]):
        ordered = g.sort_values("exit_time")
        eq = ordered["net_pnl"].cumsum()
        dd = eq - eq.cummax()
        wins = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"]
        losses = ordered.loc[ordered["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        rows.append(
            {
                "impulse_type": impulse_type,
                "variant_name": variant_name,
                "trades": int(len(g)),
                "active_days": int(g["date"].nunique()),
                "total_net_pnl": float(g["net_pnl"].sum()),
                "avg_pnl": float(g["net_pnl"].mean()),
                "win_rate": float((g["net_pnl"] > 0).mean()),
                "profit_factor": pf,
                "worst_day_pnl": float(g.groupby("date")["net_pnl"].sum().min()),
                "target_hit_rate": float((g["exit_reason"] == "TARGET_HIT").mean()),
                "avg_mfe": float(g["runup_points"].mean()),
                "avg_mae": float(g["drawdown_points"].mean()),
                "best_time_bucket": g.groupby("time_bucket")["net_pnl"].sum().sort_values(ascending=False).index[0],
                "best_strike_bucket": g.groupby("atm_bucket")["net_pnl"].sum().sort_values(ascending=False).index[0],
            }
        )
    return pd.DataFrame(rows).sort_values(["total_net_pnl", "profit_factor"], ascending=[False, False]).reset_index(drop=True)


def build_false_burst_noise(candidates_df: pd.DataFrame, event_lookup_3: dict[tuple[str, str], list[pd.Timestamp]], event_lookup_5: dict[tuple[str, str], list[pd.Timestamp]], series_cache_by_day: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    if candidates_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for rec in candidates_df.to_dict(orient="records"):
        date = str(rec["date"])
        ts = pd.Timestamp(rec["timestamp"])
        direction = "UP" if str(rec.get("side") or "").upper() == "CALL" else "DOWN"
        series = series_cache_by_day.get(date, {}).get(str(rec["symbol"]))
        hit3_5s = False
        tradable = False
        opposite_moving = False
        if series is not None and ts in series.index and ts + pd.Timedelta(seconds=5) in series.index:
            entry = safe_float(series.loc[ts, "ltp"]) or 0.0
            path = series.loc[ts: ts + pd.Timedelta(seconds=5)]
            hit3_5s = bool((path["ltp"].astype(float) >= entry + 3.0).any())
        spread_pct = safe_float(rec.get("spread_pct_now")) or safe_float(rec.get("spread_pct"))
        depth = safe_float(rec.get("depth_min_qty"))
        fresh = safe_float(rec.get("seconds_since_symbol_update"))
        tradable = bool(
            (safe_float(rec.get("spread_now")) or safe_float(rec.get("spread")) or 999) <= TRADABLE_SPREAD_ABS
            and spread_pct is not None and spread_pct <= TRADABLE_SPREAD_PCT
            and depth is not None and depth >= TRADABLE_DEPTH
            and fresh is not None and fresh <= TRADABLE_FRESHNESS
        )
        opposite_score = safe_float(rec.get("opposite_side_max_raw_score"))
        opposite_moving = bool(opposite_score is not None and opposite_score >= 5)
        has_3 = has_recent_impulse(event_lookup_3, date, direction, ts, 3)
        has_5 = has_recent_impulse(event_lookup_5, date, direction, ts, 5)
        cls = (
            "impulse_present_harvestable" if has_3 and hit3_5s else
            "impulse_present_not_harvestable" if has_3 else
            "no_impulse_harvestable" if hit3_5s else
            "no_impulse_not_harvestable"
        )
        rows.append(
            {
                "date": date,
                "atm_bucket": rec.get("atm_bucket"),
                "time_bucket": rec.get("time_bucket"),
                "premium_bucket": premium_bucket(safe_float(rec.get("ltp"))),
                "spread_bucket": spread_bucket(spread_pct),
                "class_label": cls,
                "candidate_count": 1,
                "impulse_present_0_3s": has_3,
                "impulse_present_0_5s": has_5,
                "harvestable_3pt_5s": hit3_5s,
                "tradable_flag": tradable,
                "opposite_side_moving": opposite_moving,
                "likely_underlying_led": bool(has_3 and not opposite_moving),
                "likely_option_noise_led": bool((not has_5) or opposite_moving),
            }
        )
    detail = pd.DataFrame(rows)
    grouped: list[dict[str, Any]] = []
    group_specs = [
        ("overall", None),
        ("atm_bucket", "atm_bucket"),
        ("time_bucket", "time_bucket"),
        ("premium_bucket", "premium_bucket"),
        ("spread_bucket", "spread_bucket"),
    ]
    for dim_name, col in group_specs:
        if col is None:
            g = detail.groupby("class_label")
            for cls, part in g:
                grouped.append(
                    {
                        "group_dimension": dim_name,
                        "group_value": "all",
                        "class_label": cls,
                        "count": int(len(part)),
                        "tradable_rate": float(part["tradable_flag"].mean()),
                        "opposite_side_moving_rate": float(part["opposite_side_moving"].mean()),
                        "underlying_led_rate": float(part["likely_underlying_led"].mean()),
                        "noise_led_rate": float(part["likely_option_noise_led"].mean()),
                    }
                )
        else:
            for (group_value, cls), part in detail.groupby([col, "class_label"]):
                grouped.append(
                    {
                        "group_dimension": dim_name,
                        "group_value": group_value,
                        "class_label": cls,
                        "count": int(len(part)),
                        "tradable_rate": float(part["tradable_flag"].mean()),
                        "opposite_side_moving_rate": float(part["opposite_side_moving"].mean()),
                        "underlying_led_rate": float(part["likely_underlying_led"].mean()),
                        "noise_led_rate": float(part["likely_option_noise_led"].mean()),
                    }
                )
    return pd.DataFrame(grouped)


def build_harvest_summary(event_df: pd.DataFrame) -> pd.DataFrame:
    if event_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    group_cols = [
        "date", "impulse_type", "entry_lag_seconds", "holding_horizon_seconds", "atm_bucket", "option_type", "time_bucket", "spread_bucket", "depth_bucket"
    ]
    for keys, g in event_df.groupby(group_cols):
        row = dict(zip(group_cols, keys))
        tradable = g[g["tradable_spread_depth_flag"]]
        wins = g["gross_points"]
        row.update(
            {
                "events": int(len(g)),
                "tradable_events": int(len(tradable)),
                "avg_mfe": float(g["mfe_points"].mean()),
                "median_mfe": float(g["mfe_points"].median()),
                "p25_mfe": float(g["mfe_points"].quantile(0.25)),
                "p75_mfe": float(g["mfe_points"].quantile(0.75)),
                "avg_mae": float(g["mae_points"].mean()),
                "median_mae": float(g["mae_points"].median()),
                "harvest_1pt_rate": float(g["target_1_hit"].mean()),
                "harvest_2pt_rate": float(g["target_2_hit"].mean()),
                "harvest_3pt_rate": float(g["target_3_hit"].mean()),
                "harvest_5pt_rate": float(g["target_5_hit"].mean()),
                "harvest_3_before_minus2_rate": float(g["harvest_3_before_minus2"].mean()),
                "harvest_3_before_minus3_rate": float(g["harvest_3_before_minus3"].mean()),
                "avg_net_mfe_cost_0_25": float((g["mfe_points"] - 0.25).mean()),
                "avg_net_mfe_cost_0_50": float((g["mfe_points"] - 0.50).mean()),
                "avg_net_mfe_cost_1_00": float((g["mfe_points"] - 1.00).mean()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def build_threshold_grid(event_df: pd.DataFrame) -> pd.DataFrame:
    if event_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    impulse_map = get_impulse_definition_map()
    candidate = event_df.copy()
    candidate = candidate[candidate["cooldown_mode"] == MAIN_EVENT_COOLDOWN].copy()
    candidate = candidate[candidate["holding_horizon_seconds"].isin([3, 5, 10])].copy()
    candidate = candidate[candidate["entry_lag_seconds"].isin(ENTRY_LAGS)].copy()
    for impulse_type, (horizon, threshold) in impulse_map.items():
        if impulse_type not in candidate["impulse_type"].unique():
            continue
        base = candidate[candidate["impulse_type"] == impulse_type].copy()
        for bucket in MAIN_BUCKETS:
            bucket_df = base[base["atm_bucket"] == bucket].copy()
            if bucket_df.empty:
                continue
            for lag in ENTRY_LAGS:
                for hold in [3, 5, 10]:
                    sub = bucket_df[(bucket_df["entry_lag_seconds"] == lag) & (bucket_df["holding_horizon_seconds"] == hold)].copy()
                    if sub.empty:
                        continue
                    for spread_pct_thresh in [0.005, 0.010, 0.015]:
                        for depth_thresh in [250, 500]:
                            filt = sub[
                                (sub["spread_pct_at_entry"].astype(float) <= spread_pct_thresh)
                                & (sub["depth_min_qty_at_entry"].astype(float) >= depth_thresh)
                            ].copy()
                            if filt.empty:
                                continue
                            best = filt.sort_values(["event_id", "entry_rank_score"], ascending=[True, False]).groupby("event_id", as_index=False, group_keys=False).head(1)
                            day_exp = (best["gross_points"] - 0.5).groupby(best["date"]).mean()
                            rows.append(
                                {
                                    "impulse_type": impulse_type,
                                    "impulse_horizon_seconds": horizon,
                                    "underlying_threshold_points": threshold,
                                    "entry_lag_seconds": lag,
                                    "strike_bucket": bucket,
                                    "max_hold_seconds": hold,
                                    "spread_pct_threshold": spread_pct_thresh,
                                    "depth_threshold": depth_thresh,
                                    "event_count": int(best["event_id"].nunique()),
                                    "tradable_event_count": int(len(best)),
                                    "harvest_3pt_rate": float(best["target_3_hit"].mean()),
                                    "avg_mfe": float(best["mfe_points"].mean()),
                                    "avg_mae": float(best["mae_points"].mean()),
                                    "net_expectancy_after_0_5_cost": float((best["gross_points"] - 0.5).mean()),
                                    "worst_day_expectancy": float(day_exp.min()) if not day_exp.empty else np.nan,
                                }
                            )
    return pd.DataFrame(rows).sort_values(["net_expectancy_after_0_5_cost", "harvest_3pt_rate"], ascending=[False, False]).reset_index(drop=True)


def build_time_bucket_summary(filtered_event_df: pd.DataFrame, trades_df: pd.DataFrame, best_variant_name: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bucket, g in filtered_event_df.groupby("time_bucket"):
        trade_g = trades_df[(trades_df["variant_name"] == best_variant_name) & (trades_df["time_bucket"] == bucket)]
        wins = trade_g.loc[trade_g["net_pnl"] > 0, "net_pnl"]
        losses = trade_g.loc[trade_g["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        day_pnl = trade_g.groupby("date")["net_pnl"].sum() if not trade_g.empty else pd.Series(dtype=float)
        rows.append(
            {
                "time_bucket": bucket,
                "impulse_count": int(g["event_id"].nunique()),
                "tradable_event_count": int(g[g["tradable_spread_depth_flag"]]["event_id"].nunique()),
                "harvest_3pt_rate": float(g["target_3_hit"].mean()),
                "avg_mfe": float(g["mfe_points"].mean()),
                "avg_mae": float(g["mae_points"].mean()),
                "candidate_trade_count": int(len(trade_g)),
                "candidate_trade_net_pnl": float(trade_g["net_pnl"].sum()) if not trade_g.empty else 0.0,
                "candidate_trade_profit_factor": pf,
                "candidate_trade_worst_day": float(day_pnl.min()) if not day_pnl.empty else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("candidate_trade_net_pnl", ascending=False)


def build_strike_distance_summary(filtered_event_df: pd.DataFrame, trades_df: pd.DataFrame, best_variant_name: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bucket, g in filtered_event_df.groupby("atm_bucket"):
        trade_g = trades_df[(trades_df["variant_name"] == best_variant_name) & (trades_df["atm_bucket"] == bucket)]
        rows.append(
            {
                "atm_bucket": bucket,
                "event_count": int(g["event_id"].nunique()),
                "tradable_event_count": int(g[g["tradable_spread_depth_flag"]]["event_id"].nunique()),
                "avg_mfe": float(g["mfe_points"].mean()),
                "median_mfe": float(g["mfe_points"].median()),
                "harvest_3pt_rate": float(g["target_3_hit"].mean()),
                "harvest_5pt_rate": float(g["target_5_hit"].mean()),
                "avg_mae": float(g["mae_points"].mean()),
                "net_edge_after_0_5_cost": float((g["mfe_points"] - 0.5).mean()),
                "candidate_trade_expectancy": float(trade_g["net_pnl"].mean()) if not trade_g.empty else np.nan,
                "candidate_trade_count": int(len(trade_g)),
                "candidate_trade_net_pnl": float(trade_g["net_pnl"].sum()) if not trade_g.empty else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("candidate_trade_net_pnl", ascending=False)


def build_regime_summary(filtered_event_df: pd.DataFrame, trades_df: pd.DataFrame, best_variant_name: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if filtered_event_df.empty:
        return pd.DataFrame()
    event_df = filtered_event_df.copy()

    regime_dims: list[str] = []
    if "underlying_realized_vol_1m" in event_df.columns:
        event_vol_median = float(event_df["underlying_realized_vol_1m"].median())
        event_df["event_vol_regime"] = np.where(event_df["underlying_realized_vol_1m"] >= event_vol_median, "high_vol", "low_vol")
        regime_dims.append("event_vol_regime")
    if "spread_pct_at_entry" in event_df.columns:
        spread_median = float(event_df["spread_pct_at_entry"].median())
        event_df["spread_regime"] = np.where(event_df["spread_pct_at_entry"] <= spread_median, "tight_spread", "wide_spread")
        regime_dims.append("spread_regime")
    if "depth_min_qty_at_entry" in event_df.columns:
        depth_median = float(event_df["depth_min_qty_at_entry"].median())
        event_df["depth_regime"] = np.where(event_df["depth_min_qty_at_entry"] >= depth_median, "high_depth", "low_depth")
        regime_dims.append("depth_regime")

    day_counts = event_df.groupby("date")["event_id"].nunique()
    density_median = float(day_counts.median()) if not day_counts.empty else 0.0
    date_density = pd.DataFrame({"date": day_counts.index, "impulse_density_regime": np.where(day_counts.values >= density_median, "high_density", "low_density")})
    event_df = event_df.merge(date_density, on="date", how="left")
    if "trend_regime" in event_df.columns:
        regime_dims.insert(1, "trend_regime")
    regime_dims.insert(0, "impulse_density_regime")

    for dim in regime_dims:
        for value, g in event_df.groupby(dim):
            trade_g = trades_df[(trades_df["variant_name"] == best_variant_name) & (trades_df["date"].isin(g["date"].unique()))]
            lag_group = g.groupby("entry_lag_seconds")["mfe_points"].mean().sort_values(ascending=False)
            bucket_group = g.groupby("atm_bucket")["mfe_points"].mean().sort_values(ascending=False)
            wins = trade_g.loc[trade_g["net_pnl"] > 0, "net_pnl"]
            losses = trade_g.loc[trade_g["net_pnl"] < 0, "net_pnl"]
            pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
            rows.append(
                {
                    "regime_dimension": dim,
                    "regime_value": value,
                    "impulse_events": int(g["event_id"].nunique()),
                    "tradable_event_count": int(g[g["tradable_spread_depth_flag"]]["event_id"].nunique()),
                    "harvest_3pt_rate": float(g["target_3_hit"].mean()),
                    "avg_mfe": float(g["mfe_points"].mean()),
                    "avg_mae": float(g["mae_points"].mean()),
                    "candidate_trade_expectancy": float(trade_g["net_pnl"].mean()) if not trade_g.empty else np.nan,
                    "candidate_trade_net_pnl": float(trade_g["net_pnl"].sum()) if not trade_g.empty else 0.0,
                    "candidate_trade_profit_factor": pf,
                    "best_entry_lag": int(lag_group.index[0]) if not lag_group.empty else np.nan,
                    "best_strike_bucket": str(bucket_group.index[0]) if not bucket_group.empty else None,
                }
            )
    return pd.DataFrame(rows)


def pick_best_grid_row(grid_df: pd.DataFrame) -> pd.Series | None:
    if grid_df.empty:
        return None
    viable = grid_df[(grid_df["tradable_event_count"] >= 20)].copy()
    if viable.empty:
        viable = grid_df.copy()
    viable = viable.sort_values(["net_expectancy_after_0_5_cost", "harvest_3pt_rate", "tradable_event_count"], ascending=[False, False, False])
    return viable.iloc[0]


def build_null_model_comparison(
    best_variant_row: pd.Series | None,
    real_trade_summary: pd.DataFrame,
    impulse_events_cd10: pd.DataFrame,
    meta_by_day: dict[str, pd.DataFrame],
    series_by_day: dict[str, dict[str, pd.DataFrame]],
    under_by_day: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if best_variant_row is None:
        return pd.DataFrame()
    impulse_type = str(best_variant_row["impulse_type"])
    variant_name = str(best_variant_row["variant_name"])
    variant = next(v for v in TRADE_VARIANTS if v.name == variant_name)
    real_events = impulse_events_cd10[impulse_events_cd10["impulse_type"] == impulse_type].copy()
    real_trades = real_trade_summary[(real_trade_summary["impulse_type"] == impulse_type) & (real_trade_summary["variant_name"] == variant_name)]
    rows: list[dict[str, Any]] = []
    if not real_trades.empty:
        rt = real_trades.iloc[0]
        rows.append({
            "control_type": "real",
            "sample_id": "real",
            "impulse_type": impulse_type,
            "variant_name": variant_name,
            "trades": int(rt["trades"]),
            "total_net_pnl": float(rt["total_net_pnl"]),
            "win_rate": float(rt["win_rate"]),
            "profit_factor": float(rt["profit_factor"]),
            "avg_mfe": float(rt["avg_mfe"]),
            "avg_mae": float(rt["avg_mae"]),
            "harvest_3pt_rate": float(rt["target_hit_rate"]),
        })
    if real_events.empty:
        return pd.DataFrame(rows)

    def summarize_control(name: str, sample_id: str, trades: pd.DataFrame) -> None:
        wins = trades.loc[trades["net_pnl"] > 0, "net_pnl"]
        losses = trades.loc[trades["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        rows.append(
            {
                "control_type": name,
                "sample_id": sample_id,
                "impulse_type": impulse_type,
                "variant_name": variant_name,
                "trades": int(len(trades)),
                "total_net_pnl": float(trades["net_pnl"].sum()) if not trades.empty else 0.0,
                "win_rate": float((trades["net_pnl"] > 0).mean()) if not trades.empty else np.nan,
                "profit_factor": pf,
                "avg_mfe": float(trades["runup_points"].mean()) if not trades.empty else np.nan,
                "avg_mae": float(trades["drawdown_points"].mean()) if not trades.empty else np.nan,
                "harvest_3pt_rate": float((trades["exit_reason"] == "TARGET_HIT").mean()) if not trades.empty else np.nan,
            }
        )

    # Opposite-side control
    opp_parts: list[pd.DataFrame] = []
    for date, g in real_events.groupby("date"):
        meta_df = meta_by_day[date]
        series_day = series_by_day[date]
        opposite_rows = []
        next_free_time: pd.Timestamp | None = None
        for event in g.sort_values("event_time").to_dict(orient="records"):
            ts = pd.Timestamp(event["event_time"])
            if next_free_time is not None and ts < next_free_time:
                continue
            other_side = "PUT" if event["direction"] == "UP" else "CALL"
            choice = pick_best_option_for_event(event, meta_df, series_day, side_override=other_side)
            if choice is None:
                continue
            series = series_day.get(str(choice["option_symbol"]))
            if series is None:
                continue
            entry_time = ts + pd.Timedelta(seconds=variant.entry_lag_seconds)
            if entry_time not in series.index:
                continue
            result = simulate_impulse_trade(series, entry_time, variant.max_hold_seconds)
            if result is None:
                continue
            opposite_rows.append({**event, **choice, **result})
            next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
        if opposite_rows:
            opp_parts.append(pd.DataFrame(opposite_rows))
    summarize_control("opposite_side", "deterministic", pd.concat(opp_parts, ignore_index=True) if opp_parts else pd.DataFrame())

    # Wrong-lag control: use same side but 1s before event
    wrong_parts: list[pd.DataFrame] = []
    for date, g in real_events.groupby("date"):
        meta_df = meta_by_day[date]
        series_day = series_by_day[date]
        rows_local = []
        next_free_time: pd.Timestamp | None = None
        for event in g.sort_values("event_time").to_dict(orient="records"):
            ts = pd.Timestamp(event["event_time"]) - pd.Timedelta(seconds=1)
            if next_free_time is not None and ts < next_free_time:
                continue
            shifted = dict(event)
            shifted["event_time"] = ts
            choice = pick_best_option_for_event(shifted, meta_df, series_day)
            if choice is None:
                continue
            series = series_day.get(str(choice["option_symbol"]))
            if series is None:
                continue
            entry_time = ts + pd.Timedelta(seconds=variant.entry_lag_seconds)
            if entry_time not in series.index:
                continue
            result = simulate_impulse_trade(series, entry_time, variant.max_hold_seconds)
            if result is None:
                continue
            rows_local.append({**shifted, **choice, **result})
            next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
        if rows_local:
            wrong_parts.append(pd.DataFrame(rows_local))
    summarize_control("wrong_lag_pre_event", "deterministic", pd.concat(wrong_parts, ignore_index=True) if wrong_parts else pd.DataFrame())

    # Random event times with same bucket distribution
    by_date_bucket: dict[tuple[str, str], list[pd.Timestamp]] = {}
    for date, under_df in under_by_day.items():
        for bucket, part in under_df.groupby("time_bucket"):
            by_date_bucket[(date, bucket)] = list(part.index)
    for seed in RANDOM_CONTROL_SEEDS:
        rnd = random.Random(seed)
        parts: list[pd.DataFrame] = []
        for date, g in real_events.groupby("date"):
            meta_df = meta_by_day[date]
            series_day = series_by_day[date]
            sample_events: list[dict[str, Any]] = []
            for ev in g.to_dict(orient="records"):
                pool = by_date_bucket.get((date, str(ev["time_bucket"])), [])
                if not pool:
                    continue
                sample_ts = rnd.choice(pool)
                new_ev = dict(ev)
                new_ev["event_time"] = sample_ts
                new_ev["event_id"] = f"rand|{seed}|{date}|{sample_ts.isoformat()}|{ev['direction']}|{impulse_type}"
                sample_events.append(new_ev)
            local_rows = []
            next_free_time: pd.Timestamp | None = None
            for event in sorted(sample_events, key=lambda x: x["event_time"]):
                ts = pd.Timestamp(event["event_time"])
                if next_free_time is not None and ts < next_free_time:
                    continue
                choice = pick_best_option_for_event(event, meta_df, series_day)
                if choice is None:
                    continue
                series = series_day.get(str(choice["option_symbol"]))
                if series is None:
                    continue
                entry_time = ts + pd.Timedelta(seconds=variant.entry_lag_seconds)
                if entry_time not in series.index:
                    continue
                result = simulate_impulse_trade(series, entry_time, variant.max_hold_seconds)
                if result is None:
                    continue
                local_rows.append({**event, **choice, **result})
                next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
            if local_rows:
                parts.append(pd.DataFrame(local_rows))
        summarize_control("random_event_times", str(seed), pd.concat(parts, ignore_index=True) if parts else pd.DataFrame())

    # Shuffled-day control: shift to next available day at same clock time
    dates_sorted = sorted(real_events["date"].unique().tolist())
    next_day = {dates_sorted[i]: dates_sorted[(i + 1) % len(dates_sorted)] for i in range(len(dates_sorted))}
    shuffle_parts: list[pd.DataFrame] = []
    for date, g in real_events.groupby("date"):
        target_date = next_day.get(date)
        if target_date is None or target_date not in meta_by_day:
            continue
        meta_df = meta_by_day[target_date]
        series_day = series_by_day[target_date]
        local_rows = []
        next_free_time: pd.Timestamp | None = None
        for event in g.sort_values("event_time").to_dict(orient="records"):
            clock = pd.Timestamp(event["event_time"]).time()
            shifted_ts = pd.Timestamp(f"{target_date} {clock}")
            shifted = dict(event)
            shifted["date"] = target_date
            shifted["event_time"] = shifted_ts
            shifted["event_id"] = f"shuf|{target_date}|{clock}|{event['direction']}|{impulse_type}"
            if next_free_time is not None and shifted_ts < next_free_time:
                continue
            choice = pick_best_option_for_event(shifted, meta_df, series_day)
            if choice is None:
                continue
            series = series_day.get(str(choice["option_symbol"]))
            if series is None:
                continue
            entry_time = shifted_ts + pd.Timedelta(seconds=variant.entry_lag_seconds)
            if entry_time not in series.index:
                continue
            result = simulate_impulse_trade(series, entry_time, variant.max_hold_seconds)
            if result is None:
                continue
            local_rows.append({**shifted, **choice, **result})
            next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
        if local_rows:
            shuffle_parts.append(pd.DataFrame(local_rows))
    summarize_control("shuffled_day", "cyclic_next_day", pd.concat(shuffle_parts, ignore_index=True) if shuffle_parts else pd.DataFrame())

    return pd.DataFrame(rows)


def save_charts(lag_summary: pd.DataFrame, cross_corr_df: pd.DataFrame, time_bucket_df: pd.DataFrame, strike_df: pd.DataFrame) -> list[Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if not lag_summary.empty:
        plot = lag_summary.groupby(["entry_lag_seconds", "holding_horizon_seconds"]).agg(avg_mfe=("avg_mfe", "mean"), median_h3=("harvest_3pt_rate", "median")).reset_index()
        pivot = plot.pivot(index="holding_horizon_seconds", columns="entry_lag_seconds", values="avg_mfe")
        p = CHARTS_DIR / "avg_option_response_after_underlying_impulse.png"
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(pivot.values, aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(pivot.columns)), labels=list(pivot.columns))
        ax.set_yticks(range(len(pivot.index)), labels=list(pivot.index))
        ax.set_xlabel("Entry lag (s)")
        ax.set_ylabel("Holding horizon (s)")
        ax.set_title("Average MFE After Underlying Impulse")
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)

        p2 = CHARTS_DIR / "median_option_response_after_underlying_impulse.png"
        pivot2 = plot.pivot(index="holding_horizon_seconds", columns="entry_lag_seconds", values="median_h3")
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(pivot2.values, aspect="auto", cmap="magma")
        ax.set_xticks(range(len(pivot2.columns)), labels=list(pivot2.columns))
        ax.set_yticks(range(len(pivot2.index)), labels=list(pivot2.index))
        ax.set_xlabel("Entry lag (s)")
        ax.set_ylabel("Holding horizon (s)")
        ax.set_title("Median Harvest-3 Rate")
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        fig.savefig(p2, dpi=160)
        plt.close(fig)
        paths.append(p2)

        p3 = CHARTS_DIR / "response_distribution_by_lag.png"
        dist = lag_summary.groupby("entry_lag_seconds").agg(h3=("harvest_3pt_rate", "mean")).reset_index()
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(dist["entry_lag_seconds"].astype(str), dist["h3"], color="#1f77b4")
        ax.set_title("Harvest-3 Rate by Entry Lag")
        fig.tight_layout()
        fig.savefig(p3, dpi=160)
        plt.close(fig)
        paths.append(p3)

        p4 = CHARTS_DIR / "harvestability_heatmap.png"
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(pivot2.values, aspect="auto", cmap="plasma")
        ax.set_xticks(range(len(pivot2.columns)), labels=list(pivot2.columns))
        ax.set_yticks(range(len(pivot2.index)), labels=list(pivot2.index))
        ax.set_xlabel("Entry lag (s)")
        ax.set_ylabel("Holding horizon (s)")
        ax.set_title("Harvestability Heatmap (Target 3 Rate)")
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        fig.savefig(p4, dpi=160)
        plt.close(fig)
        paths.append(p4)
    if not time_bucket_df.empty:
        p = CHARTS_DIR / "time_bucket_edge.png"
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(time_bucket_df["time_bucket"], time_bucket_df["candidate_trade_net_pnl"], color="#2ca02c")
        ax.axhline(0, color="#333", lw=1)
        ax.tick_params(axis="x", rotation=30)
        ax.set_title("Candidate Trade PnL by Time Bucket")
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not strike_df.empty:
        p = CHARTS_DIR / "strike_distance_edge.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(strike_df["atm_bucket"], strike_df["candidate_trade_net_pnl"], color="#ff7f0e")
        ax.axhline(0, color="#333", lw=1)
        ax.set_title("Candidate Trade PnL by Strike Distance")
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not cross_corr_df.empty:
        p = CHARTS_DIR / "lead_lag_cross_correlation.png"
        avg = cross_corr_df.groupby(["lag_seconds"]).agg(correlation=("correlation", "mean")).reset_index()
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(avg["lag_seconds"], avg["correlation"], marker="o")
        ax.axhline(0, color="#333", lw=1)
        ax.axvline(0, color="#999", lw=1, linestyle="--")
        ax.set_title("Average Lead-Lag Cross Correlation")
        ax.set_xlabel("Lag seconds (positive = option after underlying)")
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    return paths


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "(no data)"
    use = df.head(max_rows).copy()
    cols = list(use.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in use.iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                if math.isnan(value):
                    vals.append("")
                else:
                    vals.append(f"{value:.3f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def build_report(
    usable_dates: list[str],
    day_stats_df: pd.DataFrame,
    events_df: pd.DataFrame,
    lag_summary_df: pd.DataFrame,
    cross_corr_df: pd.DataFrame,
    strike_df: pd.DataFrame,
    time_bucket_df: pd.DataFrame,
    regime_df: pd.DataFrame,
    threshold_grid_df: pd.DataFrame,
    false_noise_df: pd.DataFrame,
    trade_summary_df: pd.DataFrame,
    null_df: pd.DataFrame,
    charts: list[Path],
) -> tuple[str, str]:
    lines: list[str] = []
    lines.append("# Convexity / Lead-Lag Feasibility Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Full-tape dates analyzed: **{', '.join(usable_dates)}**.")
    lines.append(f"- Underlying impulse events (all cooldown sets): **{int(len(events_df)) if not events_df.empty else 0}**.")
    best_grid = pick_best_grid_row(threshold_grid_df)
    best_trade = trade_summary_df.sort_values(["total_net_pnl", "profit_factor"], ascending=[False, False]).iloc[0] if not trade_summary_df.empty else None
    peak_corr = None
    if not cross_corr_df.empty:
        valid_corr = cross_corr_df.dropna(subset=["correlation"]).copy()
        if not valid_corr.empty:
            peak_corr = valid_corr.loc[valid_corr["correlation"].abs().idxmax()]
    if best_grid is not None:
        lines.append(
            f"- Best impulse grid cell: **{best_grid['impulse_type']}**, lag **{int(best_grid['entry_lag_seconds'])}s**, bucket **{best_grid['strike_bucket']}**, hold **{int(best_grid['max_hold_seconds'])}s**; "
            f"harvest-3 rate **{float(best_grid['harvest_3pt_rate']):.1%}**, net expectancy after 0.5 cost **{float(best_grid['net_expectancy_after_0_5_cost']):.2f} pts**."
        )
    if best_trade is not None:
        lines.append(
            f"- Best direct candidate trade variant: **{best_trade['variant_name']}** on **{best_trade['impulse_type']}**, total PnL **{float(best_trade['total_net_pnl']):,.0f}**, "
            f"PF **{float(best_trade['profit_factor']):.2f}**, trades **{int(best_trade['trades'])}**."
        )
    if peak_corr is not None:
        lines.append(
            f"- Peak lead-lag correlation: bucket **{peak_corr['atm_bucket']}**, side **{peak_corr['side']}**, lag **{int(peak_corr['lag_seconds'])}s**, corr **{float(peak_corr['correlation']):.3f}**."
        )
    lines.append("")
    lines.append("## Data Coverage")
    lines.append(markdown_table(day_stats_df, max_rows=20))
    lines.append("")
    lines.append("## Best Grid Cells")
    lines.append(markdown_table(threshold_grid_df, max_rows=20))
    lines.append("")
    lines.append("## Candidate Trade Summary")
    lines.append(markdown_table(trade_summary_df, max_rows=20))
    lines.append("")
    lines.append("## Time Bucket")
    lines.append(markdown_table(time_bucket_df, max_rows=20))
    lines.append("")
    lines.append("## Strike Distance")
    lines.append(markdown_table(strike_df, max_rows=20))
    lines.append("")
    lines.append("## Regime")
    lines.append(markdown_table(regime_df, max_rows=40))
    lines.append("")
    lines.append("## Null Controls")
    lines.append(markdown_table(null_df, max_rows=40))
    lines.append("")
    lines.append("## False Burst / Noise")
    lines.append(markdown_table(false_noise_df, max_rows=40))
    lines.append("")

    verdict = "DATA INSUFFICIENT"
    rand_mean = opp_pnl = wrong_pnl = shuffled_pnl = np.nan
    beats_random_opp = beats_all_controls = False
    if len(usable_dates) >= 4 and best_grid is not None and best_trade is not None:
        real_null = null_df[null_df["control_type"] == "real"] if not null_df.empty else pd.DataFrame()
        rand_null = null_df[null_df["control_type"] == "random_event_times"] if not null_df.empty else pd.DataFrame()
        opp_null = null_df[null_df["control_type"] == "opposite_side"] if not null_df.empty else pd.DataFrame()
        wrong_null = null_df[null_df["control_type"] == "wrong_lag_pre_event"] if not null_df.empty else pd.DataFrame()
        shuffled_null = null_df[null_df["control_type"] == "shuffled_day"] if not null_df.empty else pd.DataFrame()
        rand_mean = float(rand_null["total_net_pnl"].mean()) if not rand_null.empty else np.nan
        opp_pnl = float(opp_null["total_net_pnl"].mean()) if not opp_null.empty else np.nan
        wrong_pnl = float(wrong_null["total_net_pnl"].mean()) if not wrong_null.empty else np.nan
        shuffled_pnl = float(shuffled_null["total_net_pnl"].mean()) if not shuffled_null.empty else np.nan
        real_pnl = float(best_trade["total_net_pnl"])
        trade_positive_multi = bool(float(best_trade["total_net_pnl"]) > 0 and int(best_trade["active_days"]) >= 2)
        grid_positive = bool(float(best_grid["net_expectancy_after_0_5_cost"]) > 0 and float(best_grid["harvest_3pt_rate"]) >= 0.45)
        beats_random_opp = bool(
            trade_positive_multi
            and (np.isnan(rand_mean) or real_pnl > rand_mean)
            and (np.isnan(opp_pnl) or real_pnl > opp_pnl)
        )
        beats_all_controls = bool(
            beats_random_opp
            and (np.isnan(wrong_pnl) or real_pnl > wrong_pnl)
            and (np.isnan(shuffled_pnl) or real_pnl > shuffled_pnl)
        )
        if trade_positive_multi and grid_positive and beats_all_controls and float(best_trade["profit_factor"]) > 1.2:
            verdict = "FEASIBLE"
        elif grid_positive or (trade_positive_multi and beats_random_opp):
            verdict = "WEAK"
        else:
            verdict = "NOT FOUND"
    elif len(usable_dates) > 0:
        verdict = "DATA INSUFFICIENT"

    lines.append("## Direct Answers")
    if peak_corr is not None:
        lag_note = int(peak_corr["lag_seconds"])
        if lag_note > 0:
            lag_text = "positive lag, so option follows underlying"
        elif lag_note == 0:
            lag_text = "zero lag, so response is mostly simultaneous"
        else:
            lag_text = "negative lag, so option appears to lead or timestamps are not cleanly lagged"
        lines.append(f"- **Does option premium lag underlying movement in a measurable way?** Peak observed correlation was at `{lag_note}s`, which implies {lag_text}.")
    else:
        lines.append("- **Does option premium lag underlying movement in a measurable way?** Not established from the cross-correlation sample.")
    if best_grid is not None:
        lines.append(f"- **Is the lag stable enough to trade?** Best grid cell used lag `{int(best_grid['entry_lag_seconds'])}s` and hold `{int(best_grid['max_hold_seconds'])}s`, with net expectancy after 0.5 cost `{float(best_grid['net_expectancy_after_0_5_cost']):.2f}` points.")
        lines.append(f"- **How often does option premium move +3 after a sudden underlying impulse?** Best observed harvest-3 rate was `{float(best_grid['harvest_3pt_rate']):.1%}` in `{best_grid['strike_bucket']}` for `{best_grid['impulse_type']}`.")
        lines.append(f"- **What entry lag is best?** `{int(best_grid['entry_lag_seconds'])}s` in the best-performing grid cell.")
        lines.append(f"- **Which strike distance is best?** `{best_grid['strike_bucket']}` in the best-performing grid cell.")
    if not time_bucket_df.empty:
        best_time = time_bucket_df.sort_values("candidate_trade_net_pnl", ascending=False).iloc[0]
        lines.append(f"- **Which time bucket is best?** `{best_time['time_bucket']}` by candidate-trade PnL.")
    if not regime_df.empty:
        best_regime = regime_df.sort_values("candidate_trade_net_pnl", ascending=False).iloc[0]
        lines.append(f"- **Which regime is best?** `{best_regime['regime_dimension']}={best_regime['regime_value']}` had the strongest candidate-trade PnL.")
    lines.append("- **Is raw burst score capturing the phenomenon or just movement/noise?** See the false-burst table: if the `no_impulse_not_harvestable` class dominates, raw burst is mostly movement/noise; if `impulse_present_harvestable` dominates, it is capturing underlying-led convexity.")
    if best_trade is not None:
        lines.append(f"- **Do direct impulse-based candidate trades have positive expectancy?** Best candidate variant `{best_trade['variant_name']}` on `{best_trade['impulse_type']}` produced `{float(best_trade['avg_pnl']):.2f}` average PnL per trade and PF `{float(best_trade['profit_factor']):.2f}`.")
    if not null_df.empty:
        lines.append(
            "- **Does the phenomenon outperform random/opposite-side controls?** "
            f"It beats random-time controls (`{rand_mean:,.0f}` avg PnL) and opposite-side control (`{opp_pnl:,.0f}`), "
            f"but it does not beat wrong-lag pre-event (`{wrong_pnl:,.0f}`) or shuffled-day (`{shuffled_pnl:,.0f}`) controls cleanly."
        )
    lines.append(f"- **Is this strategy family feasible?** **{verdict}**.")
    lines.append("")
    lines.append("## Charts")
    for path in charts:
        lines.append(f"- ![{path.name}]({path})")
    lines.append("")
    lines.append("## Caveats")
    lines.append("- This is a market-phenomenon study, not a broker-grade execution simulation.")
    lines.append("- Option response is measured on 1-second snapshots; sub-second lead/lag is not resolved.")
    lines.append("- `2026-04-24` and `2026-04-29/30` have different session coverage lengths, so the daywise tables matter more than pooled averages.")
    lines.append("- Direct candidate trades use fixed quantity 500 and simple target/stop logic to test feasibility, not production sizing.")
    return "\n".join(lines), verdict


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    usable_dates = discover_usable_dates()
    if not usable_dates:
        raise RuntimeError("No usable full-tape dates found.")

    day_stats_rows: list[dict[str, Any]] = []
    all_events: list[pd.DataFrame] = []
    event_study_parts: list[pd.DataFrame] = []
    cross_corr_parts: list[pd.DataFrame] = []
    trade_parts: list[pd.DataFrame] = []
    series_by_day: dict[str, dict[str, pd.DataFrame]] = {}
    meta_by_day: dict[str, pd.DataFrame] = {}
    under_by_day: dict[str, pd.DataFrame] = {}

    for date in usable_dates:
        print(f"[convexity] loading {date}", flush=True)
        under_df, series_by_symbol, option_ctx, day_stats = load_day_context(date)
        day_stats_rows.append(day_stats)
        if under_df.empty or not series_by_symbol:
            continue
        meta_df = option_ctx["meta"]
        series_by_day[date] = series_by_symbol
        meta_by_day[date] = meta_df
        under_by_day[date] = under_df

        print(f"[convexity] building impulses for {date}", flush=True)
        raw_impulses = build_raw_impulse_candidates(under_df, date)
        if raw_impulses.empty:
            continue
        imp10 = dedupe_impulses(raw_impulses, 10)
        imp10["cooldown_mode"] = "cd10"
        imp10["event_id"] = [f"{date}|cd10|{row.impulse_type}|{row.direction}|{row.event_time.isoformat()}" for row in imp10.itertuples()]
        imp30 = dedupe_impulses(raw_impulses, 30)
        imp30["cooldown_mode"] = "cd30"
        imp30["event_id"] = [f"{date}|cd30|{row.impulse_type}|{row.direction}|{row.event_time.isoformat()}" for row in imp30.itertuples()]
        day_events = pd.concat([imp10, imp30], ignore_index=True)
        all_events.append(day_events)

        print(f"[convexity] option response study for {date}", flush=True)
        imp10_use = imp10.copy().reset_index(drop=True)
        imp10_use["atm_strike"] = imp10_use["underlying_ltp"].astype(float).map(round_to_strike)
        response_rows: list[dict[str, Any]] = []
        for event in imp10_use.to_dict(orient="records"):
            response_rows.extend(build_option_response_rows_for_event(event, meta_df, series_by_symbol))
        if response_rows:
            event_study_parts.append(pd.DataFrame(response_rows))

        print(f"[convexity] cross correlation for {date}", flush=True)
        cross_corr_parts.append(pd.DataFrame(compute_cross_correlation_rows(date, under_df, meta_df, series_by_symbol)))

        print(f"[convexity] direct candidate trades for {date}", flush=True)
        for variant in TRADE_VARIANTS:
            trades = build_candidate_trades_for_variant(imp10_use, variant, meta_df, series_by_symbol)
            if trades:
                trade_parts.append(pd.DataFrame(trades))

    day_stats_df = pd.DataFrame(day_stats_rows)
    events_df = pd.concat(all_events, ignore_index=True) if all_events else pd.DataFrame()
    if not events_df.empty:
        day_event_counts = events_df[events_df["cooldown_mode"] == MAIN_EVENT_COOLDOWN].groupby("date")["event_time"].count().reset_index(name="impulse_count_cd10")
        day_stats_df = day_stats_df.merge(day_event_counts, on="date", how="left")
        day_stats_df["impulse_density_per_hour_cd10"] = day_stats_df["impulse_count_cd10"] / ((day_stats_df["underlying_seconds"] / 3600.0).replace(0.0, np.nan))
        events_df = attach_day_regimes(events_df, day_stats_df)

    event_study_df = pd.concat(event_study_parts, ignore_index=True) if event_study_parts else pd.DataFrame()
    if not event_study_df.empty and not events_df.empty:
        event_study_df = event_study_df.merge(events_df[["event_id", "trend_regime", "day_vol_regime", "impulse_density_per_hour_cd10", "trend_ratio", "day_net_move", "total_abs_intraday_move"]].drop_duplicates("event_id"), on="event_id", how="left")
    cross_corr_df = pd.concat(cross_corr_parts, ignore_index=True) if cross_corr_parts else pd.DataFrame()
    candidate_trades_df = pd.concat(trade_parts, ignore_index=True) if trade_parts else pd.DataFrame()

    # Save primary raw outputs early
    events_df.to_csv(OUTPUT_DIR / "underlying_impulse_events.csv", index=False)
    event_study_df.to_csv(OUTPUT_DIR / "option_response_event_study.csv", index=False)
    candidate_trades_df.to_csv(OUTPUT_DIR / "convexity_lag_candidate_trades.csv", index=False)
    cross_corr_df.to_csv(OUTPUT_DIR / "lead_lag_cross_correlation.csv", index=False)

    lag_summary_df = build_harvest_summary(event_study_df)
    lag_summary_df.to_csv(OUTPUT_DIR / "lag_harvestability_summary.csv", index=False)

    threshold_grid_df = build_threshold_grid(event_study_df)
    threshold_grid_df.to_csv(OUTPUT_DIR / "harvestability_threshold_grid.csv", index=False)

    trade_summary_df = summarize_trades(candidate_trades_df)

    # Build focused summaries using the best grid cell and best trade variant
    best_grid = pick_best_grid_row(threshold_grid_df)
    best_trade_row = trade_summary_df.sort_values(["total_net_pnl", "profit_factor"], ascending=[False, False]).iloc[0] if not trade_summary_df.empty else None
    if best_grid is not None:
        filtered_event_df = event_study_df[
            (event_study_df["cooldown_mode"] == MAIN_EVENT_COOLDOWN)
            & (event_study_df["impulse_type"] == best_grid["impulse_type"])
            & (event_study_df["entry_lag_seconds"] == best_grid["entry_lag_seconds"])
            & (event_study_df["holding_horizon_seconds"] == best_grid["max_hold_seconds"])
            & (event_study_df["spread_pct_at_entry"] <= best_grid["spread_pct_threshold"])
            & (event_study_df["depth_min_qty_at_entry"] >= best_grid["depth_threshold"])
        ].copy()
        filtered_event_df = filtered_event_df.sort_values(["event_id", "entry_rank_score"], ascending=[True, False]).groupby(["event_id", "atm_bucket"], as_index=False, group_keys=False).head(1)
    else:
        filtered_event_df = event_study_df.copy()
    best_variant_name = str(best_trade_row["variant_name"]) if best_trade_row is not None else ""
    strike_df = build_strike_distance_summary(filtered_event_df, candidate_trades_df, best_variant_name)
    strike_df.to_csv(OUTPUT_DIR / "option_response_by_strike_distance.csv", index=False)
    time_bucket_df = build_time_bucket_summary(filtered_event_df, candidate_trades_df, best_variant_name)
    time_bucket_df.to_csv(OUTPUT_DIR / "option_response_by_time_bucket.csv", index=False)
    regime_df = build_regime_summary(filtered_event_df, candidate_trades_df, best_variant_name)
    regime_df.to_csv(OUTPUT_DIR / "option_response_by_regime.csv", index=False)

    # False burst / noise analysis
    false_noise_df = pd.DataFrame()
    if RAW_BURST_CANDIDATES_PATH.exists():
        burst_candidates = pd.read_csv(RAW_BURST_CANDIDATES_PATH, parse_dates=["timestamp"])
        burst_candidates["date"] = burst_candidates["date"].astype(str)
        burst_candidates = burst_candidates[burst_candidates["atm_distance_abs"] <= 200].copy()
        impulse_cd10 = events_df[events_df["cooldown_mode"] == MAIN_EVENT_COOLDOWN].copy()
        lookup3 = build_event_lookup(impulse_cd10)
        lookup5 = build_event_lookup(impulse_cd10)
        false_noise_df = build_false_burst_noise(burst_candidates, lookup3, lookup5, series_by_day)
    false_noise_df.to_csv(OUTPUT_DIR / "false_burst_noise_analysis.csv", index=False)

    # Null controls based on best trade variant
    null_df = build_null_model_comparison(best_trade_row, trade_summary_df, events_df[events_df["cooldown_mode"] == MAIN_EVENT_COOLDOWN].copy(), meta_by_day, series_by_day, under_by_day)
    null_df.to_csv(OUTPUT_DIR / "null_model_comparison.csv", index=False)

    charts = save_charts(lag_summary_df, cross_corr_df, time_bucket_df, strike_df)
    report, verdict = build_report(
        usable_dates,
        day_stats_df,
        events_df,
        lag_summary_df,
        cross_corr_df,
        strike_df,
        time_bucket_df,
        regime_df,
        threshold_grid_df,
        false_noise_df,
        trade_summary_df,
        null_df,
        charts,
    )
    (OUTPUT_DIR / "convexity_lag_feasibility_report.md").write_text(report, encoding="utf-8")

    total_impulses = int(len(events_df[events_df["cooldown_mode"] == MAIN_EVENT_COOLDOWN])) if not events_df.empty else 0
    best_impulse = str(best_grid["impulse_type"]) if best_grid is not None else "none"
    best_entry_lag = int(best_grid["entry_lag_seconds"]) if best_grid is not None else -1
    best_bucket = str(best_grid["strike_bucket"]) if best_grid is not None else "none"
    best_time = time_bucket_df.sort_values("candidate_trade_net_pnl", ascending=False).iloc[0]["time_bucket"] if not time_bucket_df.empty else "none"
    harvest_3 = float(best_grid["harvest_3pt_rate"]) if best_grid is not None else np.nan
    best_trade_pnl = float(best_trade_row["total_net_pnl"]) if best_trade_row is not None else 0.0
    null_compare = "n/a"
    if not null_df.empty:
        real = null_df[null_df["control_type"] == "real"]
        rand = null_df[null_df["control_type"] == "random_event_times"]
        opp = null_df[null_df["control_type"] == "opposite_side"]
        if not real.empty:
            real_pnl = float(real.iloc[0]["total_net_pnl"])
            rand_pnl = float(rand["total_net_pnl"].mean()) if not rand.empty else np.nan
            opp_pnl = float(opp["total_net_pnl"].mean()) if not opp.empty else np.nan
            null_compare = f"real {real_pnl:.0f} vs random {rand_pnl:.0f} vs opposite {opp_pnl:.0f}"

    print(f"Wrote convexity lag feasibility outputs to {OUTPUT_DIR}")
    print(f"Full-tape dates analyzed: {usable_dates}")
    print(f"Number of impulse events: {total_impulses}")
    print(f"Best impulse definition: {best_impulse}")
    print(f"Best entry lag: {best_entry_lag}s")
    print(f"Best strike bucket: {best_bucket}")
    print(f"Best time bucket: {best_time}")
    print(f"Harvest_3pt_rate: {harvest_3:.3f}" if np.isfinite(harvest_3) else "Harvest_3pt_rate: n/a")
    print(f"Best candidate-trade PnL: {best_trade_pnl:.0f}")
    print(f"Comparison vs null controls: {null_compare}")
    print(f"Final verdict: {verdict}")


if __name__ == "__main__":
    main()
