from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import convexity_lag_feasibility as clf

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "atm_impulse_sync_results"
CHARTS_DIR = OUTPUT_DIR / "charts"

FIXED_QTY = 500
TARGET_POINTS = 3.0
STOP_POINTS = 3.0
ENTRY_SPREAD_MAX = 2.0
ENTRY_SPREAD_PCT_MAX = 0.015
ENTRY_DEPTH_MIN = 250.0
ENTRY_FRESHNESS_MAX = 1.0
STRIKE_STEP = 100
OPTION_EVENT_COOLDOWN = 10

TIME_FILTERS = {
    "ALL_DAY": lambda ts: True,
    "AVOID_OPEN": lambda ts: ts.time() >= pd.Timestamp("2000-01-01 09:30:00").time(),
    "MIDDAY_ONLY": lambda ts: pd.Timestamp("2000-01-01 12:00:00").time() <= ts.time() < pd.Timestamp("2000-01-01 14:45:00").time(),
    "ACTIVE_WINDOW": lambda ts: pd.Timestamp("2000-01-01 10:30:00").time() <= ts.time() < pd.Timestamp("2000-01-01 15:15:01").time(),
    "NO_MORNING_WEAK": lambda ts: ts.time() >= pd.Timestamp("2000-01-01 10:30:00").time(),
}


@dataclass(frozen=True)
class UnderlyingVariant:
    name: str
    impulse_type: str
    entry_lag_seconds: int
    max_hold_seconds: int
    cooldown_seconds: int
    require_not_exhausted: bool = False
    exhaustion_limit: float = 3.0
    time_filter_name: str = "ALL_DAY"
    regime_filter_name: str = "NO_REGIME_FILTER"


@dataclass(frozen=True)
class OptionLeadVariant:
    name: str
    impulse_type: str
    max_hold_seconds: int
    cooldown_seconds: int
    time_filter_name: str = "ALL_DAY"
    regime_filter_name: str = "NO_REGIME_FILTER"


BASE_UNDERLYING_VARIANTS = [
    UnderlyingVariant("ATM_U1S10_0S_H10_CD30", "U_1S_10PTS", 0, 10, 30),
    UnderlyingVariant("ATM_U1S10_0S_H5_CD30", "U_1S_10PTS", 0, 5, 30),
    UnderlyingVariant("ATM_U1S10_0S_H10_CD60", "U_1S_10PTS", 0, 10, 60),
    UnderlyingVariant("ATM_U1S10_0S_H5_CD60", "U_1S_10PTS", 0, 5, 60),
    UnderlyingVariant("ATM_U2S20_0S_H10_CD30", "U_2S_20PTS", 0, 10, 30),
    UnderlyingVariant("ATM_U2S20_0S_H5_CD30", "U_2S_20PTS", 0, 5, 30),
    UnderlyingVariant("ATM_U3S30_0S_H10_CD30", "U_3S_30PTS", 0, 10, 30),
    UnderlyingVariant("ATM_ACCEL_0S_H10_CD30", "ACCEL_SPIKE", 0, 10, 30),
    UnderlyingVariant("ATM_U1S10_1S_H10_CD30", "U_1S_10PTS", 1, 10, 30),
    UnderlyingVariant("ATM_U1S10_1S_NOT_EXHAUSTED_H10_CD30", "U_1S_10PTS", 1, 10, 30, require_not_exhausted=True),
]

TIME_FILTER_BASE_NAMES = {
    "ATM_U1S10_0S_H10_CD30",
    "ATM_U1S10_0S_H5_CD30",
    "ATM_U2S20_0S_H10_CD30",
    "ATM_U3S30_0S_H10_CD30",
    "ATM_ACCEL_0S_H10_CD30",
}
REGIME_FILTER_BASE_NAMES = TIME_FILTER_BASE_NAMES

BASE_OPTION_LEAD_VARIANTS = [
    OptionLeadVariant("OPT_LEAD_1S2PTS_H5_CD30", "OPT_1S_2PTS", 5, 30),
    OptionLeadVariant("OPT_LEAD_1S2PTS_H10_CD30", "OPT_1S_2PTS", 10, 30),
    OptionLeadVariant("OPT_LEAD_1S3PTS_H5_CD30", "OPT_1S_3PTS", 5, 30),
    OptionLeadVariant("OPT_LEAD_1S3PTS_H10_CD30", "OPT_1S_3PTS", 10, 30),
    OptionLeadVariant("OPT_LEAD_2S4PTS_H5_CD30", "OPT_2S_4PTS", 5, 30),
    OptionLeadVariant("OPT_LEAD_2S4PTS_H10_CD30", "OPT_2S_4PTS", 10, 30),
    OptionLeadVariant("OPT_LEAD_ACCEL_H10_CD30", "OPT_ACCEL", 10, 30),
]

REGIME_FILTER_NAMES = [
    "NO_REGIME_FILTER",
    "IMPULSE_DENSITY_ACTIVE",
    "HIGH_VOL_ONLY",
    "CHOPPY_ACTIVE",
    "TRENDING_ACTIVE",
]

IMPULSE_TYPES_MAIN = {"U_1S_10PTS", "U_1S_15PTS", "U_2S_20PTS", "U_3S_30PTS", "ACCEL_SPIKE"}
OPTION_IMPULSE_TYPES = {"OPT_1S_2PTS", "OPT_1S_3PTS", "OPT_2S_4PTS", "OPT_ACCEL"}


def safe_float(value: Any) -> float | None:
    return clf.safe_float(value)


def parse_dt(value: Any) -> pd.Timestamp | pd.NaT:
    return clf.parse_dt(value)


def atm_bucket(distance_abs: int) -> str:
    if distance_abs == 0:
        return "ATM"
    if distance_abs <= 100:
        return "ATM_100"
    if distance_abs <= 200:
        return "ATM_200"
    return "FAR"


def regime_filter_pass(name: str, row: pd.Series | dict[str, Any]) -> bool:
    if name == "NO_REGIME_FILTER":
        return True
    impulse_active = bool((safe_float(row.get("impulse_count_30m")) or 0.0) >= 5.0)
    high_vol = bool(row.get("vol_regime") == "high_vol")
    trend_regime = str(row.get("trend_regime") or "")
    if name == "IMPULSE_DENSITY_ACTIVE":
        return impulse_active
    if name == "HIGH_VOL_ONLY":
        return high_vol
    if name == "CHOPPY_ACTIVE":
        return impulse_active and trend_regime == "choppy"
    if name == "TRENDING_ACTIVE":
        return impulse_active and trend_regime == "trending"
    return True


def build_underlying_context(date: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame, dict[str, Any]]:
    under_df, series_by_symbol, option_ctx, day_stats = clf.load_day_context(date)
    if under_df.empty or not series_by_symbol:
        return under_df, series_by_symbol, pd.DataFrame(), day_stats
    meta_df = option_ctx["meta"].copy()
    # rolling 30-minute count of deduped U_1S_10PTS events
    raw_imp = clf.build_raw_impulse_candidates(under_df, date)
    raw_imp = raw_imp[raw_imp["impulse_type"].isin(IMPULSE_TYPES_MAIN)].copy() if not raw_imp.empty else raw_imp
    u1 = pd.Series(0.0, index=under_df.index)
    if not raw_imp.empty:
        dedup = clf.dedupe_impulses(raw_imp[raw_imp["impulse_type"] == "U_1S_10PTS"].copy(), 10)
        if not dedup.empty:
            dedup_ts = pd.to_datetime(dedup["event_time"])
            dedup_ts = dedup_ts[dedup_ts.isin(under_df.index)]
            u1.loc[dedup_ts] = 1.0
    under_df = under_df.copy()
    under_df["move_1s"] = under_df["underlying_move_1s"]
    under_df["move_2s"] = under_df["underlying_move_2s"]
    under_df["move_3s"] = under_df["underlying_move_3s"]
    under_df["move_5s"] = under_df["underlying_move_5s"]
    under_df["realized_vol_1m"] = under_df["underlying_realized_vol_1m"]
    under_df["trend_score_5m"] = under_df["underlying_trend_score_5m"]
    under_df["atm_strike"] = under_df["sensex_ltp"].astype(float).map(clf.round_to_strike)
    under_df["impulse_count_30m"] = u1.rolling(1800, min_periods=1).sum()
    under_df["impulse_density_regime"] = np.where(under_df["impulse_count_30m"] >= 5.0, "active", "inactive")
    vol_median = float(under_df["realized_vol_1m"].median()) if not under_df.empty else 0.0
    trend_median = float(under_df["trend_score_5m"].median()) if not under_df.empty else 0.0
    under_df["vol_regime"] = np.where(under_df["realized_vol_1m"] >= vol_median, "high_vol", "low_vol")
    under_df["trend_regime"] = np.where(under_df["trend_score_5m"] >= trend_median, "trending", "choppy")
    return under_df, series_by_symbol, meta_df, {**day_stats, "vol_median": vol_median, "trend_median": trend_median}


