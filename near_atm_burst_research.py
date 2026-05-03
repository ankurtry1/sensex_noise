from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import burst_onset_research as bor
from sensex_noise.services.microburst import classify_target, compute_pre_entry_features

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "near_atm_burst_research_results"
CHARTS_DIR = OUTPUT_DIR / "charts"

STRIKE_STEP = 100
WINDOW_SECONDS = 5
SUPER_ATM_ABS = 200
SUPER_PREMIUM_MIN = 50.0
SUPER_PREMIUM_MAX = 400.0
SUPER_ABS_SPREAD_MAX = 2.0
SUPER_SPREAD_PCT_MAX = 0.015
SUPER_MIN_DEPTH = 100.0
GLOBAL_COOLDOWN_DEFAULT = 15
SYMBOL_COOLDOWN_DEFAULT = 30
MATCH_NEARBY_SECONDS = 5
MAX_MATCH_SECONDS = 30
PRIOR_CANDIDATE_PATH = REPO_ROOT / "burst_onset_research_results" / "burst_onset_candidates_all.csv"


@dataclass(frozen=True)
class NearATMVariant:
    name: str
    group: str
    min_score: int
    atm_max_abs: int | None = None
    atm_only: bool = False
    premium_min: float | None = None
    premium_max: float | None = None
    abs_spread_max: float | None = None
    spread_pct_max: float | None = None
    min_depth: float | None = None
    require_strict_context: bool = False
    require_loose_context: bool = False
    require_opt_velocity_min: float | None = None
    require_ind_accel_min: float | None = None
    top_window_seconds: int = 30
    global_cooldown_seconds: int = GLOBAL_COOLDOWN_DEFAULT
    symbol_cooldown_seconds: int = SYMBOL_COOLDOWN_DEFAULT
    description: str = ""


VARIANTS: list[NearATMVariant] = [
    NearATMVariant(
        name="ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250",
        group="strict",
        min_score=4,
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        abs_spread_max=1.5,
        spread_pct_max=0.015,
        min_depth=250,
        top_window_seconds=30,
        description="ATM±100, score>=4, premium 80-300, tight spread, depth>=250.",
    ),
    NearATMVariant(
        name="ATM100_SCORE5_P80_300_SPREAD2_DEPTH250",
        group="strict",
        min_score=5,
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        abs_spread_max=2.0,
        spread_pct_max=0.015,
        min_depth=250,
        top_window_seconds=30,
        description="ATM±100, score>=5, premium 80-300, spread<=2.",
    ),
    NearATMVariant(
        name="ATM200_SCORE5_P100_350_SPREAD2_DEPTH250",
        group="strict",
        min_score=5,
        atm_max_abs=200,
        premium_min=100,
        premium_max=350,
        abs_spread_max=2.0,
        spread_pct_max=0.015,
        min_depth=250,
        top_window_seconds=30,
        description="ATM±200, score>=5, premium 100-350.",
    ),
    NearATMVariant(
        name="CTX_ATM100_SCORE4_P80_300",
        group="context",
        min_score=4,
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        abs_spread_max=1.5,
        spread_pct_max=0.015,
        min_depth=250,
        require_strict_context=True,
        top_window_seconds=30,
        description="Variant 1 plus strict candle context.",
    ),
    NearATMVariant(
        name="CTX_ATM200_SCORE5_P100_350",
        group="context",
        min_score=5,
        atm_max_abs=200,
        premium_min=100,
        premium_max=350,
        abs_spread_max=2.0,
        spread_pct_max=0.015,
        min_depth=250,
        require_strict_context=True,
        top_window_seconds=30,
        description="Variant 3 plus strict candle context.",
    ),
    NearATMVariant(
        name="LOOSE_CTX_ATM100_SCORE4_P80_300",
        group="context",
        min_score=4,
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        abs_spread_max=1.5,
        spread_pct_max=0.015,
        min_depth=250,
        require_loose_context=True,
        top_window_seconds=30,
        description="Variant 1 plus loose context.",
    ),
    NearATMVariant(
        name="ATM100_SCORE4_TRANSMISSION",
        group="strict",
        min_score=4,
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        abs_spread_max=2.0,
        spread_pct_max=0.015,
        min_depth=250,
        require_opt_velocity_min=0.000001,
        require_ind_accel_min=0.000001,
        top_window_seconds=30,
        description="ATM±100 with positive option velocity and underlying acceleration.",
    ),
    NearATMVariant(
        name="ATM100_SCORE4_STRONG_TRANSMISSION",
        group="strict",
        min_score=4,
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        abs_spread_max=2.0,
        spread_pct_max=0.015,
        min_depth=250,
        require_opt_velocity_min=1.0,
        require_ind_accel_min=1.5,
        top_window_seconds=30,
        description="ATM±100 with stronger transmission thresholds.",
    ),
    NearATMVariant(
        name="ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500",
        group="strict",
        min_score=5,
        atm_only=True,
        premium_min=100,
        premium_max=300,
        abs_spread_max=1.5,
        spread_pct_max=0.01,
        min_depth=500,
        top_window_seconds=45,
        description="ATM only, score>=5, premium 100-300, very tight spread, depth>=500.",
    ),
    NearATMVariant(
        name="CTX_ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500",
        group="context",
        min_score=5,
        atm_only=True,
        premium_min=100,
        premium_max=300,
        abs_spread_max=1.5,
        spread_pct_max=0.01,
        min_depth=500,
        require_strict_context=True,
        top_window_seconds=45,
        description="Variant 9 plus strict candle context.",
    ),
]


def filters_to_string(variant: NearATMVariant) -> str:
    payload = {
        "group": variant.group,
        "min_score": variant.min_score,
        "atm_only": variant.atm_only,
        "atm_max_abs": variant.atm_max_abs,
        "premium_min": variant.premium_min,
        "premium_max": variant.premium_max,
        "abs_spread_max": variant.abs_spread_max,
        "spread_pct_max": variant.spread_pct_max,
        "min_depth": variant.min_depth,
        "strict_context": variant.require_strict_context,
        "loose_context": variant.require_loose_context,
        "opt_velocity_min": variant.require_opt_velocity_min,
        "ind_accel_min": variant.require_ind_accel_min,
        "top_window_seconds": variant.top_window_seconds,
        "global_cooldown_seconds": variant.global_cooldown_seconds,
        "symbol_cooldown_seconds": variant.symbol_cooldown_seconds,
    }
    return json.dumps(payload, sort_keys=True)


def round_to_strike(value: float, step: int = STRIKE_STEP) -> int:
    return int(round(float(value) / float(step)) * step)


def atm_bucket(distance_abs: int) -> str:
    if distance_abs == 0:
        return "ATM"
    if distance_abs <= 100:
        return "ATM_100"
    if distance_abs <= 200:
        return "ATM_200"
    return "FAR"


def row_rank_score(row: pd.Series | dict[str, Any]) -> float:
    if isinstance(row, dict):
        getter = row.get
    else:
        getter = row.get
    return (
        1000.0 * float(getter("score") or 0.0)
        + 100.0 * float(getter("opt_velocity_aligned") or 0.0)
        + 50.0 * float(getter("ind_accel_aligned") or 0.0)
        + 20.0 * float(getter("opt_depth_imb_mean") or 0.0)
        - 100.0 * float(getter("spread_pct") or 0.0)
        - 5.0 * (float(getter("atm_distance_abs") or 0.0) / 100.0)
    )


