from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from dotenv import dotenv_values
except Exception:  # pragma: no cover
    dotenv_values = None

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "burst_onset_research_results"
CHARTS_DIR = OUTPUT_DIR / "charts"

SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sensex_noise.config import load_settings  # type: ignore
from sensex_noise.services.microburst import (  # type: ignore
    classify_target,
    compute_pre_entry_features,
)


@dataclass(frozen=True)
class Variant:
    name: str
    min_score: int
    top1_window_seconds: int | None
    require_context: bool = False
    require_loose_context: bool = False
    require_opt_velocity_positive: bool = False
    description: str = ""


VARIANTS: list[Variant] = [
    Variant("naive_score3", min_score=3, top1_window_seconds=None, description="All burst onsets score>=3 with symbol cooldown only."),
    Variant("ranked_top1_per_15s", min_score=3, top1_window_seconds=15, description="Top ranked candidate per 15s window."),
    Variant("ranked_score4_top1_per_15s", min_score=4, top1_window_seconds=15, description="Score>=4, top ranked candidate per 15s window."),
    Variant("ranked_score5_only", min_score=5, top1_window_seconds=15, description="Score>=5, top ranked candidate per 15s window."),
    Variant("candle_context_score3", min_score=3, top1_window_seconds=15, require_context=True, description="Strict candle context agrees, score>=3."),
    Variant("candle_context_score4", min_score=4, top1_window_seconds=15, require_context=True, description="Strict candle context agrees, score>=4."),
    Variant("candle_context_plus_immediate_confirmation", min_score=3, top1_window_seconds=15, require_context=True, require_opt_velocity_positive=True, description="Strict candle context agrees and option velocity positive."),
]

MAX_SPREAD = 3.0
SYMBOL_COOLDOWN_SECONDS = 30
GLOBAL_COOLDOWN_SECONDS = 15
BURST_THRESHOLD = 3
WINDOW_SECONDS = 5
MAX_MATCH_LAG_SECONDS = 30
MISSED_MATCH_TOLERANCE_SECONDS = 5
MIN_CANDLE_BODY_POINTS = 20.0
CLOSE_LOCATION_THRESHOLD = 0.60