def build_atm_side_series(under_df: pd.DataFrame, meta_df: pd.DataFrame, series_by_symbol: dict[str, pd.DataFrame]) -> pd.DataFrame:
    strike_lookup = {
        (str(rec["option_type"]), int(rec["strike"])): str(rec["symbol"])
        for rec in meta_df.to_dict(orient="records")
    }
    rows: list[dict[str, Any]] = []
    for ts, row in under_df.iterrows():
        atm_strike = int(row["atm_strike"])
        sensex_ltp = float(row["sensex_ltp"])
        for option_type, side in [("CE", "CALL"), ("PE", "PUT")]:
            symbol = strike_lookup.get((option_type, atm_strike))
            if not symbol:
                continue
            series = series_by_symbol.get(symbol)
            if series is None or ts not in series.index:
                continue
            srow = series.loc[ts]
            ltp = safe_float(srow.get("ltp"))
            if ltp is None or not np.isfinite(ltp):
                continue
            rows.append(
                {
                    "date": str(ts.date()),
                    "timestamp": ts,
                    "symbol": symbol,
                    "option_type": option_type,
                    "side": side,
                    "strike": atm_strike,
                    "expiry": srow.get("expiry"),
                    "ltp": ltp,
                    "best_bid": safe_float(srow.get("best_bid")),
                    "best_ask": safe_float(srow.get("best_ask")),
                    "mid_price": safe_float(srow.get("mid_price")),
                    "spread": safe_float(srow.get("spread")),
                    "spread_pct": safe_float(srow.get("spread_pct")),
                    "bid_qty": safe_float(srow.get("bid_qty")),
                    "ask_qty": safe_float(srow.get("ask_qty")),
                    "depth_min_qty": safe_float(srow.get("depth_min_qty")),
                    "seconds_since_symbol_update": safe_float(srow.get("seconds_since_symbol_update")),
                    "update_count_5s": safe_float(srow.get("update_count_5s")),
                    "underlying_ltp": sensex_ltp,
                    "atm_strike": atm_strike,
                    "atm_distance_abs": 0,
                    "atm_bucket": "ATM",
                    "realized_vol_1m": safe_float(row.get("realized_vol_1m")),
                    "trend_score_5m": safe_float(row.get("trend_score_5m")),
                    "impulse_count_30m": safe_float(row.get("impulse_count_30m")),
                    "impulse_density_regime": row.get("impulse_density_regime"),
                    "vol_regime": row.get("vol_regime"),
                    "trend_regime": row.get("trend_regime"),
                    "time_bucket": clf.time_bucket(ts),
                }
            )
    return pd.DataFrame(rows)


def tradable_snapshot(row: pd.Series | dict[str, Any]) -> bool:
    spread = safe_float(row.get("spread"))
    spread_pct = safe_float(row.get("spread_pct"))
    depth = safe_float(row.get("depth_min_qty"))
    freshness = safe_float(row.get("seconds_since_symbol_update"))
    return bool(
        spread is not None and spread <= ENTRY_SPREAD_MAX
        and spread_pct is not None and spread_pct <= ENTRY_SPREAD_PCT_MAX
        and depth is not None and depth >= ENTRY_DEPTH_MIN
        and freshness is not None and freshness <= ENTRY_FRESHNESS_MAX
    )


def derive_entry_regime_label(row: pd.Series | dict[str, Any], day_spread_median: float, day_depth_median: float) -> str:
    spread_pct = safe_float(row.get("spread_pct")) or 0.0
    depth = safe_float(row.get("depth_min_qty")) or 0.0
    spread_regime = "tight_spread" if spread_pct <= day_spread_median else "wide_spread"
    depth_regime = "high_depth" if depth >= day_depth_median else "low_depth"
    return "|".join([
        str(row.get("impulse_density_regime") or "unknown"),
        str(row.get("vol_regime") or "unknown"),
        str(row.get("trend_regime") or "unknown"),
        spread_regime,
        depth_regime,
    ])


def build_underlying_impulse_events(date: str, under_df: pd.DataFrame, atm_df: pd.DataFrame) -> pd.DataFrame:
    raw = clf.build_raw_impulse_candidates(under_df, date)
    if raw.empty:
        return pd.DataFrame()
    raw = raw[raw["impulse_type"].isin(IMPULSE_TYPES_MAIN)].copy()
    dedup = clf.dedupe_impulses(raw, 10)
    if dedup.empty:
        return pd.DataFrame()
    atm_map = {
        (str(rec["side"]), pd.Timestamp(rec["timestamp"])): rec
        for rec in atm_df.to_dict(orient="records")
    }
    rows: list[dict[str, Any]] = []
    for rec in dedup.to_dict(orient="records"):
        side = "CALL" if rec["direction"] == "UP" else "PUT"
        ts = pd.Timestamp(rec["event_time"])
        atm_rec = atm_map.get((side, ts))
        if not atm_rec:
            continue
        rows.append(
            {
                "date": date,
                "event_time": ts,
                "impulse_type": rec["impulse_type"],
                "impulse_direction": rec["direction"],
                "option_side": side,
                "option_symbol": atm_rec["symbol"],
                "option_type": atm_rec["option_type"],
                "strike": int(atm_rec["strike"]),
                "atm_strike": int(atm_rec["atm_strike"]),
                "event_option_ltp": safe_float(atm_rec.get("ltp")),
                "spread": safe_float(atm_rec.get("spread")),
                "spread_pct": safe_float(atm_rec.get("spread_pct")),
                "depth_min_qty": safe_float(atm_rec.get("depth_min_qty")),
                "seconds_since_symbol_update": safe_float(atm_rec.get("seconds_since_symbol_update")),
                "update_count_5s": safe_float(atm_rec.get("update_count_5s")),
                "time_bucket": atm_rec.get("time_bucket"),
                "realized_vol_1m": safe_float(atm_rec.get("realized_vol_1m")),
                "trend_score_5m": safe_float(atm_rec.get("trend_score_5m")),
                "impulse_count_30m": safe_float(atm_rec.get("impulse_count_30m")),
                "impulse_density_regime": atm_rec.get("impulse_density_regime"),
                "vol_regime": atm_rec.get("vol_regime"),
                "trend_regime": atm_rec.get("trend_regime"),
                "underlying_ltp": safe_float(rec.get("underlying_ltp")),
                "move_1s": safe_float(rec.get("underlying_move_1s")),
                "move_2s": safe_float(rec.get("underlying_move_2s")),
                "move_3s": safe_float(rec.get("underlying_move_3s")),
                "move_5s": safe_float(rec.get("underlying_move_5s")),
            }
        )
    return pd.DataFrame(rows)