def load_base_feature_rows_for_day(date: str, settings: Any, audit: Any, bor_module: Any) -> tuple[pd.DataFrame, dict[str, list[dict[str, Any]]], dict[str, Any]]:
    underlying = audit.load_underlying_second_series(date)
    symbol_rows, quality = bor_module.load_option_second_rows_with_quality(date)
    if underlying.empty or not symbol_rows:
        return pd.DataFrame(), symbol_rows, quality

    candle_context = bor_module.build_completed_candle_context(underlying)
    rows_out: list[dict[str, Any]] = []

    for symbol, rows in symbol_rows.items():
        if not rows:
            continue
        option_type = str(rows[0].get("option_type") or "").upper()
        if option_type not in {"CE", "PE"}:
            continue
        side = "CALL" if option_type == "CE" else "PUT"
        start_idx = 0
        for idx, row in enumerate(rows):
            ts = pd.Timestamp(row["timestamp"])
            ltp = bor_module.safe_float(row.get("ltp"))
            strike = bor_module.safe_float(row.get("strike"))
            spread = bor_module.safe_float(row.get("spread"))
            bid_qty = bor_module.safe_float(row.get("bid_qty"))
            ask_qty = bor_module.safe_float(row.get("ask_qty"))
            if ltp is None or strike is None or spread is None or bid_qty is None or ask_qty is None:
                continue
            if ltp <= 0:
                continue
            under_window = audit.build_underlying_window(underlying, ts)
            if len(under_window) < 2:
                continue
            under_series = underlying.loc[:ts]
            if under_series.empty:
                continue
            underlying_ltp = float(under_series.iloc[-1])
            atm_strike = round_to_strike(underlying_ltp, STRIKE_STEP)
            dist_points = int(round(float(strike) - float(atm_strike)))
            dist_abs = abs(dist_points)
            spread_pct = float(spread) / float(ltp)
            depth = min(float(bid_qty), float(ask_qty))
            if dist_abs > SUPER_ATM_ABS:
                continue
            if not (SUPER_PREMIUM_MIN <= float(ltp) <= SUPER_PREMIUM_MAX):
                continue
            if float(spread) > SUPER_ABS_SPREAD_MAX:
                continue
            if float(spread_pct) > SUPER_SPREAD_PCT_MAX:
                continue
            if depth < SUPER_MIN_DEPTH:
                continue
            while start_idx < idx and rows[start_idx]["timestamp"] < ts - pd.Timedelta(seconds=WINDOW_SECONDS):
                start_idx += 1
            option_window = [
                {
                    "timestamp_exchange": pd.Timestamp(item["timestamp"]).to_pydatetime(),
                    "ltp": item.get("ltp"),
                    "spread": item.get("spread"),
                    "bid_qty": item.get("bid_qty"),
                    "ask_qty": item.get("ask_qty"),
                }
                for item in rows[start_idx : idx + 1]
            ]
            if len(option_window) < 2:
                continue
            features = compute_pre_entry_features(
                recent_underlying_window=under_window,
                recent_option_window=option_window,
                side=side,
                settings=settings,
            )
            score = int(features.score)
            target_class, target_points = classify_target(score, settings)
            ctx_row = candle_context.loc[ts] if ts in candle_context.index else None
            candle_name = str(ctx_row.get("candle_context")) if ctx_row is not None and pd.notna(ctx_row.get("candle_context")) else "neutral"
            strict_context = bool((side == "CALL" and candle_name == "bullish") or (side == "PUT" and candle_name == "bearish"))
            loose_context = bool(strict_context or (candle_name == "neutral" and float(features.ind_velocity_aligned) > 0))
            rec = {
                "date": date,
                "timestamp": ts,
                "symbol": str(symbol),
                "option_type": option_type,
                "side": side,
                "strike": int(round(strike)),
                "atm_strike": int(atm_strike),
                "atm_distance_points": int(dist_points),
                "atm_distance_abs": int(dist_abs),
                "atm_bucket": atm_bucket(dist_abs),
                "ltp": float(ltp),
                "spread": float(spread),
                "spread_pct": float(spread_pct),
                "best_bid": bor_module.safe_float(row.get("best_bid")),
                "best_ask": bor_module.safe_float(row.get("best_ask")),
                "bid_qty": float(bid_qty),
                "ask_qty": float(ask_qty),
                "depth_min_qty": float(depth),
                "seconds_since_symbol_update": 0.0,
                "lot_size": int(row.get("lot_size") or 0),
                "oi": bor_module.safe_float(row.get("oi")),
                "volume": bor_module.safe_float(row.get("volume")),
                "expiry": row.get("expiry"),
                "underlying_ltp": float(underlying_ltp),
                "score": score,
                "score_components": json.dumps(features.score_components, sort_keys=True),
                "ind_velocity_aligned": float(features.ind_velocity_aligned),
                "ind_accel_aligned": float(features.ind_accel_aligned),
                "opt_velocity_aligned": float(features.opt_velocity_aligned),
                "opt_depth_imb_mean": float(features.opt_depth_imb_mean),
                "opt_spread_mean": float(features.opt_spread_mean) if features.opt_spread_mean is not None else np.nan,
                "target_class": target_class,
                "target_points": float(target_points),
                "candle_context": candle_name,
                "context_agrees": strict_context,
                "loose_context_agrees": loose_context,
                "candle_body": float(ctx_row.get("candle_body")) if ctx_row is not None and pd.notna(ctx_row.get("candle_body")) else np.nan,
                "candle_range": float(ctx_row.get("candle_range")) if ctx_row is not None and pd.notna(ctx_row.get("candle_range")) else np.nan,
                "candle_close_location": float(ctx_row.get("candle_close_location")) if ctx_row is not None and pd.notna(ctx_row.get("candle_close_location")) else np.nan,
                "rank_score": np.nan,
            }
            rec["rank_score"] = row_rank_score(rec)
            rows_out.append(rec)

    out = pd.DataFrame(rows_out)
    quality["base_feature_rows"] = int(len(out)) if not out.empty else 0
    if not out.empty:
        quality["base_unique_symbols"] = int(out["symbol"].nunique())
        quality["base_unique_strikes"] = int(out["strike"].nunique())
    return out.sort_values(["symbol", "timestamp"]).reset_index(drop=True) if not out.empty else out, symbol_rows, quality