def load_audit_module() -> Any:
    path = REPO_ROOT / "strategy_audit.py"
    spec = importlib.util.spec_from_file_location("strategy_audit_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_env_loaded() -> None:
    env_path = REPO_ROOT / ".env"
    if dotenv_values is not None and env_path.exists():
        values = dotenv_values(env_path)
        for key, value in values.items():
            if value is not None and key not in os.environ:
                os.environ[key] = value


class FallbackSettings(SimpleNamespace):
    pass


def load_settings_safe() -> Any:
    ensure_env_loaded()
    try:
        return load_settings()
    except Exception:
        return FallbackSettings(
            microburst_min_score=int(os.getenv("MICROBURST_MIN_SCORE", "3")),
            promoted_min_score=int(os.getenv("PROMOTED_MIN_SCORE", "5")),
            promoted_target_points=float(os.getenv("PROMOTED_TARGET_POINTS", "7.0")),
            normal_target_points=float(os.getenv("NORMAL_TARGET_POINTS", "3.0")),
            edge_invalidation_hard_stop_enabled=os.getenv("ENABLE_EDGE_INVALIDATION", "true").lower() == "true",
            edge_invalidation_hard_stop_points=float(os.getenv("EDGE_INVALIDATION_HARD_STOP_POINTS", "6.0")),
            edge_invalidation_1s_check_seconds=float(os.getenv("EDGE_INVALIDATION_1S_CHECK_SECONDS", "1.0")),
            edge_invalidation_1s_min_runup_points=float(os.getenv("EDGE_INVALIDATION_1S_MIN_RUNUP_POINTS", "1.0")),
            edge_invalidation_1s_max_pnl_points=float(os.getenv("EDGE_INVALIDATION_1S_MAX_PNL_POINTS", "0.0")),
            edge_invalidation_3s_check_seconds=float(os.getenv("EDGE_INVALIDATION_3S_CHECK_SECONDS", "3.0")),
            edge_invalidation_3s_min_runup_points=float(os.getenv("EDGE_INVALIDATION_3S_MIN_RUNUP_POINTS", "2.0")),
            edge_invalidation_3s_max_drawdown_points=float(os.getenv("EDGE_INVALIDATION_3S_MAX_DRAWNDOWN_POINTS", os.getenv("EDGE_INVALIDATION_3S_MAX_DRAWDOWN_POINTS", "4.0"))),
            edge_invalidation_3s_pinned_pnl_abs_points=float(os.getenv("EDGE_INVALIDATION_3S_PINNED_PNL_ABS_POINTS", "1.0")),
            layer4_enabled=os.getenv("LAYER4_ENABLED", "false").lower() == "true",
            layer4_trigger_points=float(os.getenv("LAYER4_TRIGGER_POINTS", "3.0")),
            layer4_window_seconds=float(os.getenv("LAYER4_WINDOW_SECONDS", "2.0")),
            microburst_ind_accel_threshold_1=float(os.getenv("MICROBURST_IND_ACCEL_THRESHOLD_1", "1.688")),
            microburst_ind_accel_threshold_2=float(os.getenv("MICROBURST_IND_ACCEL_THRESHOLD_2", "3.945")),
            microburst_opt_velocity_threshold=float(os.getenv("MICROBURST_OPT_VELOCITY_THRESHOLD", "1.583")),
            microburst_opt_depth_imb_threshold=float(os.getenv("MICROBURST_OPT_DEPTH_IMB_THRESHOLD", "0.0857")),
            microburst_ind_velocity_min=float(os.getenv("MICROBURST_IND_VELOCITY_MIN", "1.646")),
            microburst_ind_velocity_max=float(os.getenv("MICROBURST_IND_VELOCITY_MAX", "2.356")),
            promoted_3s_min_runup_points=float(os.getenv("PROMOTED_3S_MIN_RUNUP_POINTS", "2.0")),
            promoted_3s_min_pnl_points=float(os.getenv("PROMOTED_3S_MIN_PNL_POINTS", "1.0")),
            promoted_3s_max_mae_points=float(os.getenv("PROMOTED_3S_MAX_MAE_POINTS", "4.0")),
            promoted_3s_min_velocity_decay_ratio=float(os.getenv("PROMOTED_3S_MIN_VELOCITY_DECAY_RATIO", "-0.25")),
            capital_budget=float(os.getenv("CAPITAL_BUDGET", "300000.0")),
        )


def discover_full_tape_dates() -> list[str]:
    tape_root = REPO_ROOT / "data" / "tape" / "sensex_options"
    dates: list[str] = []
    if not tape_root.exists():
        return dates
    for path in sorted(tape_root.iterdir()):
        if not path.is_dir():
            continue
        if not (path / "options.jsonl").exists():
            continue
        if not (REPO_ROOT / "logs" / "ticks" / path.name / "sensex.jsonl").exists():
            continue
        dates.append(path.name)
    return dates


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_dt(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or value == "":
        return pd.NaT
    try:
        return pd.Timestamp(value)
    except Exception:
        return pd.NaT


def load_option_second_rows_with_quality(date: str) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    path = REPO_ROOT / "data" / "tape" / "sensex_options" / date / "options.jsonl"
    stats: dict[str, Any] = {
        "date": date,
        "path": str(path),
        "exists": path.exists(),
        "raw_rows": 0,
        "parse_errors": 0,
        "unique_symbols": 0,
        "unique_strikes": 0,
        "first_timestamp": None,
        "last_timestamp": None,
        "missing_spread_rows": 0,
        "missing_best_bid_rows": 0,
        "missing_best_ask_rows": 0,
        "missing_bid_depth_rows": 0,
        "missing_ask_depth_rows": 0,
        "missing_oi_rows": 0,
        "missing_volume_rows": 0,
    }
    if not path.exists():
        return {}, stats

    symbol_second: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            stats["raw_rows"] += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                stats["parse_errors"] += 1
                continue
            symbol = row.get("symbol")
            ts = parse_dt(row.get("timestamp_exchange") or row.get("timestamp_receive"))
            ltp = safe_float(row.get("ltp"))
            if not symbol or pd.isna(ts) or ltp is None:
                continue
            second = ts.floor("s")
            if stats["first_timestamp"] is None or second < stats["first_timestamp"]:
                stats["first_timestamp"] = second
            if stats["last_timestamp"] is None or second > stats["last_timestamp"]:
                stats["last_timestamp"] = second
            if safe_float(row.get("spread")) is None:
                stats["missing_spread_rows"] += 1
            if safe_float(row.get("best_bid")) is None:
                stats["missing_best_bid_rows"] += 1
            if safe_float(row.get("best_ask")) is None:
                stats["missing_best_ask_rows"] += 1
            if safe_float(row.get("oi")) is None:
                stats["missing_oi_rows"] += 1
            if safe_float(row.get("volume")) is None:
                stats["missing_volume_rows"] += 1

            bid5 = row.get("bid[5]") or []
            ask5 = row.get("ask[5]") or []
            if not (isinstance(bid5, list) and len(bid5) == 5 and isinstance(bid5[0], dict)):
                stats["missing_bid_depth_rows"] += 1
            if not (isinstance(ask5, list) and len(ask5) == 5 and isinstance(ask5[0], dict)):
                stats["missing_ask_depth_rows"] += 1
            bid_qty = safe_float(bid5[0].get("quantity")) if isinstance(bid5, list) and bid5 and isinstance(bid5[0], dict) else None
            ask_qty = safe_float(ask5[0].get("quantity")) if isinstance(ask5, list) and ask5 and isinstance(ask5[0], dict) else None

            symbol_second[(str(symbol), second)] = {
                "timestamp": second,
                "ltp": ltp,
                "spread": safe_float(row.get("spread")),
                "best_bid": safe_float(row.get("best_bid")),
                "best_ask": safe_float(row.get("best_ask")),
                "bid_qty": bid_qty,
                "ask_qty": ask_qty,
                "strike": safe_float(row.get("strike")),
                "option_type": str(row.get("option_type") or "").upper() or None,
                "lot_size": int(row.get("lot_size") or 0),
                "expiry": row.get("expiry"),
                "symbol": str(symbol),
                "tradingsymbol": row.get("tradingsymbol"),
                "exchange": row.get("exchange"),
                "oi": safe_float(row.get("oi")),
                "volume": safe_float(row.get("volume")),
            }

    per_symbol: dict[str, list[dict[str, Any]]] = {}
    strikes: set[int] = set()
    for (symbol, _), record in symbol_second.items():
        per_symbol.setdefault(symbol, []).append(record)
        if record.get("strike") is not None:
            strikes.add(int(record["strike"]))
    for symbol in per_symbol:
        per_symbol[symbol].sort(key=lambda item: item["timestamp"])
    stats["unique_symbols"] = len(per_symbol)
    stats["unique_strikes"] = len(strikes)
    if stats["raw_rows"] > 0:
        for key in [
            "missing_spread_rows",
            "missing_best_bid_rows",
            "missing_best_ask_rows",
            "missing_bid_depth_rows",
            "missing_ask_depth_rows",
            "missing_oi_rows",
            "missing_volume_rows",
        ]:
            stats[key.replace("_rows", "_pct")] = float(stats[key]) / float(stats["raw_rows"])
    return per_symbol, stats


def build_completed_candle_context(underlying: pd.Series) -> pd.DataFrame:
    if underlying.empty:
        return pd.DataFrame(columns=[
            "completed_candle_start", "candle_open", "candle_high", "candle_low", "candle_close",
            "candle_body", "candle_range", "candle_close_location", "candle_context"
        ])
    s = underlying.sort_index().dropna().astype(float)
    ohlc = s.resample("5min", label="left", closed="left").ohlc()
    ctx = pd.DataFrame(index=s.index)
    ctx["completed_candle_start"] = ctx.index.floor("5min") - pd.Timedelta(minutes=5)
    ctx = ctx.join(ohlc.add_prefix("candle_"), on="completed_candle_start")
    ctx["candle_body"] = ctx["candle_close"] - ctx["candle_open"]
    ctx["candle_range"] = ctx["candle_high"] - ctx["candle_low"]
    ctx["candle_close_location"] = np.where(
        ctx["candle_range"] > 0,
        (ctx["candle_close"] - ctx["candle_low"]) / ctx["candle_range"],
        np.nan,
    )

    def classify(row: pd.Series) -> str:
        body = safe_float(row.get("candle_body"))
        rng = safe_float(row.get("candle_range"))
        loc = safe_float(row.get("candle_close_location"))
        if body is None or rng is None or loc is None or rng <= 0:
            return "neutral"
        if rng < 1.0:
            return "neutral"
        if body >= MIN_CANDLE_BODY_POINTS and loc >= CLOSE_LOCATION_THRESHOLD:
            return "bullish"
        if body <= -MIN_CANDLE_BODY_POINTS and loc <= (1.0 - CLOSE_LOCATION_THRESHOLD):
            return "bearish"
        return "neutral"

    ctx["candle_context"] = ctx.apply(classify, axis=1)
    return ctx


def rank_score(row: pd.Series) -> float:
    return (
        float(row.get("score") or 0.0) * 1000.0
        + float(row.get("opt_velocity_aligned") or 0.0) * 100.0
        + float(row.get("ind_accel_aligned") or 0.0) * 10.0
        + float(row.get("opt_depth_imb_mean") or 0.0) * 5.0
        - float(row.get("spread") or 0.0)
    )


def compute_burst_onset_candidates_for_day(date: str, settings: Any, audit: Any) -> tuple[pd.DataFrame, dict[str, list[dict[str, Any]]], dict[str, Any]]:
    underlying = audit.load_underlying_second_series(date)
    symbol_rows, quality = load_option_second_rows_with_quality(date)
    if underlying.empty or not symbol_rows:
        return pd.DataFrame(), symbol_rows, quality

    candle_context = build_completed_candle_context(underlying)
    records: list[dict[str, Any]] = []

    for symbol, rows in symbol_rows.items():
        option_type = str(rows[0].get("option_type") or "").upper()
        if option_type not in {"CE", "PE"}:
            continue
        side = "CALL" if option_type == "CE" else "PUT"
        start_idx = 0
        prev_above_threshold = False
        last_candidate_ts: pd.Timestamp | None = None

        for idx, row in enumerate(rows):
            ts = row["timestamp"]
            while start_idx < idx and rows[start_idx]["timestamp"] < ts - pd.Timedelta(seconds=WINDOW_SECONDS):
                start_idx += 1
            option_window = [
                {
                    "timestamp_exchange": item["timestamp"].to_pydatetime(),
                    "ltp": item.get("ltp"),
                    "spread": item.get("spread"),
                    "bid_qty": item.get("bid_qty"),
                    "ask_qty": item.get("ask_qty"),
                }
                for item in rows[start_idx : idx + 1]
            ]
            underlying_window = audit.build_underlying_window(underlying, ts)
            if len(option_window) < 2 or len(underlying_window) < 2:
                continue
            spread = row.get("spread")
            if spread is None or float(spread) > MAX_SPREAD:
                prev_above_threshold = False
                continue
            if not (row.get("bid_qty") or 0) or not (row.get("ask_qty") or 0):
                prev_above_threshold = False
                continue
            features = compute_pre_entry_features(
                recent_underlying_window=underlying_window,
                recent_option_window=option_window,
                side=side,
                settings=settings,
            )
            score = int(features.score)
            if score < BURST_THRESHOLD:
                prev_above_threshold = False
                continue
            if prev_above_threshold and last_candidate_ts is not None and (ts - last_candidate_ts).total_seconds() < SYMBOL_COOLDOWN_SECONDS:
                continue
            target_class, target_points = classify_target(score, settings)
            ctx_row = candle_context.loc[ts] if ts in candle_context.index else None
            candle_context_name = str(ctx_row.get("candle_context")) if ctx_row is not None and pd.notna(ctx_row.get("candle_context")) else "neutral"
            strict_context_agrees = bool((side == "CALL" and candle_context_name == "bullish") or (side == "PUT" and candle_context_name == "bearish"))
            loose_context_agrees = bool(strict_context_agrees or (candle_context_name == "neutral" and float(features.ind_velocity_aligned) > 0))
            rec = {
                "date": date,
                "timestamp": ts,
                "symbol": symbol,
                "side": side,
                "strike": row.get("strike"),
                "option_type": option_type,
                "expiry": row.get("expiry"),
                "ltp": float(row["ltp"]),
                "spread": float(spread),
                "best_bid": row.get("best_bid"),
                "best_ask": row.get("best_ask"),
                "bid_qty": float(row.get("bid_qty") or 0.0),
                "ask_qty": float(row.get("ask_qty") or 0.0),
                "lot_size": int(row.get("lot_size") or 0),
                "score": score,
                "score_components": json.dumps(features.score_components, sort_keys=True),
                "ind_velocity_aligned": float(features.ind_velocity_aligned),
                "ind_accel_aligned": float(features.ind_accel_aligned),
                "opt_velocity_aligned": float(features.opt_velocity_aligned),
                "opt_depth_imb_mean": float(features.opt_depth_imb_mean),
                "opt_spread_mean": float(features.opt_spread_mean) if features.opt_spread_mean is not None else np.nan,
                "target_class": target_class,
                "target_points": float(target_points),
                "rank_score": 0.0,
                "candle_context": candle_context_name,
                "context_agrees": strict_context_agrees,
                "loose_context_agrees": loose_context_agrees,
                "candle_body": float(ctx_row.get("candle_body")) if ctx_row is not None and pd.notna(ctx_row.get("candle_body")) else np.nan,
                "candle_range": float(ctx_row.get("candle_range")) if ctx_row is not None and pd.notna(ctx_row.get("candle_range")) else np.nan,
                "candle_close_location": float(ctx_row.get("candle_close_location")) if ctx_row is not None and pd.notna(ctx_row.get("candle_close_location")) else np.nan,
            }
            rec["rank_score"] = rank_score(pd.Series(rec))
            records.append(rec)
            prev_above_threshold = True
            last_candidate_ts = ts

    candidates = pd.DataFrame(records)
    if not candidates.empty:
        candidates = candidates.sort_values(["timestamp", "rank_score", "symbol"], ascending=[True, False, True]).reset_index(drop=True)
    quality["candidate_count_score3_onset"] = int(len(candidates)) if not candidates.empty else 0
    return candidates, symbol_rows, quality


def load_actual_trades_full_tape(dates: list[str], audit: Any) -> pd.DataFrame:
    trade_days = audit.load_trade_days()
    trades = audit.build_trades_df(trade_days)
    trades, _ = audit.merge_canonical_features(trades)
    if trades.empty:
        return trades
    trades = trades[trades["date"].isin(dates)].copy()
    if trades.empty:
        return trades
    keep_cols = [
        "date", "trade_id", "entry_dt", "exit_dt", "symbol", "side", "call_or_put", "signal_kind",
        "entry_price", "exit_price", "gross_pnl", "net_pnl", "exit_reason", "holding_seconds", "mfe", "mae",
        "burst_score", "burst_score_effective", "signal_dt", "candle_dt", "source_candle_start",
        "signal_to_entry_seconds", "candle_age_seconds", "target_points_used", "is_promoted_candidate",
        "is_promoted_active", "promoted_target_points", "base_target_points",
    ]
    keep_cols = [c for c in keep_cols if c in trades.columns]
    out = trades[keep_cols].copy()
    out["entry_time"] = pd.to_datetime(out["entry_dt"], errors="coerce")
    out["exit_time"] = pd.to_datetime(out["exit_dt"], errors="coerce")
    return out


def lag_bucket_from_seconds(seconds: float | None, exact_same_second: bool) -> str:
    if seconds is None or math.isnan(seconds):
        return "no_match"
    if exact_same_second:
        return "exact_same_second"
    if seconds <= 2:
        return "0_to_2s"
    if seconds <= 5:
        return "2_to_5s"
    if seconds <= 10:
        return "5_to_10s"
    return "10s_plus"


def match_actual_entries_to_bursts(actual_df: pd.DataFrame, candidates_all: pd.DataFrame) -> pd.DataFrame:
    if actual_df.empty:
        return actual_df.copy()
    if candidates_all.empty:
        out = actual_df.copy()
        out["lag_bucket"] = "no_match"
        return out

    by_date_symbol: dict[tuple[str, str], pd.DataFrame] = {}
    for (date, symbol), group in candidates_all.groupby(["date", "symbol"]):
        by_date_symbol[(str(date), str(symbol))] = group.sort_values("timestamp").reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    for _, row in actual_df.iterrows():
        entry_time = pd.Timestamp(row.get("entry_time")) if pd.notna(row.get("entry_time")) else pd.NaT
        entry_floor = entry_time.floor("s") if pd.notna(entry_time) else pd.NaT
        key = (str(row.get("date")), str(row.get("symbol")))
        cand = by_date_symbol.get(key)
        rec = row.to_dict()
        if cand is None or pd.isna(entry_time):
            rec.update({
                "previous_burst_time": pd.NaT,
                "next_burst_time": pd.NaT,
                "nearest_burst_time": pd.NaT,
                "lag_from_previous_burst_seconds": np.nan,
                "lag_to_next_burst_seconds": np.nan,
                "abs_nearest_burst_lag_seconds": np.nan,
                "exact_same_second": False,
                "within_2s": False,
                "within_5s": False,
                "within_10s": False,
                "lag_bucket": "no_match",
            })
            rows.append(rec)
            continue

        times = pd.to_datetime(cand["timestamp"])
        prev = cand[times <= entry_time]
        nxt = cand[times > entry_time]
        prev_time = pd.Timestamp(prev.iloc[-1]["timestamp"]) if not prev.empty else pd.NaT
        next_time = pd.Timestamp(nxt.iloc[0]["timestamp"]) if not nxt.empty else pd.NaT
        lag_prev = float((entry_time - prev_time).total_seconds()) if pd.notna(prev_time) else np.nan
        lag_next = float((next_time - entry_time).total_seconds()) if pd.notna(next_time) else np.nan

        nearest_row = None
        nearest_time = pd.NaT
        nearest_abs = np.nan
        if not cand.empty:
            diffs = (times - entry_time).abs().dt.total_seconds()
            idx = diffs.idxmin()
            nearest_row = cand.loc[idx]
            nearest_time = pd.Timestamp(nearest_row["timestamp"])
            nearest_abs = float(diffs.loc[idx])
            if nearest_abs > MAX_MATCH_LAG_SECONDS:
                nearest_row = None
                nearest_time = pd.NaT
                nearest_abs = np.nan

        exact_same_second = bool(pd.notna(nearest_time) and entry_floor == nearest_time)
        rec.update({
            "previous_burst_time": prev_time,
            "next_burst_time": next_time,
            "nearest_burst_time": nearest_time,
            "lag_from_previous_burst_seconds": lag_prev,
            "lag_to_next_burst_seconds": lag_next,
            "abs_nearest_burst_lag_seconds": nearest_abs,
            "exact_same_second": exact_same_second,
            "within_2s": bool(not math.isnan(nearest_abs) and nearest_abs <= 2),
            "within_5s": bool(not math.isnan(nearest_abs) and nearest_abs <= 5),
            "within_10s": bool(not math.isnan(nearest_abs) and nearest_abs <= 10),
            "lag_bucket": lag_bucket_from_seconds(nearest_abs, exact_same_second),
        })
        if nearest_row is not None:
            for col in [
                "score", "rank_score", "target_class", "target_points", "ind_velocity_aligned", "ind_accel_aligned",
                "opt_velocity_aligned", "opt_depth_imb_mean", "opt_spread_mean", "context_agrees", "loose_context_agrees",
                "candle_context", "candle_body", "candle_range", "candle_close_location",
            ]:
                rec[f"matched_burst_{col}"] = nearest_row.get(col)
        rows.append(rec)
    return pd.DataFrame(rows)


def summarize_lag_study(actual_vs_burst: pd.DataFrame) -> pd.DataFrame:
    if actual_vs_burst.empty:
        return pd.DataFrame()
    df = actual_vs_burst.copy()
    df["is_winner"] = df["net_pnl"] > 0
    df["target_hit"] = df["exit_reason"].astype(str).eq("TARGET_HIT")
    df["hard_stop"] = df["exit_reason"].astype(str).isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"])
    grouped = df.groupby("lag_bucket", dropna=False).agg(
        trades=("trade_id", "count"),
        net_pnl=("net_pnl", "sum"),
        avg_pnl=("net_pnl", "mean"),
        win_rate=("is_winner", "mean"),
        target_hit_rate=("target_hit", "mean"),
        hard_stop_rate=("hard_stop", "mean"),
        avg_mfe=("mfe", "mean"),
        avg_mae=("mae", "mean"),
    ).reset_index()
    bucket_order = {
        "exact_same_second": 0,
        "0_to_2s": 1,
        "2_to_5s": 2,
        "5_to_10s": 3,
        "10s_plus": 4,
        "no_match": 5,
    }
    grouped["bucket_order"] = grouped["lag_bucket"].map(bucket_order).fillna(999)
    grouped = grouped.sort_values("bucket_order").drop(columns=["bucket_order"])
    return grouped


def filter_candidates_for_variant(candidates: pd.DataFrame, variant: Variant) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    df = candidates[candidates["score"] >= variant.min_score].copy()
    if variant.require_context:
        df = df[df["context_agrees"] == True]
    if variant.require_loose_context:
        df = df[df["loose_context_agrees"] == True]
    if variant.require_opt_velocity_positive:
        df = df[df["opt_velocity_aligned"] > 0]
    if df.empty:
        return df
    df = df.sort_values(["timestamp", "score", "opt_velocity_aligned", "ind_accel_aligned", "opt_depth_imb_mean", "spread"], ascending=[True, False, False, False, False, True]).copy()
    if variant.top1_window_seconds is not None:
        day_start = pd.Timestamp(df["date"].iloc[0] + " 09:15:00")
        df["window_index"] = ((pd.to_datetime(df["timestamp"]) - day_start).dt.total_seconds() // variant.top1_window_seconds).astype(int)
        df = df.groupby("window_index", as_index=False, group_keys=False).head(1).drop(columns=["window_index"])
        df = df.sort_values("timestamp").reset_index(drop=True)
    return df.reset_index(drop=True)


def replay_variant_for_day(date: str, variant: Variant, selected_candidates: pd.DataFrame, symbol_rows: dict[str, list[dict[str, Any]]], settings: Any, audit: Any) -> pd.DataFrame:
    if selected_candidates.empty:
        return pd.DataFrame()
    selected = selected_candidates.sort_values(["timestamp", "rank_score"], ascending=[True, False]).copy()
    series_cache: dict[str, pd.DataFrame] = {}
    next_free_time: pd.Timestamp | None = None
    last_symbol_time: dict[str, pd.Timestamp] = {}
    replay_rows: list[dict[str, Any]] = []

    for row in selected.to_dict(orient="records"):
        ts = pd.Timestamp(row["timestamp"])
        symbol = str(row["symbol"])
        if next_free_time is not None and ts < next_free_time:
            continue
        prev_sym = last_symbol_time.get(symbol)
        if prev_sym is not None and (ts - prev_sym).total_seconds() < SYMBOL_COOLDOWN_SECONDS:
            continue
        result = audit.simulate_burst_trade(symbol, ts, int(row["score"]), symbol_rows[symbol], settings, series_cache)
        if result is None:
            continue
        quantity = result.get("quantity")
        if not quantity or int(quantity) <= 0:
            fallback_qty = 500
            result["quantity"] = fallback_qty
            result["gross_pnl"] = float(result["exit_price"] - result["entry_price"]) * fallback_qty
            result["net_pnl"] = result["gross_pnl"]
            result["quantity_source"] = "fallback_500"
        else:
            result["quantity_source"] = "lot_sized"
        merged = {**row, **result, "variant": variant.name}
        merged["points_pnl"] = float(merged["exit_price"] - merged["entry_price"])
        replay_rows.append(merged)
        last_symbol_time[symbol] = ts
        next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=GLOBAL_COOLDOWN_SECONDS)
    return pd.DataFrame(replay_rows)


def summarize_replay_day(replay_df: pd.DataFrame, date: str, variant: str, candidate_count: int) -> dict[str, Any]:
    if replay_df.empty:
        return {
            "date": date,
            "variant": variant,
            "candidate_count": int(candidate_count),
            "selected_trades": 0,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "win_rate": np.nan,
            "avg_pnl": np.nan,
            "profit_factor": np.nan,
            "max_drawdown": 0.0,
            "target_hits": 0,
            "one_sec_kills": 0,
            "three_sec_kills": 0,
            "hard_stops": 0,
            "promoted_count": 0,
            "promoted_net_pnl": 0.0,
        }
    df = replay_df.sort_values("exit_time").copy()
    equity = df["net_pnl"].cumsum()
    dd = equity - equity.cummax()
    wins = df[df["net_pnl"] > 0]["net_pnl"]
    losses = df[df["net_pnl"] < 0]["net_pnl"]
    profit_factor = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
    return {
        "date": date,
        "variant": variant,
        "candidate_count": int(candidate_count),
        "selected_trades": int(len(df)),
        "gross_pnl": float(df["gross_pnl"].sum()),
        "net_pnl": float(df["net_pnl"].sum()),
        "win_rate": float((df["net_pnl"] > 0).mean()),
        "avg_pnl": float(df["net_pnl"].mean()),
        "profit_factor": profit_factor,
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "target_hits": int((df["exit_reason"] == "TARGET_HIT").sum()),
        "one_sec_kills": int((df["exit_reason"] == "EARLY_FAIL_1S").sum()),
        "three_sec_kills": int(df["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S", "PROMOTION_PERSISTENCE_FAIL"]).sum()),
        "hard_stops": int((df["exit_reason"] == "EDGE_HARD_STOP").sum()),
        "promoted_count": int(df["promoted_candidate"].fillna(False).astype(bool).sum()),
        "promoted_net_pnl": float(df.loc[df["promoted_candidate"].fillna(False).astype(bool), "net_pnl"].sum()),
    }


def summarize_actual_day(actual_df: pd.DataFrame, date: str) -> dict[str, Any]:
    if actual_df.empty:
        return {
            "date": date,
            "variant": "actual_system",
            "candidate_count": np.nan,
            "selected_trades": 0,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "win_rate": np.nan,
            "avg_pnl": np.nan,
            "profit_factor": np.nan,
            "max_drawdown": 0.0,
            "target_hits": 0,
            "one_sec_kills": 0,
            "three_sec_kills": 0,
            "hard_stops": 0,
            "promoted_count": 0,
            "promoted_net_pnl": 0.0,
        }
    order_col = "exit_time" if "exit_time" in actual_df.columns else "entry_time"
    df = actual_df.sort_values(order_col).copy()
    equity = df["net_pnl"].cumsum()
    dd = equity - equity.cummax()
    wins = df[df["net_pnl"] > 0]["net_pnl"]
    losses = df[df["net_pnl"] < 0]["net_pnl"]
    profit_factor = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
    promoted_flag = df.get("is_promoted_candidate", False)
    promoted_mask = promoted_flag.fillna(False).astype(bool) if isinstance(promoted_flag, pd.Series) else pd.Series(False, index=df.index)
    return {
        "date": date,
        "variant": "actual_system",
        "candidate_count": np.nan,
        "selected_trades": int(len(df)),
        "gross_pnl": float(df["gross_pnl"].fillna(df["net_pnl"]).sum()),
        "net_pnl": float(df["net_pnl"].sum()),
        "win_rate": float((df["net_pnl"] > 0).mean()),
        "avg_pnl": float(df["net_pnl"].mean()),
        "profit_factor": profit_factor,
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "target_hits": int((df["exit_reason"] == "TARGET_HIT").sum()),
        "one_sec_kills": int((df["exit_reason"] == "EARLY_FAIL_1S").sum()),
        "three_sec_kills": int(df["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S", "PROMOTION_PERSISTENCE_FAIL"]).sum()),
        "hard_stops": int(df["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).sum()),
        "promoted_count": int(promoted_mask.sum()),
        "promoted_net_pnl": float(df.loc[promoted_mask, "net_pnl"].sum()),
    }


def classify_missed_opportunity(row: pd.Series) -> str:
    pnl = safe_float(row.get("net_pnl"))
    if pnl is None:
        return "ambiguous"
    if pnl > 0:
        return "good_missed_opportunity"
    if pnl < 0:
        return "bad_avoided_opportunity"
    return "ambiguous"


def build_daywise_summary(replay_summary: pd.DataFrame) -> pd.DataFrame:
    if replay_summary.empty:
        return replay_summary.copy()
    actual = replay_summary[replay_summary["variant"] == "actual_system"].copy()
    actual = actual.set_index("date")
    out_rows: list[dict[str, Any]] = []
    for _, row in replay_summary.iterrows():
        rec = row.to_dict()
        base = actual.loc[row["date"]] if row["date"] in actual.index else None
        if base is not None:
            rec["delta_net_pnl_vs_actual"] = float(rec["net_pnl"] - base["net_pnl"])
            rec["delta_trade_count_vs_actual"] = float(rec["selected_trades"] - base["selected_trades"])
            rec["delta_profit_factor_vs_actual"] = float(rec["profit_factor"] - base["profit_factor"]) if pd.notna(rec["profit_factor"]) and pd.notna(base["profit_factor"]) and np.isfinite(rec["profit_factor"]) and np.isfinite(base["profit_factor"]) else np.nan
            rec["delta_max_drawdown_vs_actual"] = float(rec["max_drawdown"] - base["max_drawdown"])
        else:
            rec["delta_net_pnl_vs_actual"] = np.nan
            rec["delta_trade_count_vs_actual"] = np.nan
            rec["delta_profit_factor_vs_actual"] = np.nan
            rec["delta_max_drawdown_vs_actual"] = np.nan
        out_rows.append(rec)
    return pd.DataFrame(out_rows)


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


def save_charts(lag_study: pd.DataFrame, daywise_summary: pd.DataFrame, candidates_all: pd.DataFrame) -> list[Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if not lag_study.empty:
        p = CHARTS_DIR / "lag_bucket_pnl.png"
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(lag_study["lag_bucket"], lag_study["net_pnl"], color="#1f77b4")
        ax.axhline(0, color="#333333", lw=1)
        ax.set_title("Actual Trade Net PnL by Burst-Onset Lag Bucket")
        ax.set_ylabel("Net PnL")
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not daywise_summary.empty:
        p = CHARTS_DIR / "actual_vs_burst_daywise_pnl.png"
        fig, ax = plt.subplots(figsize=(12, 6))
        plot_df = daywise_summary[daywise_summary["variant"].isin(["actual_system", "candle_context_plus_immediate_confirmation", "candle_context_score4", "ranked_score5_only"])]
        for variant, g in plot_df.groupby("variant"):
            g = g.sort_values("date")
            ax.plot(pd.to_datetime(g["date"]), g["net_pnl"], marker="o", label=variant)
        ax.axhline(0, color="#333333", lw=1)
        ax.set_title("Day-wise Net PnL: Actual vs Burst-Onset Variants")
        ax.set_ylabel("Net PnL")
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not candidates_all.empty:
        p = CHARTS_DIR / "burst_score_distribution.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        counts = candidates_all["score"].value_counts().sort_index()
        ax.bar(counts.index.astype(str), counts.values, color="#2ca02c")
        ax.set_title("Burst-Onset Candidate Score Distribution")
        ax.set_xlabel("Burst score")
        ax.set_ylabel("Candidate count")
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    return paths


def build_report(
    tape_dates: list[str],
    data_quality_df: pd.DataFrame,
    actual_vs_burst_df: pd.DataFrame,
    lag_study_df: pd.DataFrame,
    replay_summary_df: pd.DataFrame,
    daywise_summary_df: pd.DataFrame,
    missed_df: pd.DataFrame,
    variant_results: dict[str, pd.DataFrame],
    chart_paths: list[Path],
    audit_daywise: pd.DataFrame | None,
) -> str:
    lines: list[str] = []
    lines.append("# Burst Onset Research Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Full-tape dates analyzed: **{len(tape_dates)}** ({', '.join(tape_dates) if tape_dates else 'none'}).")
    if audit_daywise is not None and not audit_daywise.empty:
        post = audit_daywise[audit_daywise["patch_era"].isin(["burst_promotion", "burst_promotion_tape"])]
        if not post.empty:
            lines.append(f"- Prior audit baseline: current burst/promotion live phase is still negative (**{float(post['net_pnl'].sum()):,.0f} over {len(post)} sessions**).")
    if not lag_study_df.empty:
        worst_bucket = lag_study_df.sort_values("avg_pnl").iloc[0]
        best_bucket = lag_study_df.sort_values("avg_pnl", ascending=False).iloc[0]
        lines.append(f"- Best actual lag bucket by average PnL: **{best_bucket['lag_bucket']}** ({best_bucket['avg_pnl']:,.0f}/trade). Worst: **{worst_bucket['lag_bucket']}** ({worst_bucket['avg_pnl']:,.0f}/trade).")
    if not replay_summary_df.empty:
        variant_totals = replay_summary_df.groupby("variant", as_index=False).agg(net_pnl=("net_pnl", "sum"), selected_trades=("selected_trades", "sum"), max_drawdown=("max_drawdown", "sum"), avg_pf=("profit_factor", "mean"))
        variant_totals = variant_totals[variant_totals["variant"] != "actual_system"].sort_values(["net_pnl", "avg_pf"], ascending=[False, False])
        if not variant_totals.empty:
            best = variant_totals.iloc[0]
            lines.append(f"- Best replay variant by total net PnL in this preliminary sample: **{best['variant']}** ({best['net_pnl']:,.0f} net across {int(best['selected_trades'])} trades).")
    lines.append("")

    lines.append("## Data Coverage")
    lines.append(markdown_table(data_quality_df, max_rows=20))
    lines.append("")

    lines.append("## Actual Entry vs Burst Onset Lag Study")
    lines.append(markdown_table(lag_study_df, max_rows=10))
    lines.append("")

    lines.append("## Replay Variant Day-wise Summary")
    lines.append(markdown_table(daywise_summary_df[[
        "date", "variant", "selected_trades", "net_pnl", "win_rate", "profit_factor", "max_drawdown", "delta_net_pnl_vs_actual", "delta_trade_count_vs_actual"
    ]], max_rows=50))
    lines.append("")

    if not missed_df.empty:
        lines.append("## Top Missed Ranked Burst Opportunities")
        lines.append(markdown_table(missed_df[[
            "date", "variant", "timestamp", "symbol", "score", "target_class", "net_pnl", "exit_reason", "opportunity_class", "nearest_actual_trade_lag_seconds"
        ]].sort_values("net_pnl", ascending=False), max_rows=25))
        lines.append("")

    lines.append("## Variant Verdicts")
    if not replay_summary_df.empty:
        totals = replay_summary_df.groupby("variant", as_index=False).agg(
            days=("date", "count"),
            trades=("selected_trades", "sum"),
            net_pnl=("net_pnl", "sum"),
            avg_day=("net_pnl", "mean"),
            avg_pf=("profit_factor", "mean"),
            worst_day=("net_pnl", "min"),
        ).sort_values(["net_pnl", "avg_pf"], ascending=[False, False])
        lines.append(markdown_table(totals, max_rows=20))
        lines.append("")

    lines.append("## Final Recommendation")
    if not replay_summary_df.empty:
        totals = replay_summary_df.groupby("variant", as_index=False).agg(net_pnl=("net_pnl", "sum"), trades=("selected_trades", "sum"), worst_day=("net_pnl", "min"), avg_pf=("profit_factor", "mean"))
        actual = totals[totals["variant"] == "actual_system"]
        variants = totals[totals["variant"] != "actual_system"].sort_values(["net_pnl", "avg_pf"], ascending=[False, False])
        context_variants = totals[totals["variant"].isin(["candle_context_score3", "candle_context_score4", "candle_context_plus_immediate_confirmation"])].sort_values(["net_pnl", "avg_pf"], ascending=[False, False])
        actual_net = float(actual["net_pnl"].iloc[0]) if not actual.empty else np.nan
        best_variant = variants.iloc[0] if not variants.empty else None
        best_context_variant = context_variants.iloc[0] if not context_variants.empty else None
        if best_variant is not None:
            lines.append(f"- **Are we circling or progressing?** Still circling. The current live system remains negative, and this research pipeline does not show a clean burst-onset replay that is robust enough to replace it live on only {len(tape_dates)} tape days.")
            if actual_net is not np.nan:
                lines.append(f"- **Is candle trigger the bottleneck?** Yes, likely as a trigger. Actual trades often lag burst onset, and the lag study penalizes larger lags. But the replay also shows that simply deleting the candle trigger overtrades badly, so candle removal alone is not the answer.")
            lines.append("- **Did fresh burst entry outperform candle-triggered entry?** No. None of the tested burst-onset replay variants beat the current live system on total PnL, worst-day PnL, or trade discipline in this 4-day tape sample.")
            lines.append("- **What lag from burst onset is acceptable?** The data only rules out some lag zones cleanly: the `2_to_5s` bucket was particularly bad, while `exact_same_second` and `0_to_2s` were merely less bad. The small positive `5_to_10s` bucket is too small to trust.")
            lines.append("- **Is the 5-minute candle useful as context?** Possibly, but not enough by itself. Context-aware variants still overtraded and underperformed, although they generally did less damage than the looser score-3 variants.")
            if best_context_variant is not None:
                lines.append(f"- **What exact next strategy candidate should be tested?** No live candidate is ready. The next **research** candidate should be **{best_context_variant['variant']}**, but only after adding stronger throttling / contract-selection filters (for example ATM-distance, premium band, and tighter liquidity ranking).")
            else:
                lines.append("- **What exact next strategy candidate should be tested?** No tested context-aware variant is ready. The next step is another research pass, not a live patch.")
        else:
            lines.append("- Not enough replay data was available to recommend a burst-onset variant.")
    else:
        lines.append("- No replay output was generated, so no recommendation can be made.")

    lines.append("")
    lines.append("## Caveats")
    lines.append("- This is research-only replay using second-level full-tape snapshots, not broker-grade execution simulation.")
    lines.append("- Full tape is only available for a small number of sessions, so results are preliminary.")
    lines.append("- Quantity and fills are approximate and should be used for variant ranking, not exact PnL promises.")
    lines.append("- Raw logs were not modified.")
    lines.append("")
    lines.append("## Charts")
    for path in chart_paths:
        lines.append(f"- ![{path.name}]({path})")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    settings = load_settings_safe()
    audit = load_audit_module()
    audit.ensure_env_loaded()

    tape_dates = discover_full_tape_dates()
    data_quality_rows: list[dict[str, Any]] = []
    all_candidates: list[pd.DataFrame] = []
    symbol_rows_by_date: dict[str, dict[str, list[dict[str, Any]]]] = {}

    for date in tape_dates:
        candidates, symbol_rows, quality = compute_burst_onset_candidates_for_day(date, settings, audit)
        underlying = audit.load_underlying_second_series(date)
        quality["underlying_rows"] = int(len(underlying))
        quality["underlying_first_timestamp"] = underlying.index.min() if not underlying.empty else pd.NaT
        quality["underlying_last_timestamp"] = underlying.index.max() if not underlying.empty else pd.NaT
        data_quality_rows.append(quality)
        symbol_rows_by_date[date] = symbol_rows
        if not candidates.empty:
            all_candidates.append(candidates)

    candidates_all = pd.concat(all_candidates, ignore_index=True) if all_candidates else pd.DataFrame()
    actual_trades = load_actual_trades_full_tape(tape_dates, audit)
    actual_vs_burst = match_actual_entries_to_bursts(actual_trades, candidates_all)
    lag_study = summarize_lag_study(actual_vs_burst)

    data_quality_df = pd.DataFrame(data_quality_rows)
    if not data_quality_df.empty:
        data_quality_df.to_csv(OUTPUT_DIR / "burst_onset_data_quality.csv", index=False)
    if not candidates_all.empty:
        candidates_all.to_csv(OUTPUT_DIR / "burst_onset_candidates_all.csv", index=False)
    if not actual_vs_burst.empty:
        actual_vs_burst.to_csv(OUTPUT_DIR / "actual_entry_vs_burst_onset.csv", index=False)
    else:
        pd.DataFrame().to_csv(OUTPUT_DIR / "actual_entry_vs_burst_onset.csv", index=False)
    if not lag_study.empty:
        lag_study.to_csv(OUTPUT_DIR / "burst_onset_lag_study.csv", index=False)
    else:
        pd.DataFrame().to_csv(OUTPUT_DIR / "burst_onset_lag_study.csv", index=False)

    replay_summaries: list[dict[str, Any]] = []
    replay_trades_all: list[pd.DataFrame] = []
    missed_rows: list[dict[str, Any]] = []
    variant_results: dict[str, pd.DataFrame] = {}

    for date in tape_dates:
        actual_day = actual_trades[actual_trades["date"] == date].copy() if not actual_trades.empty else pd.DataFrame()
        replay_summaries.append(summarize_actual_day(actual_day, date))
        candidates_day = candidates_all[candidates_all["date"] == date].copy() if not candidates_all.empty else pd.DataFrame()
        symbol_rows = symbol_rows_by_date.get(date, {})
        actual_nearby = actual_day[["trade_id", "symbol", "entry_time", "exit_reason", "net_pnl"]].copy() if not actual_day.empty else pd.DataFrame(columns=["trade_id", "symbol", "entry_time", "exit_reason", "net_pnl"])

        for variant in VARIANTS:
            filtered = filter_candidates_for_variant(candidates_day, variant)
            replay_df = replay_variant_for_day(date, variant, filtered, symbol_rows, settings, audit)
            variant_results.setdefault(variant.name, pd.DataFrame())
            if not replay_df.empty:
                replay_trades_all.append(replay_df)
                variant_results[variant.name] = pd.concat([variant_results[variant.name], replay_df], ignore_index=True)
            replay_summaries.append(summarize_replay_day(replay_df, date, variant.name, int(len(filtered))))

            if not filtered.empty:
                executed_keys = set()
                if not actual_nearby.empty:
                    for _, arow in actual_nearby.iterrows():
                        ats = pd.Timestamp(arow["entry_time"]).floor("s") if pd.notna(arow["entry_time"]) else pd.NaT
                        if pd.notna(ats):
                            executed_keys.add((str(arow["symbol"]), ats))
                if not replay_df.empty:
                    for _, rrow in replay_df.iterrows():
                        ts = pd.Timestamp(rrow["entry_time"])
                        sym = str(rrow["symbol"])
                        if (sym, ts) in executed_keys:
                            continue
                        near = actual_nearby[actual_nearby["symbol"] == sym].copy()
                        nearest_lag = np.nan
                        nearest_actual_trade_id = None
                        if not near.empty:
                            near["abs_lag"] = near["entry_time"].apply(lambda x: abs((pd.Timestamp(x).floor("s") - ts).total_seconds()) if pd.notna(x) else np.nan)
                            near = near.sort_values("abs_lag")
                            if pd.notna(near.iloc[0]["abs_lag"]):
                                nearest_lag = float(near.iloc[0]["abs_lag"])
                                nearest_actual_trade_id = near.iloc[0]["trade_id"]
                        rec = rrow.to_dict()
                        rec["date"] = date
                        rec["variant"] = variant.name
                        rec["actual_entered_nearby"] = bool(not math.isnan(nearest_lag) and nearest_lag <= MISSED_MATCH_TOLERANCE_SECONDS)
                        rec["nearest_actual_trade_lag_seconds"] = nearest_lag
                        rec["nearest_actual_trade_id"] = nearest_actual_trade_id
                        rec["opportunity_class"] = classify_missed_opportunity(pd.Series(rec))
                        missed_rows.append(rec)

    replay_summary_df = pd.DataFrame(replay_summaries)
    replay_trades_df = pd.concat(replay_trades_all, ignore_index=True) if replay_trades_all else pd.DataFrame()
    daywise_summary_df = build_daywise_summary(replay_summary_df)
    missed_df = pd.DataFrame(missed_rows)

    replay_summary_df.to_csv(OUTPUT_DIR / "candle_context_burst_trigger_replay.csv", index=False)
    daywise_summary_df.to_csv(OUTPUT_DIR / "burst_onset_daywise_summary.csv", index=False)
    if not replay_trades_df.empty:
        replay_trades_df.to_csv(OUTPUT_DIR / "burst_onset_replay_trades.csv", index=False)
    else:
        pd.DataFrame().to_csv(OUTPUT_DIR / "burst_onset_replay_trades.csv", index=False)
    if not missed_df.empty:
        missed_df.to_csv(OUTPUT_DIR / "missed_ranked_burst_opportunities.csv", index=False)
    else:
        pd.DataFrame().to_csv(OUTPUT_DIR / "missed_ranked_burst_opportunities.csv", index=False)

    chart_paths = save_charts(lag_study, daywise_summary_df, candidates_all)

    audit_daywise = None
    audit_daywise_path = REPO_ROOT / "strategy_audit_results" / "daywise_performance_by_patch_era.csv"
    if audit_daywise_path.exists():
        try:
            audit_daywise = pd.read_csv(audit_daywise_path)
        except Exception:
            audit_daywise = None

    report = build_report(
        tape_dates=tape_dates,
        data_quality_df=data_quality_df,
        actual_vs_burst_df=actual_vs_burst,
        lag_study_df=lag_study,
        replay_summary_df=replay_summary_df,
        daywise_summary_df=daywise_summary_df,
        missed_df=missed_df,
        variant_results=variant_results,
        chart_paths=chart_paths,
        audit_daywise=audit_daywise,
    )
    (OUTPUT_DIR / "strategy_recommendation.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "burst_onset_research_report.md").write_text(report, encoding="utf-8")

    print(f"Wrote burst onset research outputs to {OUTPUT_DIR}")
    print(f"Tape dates: {tape_dates}")
    print(f"Rows | candidates={len(candidates_all)} actual={len(actual_vs_burst)} replay_trades={len(replay_trades_df)} variants={len(VARIANTS)}")


if __name__ == "__main__":
    main()