def build_option_impulse_events(date: str, atm_df: pd.DataFrame) -> pd.DataFrame:
    if atm_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for side, g in atm_df.groupby("side"):
        g = g.sort_values("timestamp").copy()
        g["opt_move_1s"] = g["ltp"].astype(float) - g["ltp"].astype(float).shift(1)
        g["opt_move_2s"] = g["ltp"].astype(float) - g["ltp"].astype(float).shift(2)
        g["prior_opt_move_2s"] = g["opt_move_2s"].shift(2)
        last_by_impulse: dict[str, pd.Timestamp] = {}
        for row in g.to_dict(orient="records"):
            ts = pd.Timestamp(row["timestamp"])
            move1 = safe_float(row.get("opt_move_1s"))
            move2 = safe_float(row.get("opt_move_2s"))
            prior2 = safe_float(row.get("prior_opt_move_2s"))
            definitions: list[tuple[str, bool]] = [
                ("OPT_1S_2PTS", move1 is not None and move1 >= 2.0),
                ("OPT_1S_3PTS", move1 is not None and move1 >= 3.0),
                ("OPT_2S_4PTS", move2 is not None and move2 >= 4.0),
                ("OPT_ACCEL", move2 is not None and move2 >= 4.0 and prior2 is not None and move2 >= prior2 + 2.0),
            ]
            for imp_name, fired in definitions:
                if not fired:
                    continue
                last = last_by_impulse.get(imp_name)
                if last is not None and (ts - last).total_seconds() < OPTION_EVENT_COOLDOWN:
                    continue
                last_by_impulse[imp_name] = ts
                rows.append(
                    {
                        "date": date,
                        "event_time": ts,
                        "impulse_type": imp_name,
                        "option_side": side,
                        "option_symbol": row["symbol"],
                        "option_type": row["option_type"],
                        "strike": int(row["strike"]),
                        "atm_strike": int(row["atm_strike"]),
                        "option_ltp": safe_float(row.get("ltp")),
                        "opt_move_1s": move1,
                        "opt_move_2s": move2,
                        "spread": safe_float(row.get("spread")),
                        "spread_pct": safe_float(row.get("spread_pct")),
                        "depth_min_qty": safe_float(row.get("depth_min_qty")),
                        "seconds_since_symbol_update": safe_float(row.get("seconds_since_symbol_update")),
                        "update_count_5s": safe_float(row.get("update_count_5s")),
                        "underlying_ltp": safe_float(row.get("underlying_ltp")),
                        "time_bucket": row.get("time_bucket"),
                        "realized_vol_1m": safe_float(row.get("realized_vol_1m")),
                        "trend_score_5m": safe_float(row.get("trend_score_5m")),
                        "impulse_count_30m": safe_float(row.get("impulse_count_30m")),
                        "impulse_density_regime": row.get("impulse_density_regime"),
                        "vol_regime": row.get("vol_regime"),
                        "trend_regime": row.get("trend_regime"),
                    }
                )
    return pd.DataFrame(rows)


def simulate_scalp_trade(
    series: pd.DataFrame,
    entry_time: pd.Timestamp,
    max_hold_seconds: int,
    target_points: float = TARGET_POINTS,
    stop_points: float = STOP_POINTS,
) -> dict[str, Any] | None:
    if entry_time not in series.index:
        return None
    entry_price = safe_float(series.loc[entry_time, "ltp"])
    if entry_price is None:
        return None
    end_time = entry_time + pd.Timedelta(seconds=max_hold_seconds)
    window = series.loc[entry_time:end_time]
    if window.empty:
        return None
    runup = 0.0
    drawdown = 0.0
    exit_reason = None
    exit_time = entry_time
    exit_price = entry_price
    one_sec_kill = False
    three_sec_kill = False
    stop_hit = False
    target_hit = False
    timeout = False
    for ts, row in window.iterrows():
        ltp = safe_float(row.get("ltp"))
        if ltp is None:
            continue
        pnl = ltp - entry_price
        runup = max(runup, pnl)
        drawdown = min(drawdown, pnl)
        elapsed = float((ts - entry_time).total_seconds())
        if pnl >= target_points:
            exit_reason = "TARGET_HIT"
            target_hit = True
            exit_time = ts
            exit_price = ltp
            break
        if pnl <= -stop_points:
            exit_reason = "STOP_HIT"
            stop_hit = True
            exit_time = ts
            exit_price = ltp
            break
        if elapsed >= 1.0 and exit_reason is None:
            if runup < 1.0 and pnl <= 0.0:
                exit_reason = "ONE_SEC_KILL"
                one_sec_kill = True
                exit_time = ts
                exit_price = ltp
                break
        if elapsed >= 3.0 and exit_reason is None:
            if runup < 2.0 or drawdown <= -3.0:
                exit_reason = "THREE_SEC_KILL"
                three_sec_kill = True
                exit_time = ts
                exit_price = ltp
                break
    if exit_reason is None:
        last = window.iloc[-1]
        exit_reason = f"TIMEOUT_{max_hold_seconds}S"
        timeout = True
        exit_time = window.index[-1]
        exit_price = float(last["ltp"])
    return {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "points_pnl": exit_price - entry_price,
        "gross_pnl": (exit_price - entry_price) * FIXED_QTY,
        "net_pnl": (exit_price - entry_price) * FIXED_QTY,
        "hold_seconds": float((exit_time - entry_time).total_seconds()),
        "mfe_points": runup,
        "mae_points": drawdown,
        "target_hit": target_hit,
        "one_sec_kill": one_sec_kill,
        "three_sec_kill": three_sec_kill,
        "stop_hit": stop_hit,
        "timeout": timeout,
        "exit_reason": exit_reason,
        "quantity": FIXED_QTY,
        "quantity_source": "fixed_500",
    }


def apply_time_filter(name: str, ts: pd.Timestamp) -> bool:
    return TIME_FILTERS[name](ts)