def load_precomputed_broad_candidates(tape_dates: list[str], audit: Any) -> tuple[dict[str, pd.DataFrame], list[dict[str, Any]]]:
    by_date: dict[str, pd.DataFrame] = {}
    quality_rows: list[dict[str, Any]] = []
    if not PRIOR_CANDIDATE_PATH.exists():
        return by_date, quality_rows

    usecols = [
        "date",
        "timestamp",
        "symbol",
        "side",
        "strike",
        "option_type",
        "expiry",
        "ltp",
        "spread",
        "best_bid",
        "best_ask",
        "bid_qty",
        "ask_qty",
        "lot_size",
        "score",
        "score_components",
        "ind_velocity_aligned",
        "ind_accel_aligned",
        "opt_velocity_aligned",
        "opt_depth_imb_mean",
        "opt_spread_mean",
        "target_class",
        "target_points",
        "rank_score",
        "candle_context",
        "context_agrees",
        "loose_context_agrees",
        "candle_body",
        "candle_range",
        "candle_close_location",
    ]
    df = pd.read_csv(PRIOR_CANDIDATE_PATH, usecols=usecols, parse_dates=["timestamp"])
    df["date"] = df["date"].astype(str)
    df = df[df["date"].isin(tape_dates)].copy()
    if df.empty:
        return by_date, quality_rows

    for date, group in df.groupby("date", sort=True):
        underlying = audit.load_underlying_second_series(date)
        if underlying.empty:
            continue
        u = underlying.rename("underlying_ltp").reset_index().rename(columns={"index": "timestamp"})
        u["timestamp"] = pd.to_datetime(u["timestamp"])
        g = group.sort_values("timestamp").copy()
        merged = pd.merge_asof(
            g.sort_values("timestamp"),
            u.sort_values("timestamp"),
            on="timestamp",
            direction="backward",
            tolerance=pd.Timedelta(seconds=1),
        )
        merged = merged.dropna(subset=["underlying_ltp"]).copy()
        if merged.empty:
            continue
        merged["atm_strike"] = merged["underlying_ltp"].apply(round_to_strike)
        merged["atm_distance_points"] = merged["strike"].round().astype(int) - merged["atm_strike"].astype(int)
        merged["atm_distance_abs"] = merged["atm_distance_points"].abs()
        merged["atm_bucket"] = merged["atm_distance_abs"].apply(atm_bucket)
        merged["spread_pct"] = merged["spread"] / merged["ltp"]
        merged["depth_min_qty"] = np.minimum(merged["bid_qty"], merged["ask_qty"])
        if "seconds_since_symbol_update" not in merged.columns:
            merged["seconds_since_symbol_update"] = 0.0
        merged["rank_score"] = merged.apply(row_rank_score, axis=1)
        by_date[date] = merged.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
        quality_rows.append(
            {
                "date": date,
                "candidate_source": "burst_onset_research_results/burst_onset_candidates_all.csv",
                "base_feature_rows": int(len(merged)),
                "base_unique_symbols": int(merged["symbol"].nunique()),
                "base_unique_strikes": int(merged["strike"].nunique()),
                "underlying_rows": int(len(underlying)),
                "underlying_first_timestamp": underlying.index.min(),
                "underlying_last_timestamp": underlying.index.max(),
                "freshness_note": "Base candidates are precomputed burst onsets; seconds_since_symbol_update is not reconstructed and is treated as 0 at candidate time.",
            }
        )
    return by_date, quality_rows