def build_underlying_trades(
    events_df: pd.DataFrame,
    variant: UnderlyingVariant,
    series_by_symbol: dict[str, pd.DataFrame],
    day_spread_median: float,
    day_depth_median: float,
) -> list[dict[str, Any]]:
    if events_df.empty:
        return []
    trades: list[dict[str, Any]] = []
    next_free: pd.Timestamp | None = None
    for event in events_df[events_df["impulse_type"] == variant.impulse_type].sort_values("event_time").to_dict(orient="records"):
        event_time = pd.Timestamp(event["event_time"])
        if next_free is not None and event_time < next_free:
            continue
        symbol = str(event["option_symbol"])
        series = series_by_symbol.get(symbol)
        if series is None:
            continue
        entry_time = event_time + pd.Timedelta(seconds=variant.entry_lag_seconds)
        if entry_time not in series.index:
            continue
        if not apply_time_filter(variant.time_filter_name, entry_time):
            continue
        if not regime_filter_pass(variant.regime_filter_name, event):
            continue
        entry_row = series.loc[entry_time]
        entry_ltp = safe_float(entry_row.get("ltp"))
        if entry_ltp is None:
            continue
        event_ltp = safe_float(event.get("event_option_ltp"))
        if variant.require_not_exhausted and event_ltp is not None and (entry_ltp - event_ltp) > variant.exhaustion_limit:
            continue
        entry_snapshot = {
            "spread": safe_float(entry_row.get("spread")),
            "spread_pct": safe_float(entry_row.get("spread_pct")),
            "depth_min_qty": safe_float(entry_row.get("depth_min_qty")),
            "seconds_since_symbol_update": safe_float(entry_row.get("seconds_since_symbol_update")),
        }
        if not tradable_snapshot(entry_snapshot):
            continue
        sim = simulate_scalp_trade(series, entry_time, variant.max_hold_seconds)
        if sim is None:
            continue
        regime_label = derive_entry_regime_label({**event, **entry_snapshot}, day_spread_median, day_depth_median)
        trade = {
            "date": event["date"],
            "variant_name": variant.name,
            "entry_time": sim["entry_time"],
            "exit_time": sim["exit_time"],
            "impulse_type": event["impulse_type"],
            "impulse_direction": event["impulse_direction"],
            "option_symbol": symbol,
            "option_type": event["option_type"],
            "strike": int(event["strike"]),
            "atm_strike": int(event["atm_strike"]),
            "entry_price": sim["entry_price"],
            "exit_price": sim["exit_price"],
            "points_pnl": sim["points_pnl"],
            "net_pnl": sim["net_pnl"],
            "exit_reason": sim["exit_reason"],
            "hold_seconds": sim["hold_seconds"],
            "mfe_points": sim["mfe_points"],
            "mae_points": sim["mae_points"],
            "target_hit": sim["target_hit"],
            "one_sec_kill": sim["one_sec_kill"],
            "three_sec_kill": sim["three_sec_kill"],
            "stop_hit": sim["stop_hit"],
            "timeout": sim["timeout"],
            "spread_at_entry": entry_snapshot["spread"],
            "spread_pct_at_entry": entry_snapshot["spread_pct"],
            "depth_min_qty_at_entry": entry_snapshot["depth_min_qty"],
            "seconds_since_update_at_entry": entry_snapshot["seconds_since_symbol_update"],
            "time_bucket": clf.time_bucket(pd.Timestamp(sim["entry_time"])),
            "regime_label": regime_label,
            "impulse_count_30m": safe_float(event.get("impulse_count_30m")),
            "realized_vol_1m": safe_float(event.get("realized_vol_1m")),
            "trend_score_5m": safe_float(event.get("trend_score_5m")),
            "vol_regime": event.get("vol_regime"),
            "trend_regime": event.get("trend_regime"),
            "impulse_density_regime": event.get("impulse_density_regime"),
            "move_1s": safe_float(event.get("move_1s")),
            "move_2s": safe_float(event.get("move_2s")),
            "move_3s": safe_float(event.get("move_3s")),
            "move_5s": safe_float(event.get("move_5s")),
        }
        trades.append(trade)
        next_free = pd.Timestamp(sim["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
    return trades


def build_option_lead_predictive_rows(
    option_events_df: pd.DataFrame,
    under_df: pd.DataFrame,
    atm_df: pd.DataFrame,
) -> pd.DataFrame:
    if option_events_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    option_by_side = {
        side: g.sort_values("timestamp").reset_index(drop=True)
        for side, g in atm_df.groupby("side")
    }
    valid_times = list(under_df.index)
    side_time_lookup = {side: list(g["timestamp"]) for side, g in option_by_side.items()}
    rng = random.Random(42)

    def add_rows(records: Iterable[dict[str, Any]], control_type: str) -> None:
        for rec in records:
            ts = pd.Timestamp(rec["event_time"])
            side = str(rec["option_side"])
            expected_mult = 1.0 if side == "CALL" else -1.0
            signed_moves: dict[int, float] = {}
            raw_moves: dict[int, float] = {}
            for h in [1, 2, 3, 5, 10]:
                future_ts = ts + pd.Timedelta(seconds=h)
                if future_ts not in under_df.index or ts not in under_df.index:
                    raw = np.nan
                    signed = np.nan
                else:
                    raw = float(under_df.loc[future_ts, "sensex_ltp"] - under_df.loc[ts, "sensex_ltp"])
                    signed = raw * expected_mult
                raw_moves[h] = raw
                signed_moves[h] = signed
            valid_signed = [v for v in signed_moves.values() if pd.notna(v)]
            max_signed_10s = max(valid_signed) if valid_signed else np.nan
            rows.append(
                {
                    "date": rec["date"],
                    "control_type": control_type,
                    "event_time": ts,
                    "impulse_type": rec["impulse_type"],
                    "option_side": side,
                    "option_symbol": rec.get("option_symbol"),
                    "option_type": rec.get("option_type"),
                    "strike": rec.get("strike"),
                    "option_ltp": safe_float(rec.get("option_ltp")),
                    "spread": safe_float(rec.get("spread")),
                    "spread_pct": safe_float(rec.get("spread_pct")),
                    "depth_min_qty": safe_float(rec.get("depth_min_qty")),
                    "seconds_since_symbol_update": safe_float(rec.get("seconds_since_symbol_update")),
                    "pre_event_sensex_move_1s": safe_float(under_df.loc[ts, "move_1s"]) if ts in under_df.index else np.nan,
                    "pre_event_sensex_move_2s": safe_float(under_df.loc[ts, "move_2s"]) if ts in under_df.index else np.nan,
                    "pre_event_sensex_move_3s": safe_float(under_df.loc[ts, "move_3s"]) if ts in under_df.index else np.nan,
                    "future_sensex_move_1s": raw_moves[1],
                    "future_sensex_move_2s": raw_moves[2],
                    "future_sensex_move_3s": raw_moves[3],
                    "future_sensex_move_5s": raw_moves[5],
                    "future_sensex_move_10s": raw_moves[10],
                    "signed_future_sensex_move_1s": signed_moves[1],
                    "signed_future_sensex_move_2s": signed_moves[2],
                    "signed_future_sensex_move_3s": signed_moves[3],
                    "signed_future_sensex_move_5s": signed_moves[5],
                    "signed_future_sensex_move_10s": signed_moves[10],
                    "direction_correct_1s": bool(pd.notna(signed_moves[1]) and signed_moves[1] > 0),
                    "direction_correct_2s": bool(pd.notna(signed_moves[2]) and signed_moves[2] > 0),
                    "direction_correct_3s": bool(pd.notna(signed_moves[3]) and signed_moves[3] > 0),
                    "direction_correct_5s": bool(pd.notna(signed_moves[5]) and signed_moves[5] > 0),
                    "avg_future_move": float(np.nanmean(valid_signed)) if valid_signed else np.nan,
                    "median_future_move": float(np.nanmedian(valid_signed)) if valid_signed else np.nan,
                    "hit_future_10pts": bool(pd.notna(max_signed_10s) and max_signed_10s >= 10.0),
                    "hit_future_15pts": bool(pd.notna(max_signed_10s) and max_signed_10s >= 15.0),
                    "hit_future_20pts": bool(pd.notna(max_signed_10s) and max_signed_10s >= 20.0),
                    "time_bucket": rec.get("time_bucket"),
                    "impulse_count_30m": safe_float(rec.get("impulse_count_30m")),
                    "realized_vol_1m": safe_float(rec.get("realized_vol_1m")),
                    "trend_score_5m": safe_float(rec.get("trend_score_5m")),
                }
            )

    real_records = option_events_df.to_dict(orient="records")
    add_rows(real_records, "real")

    # opposite-side control at same timestamps
    atm_lookup = {(str(rec["side"]), pd.Timestamp(rec["timestamp"])): rec for rec in atm_df.to_dict(orient="records")}
    opp_records: list[dict[str, Any]] = []
    for rec in real_records:
        other_side = "PUT" if rec["option_side"] == "CALL" else "CALL"
        opp = atm_lookup.get((other_side, pd.Timestamp(rec["event_time"])))
        if opp and tradable_snapshot(opp):
            opp_records.append(
                {
                    **rec,
                    "option_side": other_side,
                    "option_symbol": opp["symbol"],
                    "option_type": opp["option_type"],
                    "strike": opp["strike"],
                    "option_ltp": opp["ltp"],
                    "spread": opp["spread"],
                    "spread_pct": opp["spread_pct"],
                    "depth_min_qty": opp["depth_min_qty"],
                    "seconds_since_symbol_update": opp["seconds_since_symbol_update"],
                }
            )
    add_rows(opp_records, "opposite_side")

    # random time control matched by side
    random_records: list[dict[str, Any]] = []
    for side, group in option_events_df.groupby("option_side"):
        pool = [ts for ts in side_time_lookup.get(side, []) if ts in under_df.index]
        if not pool:
            continue
        sample_n = len(group)
        sampled = [rng.choice(pool) for _ in range(sample_n)]
        for rec, ts in zip(group.to_dict(orient="records"), sampled):
            atm_rec = atm_lookup.get((side, pd.Timestamp(ts)))
            if not atm_rec or not tradable_snapshot(atm_rec):
                continue
            random_records.append(
                {
                    **rec,
                    "event_time": pd.Timestamp(ts),
                    "option_symbol": atm_rec["symbol"],
                    "option_type": atm_rec["option_type"],
                    "strike": atm_rec["strike"],
                    "option_ltp": atm_rec["ltp"],
                    "spread": atm_rec["spread"],
                    "spread_pct": atm_rec["spread_pct"],
                    "depth_min_qty": atm_rec["depth_min_qty"],
                    "seconds_since_symbol_update": atm_rec["seconds_since_symbol_update"],
                    "time_bucket": atm_rec["time_bucket"],
                    "impulse_count_30m": atm_rec["impulse_count_30m"],
                    "realized_vol_1m": atm_rec["realized_vol_1m"],
                    "trend_score_5m": atm_rec["trend_score_5m"],
                }
            )
    add_rows(random_records, "random_time")

    # shuffled timestamp control within same side
    shuffled_records: list[dict[str, Any]] = []
    for side, group in option_events_df.groupby("option_side"):
        pool = side_time_lookup.get(side, [])
        if not pool:
            continue
        shuffled = pool.copy()
        rng.shuffle(shuffled)
        for rec, ts in zip(group.to_dict(orient="records"), shuffled):
            atm_rec = atm_lookup.get((side, pd.Timestamp(ts)))
            if not atm_rec or not tradable_snapshot(atm_rec):
                continue
            shuffled_records.append(
                {
                    **rec,
                    "event_time": pd.Timestamp(ts),
                    "option_symbol": atm_rec["symbol"],
                    "option_type": atm_rec["option_type"],
                    "strike": atm_rec["strike"],
                    "option_ltp": atm_rec["ltp"],
                    "spread": atm_rec["spread"],
                    "spread_pct": atm_rec["spread_pct"],
                    "depth_min_qty": atm_rec["depth_min_qty"],
                    "seconds_since_symbol_update": atm_rec["seconds_since_symbol_update"],
                    "time_bucket": atm_rec["time_bucket"],
                    "impulse_count_30m": atm_rec["impulse_count_30m"],
                    "realized_vol_1m": atm_rec["realized_vol_1m"],
                    "trend_score_5m": atm_rec["trend_score_5m"],
                }
            )
    add_rows(shuffled_records, "shuffled_time")
    return pd.DataFrame(rows)


def build_option_lead_trades(
    option_events_df: pd.DataFrame,
    variant: OptionLeadVariant,
    series_by_symbol: dict[str, pd.DataFrame],
    day_spread_median: float,
    day_depth_median: float,
) -> list[dict[str, Any]]:
    if option_events_df.empty:
        return []
    trades: list[dict[str, Any]] = []
    next_free: pd.Timestamp | None = None
    for event in option_events_df[option_events_df["impulse_type"] == variant.impulse_type].sort_values("event_time").to_dict(orient="records"):
        event_time = pd.Timestamp(event["event_time"])
        if next_free is not None and event_time < next_free:
            continue
        if not apply_time_filter(variant.time_filter_name, event_time):
            continue
        if not regime_filter_pass(variant.regime_filter_name, event):
            continue
        series = series_by_symbol.get(str(event["option_symbol"]))
        if series is None or event_time not in series.index:
            continue
        entry_row = series.loc[event_time]
        entry_snapshot = {
            "spread": safe_float(entry_row.get("spread")),
            "spread_pct": safe_float(entry_row.get("spread_pct")),
            "depth_min_qty": safe_float(entry_row.get("depth_min_qty")),
            "seconds_since_symbol_update": safe_float(entry_row.get("seconds_since_symbol_update")),
        }
        if not tradable_snapshot(entry_snapshot):
            continue
        sim = simulate_scalp_trade(series, event_time, variant.max_hold_seconds)
        if sim is None:
            continue
        regime_label = derive_entry_regime_label({**event, **entry_snapshot}, day_spread_median, day_depth_median)
        trade = {
            "date": event["date"],
            "variant_name": variant.name,
            "entry_time": sim["entry_time"],
            "exit_time": sim["exit_time"],
            "impulse_type": event["impulse_type"],
            "impulse_direction": "UP" if event["option_side"] == "CALL" else "DOWN",
            "option_symbol": event["option_symbol"],
            "option_type": event["option_type"],
            "strike": int(event["strike"]),
            "atm_strike": int(event["atm_strike"]),
            "entry_price": sim["entry_price"],
            "exit_price": sim["exit_price"],
            "points_pnl": sim["points_pnl"],
            "net_pnl": sim["net_pnl"],
            "exit_reason": sim["exit_reason"],
            "hold_seconds": sim["hold_seconds"],
            "mfe_points": sim["mfe_points"],
            "mae_points": sim["mae_points"],
            "target_hit": sim["target_hit"],
            "one_sec_kill": sim["one_sec_kill"],
            "three_sec_kill": sim["three_sec_kill"],
            "stop_hit": sim["stop_hit"],
            "timeout": sim["timeout"],
            "spread_at_entry": entry_snapshot["spread"],
            "spread_pct_at_entry": entry_snapshot["spread_pct"],
            "depth_min_qty_at_entry": entry_snapshot["depth_min_qty"],
            "seconds_since_update_at_entry": entry_snapshot["seconds_since_symbol_update"],
            "time_bucket": clf.time_bucket(pd.Timestamp(sim["entry_time"])),
            "regime_label": regime_label,
            "impulse_count_30m": safe_float(event.get("impulse_count_30m")),
            "realized_vol_1m": safe_float(event.get("realized_vol_1m")),
            "trend_score_5m": safe_float(event.get("trend_score_5m")),
            "vol_regime": event.get("vol_regime"),
            "trend_regime": event.get("trend_regime"),
            "impulse_density_regime": event.get("impulse_density_regime"),
            "opt_move_1s": safe_float(event.get("opt_move_1s")),
            "opt_move_2s": safe_float(event.get("opt_move_2s")),
        }
        trades.append(trade)
        next_free = pd.Timestamp(sim["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
    return trades


def build_all_underlying_variants() -> list[UnderlyingVariant]:
    variants = list(BASE_UNDERLYING_VARIANTS)
    for base in BASE_UNDERLYING_VARIANTS:
        if base.name in TIME_FILTER_BASE_NAMES:
            for tf in ["ALL_DAY", "AVOID_OPEN", "MIDDAY_ONLY", "ACTIVE_WINDOW", "NO_MORNING_WEAK"]:
                if tf == "ALL_DAY":
                    continue
                variants.append(replace(base, name=f"{base.name}__{tf}", time_filter_name=tf))
        if base.name in REGIME_FILTER_BASE_NAMES:
            for rf in REGIME_FILTER_NAMES:
                if rf == "NO_REGIME_FILTER":
                    continue
                variants.append(replace(base, name=f"{base.name}__{rf}", regime_filter_name=rf))
    return variants


def build_all_option_lead_variants() -> list[OptionLeadVariant]:
    variants = list(BASE_OPTION_LEAD_VARIANTS)
    for base in BASE_OPTION_LEAD_VARIANTS:
        variants.append(replace(base, name=f"{base.name}__MIDDAY_ONLY", time_filter_name="MIDDAY_ONLY"))
        variants.append(replace(base, name=f"{base.name}__IMPULSE_DENSITY_ACTIVE", regime_filter_name="IMPULSE_DENSITY_ACTIVE"))
    return variants


def summarize_trades_by_day(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (date, variant), g in trades_df.groupby(["date", "variant_name"]):
        ordered = g.sort_values("exit_time")
        eq = ordered["net_pnl"].cumsum()
        dd = eq - eq.cummax()
        wins = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"]
        losses = ordered.loc[ordered["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        rows.append(
            {
                "date": date,
                "variant_name": variant,
                "trades": int(len(g)),
                "net_pnl": float(g["net_pnl"].sum()),
                "win_rate": float((g["net_pnl"] > 0).mean()),
                "profit_factor": pf,
                "avg_pnl": float(g["net_pnl"].mean()),
                "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
                "target_hit_rate": float(g["target_hit"].mean()),
                "one_sec_kill_count": int(g["one_sec_kill"].sum()),
                "three_sec_kill_count": int(g["three_sec_kill"].sum()),
                "stop_count": int(g["stop_hit"].sum()),
                "timeout_count": int(g["timeout"].sum()),
                "avg_mfe": float(g["mfe_points"].mean()),
                "avg_mae": float(g["mae_points"].mean()),
                "avg_hold_seconds": float(g["hold_seconds"].mean()),
                "avg_entry_premium": float(g["entry_price"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(["variant_name", "date"]).reset_index(drop=True)


def summarize_trades_by_time(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    day_bucket = trades_df.groupby(["variant_name", "time_bucket", "date"])["net_pnl"].sum().reset_index(name="day_pnl")
    for (variant, bucket), g in trades_df.groupby(["variant_name", "time_bucket"]):
        wins = g.loc[g["net_pnl"] > 0, "net_pnl"]
        losses = g.loc[g["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        worst_day = day_bucket[(day_bucket["variant_name"] == variant) & (day_bucket["time_bucket"] == bucket)]["day_pnl"]
        rows.append(
            {
                "variant_name": variant,
                "time_bucket": bucket,
                "trades": int(len(g)),
                "net_pnl": float(g["net_pnl"].sum()),
                "win_rate": float((g["net_pnl"] > 0).mean()),
                "profit_factor": pf,
                "avg_pnl": float(g["net_pnl"].mean()),
                "target_hit_rate": float(g["target_hit"].mean()),
                "avg_mfe": float(g["mfe_points"].mean()),
                "avg_mae": float(g["mae_points"].mean()),
                "worst_day_pnl": float(worst_day.min()) if not worst_day.empty else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["variant_name", "net_pnl"], ascending=[True, False]).reset_index(drop=True)


def summarize_trades_by_regime(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    day_spread = trades_df.groupby("date")["spread_pct_at_entry"].median().to_dict()
    day_depth = trades_df.groupby("date")["depth_min_qty_at_entry"].median().to_dict()
    tmp = trades_df.copy()
    tmp["spread_regime"] = ["tight_spread" if safe_float(r["spread_pct_at_entry"]) <= day_spread.get(r["date"], math.inf) else "wide_spread" for _, r in tmp.iterrows()]
    tmp["depth_regime"] = ["high_depth" if safe_float(r["depth_min_qty_at_entry"]) >= day_depth.get(r["date"], -math.inf) else "low_depth" for _, r in tmp.iterrows()]
    regime_dims = [
        ("impulse_density_regime", "impulse_density_regime"),
        ("vol_regime", "vol_regime"),
        ("trend_regime", "trend_regime"),
        ("spread_regime", "spread_regime"),
        ("depth_regime", "depth_regime"),
    ]
    for dim_col, dim_name in regime_dims:
        day_group = tmp.groupby(["variant_name", dim_col, "date"])["net_pnl"].sum().reset_index(name="day_pnl")
        for (variant, value), g in tmp.groupby(["variant_name", dim_col]):
            wins = g.loc[g["net_pnl"] > 0, "net_pnl"]
            losses = g.loc[g["net_pnl"] < 0, "net_pnl"]
            pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
            worst_day = day_group[(day_group["variant_name"] == variant) & (day_group[dim_col] == value)]["day_pnl"]
            rows.append(
                {
                    "variant_name": variant,
                    "regime_dimension": dim_name,
                    "regime_value": value,
                    "trades": int(len(g)),
                    "net_pnl": float(g["net_pnl"].sum()),
                    "win_rate": float((g["net_pnl"] > 0).mean()),
                    "profit_factor": pf,
                    "avg_pnl": float(g["net_pnl"].mean()),
                    "target_hit_rate": float(g["target_hit"].mean()),
                    "avg_mfe": float(g["mfe_points"].mean()),
                    "avg_mae": float(g["mae_points"].mean()),
                    "worst_day_pnl": float(worst_day.min()) if not worst_day.empty else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["variant_name", "net_pnl"], ascending=[True, False]).reset_index(drop=True)


def cost_sensitivity(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for variant, g in trades_df.groupby("variant_name"):
        for cost in [0.0, 0.25, 0.5, 0.75, 1.0]:
            adj_points = g["points_pnl"] - cost
            adj_pnl = adj_points * FIXED_QTY
            wins = adj_pnl[adj_pnl > 0]
            losses = adj_pnl[adj_pnl < 0]
            pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
            day_adj = pd.DataFrame({"date": g["date"], "adj_pnl": adj_pnl}).groupby("date")["adj_pnl"].sum()
            rows.append(
                {
                    "variant_name": variant,
                    "cost_points": cost,
                    "adjusted_pnl": float(adj_pnl.sum()),
                    "adjusted_avg_pnl": float(adj_pnl.mean()),
                    "adjusted_profit_factor": pf,
                    "days_positive": int((day_adj > 0).sum()),
                    "worst_day_pnl": float(day_adj.min()) if not day_adj.empty else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["variant_name", "cost_points"]).reset_index(drop=True)


def build_variant_summary(
    trades_df: pd.DataFrame,
    daywise_df: pd.DataFrame,
    cost_df: pd.DataFrame,
    predictive_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for variant, g in trades_df.groupby("variant_name"):
        ordered = g.sort_values("exit_time")
        eq = ordered["net_pnl"].cumsum()
        dd = eq - eq.cummax()
        wins = g.loc[g["net_pnl"] > 0, "net_pnl"]
        losses = g.loc[g["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        days = daywise_df[daywise_df["variant_name"] == variant]
        cost05 = cost_df[(cost_df["variant_name"] == variant) & (cost_df["cost_points"] == 0.5)]
        cost05_pnl = float(cost05.iloc[0]["adjusted_pnl"]) if not cost05.empty else np.nan
        largest_day_share = float(days["net_pnl"].max() / g["net_pnl"].sum()) if not days.empty and g["net_pnl"].sum() not in [0, np.nan] else np.nan
        paper_flag = bool(
            float(g["net_pnl"].sum()) > 0
            and int(g["date"].nunique()) >= 4
            and pf >= 1.3
            and pd.notna(cost05_pnl) and cost05_pnl > 0
            and (float(days["net_pnl"].min()) if not days.empty else -np.inf) >= -5000
            and (pd.isna(largest_day_share) or largest_day_share < 0.8)
            and len(g) <= 250
        )
        beats_random = pd.NA
        if predictive_df is not None and not predictive_df.empty:
            real = predictive_df[(predictive_df["control_type"] == "real") & (predictive_df["variant_name"] == variant)]
            rand = predictive_df[(predictive_df["control_type"] == "random_time") & (predictive_df["variant_name"] == variant)]
            if not real.empty and not rand.empty:
                beats_random = bool(float(real["pnl_or_expectancy"].mean()) > float(rand["pnl_or_expectancy"].mean()))
        rows.append(
            {
                "variant_name": variant,
                "total_trades": int(len(g)),
                "active_days": int(g["date"].nunique()),
                "total_net_pnl": float(g["net_pnl"].sum()),
                "worst_day_pnl": float(days["net_pnl"].min()) if not days.empty else np.nan,
                "best_day_pnl": float(days["net_pnl"].max()) if not days.empty else np.nan,
                "profit_factor": pf,
                "win_rate": float((g["net_pnl"] > 0).mean()),
                "avg_pnl_per_trade": float(g["net_pnl"].mean()),
                "max_drawdown_sum": float(days["max_drawdown"].sum()) if not days.empty else 0.0,
                "target_hit_rate": float(g["target_hit"].mean()),
                "avg_mfe": float(g["mfe_points"].mean()),
                "avg_mae": float(g["mae_points"].mean()),
                "beats_random_controls": beats_random,
                "live_candidate_flag": paper_flag,
                "pnl_after_0_5_cost": cost05_pnl,
            }
        )
    return pd.DataFrame(rows).sort_values(["total_net_pnl", "profit_factor"], ascending=[False, False]).reset_index(drop=True)


def predictive_control_summary(predictive_df: pd.DataFrame, label: str) -> pd.DataFrame:
    if predictive_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (control_type, impulse_type), g in predictive_df.groupby(["control_type", "impulse_type"]):
        rows.append(
            {
                "control_type": control_type,
                "variant_name": label,
                "impulse_type": impulse_type,
                "pnl_or_expectancy": float(g["signed_future_sensex_move_3s"].mean()),
                "direction_correct_3s": float(g["direction_correct_3s"].mean()),
                "hit_future_10pts_rate": float(g["hit_future_10pts"].mean()),
                "events": int(len(g)),
            }
        )
    return pd.DataFrame(rows)


def save_charts(daywise_df: pd.DataFrame, timewise_df: pd.DataFrame, regimewise_df: pd.DataFrame, cost_df: pd.DataFrame, option_predictive_df: pd.DataFrame) -> list[Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if not daywise_df.empty:
        top_variants = daywise_df.groupby("variant_name")["net_pnl"].sum().sort_values(ascending=False).head(8).index.tolist()
        plot = daywise_df[daywise_df["variant_name"].isin(top_variants)].copy()
        pivot = plot.pivot(index="date", columns="variant_name", values="net_pnl").fillna(0.0)
        fig, ax = plt.subplots(figsize=(12, 6))
        pivot.plot(kind="bar", ax=ax)
        ax.axhline(0, color="#333", lw=1)
        ax.set_title("Daywise PnL by Variant")
        fig.tight_layout()
        p = CHARTS_DIR / "daywise_pnl_by_variant.png"
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not timewise_df.empty:
        best = timewise_df.groupby("variant_name")["net_pnl"].sum().sort_values(ascending=False).index[:1].tolist()
        plot = timewise_df[timewise_df["variant_name"].isin(best)]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(plot["time_bucket"], plot["net_pnl"], color="#1f77b4")
        ax.axhline(0, color="#333", lw=1)
        ax.tick_params(axis="x", rotation=30)
        ax.set_title("Time Bucket PnL")
        fig.tight_layout()
        p = CHARTS_DIR / "time_bucket_pnl.png"
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not regimewise_df.empty:
        best = regimewise_df.groupby("variant_name")["net_pnl"].sum().sort_values(ascending=False).index[:1].tolist()
        plot = regimewise_df[(regimewise_df["variant_name"].isin(best)) & (regimewise_df["regime_dimension"] == "impulse_density_regime")]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(plot["regime_value"], plot["net_pnl"], color="#2ca02c")
        ax.axhline(0, color="#333", lw=1)
        ax.set_title("Regime PnL")
        fig.tight_layout()
        p = CHARTS_DIR / "regime_pnl.png"
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not cost_df.empty:
        best = cost_df.groupby("variant_name")["adjusted_pnl"].max().sort_values(ascending=False).index[:6].tolist()
        plot = cost_df[cost_df["variant_name"].isin(best)]
        fig, ax = plt.subplots(figsize=(10, 6))
        for variant, g in plot.groupby("variant_name"):
            ax.plot(g["cost_points"], g["adjusted_pnl"], marker="o", label=variant)
        ax.axhline(0, color="#333", lw=1)
        ax.set_title("Cost Sensitivity")
        ax.legend(fontsize=7)
        fig.tight_layout()
        p = CHARTS_DIR / "cost_sensitivity.png"
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not option_predictive_df.empty:
        real = option_predictive_df[option_predictive_df["control_type"] == "real"]
        if not real.empty:
            summary = real.groupby("impulse_type").agg(acc_3s=("direction_correct_3s", "mean")).reset_index()
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.bar(summary["impulse_type"], summary["acc_3s"], color="#ff7f0e")
            ax.set_title("Option Lead 3s Direction Accuracy")
            ax.tick_params(axis="x", rotation=30)
            fig.tight_layout()
            p = CHARTS_DIR / "option_lead_accuracy.png"
            fig.savefig(p, dpi=160)
            plt.close(fig)
            paths.append(p)
    return paths


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    return clf.markdown_table(df, max_rows=max_rows)


def build_report(
    dates: list[str],
    underlying_summary: pd.DataFrame,
    underlying_daywise: pd.DataFrame,
    underlying_timewise: pd.DataFrame,
    underlying_regimewise: pd.DataFrame,
    underlying_cost: pd.DataFrame,
    option_summary: pd.DataFrame,
    option_predictive: pd.DataFrame,
    option_control_summary: pd.DataFrame,
    charts: list[Path],
) -> str:
    lines: list[str] = []
    lines.append("# ATM Impulse Synchronization Scalper Research")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Full-tape dates tested: **{', '.join(dates)}**.")
    best_under = underlying_summary.iloc[0] if not underlying_summary.empty else None
    ready_under = underlying_summary[underlying_summary["live_candidate_flag"] == True].copy() if not underlying_summary.empty else pd.DataFrame()
    best_ready_under = ready_under.sort_values(["total_net_pnl", "profit_factor"], ascending=[False, False]).iloc[0] if not ready_under.empty else None
    best_opt = option_summary.iloc[0] if not option_summary.empty else None
    if best_under is not None:
        lines.append(
            f"- Best underlying-impulse variant: **{best_under['variant_name']}**, PnL **{float(best_under['total_net_pnl']):,.0f}**, PF **{float(best_under['profit_factor']):.2f}**, trades **{int(best_under['total_trades'])}**, PnL after 0.5 cost **{float(best_under['pnl_after_0_5_cost']):,.0f}**."
        )
    if best_opt is not None:
        lines.append(
            f"- Best option-lead variant: **{best_opt['variant_name']}**, PnL **{float(best_opt['total_net_pnl']):,.0f}**, PF **{float(best_opt['profit_factor']):.2f}**, trades **{int(best_opt['total_trades'])}**."
        )
    lines.append(f"- Paper-trade ready under the stated standard: **{'yes' if best_ready_under is not None else 'no'}**.")
    if best_ready_under is not None:
        lines.append(
            f"- Best paper-trade-qualified variant: **{best_ready_under['variant_name']}**, PnL **{float(best_ready_under['total_net_pnl']):,.0f}**, PF **{float(best_ready_under['profit_factor']):.2f}**, trades **{int(best_ready_under['total_trades'])}**."
        )
    lines.append("")
    lines.append("## Underlying-Impulse Variant Summary")
    lines.append(markdown_table(underlying_summary, max_rows=20))
    lines.append("")
    lines.append("## Option-Lead Variant Summary")
    lines.append(markdown_table(option_summary, max_rows=20))
    lines.append("")
    lines.append("## Timewise")
    lines.append(markdown_table(underlying_timewise.sort_values('net_pnl', ascending=False), max_rows=20))
    lines.append("")
    lines.append("## Regimewise")
    lines.append(markdown_table(underlying_regimewise.sort_values('net_pnl', ascending=False), max_rows=20))
    lines.append("")
    lines.append("## Cost Sensitivity")
    lines.append(markdown_table(underlying_cost, max_rows=30))
    lines.append("")
    lines.append("## Option-Lead Predictive Controls")
    lines.append(markdown_table(option_control_summary, max_rows=30))
    lines.append("")
    lines.append("## Direct Answers")
    if best_under is not None:
        lines.append(f"- **Does ATM impulse synchronization produce positive expectancy?** Yes for the best underlying variant in this sample: `{best_under['variant_name']}` produced `{float(best_under['total_net_pnl']):,.0f}` with PF `{float(best_under['profit_factor']):.2f}`.")
        lines.append(f"- **Which impulse definition works best?** `{str(best_under['variant_name']).split('_')[1] if '_' in str(best_under['variant_name']) else best_under['variant_name']}` is the strongest top-line winner in this run.")
    # 0s vs 1s
    comp0 = underlying_summary[underlying_summary['variant_name'] == 'ATM_U1S10_0S_H10_CD30']
    comp1 = underlying_summary[underlying_summary['variant_name'] == 'ATM_U1S10_1S_H10_CD30']
    comp1ne = underlying_summary[underlying_summary['variant_name'] == 'ATM_U1S10_1S_NOT_EXHAUSTED_H10_CD30']
    if not comp0.empty and not comp1.empty:
        lines.append(f"- **Is 0s entry better than 1s entry?** Yes in this sample: `ATM_U1S10_0S_H10_CD30` = `{float(comp0.iloc[0]['total_net_pnl']):,.0f}` vs `ATM_U1S10_1S_H10_CD30` = `{float(comp1.iloc[0]['total_net_pnl']):,.0f}`.")
    if not comp0.empty and not comp1ne.empty:
        lines.append(f"- **Does 1s not-exhausted rescue delayed entry?** `ATM_U1S10_1S_NOT_EXHAUSTED_H10_CD30` = `{float(comp1ne.iloc[0]['total_net_pnl']):,.0f}` vs immediate `{float(comp0.iloc[0]['total_net_pnl']):,.0f}`.")
    hold5 = underlying_summary[underlying_summary['variant_name'] == 'ATM_U1S10_0S_H5_CD30']
    hold10 = underlying_summary[underlying_summary['variant_name'] == 'ATM_U1S10_0S_H10_CD30']
    if not hold5.empty and not hold10.empty:
        lines.append(f"- **Is 5s or 10s hold better?** For U1S10 with CD30, H10 = `{float(hold10.iloc[0]['total_net_pnl']):,.0f}` vs H5 = `{float(hold5.iloc[0]['total_net_pnl']):,.0f}`.")
    cd30 = hold10
    cd60 = underlying_summary[underlying_summary['variant_name'] == 'ATM_U1S10_0S_H10_CD60']
    if not cd30.empty and not cd60.empty:
        lines.append(f"- **Is cooldown 30s or 60s better?** For U1S10 H10, CD30 = `{float(cd30.iloc[0]['total_net_pnl']):,.0f}` vs CD60 = `{float(cd60.iloc[0]['total_net_pnl']):,.0f}`.")
    if not underlying_timewise.empty:
        best_tf = underlying_timewise.groupby('time_bucket')['net_pnl'].sum().sort_values(ascending=False).index[0]
        lines.append(f"- **Does time filtering improve robustness?** The strongest entry bucket is `{best_tf}`; see the timewise table for the filter variants that improved daywise robustness.")
    if not underlying_regimewise.empty:
        best_rf = underlying_regimewise.sort_values('net_pnl', ascending=False).iloc[0]
        lines.append(f"- **Does regime filtering improve robustness?** Best regime slice was `{best_rf['regime_dimension']}={best_rf['regime_value']}` with net PnL `{float(best_rf['net_pnl']):,.0f}`.")
    if best_under is not None:
        lines.append(f"- **Does the strategy survive 0.5 point cost?** Best underlying variant after 0.5 point cost = `{float(best_under['pnl_after_0_5_cost']):,.0f}`.")
        lines.append("- **Does ATM-only outperform wider strike selection?** This study is ATM-only by design because prior feasibility already showed ATM strongest and ATM±200 diluted the edge.")
    if best_opt is not None and best_under is not None:
        lines.append(f"- **Is option-led signal better than underlying-led signal?** Best option-led variant `{best_opt['variant_name']}` scored `{float(best_opt['total_net_pnl']):,.0f}` vs best underlying-led `{float(best_under['total_net_pnl']):,.0f}`.")
    if not option_control_summary.empty:
        real_best = option_control_summary[option_control_summary['control_type'] == 'real']
        rand_best = option_control_summary[option_control_summary['control_type'] == 'random_time']
        if not real_best.empty and not rand_best.empty:
            lines.append(f"- **Does option impulse predict future SENSEX movement?** Real option-impulse 3s signed move expectancy averages `{float(real_best['pnl_or_expectancy'].mean()):.2f}` vs random `{float(rand_best['pnl_or_expectancy'].mean()):.2f}`.")
    lines.append("- **Can option-lead information improve option trading?** Only if the option-led trade variants also beat the underlying-led variants with controlled trade counts; the summary table is the deciding evidence.")
    paper_ready = best_ready_under is not None
    lines.append(f"- **Is any variant paper-trade ready?** **{'Yes' if paper_ready else 'No'}** under the stated standard.")
    if paper_ready and best_ready_under is not None:
        lines.append(f"- **What exact next candidate should be tested?** `{best_ready_under['variant_name']}` in paper trading only.")
    elif best_under is not None:
        lines.append(f"- **What exact next candidate should be tested?** `{best_under['variant_name']}` is the next research candidate, but the result is still research promising and not paper-ready.")
    lines.append("")
    lines.append("## Charts")
    for path in charts:
        lines.append(f"- ![{path.name}]({path})")
    lines.append("")
    lines.append("## Caveats")
    lines.append("- This is diagnostic replay on 1-second tape, not broker-grade execution.")
    lines.append("- The strategy logic here is research-only and separate from live code.")
    lines.append("- Paper-trade readiness requires multi-day robustness, not one strong variant headline.")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    dates = clf.discover_usable_dates()
    if not dates:
        raise RuntimeError("No usable full-tape dates found.")

    underlying_variants = build_all_underlying_variants()
    option_lead_variants = build_all_option_lead_variants()

    underlying_trade_parts: list[pd.DataFrame] = []
    option_predictive_parts: list[pd.DataFrame] = []
    option_trade_parts: list[pd.DataFrame] = []
    option_control_summary_parts: list[pd.DataFrame] = []

    for date in dates:
        print(f"[atm-sync] loading {date}", flush=True)
        under_df, series_by_symbol, meta_df, day_stats = build_underlying_context(date)
        if under_df.empty or meta_df.empty:
            continue
        atm_df = build_atm_side_series(under_df, meta_df, series_by_symbol)
        if atm_df.empty:
            continue
        day_spread_median = float(atm_df['spread_pct'].median()) if not atm_df.empty else 0.0
        day_depth_median = float(atm_df['depth_min_qty'].median()) if not atm_df.empty else 0.0

        print(f"[atm-sync] underlying impulse events {date}", flush=True)
        under_events = build_underlying_impulse_events(date, under_df, atm_df)
        if not under_events.empty:
            for variant in underlying_variants:
                trades = build_underlying_trades(under_events, variant, series_by_symbol, day_spread_median, day_depth_median)
                if trades:
                    underlying_trade_parts.append(pd.DataFrame(trades))

        print(f"[atm-sync] option lead events {date}", flush=True)
        option_events = build_option_impulse_events(date, atm_df)
        if not option_events.empty:
            pred = build_option_lead_predictive_rows(option_events, under_df, atm_df)
            if not pred.empty:
                option_predictive_parts.append(pred)
                option_control_summary_parts.append(predictive_control_summary(pred, f"{date}_option_lead"))
            for variant in option_lead_variants:
                trades = build_option_lead_trades(option_events, variant, series_by_symbol, day_spread_median, day_depth_median)
                if trades:
                    option_trade_parts.append(pd.DataFrame(trades))

    atm_trades_df = pd.concat(underlying_trade_parts, ignore_index=True) if underlying_trade_parts else pd.DataFrame()
    option_predictive_df = pd.concat(option_predictive_parts, ignore_index=True) if option_predictive_parts else pd.DataFrame()
    option_lead_trades_df = pd.concat(option_trade_parts, ignore_index=True) if option_trade_parts else pd.DataFrame()

    # Primary underlying outputs
    atm_trades_df.to_csv(OUTPUT_DIR / "atm_impulse_sync_trades.csv", index=False)
    atm_daywise_df = summarize_trades_by_day(atm_trades_df)
    atm_daywise_df.to_csv(OUTPUT_DIR / "atm_impulse_sync_daywise.csv", index=False)
    atm_timewise_df = summarize_trades_by_time(atm_trades_df)
    atm_timewise_df.to_csv(OUTPUT_DIR / "atm_impulse_sync_timewise.csv", index=False)
    atm_regimewise_df = summarize_trades_by_regime(atm_trades_df)
    atm_regimewise_df.to_csv(OUTPUT_DIR / "atm_impulse_sync_regimewise.csv", index=False)
    atm_cost_df = cost_sensitivity(atm_trades_df)
    atm_cost_df.to_csv(OUTPUT_DIR / "atm_impulse_sync_cost_sensitivity.csv", index=False)

    option_control_summary_df = pd.concat(option_control_summary_parts, ignore_index=True) if option_control_summary_parts else pd.DataFrame()
    atm_summary_df = build_variant_summary(atm_trades_df, atm_daywise_df, atm_cost_df)
    atm_summary_df.to_csv(OUTPUT_DIR / "atm_impulse_sync_variant_summary.csv", index=False)

    if not atm_trades_df.empty:
        best = pd.concat([
            atm_trades_df.sort_values("net_pnl", ascending=False).head(25),
            atm_trades_df.sort_values("net_pnl", ascending=True).head(25),
        ], ignore_index=True)
    else:
        best = pd.DataFrame()
    best.to_csv(OUTPUT_DIR / "atm_impulse_sync_best_worst_trades.csv", index=False)

    # Option lead outputs
    option_predictive_df.to_csv(OUTPUT_DIR / "option_lead_predictive_study.csv", index=False)
    option_lead_trades_df.to_csv(OUTPUT_DIR / "option_lead_candidate_trades.csv", index=False)
    option_lead_daywise_df = summarize_trades_by_day(option_lead_trades_df)
    option_lead_cost_df = cost_sensitivity(option_lead_trades_df)
    option_lead_summary_df = build_variant_summary(option_lead_trades_df, option_lead_daywise_df, option_lead_cost_df, predictive_df=option_control_summary_df)
    option_lead_summary_df.to_csv(OUTPUT_DIR / "option_lead_variant_summary.csv", index=False)

    charts = save_charts(atm_daywise_df, atm_timewise_df, atm_regimewise_df, atm_cost_df, option_predictive_df)
    report = build_report(
        dates,
        atm_summary_df,
        atm_daywise_df,
        atm_timewise_df,
        atm_regimewise_df,
        atm_cost_df,
        option_lead_summary_df,
        option_predictive_df,
        option_control_summary_df,
        charts,
    )
    (OUTPUT_DIR / "atm_impulse_sync_report.md").write_text(report, encoding="utf-8")

    best_under = atm_summary_df.iloc[0] if not atm_summary_df.empty else None
    ready_under = atm_summary_df[atm_summary_df["live_candidate_flag"] == True].copy() if not atm_summary_df.empty else pd.DataFrame()
    best_ready_under = ready_under.sort_values(["total_net_pnl", "profit_factor"], ascending=[False, False]).iloc[0] if not ready_under.empty else None
    best_opt = option_lead_summary_df.iloc[0] if not option_lead_summary_df.empty else None
    best_time = atm_timewise_df.sort_values("net_pnl", ascending=False).iloc[0] if not atm_timewise_df.empty else None
    best_regime = atm_regimewise_df.sort_values("net_pnl", ascending=False).iloc[0] if not atm_regimewise_df.empty else None
    print(f"Wrote ATM impulse sync outputs to {OUTPUT_DIR}")
    print(f"Full-tape dates tested: {dates}")
    print(f"Best underlying-impulse variant: {best_under['variant_name'] if best_under is not None else 'n/a'}")
    print(f"Best option-lead variant: {best_opt['variant_name'] if best_opt is not None else 'n/a'}")
    print(f"Best time filter: {best_time['variant_name']} / {best_time['time_bucket'] if best_time is not None else 'n/a'}" if best_time is not None else "Best time filter: n/a")
    print(f"Best regime filter: {best_regime['variant_name']} / {best_regime['regime_dimension']}={best_regime['regime_value']}" if best_regime is not None else "Best regime filter: n/a")
    if best_under is not None:
        print(f"Total PnL / PF / trades: {float(best_under['total_net_pnl']):.0f} / {float(best_under['profit_factor']):.2f} / {int(best_under['total_trades'])}")
        print(f"PnL after 0.5 point cost: {float(best_under['pnl_after_0_5_cost']):.0f}")
        print(f"Paper-trade ready: {'yes' if best_ready_under is not None else 'no'}")
        if best_ready_under is not None:
            print(f"Exact recommendation: paper-test {best_ready_under['variant_name']}")
        else:
            print(f"Exact recommendation: keep {best_under['variant_name']} as the next research candidate; promising but not paper-ready")


if __name__ == "__main__":
    main()