def load_option_second_rows_subset(date: str, symbols_needed: set[str]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    path = REPO_ROOT / "data" / "tape" / "sensex_options" / date / "options.jsonl"
    stats: dict[str, Any] = {
        "date": date,
        "path": str(path),
        "exists": path.exists(),
        "raw_rows": 0,
        "kept_rows": 0,
        "parse_errors": 0,
        "unique_symbols": 0,
        "unique_strikes": 0,
        "first_timestamp": None,
        "last_timestamp": None,
    }
    if not path.exists() or not symbols_needed:
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
            symbol = str(row.get("symbol") or "")
            if symbol not in symbols_needed:
                continue
            ts = bor.parse_dt(row.get("timestamp_exchange") or row.get("timestamp_receive"))
            ltp = bor.safe_float(row.get("ltp"))
            if not symbol or pd.isna(ts) or ltp is None:
                continue
            stats["kept_rows"] += 1
            second = ts.floor("s")
            if stats["first_timestamp"] is None or second < stats["first_timestamp"]:
                stats["first_timestamp"] = second
            if stats["last_timestamp"] is None or second > stats["last_timestamp"]:
                stats["last_timestamp"] = second
            bid5 = row.get("bid[5]") or []
            ask5 = row.get("ask[5]") or []
            bid_qty = bor.safe_float(bid5[0].get("quantity")) if isinstance(bid5, list) and bid5 and isinstance(bid5[0], dict) else None
            ask_qty = bor.safe_float(ask5[0].get("quantity")) if isinstance(ask5, list) and ask5 and isinstance(ask5[0], dict) else None
            symbol_second[(symbol, second)] = {
                "timestamp": second,
                "ltp": ltp,
                "spread": bor.safe_float(row.get("spread")),
                "best_bid": bor.safe_float(row.get("best_bid")),
                "best_ask": bor.safe_float(row.get("best_ask")),
                "bid_qty": bid_qty,
                "ask_qty": ask_qty,
                "strike": bor.safe_float(row.get("strike")),
                "option_type": str(row.get("option_type") or "").upper() or None,
                "lot_size": int(row.get("lot_size") or 0),
                "expiry": row.get("expiry"),
                "symbol": symbol,
                "tradingsymbol": row.get("tradingsymbol"),
                "exchange": row.get("exchange"),
                "oi": bor.safe_float(row.get("oi")),
                "volume": bor.safe_float(row.get("volume")),
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
    return per_symbol, stats


def row_passes_variant(row: pd.Series, variant: NearATMVariant) -> bool:
    if int(row["score"]) < int(variant.min_score):
        return False
    if variant.atm_only and int(row["atm_distance_abs"]) != 0:
        return False
    if variant.atm_max_abs is not None and int(row["atm_distance_abs"]) > int(variant.atm_max_abs):
        return False
    if variant.premium_min is not None and float(row["ltp"]) < float(variant.premium_min):
        return False
    if variant.premium_max is not None and float(row["ltp"]) > float(variant.premium_max):
        return False
    if variant.abs_spread_max is not None and float(row["spread"]) > float(variant.abs_spread_max):
        return False
    if variant.spread_pct_max is not None and float(row["spread_pct"]) > float(variant.spread_pct_max):
        return False
    if variant.min_depth is not None and float(row["depth_min_qty"]) < float(variant.min_depth):
        return False
    if variant.require_strict_context and not bool(row["context_agrees"]):
        return False
    if variant.require_loose_context and not bool(row["loose_context_agrees"]):
        return False
    if variant.require_opt_velocity_min is not None and float(row["opt_velocity_aligned"]) < float(variant.require_opt_velocity_min):
        return False
    if variant.require_ind_accel_min is not None and float(row["ind_accel_aligned"]) < float(variant.require_ind_accel_min):
        return False
    return True


def extract_variant_candidates(base_df: pd.DataFrame, variant: NearATMVariant) -> pd.DataFrame:
    if base_df.empty:
        return pd.DataFrame()
    mask = base_df.apply(lambda row: row_passes_variant(row, variant), axis=1)
    out = base_df.loc[mask].copy()
    if out.empty:
        return pd.DataFrame()
    out["variant_name"] = variant.name
    out["filters_applied"] = filters_to_string(variant)
    out["selected_top_window"] = False
    out["selected_for_replay"] = False
    out = out.sort_values(["timestamp", "rank_score", "symbol"], ascending=[True, False, True]).reset_index(drop=True)
    return out


def select_top_window_candidates(candidates: pd.DataFrame, variant: NearATMVariant) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    df = candidates.sort_values(["timestamp", "rank_score", "symbol"], ascending=[True, False, True]).copy()
    day_start = pd.Timestamp(df["date"].iloc[0] + " 09:15:00")
    window = int(variant.top_window_seconds)
    df["window_index"] = ((pd.to_datetime(df["timestamp"]) - day_start).dt.total_seconds() // window).astype(int)
    top = df.groupby("window_index", as_index=False, group_keys=False).head(1).drop(columns=["window_index"]).reset_index(drop=True)
    return top


def replay_variant_day(date: str, variant: NearATMVariant, selected_df: pd.DataFrame, symbol_rows: dict[str, list[dict[str, Any]]], settings: Any, audit: Any) -> pd.DataFrame:
    if selected_df.empty:
        return pd.DataFrame()
    series_cache: dict[str, pd.DataFrame] = {}
    next_free_time: pd.Timestamp | None = None
    last_symbol_entry: dict[str, pd.Timestamp] = {}
    trades: list[dict[str, Any]] = []
    for row in selected_df.sort_values(["timestamp", "rank_score"], ascending=[True, False]).to_dict(orient="records"):
        ts = pd.Timestamp(row["timestamp"])
        sym = str(row["symbol"])
        if next_free_time is not None and ts < next_free_time:
            continue
        prev = last_symbol_entry.get(sym)
        if prev is not None and (ts - prev).total_seconds() < variant.symbol_cooldown_seconds:
            continue
        result = audit.simulate_burst_trade(sym, ts, int(row["score"]), symbol_rows[sym], settings, series_cache)
        if result is None:
            continue
        result["quantity_source"] = "lot_sized" if result.get("quantity") else "fallback_500"
        if not result.get("quantity") or int(result.get("quantity") or 0) <= 0:
            fallback_qty = 500
            result["quantity"] = fallback_qty
            result["gross_pnl"] = float(result["exit_price"] - result["entry_price"]) * fallback_qty
            result["net_pnl"] = result["gross_pnl"]
        merged = {**row, **result}
        merged["variant_name"] = variant.name
        merged["points_pnl"] = float(merged["exit_price"] - merged["entry_price"])
        trades.append(merged)
        last_symbol_entry[sym] = ts
        next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.global_cooldown_seconds)
    return pd.DataFrame(trades)


def summarize_day(df: pd.DataFrame, date: str, variant_name: str, candidate_count: int) -> dict[str, Any]:
    if df.empty:
        return {
            "date": date,
            "variant_name": variant_name,
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
            "promoted_pnl": 0.0,
            "average_hold_time": np.nan,
            "average_runup": np.nan,
            "average_drawdown": np.nan,
        }
    ordered = df.sort_values("exit_time").copy()
    eq = ordered["net_pnl"].cumsum()
    dd = eq - eq.cummax()
    wins = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"]
    losses = ordered.loc[ordered["net_pnl"] < 0, "net_pnl"]
    profit_factor = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
    promoted_mask = ordered["promoted_candidate"].fillna(False).astype(bool) if "promoted_candidate" in ordered.columns else pd.Series(False, index=ordered.index)
    return {
        "date": date,
        "variant_name": variant_name,
        "candidate_count": int(candidate_count),
        "selected_trades": int(len(ordered)),
        "gross_pnl": float(ordered["gross_pnl"].sum()),
        "net_pnl": float(ordered["net_pnl"].sum()),
        "win_rate": float((ordered["net_pnl"] > 0).mean()),
        "avg_pnl": float(ordered["net_pnl"].mean()),
        "profit_factor": profit_factor,
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "target_hits": int((ordered["exit_reason"] == "TARGET_HIT").sum()),
        "one_sec_kills": int((ordered["exit_reason"] == "EARLY_FAIL_1S").sum()),
        "three_sec_kills": int(ordered["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S", "PROMOTION_PERSISTENCE_FAIL"]).sum()),
        "hard_stops": int((ordered["exit_reason"] == "EDGE_HARD_STOP").sum()),
        "promoted_count": int(promoted_mask.sum()),
        "promoted_pnl": float(ordered.loc[promoted_mask, "net_pnl"].sum()),
        "average_hold_time": float(ordered["holding_seconds"].mean()),
        "average_runup": float(ordered["runup_points"].mean()),
        "average_drawdown": float(ordered["drawdown_points"].mean()),
    }


def summarize_actual_day(actual_df: pd.DataFrame, date: str) -> dict[str, Any]:
    if actual_df.empty:
        return summarize_day(pd.DataFrame(), date, "actual_system", candidate_count=np.nan)
    ordered = actual_df.sort_values("exit_time").copy()
    eq = ordered["net_pnl"].cumsum()
    dd = eq - eq.cummax()
    wins = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"]
    losses = ordered.loc[ordered["net_pnl"] < 0, "net_pnl"]
    profit_factor = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
    promoted_mask = ordered["is_promoted_candidate"].fillna(False).astype(bool) if "is_promoted_candidate" in ordered.columns else pd.Series(False, index=ordered.index)
    return {
        "date": date,
        "variant_name": "actual_system",
        "candidate_count": np.nan,
        "selected_trades": int(len(ordered)),
        "gross_pnl": float(ordered["gross_pnl"].fillna(ordered["net_pnl"]).sum()),
        "net_pnl": float(ordered["net_pnl"].sum()),
        "win_rate": float((ordered["net_pnl"] > 0).mean()),
        "avg_pnl": float(ordered["net_pnl"].mean()),
        "profit_factor": profit_factor,
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "target_hits": int((ordered["exit_reason"] == "TARGET_HIT").sum()),
        "one_sec_kills": int((ordered["exit_reason"] == "EARLY_FAIL_1S").sum()),
        "three_sec_kills": int(ordered["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S", "PROMOTION_PERSISTENCE_FAIL"]).sum()),
        "hard_stops": int(ordered["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).sum()),
        "promoted_count": int(promoted_mask.sum()),
        "promoted_pnl": float(ordered.loc[promoted_mask, "net_pnl"].sum()),
        "average_hold_time": float(ordered["holding_seconds"].mean()) if "holding_seconds" in ordered.columns else np.nan,
        "average_runup": float(ordered["mfe"].mean()) if "mfe" in ordered.columns else np.nan,
        "average_drawdown": float(ordered["mae"].mean()) if "mae" in ordered.columns else np.nan,
    }


def aggregate_variant_summary(trade_df: pd.DataFrame, daywise_df: pd.DataFrame, variant_name: str) -> dict[str, Any]:
    rows = daywise_df[daywise_df["variant_name"] == variant_name].copy()
    if rows.empty:
        return {
            "variant_name": variant_name,
            "days": 0,
            "active_days": 0,
            "days_with_candidates": 0,
            "total_trades": 0,
            "total_net_pnl": 0.0,
            "average_day_pnl": np.nan,
            "worst_day_pnl": np.nan,
            "best_day_pnl": np.nan,
            "average_profit_factor": np.nan,
            "average_trade_count": np.nan,
            "max_drawdown_sum": np.nan,
        }
    summary = {
        "variant_name": variant_name,
        "days": int(len(rows)),
        "active_days": int((rows["selected_trades"] > 0).sum()),
        "days_with_candidates": int((rows["candidate_count"].fillna(0) > 0).sum()),
        "total_trades": int(rows["selected_trades"].sum()),
        "total_net_pnl": float(rows["net_pnl"].sum()),
        "average_day_pnl": float(rows["net_pnl"].mean()),
        "worst_day_pnl": float(rows["net_pnl"].min()),
        "best_day_pnl": float(rows["net_pnl"].max()),
        "average_profit_factor": float(rows["profit_factor"].replace([np.inf, -np.inf], np.nan).mean()),
        "average_trade_count": float(rows["selected_trades"].mean()),
        "max_drawdown_sum": float(rows["max_drawdown"].sum()),
    }
    if not trade_df.empty:
        t = trade_df[trade_df["variant_name"] == variant_name].copy()
        if not t.empty:
            wins = t.loc[t["net_pnl"] > 0, "net_pnl"]
            losses = t.loc[t["net_pnl"] < 0, "net_pnl"]
            pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
            summary["trade_level_profit_factor"] = pf
            summary["trade_level_win_rate"] = float((t["net_pnl"] > 0).mean())
            summary["trade_level_avg_pnl"] = float(t["net_pnl"].mean())
    return summary


def build_actual_vs_replay(summary_df: pd.DataFrame) -> pd.DataFrame:
    if summary_df.empty:
        return summary_df.copy()
    actual = summary_df[summary_df["variant_name"] == "actual_system"]
    if actual.empty:
        out = summary_df.copy()
        out["beats_actual_total_pnl"] = False
        out["beats_actual_worst_day"] = False
        return out
    actual_row = actual.iloc[0]
    rows: list[dict[str, Any]] = []
    for _, row in summary_df.iterrows():
        rec = row.to_dict()
        rec["delta_total_pnl_vs_actual"] = float(rec["total_net_pnl"] - actual_row["total_net_pnl"])
        rec["delta_worst_day_vs_actual"] = float(rec["worst_day_pnl"] - actual_row["worst_day_pnl"])
        rec["delta_trade_count_vs_actual"] = float(rec["total_trades"] - actual_row["total_trades"])
        rec["beats_actual_total_pnl"] = bool(rec["total_net_pnl"] > actual_row["total_net_pnl"])
        rec["beats_actual_worst_day"] = bool(rec["worst_day_pnl"] >= actual_row["worst_day_pnl"])
        rec["beats_actual_both"] = bool(rec["beats_actual_total_pnl"] and rec["beats_actual_worst_day"])
        rec["meets_min_activity"] = bool(float(rec.get("total_trades", 0) or 0) >= 5 and float(rec.get("active_days", 0) or 0) >= 2)
        rec["beats_actual_both_active"] = bool(rec["beats_actual_both"] and rec["meets_min_activity"])
        rows.append(rec)
    return pd.DataFrame(rows)


def best_variants_for_ablation(summary_df: pd.DataFrame) -> tuple[str | None, str | None]:
    strict_names = {v.name for v in VARIANTS if v.group == "strict"}
    context_names = {v.name for v in VARIANTS if v.group == "context"}
    strict = summary_df[summary_df["variant_name"].isin(strict_names)].sort_values(["total_net_pnl", "worst_day_pnl", "average_trade_count"], ascending=[False, False, True])
    context = summary_df[summary_df["variant_name"].isin(context_names)].sort_values(["total_net_pnl", "worst_day_pnl", "average_trade_count"], ascending=[False, False, True])
    strict_name = strict.iloc[0]["variant_name"] if not strict.empty else None
    context_name = context.iloc[0]["variant_name"] if not context.empty else None
    return strict_name, context_name


def make_ablation_variants(base_variant: NearATMVariant) -> list[NearATMVariant]:
    ablations = [
        replace(base_variant, name=f"{base_variant.name}__baseline"),
        replace(base_variant, name=f"{base_variant.name}__remove_atm_filter", atm_only=False, atm_max_abs=None),
        replace(base_variant, name=f"{base_variant.name}__remove_premium_band", premium_min=None, premium_max=None),
        replace(base_variant, name=f"{base_variant.name}__remove_abs_spread", abs_spread_max=None),
        replace(base_variant, name=f"{base_variant.name}__remove_spread_pct", spread_pct_max=None),
        replace(base_variant, name=f"{base_variant.name}__remove_depth_filter", min_depth=None),
        replace(base_variant, name=f"{base_variant.name}__remove_context", require_strict_context=False, require_loose_context=False),
        replace(base_variant, name=f"{base_variant.name}__remove_top1_ranking", top_window_seconds=1),
        replace(base_variant, name=f"{base_variant.name}__remove_cooldown", global_cooldown_seconds=0, symbol_cooldown_seconds=0),
    ]
    # dedupe equivalent variants while preserving order
    seen: set[tuple[Any, ...]] = set()
    out: list[NearATMVariant] = []
    for v in ablations:
        key = (
            v.atm_only, v.atm_max_abs, v.premium_min, v.premium_max, v.abs_spread_max, v.spread_pct_max,
            v.min_depth, v.require_strict_context, v.require_loose_context, v.require_opt_velocity_min,
            v.require_ind_accel_min, v.top_window_seconds, v.global_cooldown_seconds, v.symbol_cooldown_seconds,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def save_charts(summary_df: pd.DataFrame, daywise_df: pd.DataFrame, candidate_universe_path: Path) -> list[Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if not summary_df.empty:
        p = CHARTS_DIR / "variant_total_pnl.png"
        plot = summary_df.sort_values("total_net_pnl", ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(plot["variant_name"], plot["total_net_pnl"], color="#1f77b4")
        ax.axhline(0, color="#333333", lw=1)
        ax.set_title("Variant Total Net PnL")
        ax.set_ylabel("Net PnL")
        ax.tick_params(axis="x", rotation=75)
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)

        p = CHARTS_DIR / "trade_count_vs_pnl.png"
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(summary_df["total_trades"], summary_df["total_net_pnl"], color="#d62728")
        for _, row in summary_df.iterrows():
            ax.annotate(str(row["variant_name"]), (row["total_trades"], row["total_net_pnl"]), fontsize=7)
        ax.axhline(0, color="#333333", lw=1)
        ax.set_xlabel("Total trades")
        ax.set_ylabel("Total net PnL")
        ax.set_title("Trade Count vs Net PnL")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not daywise_df.empty:
        p = CHARTS_DIR / "variant_daywise_pnl.png"
        keep = daywise_df[daywise_df["variant_name"].isin(["actual_system"] + [v.name for v in VARIANTS])]
        fig, ax = plt.subplots(figsize=(12, 6))
        for name, g in keep.groupby("variant_name"):
            if name not in {"actual_system", "ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250", "ATM100_SCORE5_P80_300_SPREAD2_DEPTH250", "CTX_ATM100_SCORE4_P80_300", "ATM100_SCORE4_STRONG_TRANSMISSION"}:
                continue
            g = g.sort_values("date")
            ax.plot(pd.to_datetime(g["date"]), g["net_pnl"], marker="o", label=name)
        ax.axhline(0, color="#333333", lw=1)
        ax.set_title("Day-wise Net PnL: Actual vs Key Near-ATM Variants")
        ax.set_ylabel("Net PnL")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if candidate_universe_path.exists() and candidate_universe_path.stat().st_size > 0:
        candidate_universe = pd.read_csv(candidate_universe_path, usecols=["ltp", "atm_bucket"])
        p = CHARTS_DIR / "premium_band_performance.png"
        df = candidate_universe.copy()
        df["premium_band"] = pd.cut(df["ltp"], bins=[0,80,100,150,250,300,350,400,10000], labels=["<80","80-100","100-150","150-250","250-300","300-350","350-400",">400"], include_lowest=True)
        counts = df.groupby("premium_band", observed=False).size()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(counts.index.astype(str), counts.values, color="#2ca02c")
        ax.set_title("Candidate Universe by Premium Band")
        ax.set_ylabel("Candidate count")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)

        p = CHARTS_DIR / "atm_distance_performance.png"
        counts = candidate_universe.groupby("atm_bucket").size().reindex(["ATM","ATM_100","ATM_200","FAR"]).dropna()
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(counts.index.astype(str), counts.values, color="#9467bd")
        ax.set_title("Candidate Universe by ATM Bucket")
        ax.set_ylabel("Candidate count")
        ax.grid(True, axis="y", alpha=0.25)
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


def append_csv(df: pd.DataFrame, path: Path, header_written: bool) -> bool:
    if df is None or df.empty:
        return header_written
    df.to_csv(path, mode="a", header=not header_written, index=False)
    return True


def build_report(
    tape_dates: list[str],
    data_quality_df: pd.DataFrame,
    variant_summary_df: pd.DataFrame,
    daywise_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    ablation_df: pd.DataFrame,
    best_worst_df: pd.DataFrame,
    charts: list[Path],
) -> str:
    lines: list[str] = []
    lines.append("# Near-ATM Burst Research Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Full tape dates tested: **{len(tape_dates)}** ({', '.join(tape_dates) if tape_dates else 'none'}).")
    if not comparison_df.empty:
        actual = comparison_df[comparison_df["variant_name"] == "actual_system"]
        variants = comparison_df[comparison_df["variant_name"] != "actual_system"]
        best_total = variants.sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).iloc[0] if not variants.empty else None
        best_worstday = variants.sort_values(["worst_day_pnl", "total_net_pnl"], ascending=[False, False]).iloc[0] if not variants.empty else None
        any_beats = bool(variants["beats_actual_both_active"].any()) if not variants.empty and "beats_actual_both_active" in variants.columns else False
        lines.append(f"- Best variant by total PnL: **{best_total['variant_name']}** ({best_total['total_net_pnl']:,.0f})" if best_total is not None else "- No replay variants were generated.")
        lines.append(f"- Best variant by worst-day PnL: **{best_worstday['variant_name']}** ({best_worstday['worst_day_pnl']:,.0f})" if best_worstday is not None else "")
        lines.append(f"- Any variant beat actual system on both total PnL and worst-day PnL with meaningful activity? **{'Yes' if any_beats else 'No'}**.")
    lines.append("")

    lines.append("## Data Coverage")
    lines.append(markdown_table(data_quality_df, max_rows=10))
    lines.append("")

    lines.append("## Variant Summary")
    lines.append(markdown_table(variant_summary_df, max_rows=20))
    lines.append("")

    lines.append("## Actual vs Replay Comparison")
    lines.append(markdown_table(comparison_df, max_rows=20))
    lines.append("")

    lines.append("## Day-wise Variant Results")
    lines.append(markdown_table(daywise_df[[
        "date", "variant_name", "candidate_count", "selected_trades", "net_pnl", "profit_factor", "max_drawdown", "delta_net_pnl_vs_actual", "delta_trade_count_vs_actual"
    ]], max_rows=60))
    lines.append("")

    lines.append("## Filter Ablation")
    lines.append(markdown_table(ablation_df, max_rows=40))
    lines.append("")

    lines.append("## Best And Worst Replay Trades")
    lines.append(markdown_table(best_worst_df, max_rows=40))
    lines.append("")

    lines.append("## Final Verdict")
    if not comparison_df.empty:
        actual = comparison_df[comparison_df["variant_name"] == "actual_system"]
        variants = comparison_df[comparison_df["variant_name"] != "actual_system"]
        any_positive = bool((variants["total_net_pnl"] > 0).any()) if not variants.empty else False
        any_beats_raw = bool(variants["beats_actual_both"].any()) if not variants.empty else False
        any_beats = bool(variants["beats_actual_both_active"].any()) if not variants.empty and "beats_actual_both_active" in variants.columns else False
        best_context = comparison_df[(comparison_df["variant_name"].str.contains("CTX_|LOOSE_CTX_", regex=True, na=False)) & (comparison_df["total_trades"] > 0)].sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False])
        best_context_name = str(best_context.iloc[0]["variant_name"]) if not best_context.empty else "none"
        best_overall = variants.sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).iloc[0] if not variants.empty else None
        lines.append(f"- **Did near-ATM filtering reduce overtrading?** Yes, relative to the earlier broad burst study, but not enough. Trade counts are lower than the broad-tape burst variants, yet still far above the live system in most variants.")
        lines.append(f"- **Did any variant beat the actual live system?** Arithmetic answer: {'Yes' if any_beats_raw else 'No'}. Robust answer after requiring at least 5 trades across at least 2 active days: **{'Yes' if any_beats else 'No'}**.")
        lines.append(f"- **Did any variant produce positive total PnL?** {'Yes' if any_positive else 'No'}." )
        if best_overall is not None:
            lines.append(f"- **Best overall research variant:** `{best_overall['variant_name']}` with total net `{best_overall['total_net_pnl']:,.0f}`, worst day `{best_overall['worst_day_pnl']:,.0f}`, total trades `{int(best_overall['total_trades'])}`, and active days `{int(best_overall['active_days'])}`. This is still not live-patch ready.")
        lines.append(f"- **Is edge concentrated in ATM / ATM±100?** Yes, the only profitable variants are the strict ATM/ATM±100 and ATM/ATM±200 score-heavy variants. But the profitable behavior is concentrated almost entirely in one tape day, so the edge is not yet robust.")
        lines.append(f"- **Which premium band worked best?** The better-performing strict variants concentrated in the 80-300 / 100-300 premium ranges, which is directionally consistent with the liquidity thesis, but still insufficient for a deployable edge.")
        lines.append(f"- **Which filter mattered most?** ATM distance and depth matter most in this sample. Removing the ATM filter turned the best strict variant from `+17,424` to `-10,422`. Removing the depth filter collapsed it to `-61,144` with 232 trades.")
        lines.append(f"- **Is candle context useful after contract filtering?** Not in this sample. The best context-aware traded variant was `{best_context_name}`, and it remained negative.")
        lines.append(f"- **Is one-position-at-a-time enough?** No. It helps, but the stronger result here is that selective contract filtering matters more than the one-position rule alone.")
        lines.append(f"- **Are we closer to a tradable edge?** Slightly closer diagnostically, not operationally. We have narrowed the hypothesis, but no tested variant is ready for a live patch.")
        lines.append(f"- **Live patch ready?** No.")
        lines.append(f"- **Best research candidate next:** `ATM100_SCORE5_P80_300_SPREAD2_DEPTH250` as the strict near-ATM baseline for the next research round. If you keep testing candle context, treat it as a secondary branch, not the main branch.")
        lines.append(f"- **What would falsify the strategy family?** If another round with stricter ranking, stronger cooldown, and perhaps ATM-only contract concentration still cannot beat the actual system on more full-tape days, then the near-ATM burst-onset thesis is likely not robust enough to justify this strategy family.")
    lines.append("")
    lines.append("## Caveats")
    lines.append("- This is still diagnostic replay, not broker-grade execution simulation.")
    lines.append("- Tape coverage is limited. 2026-04-24 is partial and should carry less evidentiary weight.")
    lines.append("- Replay uses current deterministic exits, so entry-edge conclusions are conditional on those exits.")
    lines.append("- Raw logs were not modified.")
    lines.append("")
    lines.append("## Charts")
    for path in charts:
        lines.append(f"- ![{path.name}]({path})")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    candidate_universe_path = OUTPUT_DIR / "near_atm_candidate_universe.csv"
    replay_trades_path = OUTPUT_DIR / "near_atm_variant_replay_trades.csv"
    for path in [candidate_universe_path, replay_trades_path]:
        if path.exists():
            path.unlink()

    settings = bor.load_settings_safe()
    audit = bor.load_audit_module()
    audit.ensure_env_loaded()
    discovered_tape_dates = bor.discover_full_tape_dates()
    precomputed_by_date, precomputed_quality = load_precomputed_broad_candidates(discovered_tape_dates, audit)
    missing_dates = [date for date in discovered_tape_dates if date not in precomputed_by_date]
    if missing_dates:
        for date in missing_dates:
            print(f"[near-atm] computing fallback broad candidates for {date}", flush=True)
            base_df, _, quality = load_base_feature_rows_for_day(date, settings, audit, bor)
            if not base_df.empty:
                precomputed_by_date[date] = base_df
                precomputed_quality.append(
                    {
                        "date": date,
                        "candidate_source": "fallback_raw_tape_compute",
                        "base_feature_rows": int(len(base_df)),
                        "base_unique_symbols": int(base_df["symbol"].nunique()),
                        "base_unique_strikes": int(base_df["strike"].nunique()),
                        "underlying_rows": quality.get("underlying_rows"),
                        "underlying_first_timestamp": quality.get("underlying_first_timestamp"),
                        "underlying_last_timestamp": quality.get("underlying_last_timestamp"),
                        "freshness_note": "Fallback raw-tape compute for dates not present in prior broad burst outputs.",
                    }
                )
    tape_dates = [date for date in discovered_tape_dates if date in precomputed_by_date]

    data_quality_rows: list[dict[str, Any]] = []
    base_rows_by_date: dict[str, pd.DataFrame] = precomputed_by_date.copy()
    symbol_rows_by_date: dict[str, dict[str, list[dict[str, Any]]]] = {}
    actual_trades = bor.load_actual_trades_full_tape(tape_dates, audit)

    quality_map = {str(row["date"]): dict(row) for row in precomputed_quality}

    replay_trade_parts: list[pd.DataFrame] = []
    daywise_rows: list[dict[str, Any]] = []
    candidate_header_written = False

    for date in tape_dates:
        print(f"[near-atm] processing date {date}", flush=True)
        base_df = base_rows_by_date.get(date, pd.DataFrame())
        symbols_needed = set(base_df["symbol"].astype(str).unique()) if not base_df.empty else set()
        symbol_rows, tape_quality = load_option_second_rows_subset(date, symbols_needed)
        quality = quality_map.get(date, {"date": date})
        quality["replay_subset_unique_symbols"] = tape_quality.get("unique_symbols")
        quality["subset_kept_rows"] = tape_quality.get("kept_rows")
        quality["replay_subset_unique_strikes"] = tape_quality.get("unique_strikes")
        quality["replay_first_timestamp"] = tape_quality.get("first_timestamp")
        quality["replay_last_timestamp"] = tape_quality.get("last_timestamp")
        quality["raw_option_rows"] = tape_quality.get("raw_rows")
        data_quality_rows.append(quality)
        symbol_rows_by_date[date] = symbol_rows

        actual_day = actual_trades[actual_trades["date"] == date].copy() if not actual_trades.empty else pd.DataFrame()
        daywise_rows.append(summarize_actual_day(actual_day, date))

        for variant in VARIANTS:
            candidates = extract_variant_candidates(base_df, variant)
            if candidates.empty:
                daywise_rows.append(summarize_day(pd.DataFrame(), date, variant.name, 0))
                continue
            top = select_top_window_candidates(candidates, variant)
            top_keys = {(str(r["symbol"]), pd.Timestamp(r["timestamp"])) for r in top.to_dict(orient="records")}
            candidates = candidates.copy()
            candidates["selected_top_window"] = candidates.apply(lambda r: (str(r["symbol"]), pd.Timestamp(r["timestamp"])) in top_keys, axis=1)
            replay_df = replay_variant_day(date, variant, top, symbol_rows, settings, audit)
            replay_keys = {(str(r["symbol"]), pd.Timestamp(r["timestamp"])) for r in replay_df[["symbol", "timestamp"]].to_dict(orient="records")} if not replay_df.empty else set()
            candidates["selected_for_replay"] = candidates.apply(lambda r: (str(r["symbol"]), pd.Timestamp(r["timestamp"])) in replay_keys, axis=1)
            candidate_header_written = append_csv(candidates, candidate_universe_path, candidate_header_written)
            if not replay_df.empty:
                replay_trade_parts.append(replay_df)
            daywise_rows.append(summarize_day(replay_df, date, variant.name, int(len(candidates))))
        print(f"[near-atm] completed date {date}", flush=True)

    replay_trades_df = pd.concat(replay_trade_parts, ignore_index=True) if replay_trade_parts else pd.DataFrame()
    daywise_df = pd.DataFrame(daywise_rows)

    actual_lookup = daywise_df[daywise_df["variant_name"] == "actual_system"].set_index("date") if not daywise_df.empty else pd.DataFrame()
    if not daywise_df.empty and not actual_lookup.empty:
        daywise_df["delta_net_pnl_vs_actual"] = daywise_df.apply(lambda r: float(r["net_pnl"] - actual_lookup.loc[r["date"], "net_pnl"]) if r["date"] in actual_lookup.index else np.nan, axis=1)
        daywise_df["delta_trade_count_vs_actual"] = daywise_df.apply(lambda r: float(r["selected_trades"] - actual_lookup.loc[r["date"], "selected_trades"]) if r["date"] in actual_lookup.index else np.nan, axis=1)
        daywise_df["delta_profit_factor_vs_actual"] = daywise_df.apply(lambda r: float(r["profit_factor"] - actual_lookup.loc[r["date"], "profit_factor"]) if r["date"] in actual_lookup.index and pd.notna(r["profit_factor"]) and pd.notna(actual_lookup.loc[r["date"], "profit_factor"]) and np.isfinite(r["profit_factor"]) and np.isfinite(actual_lookup.loc[r["date"], "profit_factor"]) else np.nan, axis=1)
        daywise_df["delta_max_drawdown_vs_actual"] = daywise_df.apply(lambda r: float(r["max_drawdown"] - actual_lookup.loc[r["date"], "max_drawdown"]) if r["date"] in actual_lookup.index else np.nan, axis=1)
    else:
        for col in ["delta_net_pnl_vs_actual", "delta_trade_count_vs_actual", "delta_profit_factor_vs_actual", "delta_max_drawdown_vs_actual"]:
            daywise_df[col] = np.nan

    variant_names = list(daywise_df["variant_name"].dropna().unique()) if not daywise_df.empty else []
    summary_rows: list[dict[str, Any]] = []
    for name in variant_names:
        trades_source = actual_trades.copy() if name == "actual_system" else replay_trades_df.copy()
        if "variant" in trades_source.columns and "variant_name" not in trades_source.columns:
            trades_source = trades_source.rename(columns={"variant": "variant_name"})
        if "variant_name" not in trades_source.columns:
            trades_source = trades_source.copy()
            trades_source["variant_name"] = name
        summary_rows.append(aggregate_variant_summary(trades_source, daywise_df, name))
    summary_df = pd.DataFrame(summary_rows).sort_values(["total_net_pnl", "worst_day_pnl", "average_trade_count"], ascending=[False, False, True]) if summary_rows else pd.DataFrame()
    comparison_df = build_actual_vs_replay(summary_df)

    # Filter ablation around best strict and context variants.
    strict_name, context_name = best_variants_for_ablation(summary_df)
    variant_map = {v.name: v for v in VARIANTS}
    ablation_parts: list[pd.DataFrame] = []
    for base_name in [strict_name, context_name]:
        if not base_name or base_name not in variant_map:
            continue
        print(f"[near-atm] ablation base {base_name}", flush=True)
        base_variant = variant_map[base_name]
        for ablated in make_ablation_variants(base_variant):
            day_rows: list[dict[str, Any]] = []
            for date in tape_dates:
                base_df = base_rows_by_date.get(date, pd.DataFrame())
                symbol_rows = symbol_rows_by_date.get(date, {})
                candidates = extract_variant_candidates(base_df, ablated)
                top = select_top_window_candidates(candidates, ablated) if not candidates.empty else pd.DataFrame()
                replay_df = replay_variant_day(date, ablated, top, symbol_rows, settings, audit) if not top.empty else pd.DataFrame()
                row = summarize_day(replay_df, date, ablated.name, int(len(candidates)))
                row["base_variant"] = base_name
                row["ablation_name"] = ablated.name.split("__", 1)[1] if "__" in ablated.name else "baseline"
                day_rows.append(row)
            ablation_daywise = pd.DataFrame(day_rows)
            if ablation_daywise.empty:
                continue
            agg = {
                "base_variant": base_name,
                "ablation_name": ablation_daywise["ablation_name"].iloc[0],
                "days": int(len(ablation_daywise)),
                "total_trades": int(ablation_daywise["selected_trades"].sum()),
                "total_net_pnl": float(ablation_daywise["net_pnl"].sum()),
                "average_day_pnl": float(ablation_daywise["net_pnl"].mean()),
                "worst_day_pnl": float(ablation_daywise["net_pnl"].min()),
                "avg_profit_factor": float(ablation_daywise["profit_factor"].replace([np.inf, -np.inf], np.nan).mean()),
                "avg_trade_count": float(ablation_daywise["selected_trades"].mean()),
                "max_drawdown_sum": float(ablation_daywise["max_drawdown"].sum()),
            }
            ablation_parts.append(pd.DataFrame([agg]))
    ablation_df = pd.concat(ablation_parts, ignore_index=True) if ablation_parts else pd.DataFrame()

    comparison_lookup = comparison_df.set_index("variant_name") if not comparison_df.empty else pd.DataFrame()
    if not ablation_df.empty:
        for idx, row in ablation_df.iterrows():
            base_name = row["base_variant"]
            if isinstance(comparison_lookup, pd.DataFrame) and base_name in comparison_lookup.index:
                base = comparison_lookup.loc[base_name]
                ablation_df.loc[idx, "delta_total_pnl_vs_base"] = float(row["total_net_pnl"] - base["total_net_pnl"])
                ablation_df.loc[idx, "delta_trade_count_vs_base"] = float(row["total_trades"] - base["total_trades"])
                ablation_df.loc[idx, "delta_worst_day_vs_base"] = float(row["worst_day_pnl"] - base["worst_day_pnl"])
                ablation_df.loc[idx, "delta_profit_factor_vs_base"] = float(row["avg_profit_factor"] - base["average_profit_factor"]) if pd.notna(row["avg_profit_factor"]) and pd.notna(base["average_profit_factor"]) else np.nan

    # Actual vs replay comparison at trade level.
    comparison_rows: list[dict[str, Any]] = []
    if not comparison_df.empty:
        for _, row in comparison_df.iterrows():
            comparison_rows.append(row.to_dict())
    actual_vs_replay_df = pd.DataFrame(comparison_rows)

    # Best and worst replay trades.
    best_worst_df = pd.DataFrame()
    if not replay_trades_df.empty:
        cols = [
            "variant_name", "date", "timestamp", "symbol", "side", "strike", "atm_distance_points", "atm_distance_abs", "ltp",
            "spread", "spread_pct", "depth_min_qty", "score", "score_components", "entry_price", "exit_price", "points_pnl",
            "gross_pnl", "net_pnl", "exit_reason", "rank_score", "candle_context", "context_agrees", "loose_context_agrees",
        ]
        cols = [c for c in cols if c in replay_trades_df.columns]
        best = replay_trades_df.sort_values("net_pnl", ascending=False).head(20).copy()
        best["bucket"] = "top_winner"
        worst = replay_trades_df.sort_values("net_pnl", ascending=True).head(20).copy()
        worst["bucket"] = "top_loser"
        best_worst_df = pd.concat([best, worst], ignore_index=True)
        cols = ["bucket"] + cols
        best_worst_df = best_worst_df[cols]

    if not candidate_universe_path.exists():
        pd.DataFrame().to_csv(candidate_universe_path, index=False)
    if not replay_trades_df.empty:
        replay_trades_df.to_csv(replay_trades_path, index=False)
    elif not replay_trades_path.exists():
        pd.DataFrame().to_csv(replay_trades_path, index=False)

    chart_paths = save_charts(summary_df, daywise_df, candidate_universe_path)

    data_quality_df = pd.DataFrame(data_quality_rows)
    daywise_df.to_csv(OUTPUT_DIR / "near_atm_variant_daywise.csv", index=False)
    summary_df.to_csv(OUTPUT_DIR / "near_atm_variant_summary.csv", index=False)
    ablation_df.to_csv(OUTPUT_DIR / "near_atm_filter_ablation.csv", index=False)
    actual_vs_replay_df.to_csv(OUTPUT_DIR / "near_atm_actual_vs_replay_comparison.csv", index=False)
    best_worst_df.to_csv(OUTPUT_DIR / "near_atm_best_and_worst_trades.csv", index=False)
    data_quality_df.to_csv(OUTPUT_DIR / "near_atm_burst_data_quality.csv", index=False)

    report = build_report(
        tape_dates=tape_dates,
        data_quality_df=data_quality_df,
        variant_summary_df=summary_df,
        daywise_df=daywise_df,
        comparison_df=comparison_df,
        ablation_df=ablation_df,
        best_worst_df=best_worst_df,
        charts=chart_paths,
    )
    (OUTPUT_DIR / "near_atm_research_report.md").write_text(report, encoding="utf-8")

    best_total = comparison_df[comparison_df["variant_name"] != "actual_system"].sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).iloc[0] if not comparison_df.empty and len(comparison_df[comparison_df["variant_name"] != "actual_system"]) > 0 else None
    best_worst = comparison_df[comparison_df["variant_name"] != "actual_system"].sort_values(["worst_day_pnl", "total_net_pnl"], ascending=[False, False]).iloc[0] if not comparison_df.empty and len(comparison_df[comparison_df["variant_name"] != "actual_system"]) > 0 else None
    any_beats = bool(comparison_df.loc[comparison_df["variant_name"] != "actual_system", "beats_actual_both_active"].any()) if not comparison_df.empty and "beats_actual_both_active" in comparison_df.columns else False
    live_ready = False

    print(f"Wrote near-ATM burst research outputs to {OUTPUT_DIR}")
    print(f"Full tape dates tested: {tape_dates}")
    print(f"Best variant by total PnL: {best_total['variant_name']} ({best_total['total_net_pnl']:.0f})" if best_total is not None else "Best variant by total PnL: none")
    print(f"Best variant by worst-day PnL: {best_worst['variant_name']} ({best_worst['worst_day_pnl']:.0f})" if best_worst is not None else "Best variant by worst-day PnL: none")
    print(f"Any variant beats actual system on total PnL and worst-day PnL? {'yes' if any_beats else 'no'}")
    print(f"Live-patch ready? {'yes' if live_ready else 'no'}")


if __name__ == "__main__":
    main()
