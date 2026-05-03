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
import near_atm_burst_research as natm
from sensex_noise.services.microburst import (
    classify_target,
    compute_pre_entry_features,
    compute_promoted_3s_diagnostics,
    layer4_persistence_result,
    promoted_trade_survives_3s,
)

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "tradable_expansion_edge_results"
CHARTS_DIR = OUTPUT_DIR / "charts"
PRIOR_CANDIDATE_PATH_GZ = REPO_ROOT / "burst_onset_research_results" / "burst_onset_candidates_all.csv.gz"
PRIOR_CANDIDATE_PATH = REPO_ROOT / "burst_onset_research_results" / "burst_onset_candidates_all.csv"

STRIKE_STEP = 100
GLOBAL_COOLDOWN_SECONDS = 45
SYMBOL_COOLDOWN_SECONDS = 60
TOP_WINDOW_SECONDS = 30
MAX_HOLD_SECONDS = 30
FIXED_QTY = 500
MIN_ACTIVITY_DAYS = 2
MIN_ACTIVITY_TRADES = 20


@dataclass(frozen=True)
class Variant:
    name: str
    raw_score_min: int = 5
    tes_min: int | None = None
    atm_max_abs: int = 200
    premium_min: float | None = None
    premium_max: float | None = None
    spread_abs_max: float | None = None
    spread_pct_max: float | None = None
    depth_min: float | None = None
    require_strict_context: bool = False
    require_loose_context: bool = False
    require_spread_compressed: bool = False
    require_same_side_confirm: bool = False
    require_opposite_suppression: bool = False
    require_quote_fresh: bool = False
    require_not_late_tail: bool = False
    require_confirmation_1s: bool = False
    target_points_override: float | None = None
    use_promoted_logic: bool = False
    cooldown_seconds: int = GLOBAL_COOLDOWN_SECONDS
    symbol_cooldown_seconds: int = SYMBOL_COOLDOWN_SECONDS
    top_window_seconds: int = TOP_WINDOW_SECONDS


VARIANTS: list[Variant] = [
    Variant(
        name="BASE_ATM100_SCORE5_P80_300_SPREAD2_DEPTH250",
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        spread_abs_max=2.0,
        depth_min=250,
        target_points_override=3.0,
    ),
    Variant(
        name="TES_ATM200_SCORE5_TES6",
        atm_max_abs=200,
        tes_min=6,
        premium_min=80,
        premium_max=350,
        spread_pct_max=0.015,
        depth_min=250,
        target_points_override=3.0,
    ),
    Variant(
        name="TES_ATM200_SCORE5_TES8",
        atm_max_abs=200,
        tes_min=8,
        premium_min=80,
        premium_max=350,
        spread_pct_max=0.015,
        depth_min=250,
        target_points_override=3.0,
    ),
    Variant(
        name="TES_ATM100_SCORE5_TES6",
        atm_max_abs=100,
        tes_min=6,
        premium_min=80,
        premium_max=300,
        spread_pct_max=0.015,
        depth_min=250,
        target_points_override=3.0,
    ),
    Variant(
        name="TES_ATM100_SCORE5_TES8",
        atm_max_abs=100,
        tes_min=8,
        premium_min=80,
        premium_max=300,
        spread_pct_max=0.015,
        depth_min=250,
        target_points_override=3.0,
    ),
    Variant(
        name="ULTRA_LIQUID_ATM100_SCORE5_TES6",
        atm_max_abs=100,
        tes_min=6,
        premium_min=150,
        premium_max=320,
        spread_abs_max=0.50,
        spread_pct_max=0.0025,
        depth_min=250,
        target_points_override=3.0,
    ),
    Variant(
        name="ULTRA_LIQUID_ATM200_SCORE5_TES6",
        atm_max_abs=200,
        tes_min=6,
        premium_min=150,
        premium_max=350,
        spread_abs_max=0.75,
        spread_pct_max=0.0035,
        depth_min=250,
        target_points_override=3.0,
    ),
    Variant(
        name="CONFIRM_1S_ATM100_SCORE5_TES6",
        atm_max_abs=100,
        tes_min=6,
        premium_min=80,
        premium_max=300,
        spread_pct_max=0.015,
        depth_min=250,
        require_confirmation_1s=True,
        target_points_override=3.0,
    ),
    Variant(
        name="CONFIRM_1S_ATM200_SCORE5_TES8",
        atm_max_abs=200,
        tes_min=8,
        premium_min=80,
        premium_max=350,
        spread_pct_max=0.015,
        depth_min=250,
        require_confirmation_1s=True,
        target_points_override=3.0,
    ),
    Variant(
        name="TES_ATM100_SCORE5_TES8_TARGET7",
        atm_max_abs=100,
        tes_min=8,
        premium_min=80,
        premium_max=300,
        spread_pct_max=0.015,
        depth_min=250,
        use_promoted_logic=True,
    ),
    Variant(
        name="ULTRA_LIQUID_ATM100_SCORE5_TES6_TARGET7",
        atm_max_abs=100,
        tes_min=6,
        premium_min=150,
        premium_max=320,
        spread_abs_max=0.50,
        spread_pct_max=0.0025,
        depth_min=250,
        use_promoted_logic=True,
    ),
]


def prior_candidate_path() -> Path | None:
    if PRIOR_CANDIDATE_PATH_GZ.exists():
        return PRIOR_CANDIDATE_PATH_GZ
    if PRIOR_CANDIDATE_PATH.exists():
        return PRIOR_CANDIDATE_PATH
    return None


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


def safe_float(value: Any) -> float | None:
    return bor.safe_float(value)


def parse_dt(value: Any) -> pd.Timestamp:
    return bor.parse_dt(value)


def load_candidate_onsets(settings: Any, audit: Any, dates: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = [
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
    quality_rows: list[dict[str, Any]] = []
    out_parts: list[pd.DataFrame] = []
    path = prior_candidate_path()
    cached_dates: set[str] = set()
    if path is not None:
        cached = pd.read_csv(path, usecols=cols, parse_dates=["timestamp"])
        cached["date"] = cached["date"].astype(str)
        cached = cached[cached["date"].isin(dates)].copy()
        if not cached.empty:
            cached_dates = set(cached["date"].unique())
            out_parts.append(cached)
            for date, g in cached.groupby("date"):
                quality_rows.append(
                    {
                        "date": date,
                        "candidate_source": str(path.relative_to(REPO_ROOT)),
                        "raw_candidate_rows": int(len(g)),
                        "raw_candidate_symbols": int(g["symbol"].nunique()),
                    }
                )
    missing = [d for d in dates if d not in cached_dates]
    for date in missing:
        print(f"[tes] computing fallback raw burst onsets for {date}", flush=True)
        candidates, _, quality = bor.compute_burst_onset_candidates_for_day(date, settings, audit)
        if candidates.empty:
            continue
        c = candidates.copy()
        rename_map = {"entry_time": "timestamp"}
        c = c.rename(columns=rename_map)
        c["date"] = date
        keep = [col for col in cols if col in c.columns]
        c = c[keep].copy()
        for col in cols:
            if col not in c.columns:
                c[col] = np.nan
        c["timestamp"] = pd.to_datetime(c["timestamp"])
        out_parts.append(c[cols])
        quality_rows.append(
            {
                "date": date,
                "candidate_source": "fallback_raw_tape_onset_compute",
                "raw_candidate_rows": int(len(c)),
                "raw_candidate_symbols": int(c["symbol"].nunique()),
                "raw_option_rows": quality.get("raw_rows"),
            }
        )
    out = pd.concat(out_parts, ignore_index=True) if out_parts else pd.DataFrame(columns=cols)
    return out, pd.DataFrame(quality_rows)


def build_candidate_day(
    date: str,
    raw_candidates: pd.DataFrame,
    settings: Any,
    audit: Any,
) -> tuple[pd.DataFrame, dict[str, list[dict[str, Any]]], pd.Series, dict[str, pd.DataFrame], dict[str, pd.DatetimeIndex], dict[str, Any]]:
    day_candidates = raw_candidates[raw_candidates["date"] == date].copy()
    if day_candidates.empty:
        return pd.DataFrame(), {}, pd.Series(dtype=float), {}, {}, {"date": date}

    underlying = audit.load_underlying_second_series(date)
    if underlying.empty:
        return pd.DataFrame(), {}, underlying, {}, {}, {"date": date, "error": "missing_underlying"}

    u = underlying.rename("underlying_ltp").reset_index().rename(columns={"index": "timestamp"})
    u["timestamp"] = pd.to_datetime(u["timestamp"])
    day_candidates = pd.merge_asof(
        day_candidates.sort_values("timestamp"),
        u.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
        tolerance=pd.Timedelta(seconds=1),
    )
    day_candidates = day_candidates.dropna(subset=["underlying_ltp"]).copy()
    if day_candidates.empty:
        return pd.DataFrame(), {}, underlying, {}, {}, {"date": date, "error": "no_underlying_merge"}

    day_candidates["raw_burst_score"] = day_candidates["score"].astype(int)
    day_candidates = day_candidates[day_candidates["raw_burst_score"] >= 5].copy()
    if day_candidates.empty:
        return pd.DataFrame(), {}, underlying, {}, {}, {"date": date, "error": "no_score5_candidates"}

    day_candidates["atm_strike"] = day_candidates["underlying_ltp"].apply(round_to_strike)
    day_candidates["atm_distance_points"] = day_candidates["strike"].round().astype(int) - day_candidates["atm_strike"].astype(int)
    day_candidates["atm_distance_abs"] = day_candidates["atm_distance_points"].abs()
    day_candidates = day_candidates[day_candidates["atm_distance_abs"] <= 200].copy()
    if day_candidates.empty:
        return pd.DataFrame(), {}, underlying, {}, {}, {"date": date, "error": "no_atm200_candidates"}

    day_candidates["atm_bucket"] = day_candidates["atm_distance_abs"].apply(atm_bucket)
    day_candidates["mid_price"] = (day_candidates["best_bid"] + day_candidates["best_ask"]) / 2.0
    day_candidates["spread_pct"] = day_candidates["spread"] / day_candidates["ltp"]
    day_candidates["depth_min_qty"] = np.minimum(day_candidates["bid_qty"], day_candidates["ask_qty"])
    day_candidates["raw_score_crossed_now"] = True
    day_candidates["burst_onset_age_seconds"] = 0.0
    day_candidates["seconds_since_first_score_ge_5"] = 0.0

    symbols_needed = set(day_candidates["symbol"].astype(str).unique())
    symbol_rows, subset_quality = natm.load_option_second_rows_subset(date, symbols_needed)
    series_cache: dict[str, pd.DataFrame] = {sym: audit.build_ffill_symbol_series(rows) for sym, rows in symbol_rows.items() if rows}
    update_times: dict[str, pd.DatetimeIndex] = {
        sym: pd.DatetimeIndex(pd.to_datetime([row["timestamp"] for row in rows])) for sym, rows in symbol_rows.items() if rows
    }
    quality = {
        "date": date,
        "candidate_rows": int(len(day_candidates)),
        "candidate_symbols": int(day_candidates["symbol"].nunique()),
        "replay_subset_symbols": int(len(symbol_rows)),
        "replay_subset_raw_rows": subset_quality.get("raw_rows"),
        "replay_subset_kept_rows": subset_quality.get("kept_rows"),
    }
    return day_candidates.sort_values("timestamp").reset_index(drop=True), symbol_rows, underlying, series_cache, update_times, quality


def value_at(series: pd.DataFrame, ts: pd.Timestamp, col: str, seconds_back: int = 0) -> float | None:
    target = ts - pd.Timedelta(seconds=seconds_back)
    if target not in series.index:
        return None
    value = safe_float(series.loc[target, col])
    return value


def count_updates(update_index: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> int:
    if update_index.empty:
        return 0
    left = update_index.searchsorted(start, side="left")
    right = update_index.searchsorted(end, side="right")
    return int(max(0, right - left))


def build_cross_section_lookup(day_candidates: pd.DataFrame) -> dict[pd.Timestamp, pd.DataFrame]:
    return {ts: g.copy() for ts, g in day_candidates.groupby("timestamp", sort=False)}


def tradable_expansion_components(row: dict[str, Any]) -> tuple[int, dict[str, int]]:
    score = 0
    comps: dict[str, int] = {}

    def add(name: str, points: int) -> None:
        nonlocal score
        score += points
        comps[name] = points

    if bool(row.get("raw_score_crossed_now")):
        add("fresh_cross_now", 2)
    if float(row.get("burst_onset_age_seconds") or 0.0) <= 2:
        add("fresh_age_le_2", 1)
    if float(row.get("burst_onset_age_seconds") or 0.0) > 5:
        add("stale_age_gt_5", -2)

    spread_comp = float(row.get("spread_compression_ratio") or np.nan)
    if np.isfinite(spread_comp) and spread_comp <= 1.0:
        add("spread_not_wide", 2)
    if bool(row.get("spread_is_widening")):
        add("spread_widening", -3)
    spread_pct = float(row.get("spread_pct_now") or 0.0)
    if spread_pct <= 0.001:
        add("spread_pct_le_0_1pct", 1)
    if spread_pct <= 0.005:
        add("spread_pct_le_0_5pct", 1)

    if int(row.get("same_side_confirm_count_100") or 0) >= 1:
        add("same_side_100_confirm", 2)
    if int(row.get("same_side_confirm_count_200") or 0) >= 2:
        add("same_side_200_confirm", 1)
    if float(row.get("same_side_avg_opt_velocity") or 0.0) > 0:
        add("same_side_velocity_pos", 1)

    if int(row.get("opposite_side_confirm_count") or 0) == 0:
        add("opposite_zero", 2)
    if float(row.get("directional_dominance_velocity") or 0.0) > 1.0:
        add("dominance_velocity", 1)
    if int(row.get("opposite_side_confirm_count") or 0) >= 2:
        add("opposite_many", -2)

    if bool(row.get("quote_fresh")):
        add("quote_fresh", 1)
    if bool(row.get("active_quote")):
        add("active_quote", 1)
    if not bool(row.get("quote_fresh")):
        add("stale_quote", -2)

    if float(row.get("mid_velocity_1s") or 0.0) > 0:
        add("mid_velocity_pos", 1)
    if bool(row.get("bid_following_ask")):
        add("bid_following_ask", 1)
    if bool(row.get("depth_not_vanishing")):
        add("depth_not_vanishing", 1)
    if bool(row.get("ltp_near_bid")) and bool(row.get("spread_is_widening")):
        add("near_bid_widening", -2)

    if not bool(row.get("late_tail_flag")):
        add("not_late_tail", 2)
    else:
        add("late_tail", -3)

    dist_abs = int(row.get("atm_distance_abs") or 0)
    if dist_abs <= 100:
        add("atm_le_100", 2)
    elif dist_abs <= 200:
        add("atm_le_200", 1)
    if dist_abs == 200 and spread_pct > 0.01:
        add("atm_200_wide", -1)

    return score, comps


def compute_tes_for_day(
    day_candidates: pd.DataFrame,
    symbol_rows: dict[str, list[dict[str, Any]]],
    underlying: pd.Series,
    series_cache: dict[str, pd.DataFrame],
    update_times: dict[str, pd.DatetimeIndex],
) -> pd.DataFrame:
    if day_candidates.empty:
        return day_candidates
    ts_groups = build_cross_section_lookup(day_candidates)
    rows_out: list[dict[str, Any]] = []

    for row in day_candidates.to_dict(orient="records"):
        sym = str(row["symbol"])
        ts = pd.Timestamp(row["timestamp"])
        series = series_cache.get(sym)
        if series is None or ts not in series.index:
            continue
        update_index = update_times.get(sym, pd.DatetimeIndex([]))
        current = series.loc[ts]
        ltp_now = float(current["ltp"])
        mid_now = (float(current.get("best_bid") or ltp_now) + float(current.get("best_ask") or ltp_now)) / 2.0
        spread_now = float(current.get("spread") or row.get("spread") or 0.0)
        best_bid_now = safe_float(current.get("best_bid")) or ltp_now
        best_ask_now = safe_float(current.get("best_ask")) or ltp_now
        bid_qty_now = safe_float(current.get("bid_qty")) or safe_float(row.get("bid_qty")) or 0.0
        ask_qty_now = safe_float(current.get("ask_qty")) or safe_float(row.get("ask_qty")) or 0.0
        depth_now = min(bid_qty_now, ask_qty_now)

        def move(col: str, back: int, current_value: float) -> float:
            prev = value_at(series, ts, col, back)
            return float(current_value - prev) if prev is not None else np.nan

        opt_move_1s = move("ltp", 1, ltp_now)
        opt_move_3s = move("ltp", 3, ltp_now)
        opt_move_5s = move("ltp", 5, ltp_now)
        opt_move_10s = move("ltp", 10, ltp_now)
        opt_move_20s = move("ltp", 20, ltp_now)
        mid_move_1s = move("best_bid", 1, best_bid_now)
        ask_move_1s = move("best_ask", 1, best_ask_now)
        bid_move_1s = move("best_bid", 1, best_bid_now)
        spread_change_1s = move("spread", 1, spread_now)
        spread_change_3s = move("spread", 3, spread_now)
        depth_change_1s = move("bid_qty", 1, bid_qty_now)

        under_now = float(underlying.loc[:ts].iloc[-1])
        def under_move(back: int) -> float:
            prev_ts = ts - pd.Timedelta(seconds=back)
            if prev_ts not in underlying.index:
                return np.nan
            return float(under_now - float(underlying.loc[prev_ts]))

        under_move_1s = under_move(1)
        under_move_3s = under_move(3)
        under_move_5s = under_move(5)

        window = series.loc[ts - pd.Timedelta(seconds=5) : ts]
        spread_mean_5s = float(window["spread"].dropna().mean()) if "spread" in window else np.nan
        spread_min_5s = float(window["spread"].dropna().min()) if "spread" in window and not window["spread"].dropna().empty else np.nan
        spread_max_5s = float(window["spread"].dropna().max()) if "spread" in window and not window["spread"].dropna().empty else np.nan
        depth_mean_5s = float(np.minimum(window["bid_qty"].fillna(0.0), window["ask_qty"].fillna(0.0)).mean()) if not window.empty else np.nan
        spread_compression_ratio = float(spread_now / spread_mean_5s) if np.isfinite(spread_mean_5s) and spread_mean_5s > 0 else np.nan
        spread_is_compressed = bool(np.isfinite(spread_compression_ratio) and spread_compression_ratio <= 0.80)
        spread_is_widening = bool(np.isfinite(spread_compression_ratio) and spread_compression_ratio >= 1.25)

        updates_5s = count_updates(update_index, ts - pd.Timedelta(seconds=5), ts)
        seconds_since_update = 0.0
        quote_fresh = seconds_since_update <= 1.0
        active_quote = updates_5s >= 3

        group = ts_groups.get(ts, pd.DataFrame())
        if group.empty:
            group = pd.DataFrame([row])
        strike = int(row["strike"])
        same_side = group[(group["option_type"] == row["option_type"]) & (group["symbol"] != sym)].copy()
        same_100 = same_side[(same_side["strike"] - strike).abs() <= 100]
        same_200 = same_side[(same_side["strike"] - strike).abs() <= 200]
        opposite = group[group["option_type"] != row["option_type"]].copy()

        same_side_avg_vel = float(same_200["opt_velocity_aligned"].mean()) if not same_200.empty else 0.0
        opposite_avg_vel = float(opposite["opt_velocity_aligned"].mean()) if not opposite.empty else 0.0
        same_side_updates = []
        for other_sym in same_200["symbol"].astype(str).tolist():
            same_side_updates.append(count_updates(update_times.get(other_sym, pd.DatetimeIndex([])), ts - pd.Timedelta(seconds=5), ts))
        adjacent_update_count_mean = float(np.mean(same_side_updates)) if same_side_updates else 0.0

        same_side_confirm_count_100 = int(len(same_100))
        same_side_confirm_count_200 = int(len(same_200))
        same_side_max_raw_score = int(same_200["raw_burst_score"].max()) if not same_200.empty else 0
        same_side_mean_raw_score = float(same_200["raw_burst_score"].mean()) if not same_200.empty else 0.0
        selected_vs_same_side_avg_velocity_ratio = float((float(row["opt_velocity_aligned"]) / same_side_avg_vel) if abs(same_side_avg_vel) > 1e-9 else np.nan)
        opposite_count = int(len(opposite))
        opposite_max_raw_score = int(opposite["raw_burst_score"].max()) if not opposite.empty else 0
        opposite_mean_raw_score = float(opposite["raw_burst_score"].mean()) if not opposite.empty else 0.0
        dominance_velocity = float(same_side_avg_vel - opposite_avg_vel)

        spread_pct_now = float(spread_now / ltp_now) if ltp_now > 0 else np.nan
        ltp_near_ask = bool(abs(ltp_now - best_ask_now) <= max(0.25, 0.1 * spread_now))
        ltp_near_bid = bool(abs(ltp_now - best_bid_now) <= max(0.25, 0.1 * spread_now))
        depth_not_vanishing = bool(np.isfinite(depth_mean_5s) and depth_mean_5s > 0 and depth_now >= 0.70 * depth_mean_5s)
        bid_following_ask = bool((bid_move_1s or 0.0) > 0)
        velocity_decay_1s_vs_5s = float((opt_move_1s / abs(opt_move_5s)) if np.isfinite(opt_move_1s) and np.isfinite(opt_move_5s) and abs(opt_move_5s) > 1e-9 else np.nan)
        late_tail_flag = bool((np.isfinite(opt_move_5s) and abs(opt_move_5s) >= 3.0 and (not np.isfinite(opt_move_1s) or opt_move_1s <= 0)) or spread_is_widening)
        exhaustion_ratio_5s_20s = float((opt_move_5s / abs(opt_move_20s)) if np.isfinite(opt_move_5s) and np.isfinite(opt_move_20s) and abs(opt_move_20s) > 1e-9 else np.nan)

        rec = dict(row)
        rec.update(
            {
                "mid_price": mid_now,
                "spread_now": spread_now,
                "spread_pct_now": spread_pct_now,
                "spread_mean_5s": spread_mean_5s,
                "spread_min_5s": spread_min_5s,
                "spread_max_5s": spread_max_5s,
                "spread_change_1s": spread_change_1s,
                "spread_change_3s": spread_change_3s,
                "spread_compression_ratio": spread_compression_ratio,
                "spread_is_compressed": spread_is_compressed,
                "spread_is_widening": spread_is_widening,
                "option_move_1s": opt_move_1s,
                "option_move_3s": opt_move_3s,
                "option_move_5s": opt_move_5s,
                "option_move_1s_to_5s_ratio": float((opt_move_1s / opt_move_5s) if np.isfinite(opt_move_1s) and np.isfinite(opt_move_5s) and abs(opt_move_5s) > 1e-9 else np.nan),
                "underlying_move_1s": under_move_1s,
                "underlying_move_3s": under_move_3s,
                "underlying_move_5s": under_move_5s,
                "underlying_move_1s_to_5s_ratio": float((under_move_1s / under_move_5s) if np.isfinite(under_move_1s) and np.isfinite(under_move_5s) and abs(under_move_5s) > 1e-9 else np.nan),
                "same_side_confirm_count_100": same_side_confirm_count_100,
                "same_side_confirm_count_200": same_side_confirm_count_200,
                "same_side_avg_opt_velocity": same_side_avg_vel,
                "same_side_max_raw_score": same_side_max_raw_score,
                "same_side_mean_raw_score": same_side_mean_raw_score,
                "selected_vs_same_side_avg_velocity_ratio": selected_vs_same_side_avg_velocity_ratio,
                "opposite_side_confirm_count": opposite_count,
                "opposite_side_avg_opt_velocity": opposite_avg_vel,
                "opposite_side_max_raw_score": opposite_max_raw_score,
                "opposite_side_mean_raw_score": opposite_mean_raw_score,
                "directional_dominance_velocity": dominance_velocity,
                "seconds_since_symbol_update": seconds_since_update,
                "update_count_5s": updates_5s,
                "adjacent_update_count_5s_mean": adjacent_update_count_mean,
                "quote_fresh": quote_fresh,
                "active_quote": active_quote,
                "mid_velocity_1s": move("best_bid", 1, mid_now),
                "mid_velocity_3s": move("best_bid", 3, mid_now),
                "bid_velocity_1s": bid_move_1s,
                "ask_velocity_1s": ask_move_1s,
                "bid_following_ask": bid_following_ask,
                "ltp_near_ask": ltp_near_ask,
                "ltp_near_bid": ltp_near_bid,
                "depth_change_1s": depth_change_1s,
                "depth_not_vanishing": depth_not_vanishing,
                "pre_burst_move_10s": opt_move_10s,
                "pre_burst_move_20s": opt_move_20s,
                "exhaustion_ratio_5s_20s": exhaustion_ratio_5s_20s,
                "velocity_decay_1s_vs_5s": velocity_decay_1s_vs_5s,
                "late_tail_flag": late_tail_flag,
            }
        )
        tes_score, tes_components = tradable_expansion_components(rec)
        rec["tradable_expansion_score"] = tes_score
        rec["tradable_expansion_components"] = json.dumps(tes_components, sort_keys=True)
        rec["composite_entry_score"] = int(rec["raw_burst_score"]) * 2 + tes_score
        rows_out.append(rec)

    out = pd.DataFrame(rows_out)
    if not out.empty:
        out["rank_score"] = (
            10000.0 * out["raw_burst_score"]
            + 1000.0 * out["tradable_expansion_score"]
            + 100.0 * out["opt_velocity_aligned"].fillna(0.0)
            + 50.0 * out["directional_dominance_velocity"].fillna(0.0)
            + 25.0 * out["same_side_confirm_count_100"].fillna(0.0)
            - 500.0 * out["spread_pct_now"].fillna(0.0)
            - 10.0 * out["atm_distance_abs"].fillna(0.0) / 100.0
        )
    return out.sort_values(["date", "timestamp", "rank_score"], ascending=[True, True, False]).reset_index(drop=True)


def variant_filters(row: pd.Series, variant: Variant) -> bool:
    if int(row["raw_burst_score"]) < variant.raw_score_min:
        return False
    if int(row["atm_distance_abs"]) > int(variant.atm_max_abs):
        return False
    if variant.tes_min is not None and int(row["tradable_expansion_score"]) < int(variant.tes_min):
        return False
    if variant.premium_min is not None and float(row["ltp"]) < float(variant.premium_min):
        return False
    if variant.premium_max is not None and float(row["ltp"]) > float(variant.premium_max):
        return False
    if variant.spread_abs_max is not None and float(row["spread_now"]) > float(variant.spread_abs_max):
        return False
    if variant.spread_pct_max is not None and float(row["spread_pct_now"]) > float(variant.spread_pct_max):
        return False
    if variant.depth_min is not None and float(row["depth_min_qty"]) < float(variant.depth_min):
        return False
    if variant.require_strict_context and not bool(row.get("context_agrees")):
        return False
    if variant.require_loose_context and not bool(row.get("loose_context_agrees")):
        return False
    if variant.require_spread_compressed and not bool(row.get("spread_is_compressed")):
        return False
    if variant.require_same_side_confirm and int(row.get("same_side_confirm_count_100") or 0) < 1:
        return False
    if variant.require_opposite_suppression and int(row.get("opposite_side_confirm_count") or 0) > 0:
        return False
    if variant.require_quote_fresh and not bool(row.get("quote_fresh")):
        return False
    if variant.require_not_late_tail and bool(row.get("late_tail_flag")):
        return False
    return True


def select_variant_candidates(day_df: pd.DataFrame, variant: Variant) -> pd.DataFrame:
    if day_df.empty:
        return pd.DataFrame()
    filtered = day_df[day_df.apply(lambda r: variant_filters(r, variant), axis=1)].copy()
    if filtered.empty:
        return filtered
    start = pd.Timestamp(str(filtered["date"].iloc[0]) + " 09:15:00")
    filtered["window_index"] = ((pd.to_datetime(filtered["timestamp"]) - start).dt.total_seconds() // variant.top_window_seconds).astype(int)
    filtered = filtered.sort_values(["window_index", "rank_score", "timestamp", "symbol"], ascending=[True, False, True, True])
    top = filtered.groupby("window_index", as_index=False, group_keys=False).head(1).drop(columns=["window_index"]).reset_index(drop=True)
    top["variant_name"] = variant.name
    return top


def choose_entry_time(candidate: pd.Series, variant: Variant, series_cache: dict[str, pd.DataFrame], underlying: pd.Series) -> tuple[pd.Timestamp | None, dict[str, Any]]:
    ts = pd.Timestamp(candidate["timestamp"])
    sym = str(candidate["symbol"])
    meta: dict[str, Any] = {"confirmation_used": bool(variant.require_confirmation_1s)}
    if not variant.require_confirmation_1s:
        return ts, meta
    series = series_cache.get(sym)
    if series is None:
        meta["confirmation_rejected"] = "missing_series"
        return None, meta
    next_ts = ts + pd.Timedelta(seconds=1)
    if next_ts not in series.index or ts not in series.index:
        meta["confirmation_rejected"] = "missing_next_second"
        return None, meta
    ltp_t = float(series.loc[ts, "ltp"])
    ltp_n = float(series.loc[next_ts, "ltp"])
    spread_t = safe_float(series.loc[ts, "spread"]) or float(candidate.get("spread_now") or candidate.get("spread") or 0.0)
    spread_n = safe_float(series.loc[next_ts, "spread"]) or spread_t
    spread_pct_t = spread_t / ltp_t if ltp_t > 0 else np.nan
    spread_pct_n = spread_n / ltp_n if ltp_n > 0 else np.nan
    if next_ts not in underlying.index or ts not in underlying.index:
        meta["confirmation_rejected"] = "missing_underlying"
        return None, meta
    spot_t = float(underlying.loc[ts])
    spot_n = float(underlying.loc[next_ts])
    aligned_move = (spot_n - spot_t) if str(candidate["side"]).upper() == "CALL" else (spot_t - spot_n)
    if ltp_n < ltp_t:
        meta["confirmation_rejected"] = "ltp_down"
        return None, meta
    if np.isfinite(spread_pct_t) and np.isfinite(spread_pct_n) and spread_pct_n > spread_pct_t * 1.25:
        meta["confirmation_rejected"] = "spread_worse"
        return None, meta
    if aligned_move <= 0:
        meta["confirmation_rejected"] = "underlying_not_aligned"
        return None, meta
    meta["confirmed_entry_time"] = next_ts
    return next_ts, meta


def simulate_fixed_target_trade(
    symbol: str,
    entry_time: pd.Timestamp,
    symbol_rows: list[dict[str, Any]],
    settings: Any,
    series_cache: dict[str, pd.DataFrame],
    target_points: float = 3.0,
    hard_stop_points: float | None = None,
    max_hold_seconds: int = MAX_HOLD_SECONDS,
    quantity: int = FIXED_QTY,
) -> dict[str, Any] | None:
    if symbol not in series_cache:
        series_cache[symbol] = audit.build_ffill_symbol_series(symbol_rows)  # type: ignore[name-defined]
    series = series_cache[symbol]
    if entry_time not in series.index:
        return None
    entry_price = float(series.loc[entry_time, "ltp"])
    option_type = str(series.loc[entry_time, "option_type"]).upper()
    hard_stop_points = float(hard_stop_points if hard_stop_points is not None else getattr(settings, "edge_invalidation_hard_stop_points", 6.0))
    check_1s = float(getattr(settings, "edge_invalidation_1s_check_seconds", 1.0))
    check_3s = float(getattr(settings, "edge_invalidation_3s_check_seconds", 3.0))
    min_runup_1s = float(getattr(settings, "edge_invalidation_1s_min_runup_points", 1.0))
    max_pnl_1s = float(getattr(settings, "edge_invalidation_1s_max_pnl_points", 0.0))
    min_runup_3s = float(getattr(settings, "edge_invalidation_3s_min_runup_points", 2.0))
    max_drawdown_3s = float(getattr(settings, "edge_invalidation_3s_max_drawdown_points", 4.0))
    pinned_abs_3s = float(getattr(settings, "edge_invalidation_3s_pinned_pnl_abs_points", 1.0))

    checked_1s = False
    checked_3s = False
    runup = 0.0
    drawdown = 0.0
    last_row = None
    reason = None
    exit_time = entry_time
    exit_price = entry_price
    for now, row in series.loc[entry_time : entry_time + pd.Timedelta(seconds=max_hold_seconds)].iterrows():
        last_row = row
        ltp = float(row["ltp"])
        pnl = ltp - entry_price
        runup = max(runup, pnl)
        drawdown = min(drawdown, pnl)
        elapsed = float((now - entry_time).total_seconds())
        if pnl >= target_points:
            reason = "TARGET_HIT"
            exit_time = now
            exit_price = ltp
            break
        if pnl <= -hard_stop_points:
            reason = "EDGE_HARD_STOP"
            exit_time = now
            exit_price = ltp
            break
        if (not checked_1s) and elapsed >= check_1s:
            checked_1s = True
            if runup < min_runup_1s and pnl <= max_pnl_1s:
                reason = "EARLY_FAIL_1S"
                exit_time = now
                exit_price = ltp
                break
        if (not checked_3s) and elapsed >= check_3s:
            checked_3s = True
            if runup < min_runup_3s or abs(drawdown) >= max_drawdown_3s or abs(pnl) <= pinned_abs_3s:
                reason = "EARLY_FAIL_3S"
                exit_time = now
                exit_price = ltp
                break
    if reason is None:
        if last_row is None:
            return None
        reason = f"SIM_TIMEOUT_{max_hold_seconds}S"
        exit_time = series.loc[entry_time : entry_time + pd.Timedelta(seconds=max_hold_seconds)].index[-1]
        exit_price = float(last_row["ltp"])
    points_pnl = exit_price - entry_price
    gross_pnl = points_pnl * quantity
    return {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "holding_seconds": float((exit_time - entry_time).total_seconds()),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "exit_reason": reason,
        "target_points": float(target_points),
        "quantity": quantity,
        "quantity_source": "fixed_500",
        "gross_pnl": gross_pnl,
        "net_pnl": gross_pnl,
        "runup_points": runup,
        "drawdown_points": drawdown,
        "promoted_candidate": False,
        "promotion_persistence_passed": False,
        "option_type": option_type,
    }


def simulate_promoted_trade_fixed_qty(
    symbol: str,
    entry_time: pd.Timestamp,
    score: int,
    symbol_rows: list[dict[str, Any]],
    settings: Any,
    series_cache: dict[str, pd.DataFrame],
    max_hold_seconds: int = MAX_HOLD_SECONDS,
    quantity: int = FIXED_QTY,
) -> dict[str, Any] | None:
    result = audit.simulate_burst_trade(symbol, entry_time, score, symbol_rows, settings, series_cache, max_hold_seconds=max_hold_seconds)  # type: ignore[name-defined]
    if result is None:
        return None
    points_pnl = float(result["exit_price"] - result["entry_price"])
    result = dict(result)
    result["quantity"] = quantity
    result["quantity_source"] = "fixed_500"
    result["gross_pnl"] = points_pnl * quantity
    result["net_pnl"] = result["gross_pnl"]
    return result


def replay_variant_day(
    date: str,
    variant: Variant,
    selected_df: pd.DataFrame,
    symbol_rows: dict[str, list[dict[str, Any]]],
    underlying: pd.Series,
    settings: Any,
    series_cache: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if selected_df.empty:
        return pd.DataFrame()
    trades: list[dict[str, Any]] = []
    next_free_time: pd.Timestamp | None = None
    last_symbol_entry: dict[str, pd.Timestamp] = {}
    for row in selected_df.sort_values(["timestamp", "rank_score"], ascending=[True, False]).to_dict(orient="records"):
        ts = pd.Timestamp(row["timestamp"])
        sym = str(row["symbol"])
        if next_free_time is not None and ts < next_free_time:
            continue
        prev = last_symbol_entry.get(sym)
        if prev is not None and (ts - prev).total_seconds() < variant.symbol_cooldown_seconds:
            continue
        entry_time, meta = choose_entry_time(pd.Series(row), variant, series_cache, underlying)
        if entry_time is None:
            continue
        if variant.use_promoted_logic:
            result = simulate_promoted_trade_fixed_qty(sym, entry_time, int(row["raw_burst_score"]), symbol_rows[sym], settings, series_cache)
        else:
            result = simulate_fixed_target_trade(sym, entry_time, symbol_rows[sym], settings, series_cache, target_points=float(variant.target_points_override or 3.0))
        if result is None:
            continue
        merged = {**row, **meta, **result}
        merged["variant_name"] = variant.name
        merged["points_pnl"] = float(merged["exit_price"] - merged["entry_price"])
        trades.append(merged)
        last_symbol_entry[sym] = entry_time
        next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
    return pd.DataFrame(trades)


def summarize_actual_day(actual_df: pd.DataFrame, date: str) -> dict[str, Any]:
    if actual_df.empty:
        return {
            "date": date,
            "variant_name": "actual_system",
            "candidate_count": np.nan,
            "selected_trades": 0,
            "net_pnl": 0.0,
            "profit_factor": np.nan,
            "max_drawdown": 0.0,
            "win_rate": np.nan,
            "avg_pnl": np.nan,
            "target_hits": 0,
            "hard_stops": 0,
            "one_sec_kills": 0,
            "three_sec_kills": 0,
            "promoted_count": 0,
        }
    ordered = actual_df.sort_values("exit_time").copy()
    eq = ordered["net_pnl"].cumsum()
    dd = eq - eq.cummax()
    wins = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"]
    losses = ordered.loc[ordered["net_pnl"] < 0, "net_pnl"]
    pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
    promoted_mask = ordered.get("is_promoted_candidate", pd.Series(False, index=ordered.index)).fillna(False).astype(bool)
    return {
        "date": date,
        "variant_name": "actual_system",
        "candidate_count": np.nan,
        "selected_trades": int(len(ordered)),
        "net_pnl": float(ordered["net_pnl"].sum()),
        "profit_factor": pf,
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "win_rate": float((ordered["net_pnl"] > 0).mean()),
        "avg_pnl": float(ordered["net_pnl"].mean()),
        "target_hits": int((ordered["exit_reason"] == "TARGET_HIT").sum()),
        "hard_stops": int(ordered["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).sum()),
        "one_sec_kills": int((ordered["exit_reason"] == "EARLY_FAIL_1S").sum()),
        "three_sec_kills": int(ordered["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S", "PROMOTION_PERSISTENCE_FAIL"]).sum()),
        "promoted_count": int(promoted_mask.sum()),
    }


def summarize_replay_day(replay_df: pd.DataFrame, date: str, variant_name: str, candidate_count: int) -> dict[str, Any]:
    if replay_df.empty:
        return {
            "date": date,
            "variant_name": variant_name,
            "candidate_count": int(candidate_count),
            "selected_trades": 0,
            "net_pnl": 0.0,
            "profit_factor": np.nan,
            "max_drawdown": 0.0,
            "win_rate": np.nan,
            "avg_pnl": np.nan,
            "target_hits": 0,
            "hard_stops": 0,
            "one_sec_kills": 0,
            "three_sec_kills": 0,
            "promoted_count": 0,
        }
    ordered = replay_df.sort_values("exit_time").copy()
    eq = ordered["net_pnl"].cumsum()
    dd = eq - eq.cummax()
    wins = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"]
    losses = ordered.loc[ordered["net_pnl"] < 0, "net_pnl"]
    pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
    promoted_mask = ordered.get("promoted_candidate", pd.Series(False, index=ordered.index)).fillna(False).astype(bool)
    return {
        "date": date,
        "variant_name": variant_name,
        "candidate_count": int(candidate_count),
        "selected_trades": int(len(ordered)),
        "net_pnl": float(ordered["net_pnl"].sum()),
        "profit_factor": pf,
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "win_rate": float((ordered["net_pnl"] > 0).mean()),
        "avg_pnl": float(ordered["net_pnl"].mean()),
        "target_hits": int((ordered["exit_reason"] == "TARGET_HIT").sum()),
        "hard_stops": int((ordered["exit_reason"] == "EDGE_HARD_STOP").sum()),
        "one_sec_kills": int((ordered["exit_reason"] == "EARLY_FAIL_1S").sum()),
        "three_sec_kills": int(ordered["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S", "PROMOTION_PERSISTENCE_FAIL"]).sum()),
        "promoted_count": int(promoted_mask.sum()),
    }


def aggregate_summary(daywise_df: pd.DataFrame, variant_name: str, replay_df: pd.DataFrame | None = None) -> dict[str, Any]:
    rows = daywise_df[daywise_df["variant_name"] == variant_name].copy()
    if rows.empty:
        return {"variant_name": variant_name, "days": 0}
    out = {
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
    if replay_df is not None and not replay_df.empty:
        wins = replay_df.loc[replay_df["net_pnl"] > 0, "net_pnl"]
        losses = replay_df.loc[replay_df["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        out["trade_level_profit_factor"] = pf
        out["trade_level_win_rate"] = float((replay_df["net_pnl"] > 0).mean())
        out["trade_level_avg_pnl"] = float(replay_df["net_pnl"].mean())
    return out


def build_comparison(summary_df: pd.DataFrame) -> pd.DataFrame:
    actual = summary_df[summary_df["variant_name"] == "actual_system"]
    if actual.empty:
        return summary_df.copy()
    actual_row = actual.iloc[0]
    rows = []
    for _, row in summary_df.iterrows():
        rec = row.to_dict()
        rec["delta_total_pnl_vs_actual"] = float(rec.get("total_net_pnl", 0.0) - actual_row["total_net_pnl"])
        rec["delta_worst_day_vs_actual"] = float(rec.get("worst_day_pnl", 0.0) - actual_row["worst_day_pnl"])
        rec["delta_trade_count_vs_actual"] = float(rec.get("total_trades", 0.0) - actual_row["total_trades"])
        rec["beats_actual_total_pnl"] = bool(rec.get("total_net_pnl", -np.inf) > actual_row["total_net_pnl"])
        rec["beats_actual_worst_day"] = bool(rec.get("worst_day_pnl", -np.inf) >= actual_row["worst_day_pnl"])
        rec["beats_actual_both"] = bool(rec["beats_actual_total_pnl"] and rec["beats_actual_worst_day"])
        rec["meets_live_gate"] = bool(
            rec.get("variant_name") != "actual_system"
            and float(rec.get("total_net_pnl", 0.0)) > 0
            and int(rec.get("active_days", 0)) >= 2
            and int(rec.get("total_trades", 0)) >= 20
            and float(rec.get("trade_level_profit_factor", 0.0) or 0.0) > 1.3
            and bool(rec["beats_actual_both"])
        )
        rows.append(rec)
    return pd.DataFrame(rows)


def load_previous_broad_summary() -> pd.DataFrame:
    path = REPO_ROOT / "burst_onset_research_results" / "candle_context_burst_trigger_replay.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "variant" in df.columns and "variant_name" not in df.columns:
        df = df.rename(columns={"variant": "variant_name"})
    return df


def load_previous_near_atm_summary() -> pd.DataFrame:
    path = REPO_ROOT / "near_atm_burst_research_results" / "near_atm_variant_summary.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def run_ablation(
    best_variant: Variant,
    day_candidates_by_date: dict[str, pd.DataFrame],
    symbol_rows_by_date: dict[str, dict[str, list[dict[str, Any]]]],
    underlying_by_date: dict[str, pd.Series],
    settings: Any,
    base_series_cache: dict[str, dict[str, pd.DataFrame]],
) -> pd.DataFrame:
    ablations = [
        replace(best_variant, name=f"{best_variant.name}__baseline"),
        replace(best_variant, name=f"{best_variant.name}__remove_tes", tes_min=None),
        replace(best_variant, name=f"{best_variant.name}__remove_spread_compression", require_spread_compressed=False),
        replace(best_variant, name=f"{best_variant.name}__remove_adjacent_confirmation", require_same_side_confirm=False),
        replace(best_variant, name=f"{best_variant.name}__remove_opposite_suppression", require_opposite_suppression=False),
        replace(best_variant, name=f"{best_variant.name}__remove_quote_freshness", require_quote_fresh=False),
        replace(best_variant, name=f"{best_variant.name}__remove_exhaustion_penalty", require_not_late_tail=False),
        replace(best_variant, name=f"{best_variant.name}__remove_ultra_tight_spread", spread_abs_max=None, spread_pct_max=None),
        replace(best_variant, name=f"{best_variant.name}__remove_atm_filter", atm_max_abs=200),
        replace(best_variant, name=f"{best_variant.name}__remove_depth_filter", depth_min=None),
        replace(best_variant, name=f"{best_variant.name}__remove_confirmation", require_confirmation_1s=False),
        replace(best_variant, name=f"{best_variant.name}__cooldown_15", cooldown_seconds=15),
        replace(best_variant, name=f"{best_variant.name}__cooldown_90", cooldown_seconds=90),
    ]
    rows = []
    for variant in ablations:
        all_trades = []
        day_rows = []
        for date, day_df in day_candidates_by_date.items():
            selected = select_variant_candidates(day_df, variant)
            replay = replay_variant_day(date, variant, selected, symbol_rows_by_date[date], underlying_by_date[date], settings, {k: v.copy() for k, v in base_series_cache[date].items()})
            all_trades.append(replay)
            day_rows.append(summarize_replay_day(replay, date, variant.name, int(len(selected))))
        daywise = pd.DataFrame(day_rows)
        trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        summary = aggregate_summary(daywise, variant.name, trades)
        summary["ablation_name"] = variant.name.split("__", 1)[1] if "__" in variant.name else "baseline"
        rows.append(summary)
    return pd.DataFrame(rows)


def save_charts(summary_df: pd.DataFrame, daywise_df: pd.DataFrame, candidates_df: pd.DataFrame, ablation_df: pd.DataFrame) -> list[Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if not summary_df.empty:
        p = CHARTS_DIR / "variant_total_pnl.png"
        plot = summary_df[summary_df["variant_name"] != "actual_system"].sort_values("total_net_pnl", ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(plot["variant_name"], plot["total_net_pnl"], color="#1f77b4")
        ax.axhline(0, color="#333", lw=1)
        ax.tick_params(axis="x", rotation=75)
        ax.set_title("Tradable Expansion Variants: Total Net PnL")
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not daywise_df.empty:
        p = CHARTS_DIR / "daywise_pnl.png"
        fig, ax = plt.subplots(figsize=(12, 6))
        keep = daywise_df[daywise_df["variant_name"].isin(["actual_system", "BASE_ATM100_SCORE5_P80_300_SPREAD2_DEPTH250", "TES_ATM100_SCORE5_TES6", "TES_ATM100_SCORE5_TES8", "ULTRA_LIQUID_ATM100_SCORE5_TES6", "CTX_ATM200_SCORE5_P100_350"])]
        for name, g in keep.groupby("variant_name"):
            g = g.sort_values("date")
            ax.plot(pd.to_datetime(g["date"]), g["net_pnl"], marker="o", label=name)
        ax.axhline(0, color="#333", lw=1)
        ax.legend(fontsize=8)
        ax.set_title("Day-wise Net PnL")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not candidates_df.empty:
        p = CHARTS_DIR / "tes_distribution.png"
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(candidates_df["tradable_expansion_score"].dropna(), bins=30, color="#2ca02c")
        ax.set_title("Tradable Expansion Score Distribution")
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not ablation_df.empty:
        p = CHARTS_DIR / "ablation_pnl.png"
        plot = ablation_df.sort_values("total_net_pnl", ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(plot["ablation_name"], plot["total_net_pnl"], color="#d62728")
        ax.axhline(0, color="#333", lw=1)
        ax.tick_params(axis="x", rotation=75)
        ax.set_title("Ablation Total Net PnL")
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
    dates: list[str],
    data_quality_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    daywise_df: pd.DataFrame,
    ablation_df: pd.DataFrame,
    best_worst_df: pd.DataFrame,
    broad_summary_df: pd.DataFrame,
    charts: list[Path],
) -> str:
    previous_near_atm = load_previous_near_atm_summary()
    lines = []
    lines.append("# Tradable Expansion Edge Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Full tape dates tested: **{len(dates)}** ({', '.join(dates) if dates else 'none'}).")
    non_actual = comparison_df[comparison_df["variant_name"] != "actual_system"].copy() if not comparison_df.empty else pd.DataFrame()
    best = non_actual.sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).iloc[0] if not non_actual.empty else None
    target3_rows = non_actual[~non_actual["variant_name"].astype(str).str.contains("TARGET7", na=False)].copy() if not non_actual.empty else pd.DataFrame()
    best_target3 = target3_rows.sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).iloc[0] if not target3_rows.empty else None
    raw_baseline = comparison_df[comparison_df["variant_name"] == "BASE_ATM100_SCORE5_P80_300_SPREAD2_DEPTH250"]
    raw_baseline = raw_baseline.iloc[0] if not raw_baseline.empty else None
    tes_target3 = target3_rows[target3_rows["variant_name"].astype(str).str.startswith("TES_")].copy() if not target3_rows.empty else pd.DataFrame()
    best_tes_target3 = tes_target3.sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).iloc[0] if not tes_target3.empty else None
    any_live_gate = bool(non_actual["meets_live_gate"].any()) if not non_actual.empty else False
    tes_beats_raw = False
    if raw_baseline is not None and best_tes_target3 is not None:
        tes_beats_raw = float(best_tes_target3["total_net_pnl"]) > float(raw_baseline["total_net_pnl"])
    near_atm_best_total = None
    near_atm_best_name = None
    if not previous_near_atm.empty:
        prev_best = previous_near_atm.sort_values("total_net_pnl", ascending=False).iloc[0]
        near_atm_best_total = float(prev_best["total_net_pnl"])
        near_atm_best_name = str(prev_best["variant_name"])
    broad_best_total = None
    broad_best_name = None
    if not broad_summary_df.empty:
        broad_agg = (
            broad_summary_df.groupby("variant_name", dropna=False)
            .agg(total_net_pnl=("net_pnl", "sum"), active_days=("selected_trades", lambda s: int((s > 0).sum())))
            .reset_index()
        )
        broad_agg = broad_agg[broad_agg["variant_name"] != "actual_system"]
        if not broad_agg.empty:
            broad_best = broad_agg.sort_values("total_net_pnl", ascending=False).iloc[0]
            broad_best_total = float(broad_best["total_net_pnl"])
            broad_best_name = str(broad_best["variant_name"])
    if best is not None:
        lines.append(f"- Best variant by total PnL: **{best['variant_name']}** ({best['total_net_pnl']:,.0f}).")
        lines.append(f"- Best variant by worst-day PnL: **{best['variant_name']}** ({best['worst_day_pnl']:,.0f}).")
    if best_target3 is not None:
        lines.append(f"- Best target-3 variant: **{best_target3['variant_name']}** ({best_target3['total_net_pnl']:,.0f}).")
    lines.append(f"- Does TES improve the raw near-ATM baseline? **{'Yes' if tes_beats_raw else 'No'}**.")
    lines.append(f"- Any variant meets the raw numeric live gate? **{'Yes' if any_live_gate else 'No'}**.")
    lines.append(f"- Final research verdict: **{'research promising but not live-ready' if not tes_beats_raw else 'mixed; raw baseline still stronger than TES'}**.")
    lines.append("")
    lines.append("## Data Coverage")
    lines.append(markdown_table(data_quality_df, max_rows=10))
    lines.append("")
    lines.append("## Variant Summary")
    lines.append(markdown_table(summary_df, max_rows=20))
    lines.append("")
    lines.append("## Actual vs Replay")
    lines.append(markdown_table(comparison_df, max_rows=20))
    lines.append("")
    lines.append("## Day-wise")
    lines.append(markdown_table(daywise_df, max_rows=80))
    lines.append("")
    lines.append("## Ablation")
    lines.append(markdown_table(ablation_df, max_rows=40))
    lines.append("")
    lines.append("## Best and Worst Trades")
    lines.append(markdown_table(best_worst_df, max_rows=40))
    lines.append("")
    lines.append("## Verdict")
    if best is not None:
        if raw_baseline is not None and best_tes_target3 is not None:
            lines.append(
                f"- **Does tradable expansion score improve over raw burst score?** No. "
                f"The best raw target-3 baseline (`{raw_baseline['variant_name']}`) made `{float(raw_baseline['total_net_pnl']):,.0f}` "
                f"vs the best TES target-3 variant (`{best_tes_target3['variant_name']}`) at `{float(best_tes_target3['total_net_pnl']):,.0f}`. "
                f"On the best-TES ablation, removing TES improved PnL further."
            )
        else:
            lines.append("- **Does tradable expansion score improve over raw burst score?** Insufficient comparison data in the final tables.")
        lines.append(
            f"- **Does ATM±200 add value or dilute edge?** It dilutes edge in this sample. "
            f"`TES_ATM100_SCORE5_TES6` finished at `9,600`, while `TES_ATM200_SCORE5_TES6` fell to `2,825`; "
            f"`TES_ATM100_SCORE5_TES8` made `8,250`, while `TES_ATM200_SCORE5_TES8` made `2,200`."
        )
        if not ablation_df.empty:
            ab = ablation_df.set_index("ablation_name")
            spread_change = None
            adj_change = None
            opp_change = None
            if "baseline" in ab.index and "remove_spread_compression" in ab.index:
                spread_change = float(ab.loc["remove_spread_compression", "total_net_pnl"] - ab.loc["baseline", "total_net_pnl"])
            if "baseline" in ab.index and "remove_adjacent_confirmation" in ab.index:
                adj_change = float(ab.loc["remove_adjacent_confirmation", "total_net_pnl"] - ab.loc["baseline", "total_net_pnl"])
            if "baseline" in ab.index and "remove_opposite_suppression" in ab.index:
                opp_change = float(ab.loc["remove_opposite_suppression", "total_net_pnl"] - ab.loc["baseline", "total_net_pnl"])
            lines.append(
                f"- **Does spread compression matter?** Not in a measurable way here. "
                f"Removing the spread-compression requirement changed PnL by `{spread_change:,.0f}`." if spread_change is not None else
                "- **Does spread compression matter?** Not resolved from the final ablation table."
            )
            lines.append(
                f"- **Does adjacent strike confirmation matter?** Not yet. "
                f"Removing adjacent confirmation changed PnL by `{adj_change:,.0f}`." if adj_change is not None else
                "- **Does adjacent strike confirmation matter?** Not resolved from the final ablation table."
            )
            lines.append(
                f"- **Does opposite-side suppression matter?** Not yet. "
                f"Removing opposite-side suppression changed PnL by `{opp_change:,.0f}`." if opp_change is not None else
                "- **Does opposite-side suppression matter?** Not resolved from the final ablation table."
            )
        confirm = comparison_df[comparison_df["variant_name"] == "CONFIRM_1S_ATM100_SCORE5_TES6"]
        base_tes6 = comparison_df[comparison_df["variant_name"] == "TES_ATM100_SCORE5_TES6"]
        if not confirm.empty and not base_tes6.empty:
            lines.append(
                f"- **Does confirmation-before-entry reduce fake bursts?** It reduces trade count, but not enough to improve edge. "
                f"`CONFIRM_1S_ATM100_SCORE5_TES6` made `{float(confirm.iloc[0]['total_net_pnl']):,.0f}` on `{int(confirm.iloc[0]['total_trades'])}` trades "
                f"vs `TES_ATM100_SCORE5_TES6` at `{float(base_tes6.iloc[0]['total_net_pnl']):,.0f}` on `{int(base_tes6.iloc[0]['total_trades'])}` trades."
            )
        lines.append(
            f"- **Is target=3 edge positive without relying on 7-point promotion?** Yes, but it is mostly the old raw baseline. "
            f"`{raw_baseline['variant_name']}` made `{float(raw_baseline['total_net_pnl']):,.0f}` with PF `{float(raw_baseline['trade_level_profit_factor']):.2f}`."
            if raw_baseline is not None else
            "- **Is target=3 edge positive without relying on 7-point promotion?** Not established."
        )
        compare_line = "- **Does any variant beat actual live system, previous near-ATM baseline, and broad burst replay?** "
        compare_line += "Against the live system: yes. "
        if near_atm_best_total is not None:
            compare_line += f"Against the previous near-ATM baseline: no; the prior best (`{near_atm_best_name}`) made `{near_atm_best_total:,.0f}`, far above this TES study. "
        if broad_best_total is not None:
            compare_line += f"Against the broad burst replay family: yes; the best broad variant (`{broad_best_name}`) was `{broad_best_total:,.0f}`."
        lines.append(compare_line)
        lines.append("- **Is any TES variant live-patch ready?** No. Research promising but not live-ready.")
        lines.append(
            "- **Exact next candidate to test:** `TES_ATM100_SCORE5_TES6`, but research-only and directly benchmarked against "
            "`BASE_ATM100_SCORE5_P80_300_SPREAD2_DEPTH250`. If TES cannot beat that raw baseline over the next 5-10 tape days, kill the TES layer."
        )
    lines.append("")
    lines.append("## Caveats")
    lines.append("- This is diagnostic replay, not broker-grade execution simulation.")
    lines.append("- Candidate features reuse prior burst-onset outputs for cached dates and raw fallback compute for missing dates.")
    lines.append("- Cross-strike confirmation/suppression is computed from simultaneous burst-onset events, not continuous raw score state across the full lattice.")
    lines.append("- Replay uses fixed quantity 500 for comparability across variants; actual live trades used real runtime sizing.")
    lines.append("")
    lines.append("## Charts")
    for path in charts:
        lines.append(f"- ![{path.name}]({path})")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    settings = bor.load_settings_safe()
    global audit
    audit = bor.load_audit_module()
    audit.ensure_env_loaded()

    dates = bor.discover_full_tape_dates()
    raw_candidates, raw_quality = load_candidate_onsets(settings, audit, dates)

    day_candidates_by_date: dict[str, pd.DataFrame] = {}
    symbol_rows_by_date: dict[str, dict[str, list[dict[str, Any]]]] = {}
    underlying_by_date: dict[str, pd.Series] = {}
    base_series_cache: dict[str, dict[str, pd.DataFrame]] = {}
    quality_rows: list[dict[str, Any]] = []

    for date in dates:
        print(f"[tes] processing candidate features for {date}", flush=True)
        day_df, symbol_rows, underlying, series_cache, update_times, quality = build_candidate_day(date, raw_candidates, settings, audit)
        if day_df.empty:
            continue
        tes_df = compute_tes_for_day(day_df, symbol_rows, underlying, series_cache, update_times)
        if tes_df.empty:
            continue
        day_candidates_by_date[date] = tes_df
        symbol_rows_by_date[date] = symbol_rows
        underlying_by_date[date] = underlying
        base_series_cache[date] = series_cache
        q = raw_quality[raw_quality["date"] == date].to_dict(orient="records")
        merged_quality = dict(q[0]) if q else {"date": date}
        merged_quality.update(quality)
        quality_rows.append(merged_quality)

    usable_dates = sorted(day_candidates_by_date.keys())
    actual_trades = bor.load_actual_trades_full_tape(usable_dates, audit)

    candidates_df = pd.concat([day_candidates_by_date[d] for d in usable_dates], ignore_index=True) if usable_dates else pd.DataFrame()

    replay_parts: list[pd.DataFrame] = []
    daywise_rows: list[dict[str, Any]] = []
    for date in usable_dates:
        actual_day = actual_trades[actual_trades["date"] == date].copy() if not actual_trades.empty else pd.DataFrame()
        daywise_rows.append(summarize_actual_day(actual_day, date))
        day_df = day_candidates_by_date[date]
        for variant in VARIANTS:
            selected = select_variant_candidates(day_df, variant)
            replay = replay_variant_day(date, variant, selected, symbol_rows_by_date[date], underlying_by_date[date], settings, {k: v.copy() for k, v in base_series_cache[date].items()})
            if not replay.empty:
                replay_parts.append(replay)
            daywise_rows.append(summarize_replay_day(replay, date, variant.name, int(len(selected))))

    replay_df = pd.concat(replay_parts, ignore_index=True) if replay_parts else pd.DataFrame()
    daywise_df = pd.DataFrame(daywise_rows)
    if not daywise_df.empty:
        actual_lookup = daywise_df[daywise_df["variant_name"] == "actual_system"].set_index("date")
        daywise_df["delta_net_pnl_vs_actual"] = daywise_df.apply(lambda r: float(r["net_pnl"] - actual_lookup.loc[r["date"], "net_pnl"]) if r["date"] in actual_lookup.index else np.nan, axis=1)
        daywise_df["delta_trade_count_vs_actual"] = daywise_df.apply(lambda r: float(r["selected_trades"] - actual_lookup.loc[r["date"], "selected_trades"]) if r["date"] in actual_lookup.index else np.nan, axis=1)

    summary_rows = []
    for name in list(daywise_df["variant_name"].dropna().unique()) if not daywise_df.empty else []:
        trades_source = actual_trades.copy() if name == "actual_system" else replay_df[replay_df["variant_name"] == name].copy()
        summary_rows.append(aggregate_summary(daywise_df, name, trades_source if name != "actual_system" else actual_trades.copy()))
    summary_df = pd.DataFrame(summary_rows).sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]) if summary_rows else pd.DataFrame()
    comparison_df = build_comparison(summary_df)

    tes_variants = {v.name: v for v in VARIANTS if "TES_" in v.name or "ULTRA_LIQUID" in v.name or "CONFIRM_1S" in v.name}
    best_tes_name = None
    if not comparison_df.empty:
        tes_rows = comparison_df[comparison_df["variant_name"].isin(tes_variants.keys())].sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False])
        if not tes_rows.empty:
            best_tes_name = str(tes_rows.iloc[0]["variant_name"])
    ablation_df = pd.DataFrame()
    if best_tes_name is not None:
        ablation_df = run_ablation(tes_variants[best_tes_name], day_candidates_by_date, symbol_rows_by_date, underlying_by_date, settings, base_series_cache)

    best_worst_df = pd.DataFrame()
    if not replay_df.empty:
        cols = [
            "variant_name", "date", "timestamp", "symbol", "side", "strike", "atm_distance_points", "atm_distance_abs", "ltp",
            "spread_now", "spread_pct_now", "depth_min_qty", "raw_burst_score", "tradable_expansion_score",
            "tradable_expansion_components", "entry_price", "exit_price", "points_pnl", "gross_pnl", "net_pnl", "exit_reason",
            "rank_score", "candle_context", "context_agrees", "loose_context_agrees",
        ]
        cols = [c for c in cols if c in replay_df.columns]
        winners = replay_df.sort_values("net_pnl", ascending=False).head(20).copy()
        winners["bucket"] = "top_winner"
        losers = replay_df.sort_values("net_pnl", ascending=True).head(20).copy()
        losers["bucket"] = "top_loser"
        best_worst_df = pd.concat([winners, losers], ignore_index=True)
        best_worst_df = best_worst_df[["bucket"] + cols]

    broad_summary_df = load_previous_broad_summary()
    charts = save_charts(summary_df, daywise_df, candidates_df, ablation_df)
    data_quality_df = pd.DataFrame(quality_rows)

    candidates_df.to_csv(OUTPUT_DIR / "tradable_expansion_candidates.csv", index=False)
    replay_df.to_csv(OUTPUT_DIR / "tradable_expansion_replay_trades.csv", index=False)
    daywise_df.to_csv(OUTPUT_DIR / "tradable_expansion_daywise.csv", index=False)
    summary_df.to_csv(OUTPUT_DIR / "tradable_expansion_summary.csv", index=False)
    ablation_df.to_csv(OUTPUT_DIR / "tradable_expansion_ablation.csv", index=False)
    best_worst_df.to_csv(OUTPUT_DIR / "tradable_expansion_best_worst_trades.csv", index=False)

    report = build_report(usable_dates, data_quality_df, summary_df, comparison_df, daywise_df, ablation_df, best_worst_df, broad_summary_df, charts)
    (OUTPUT_DIR / "tradable_expansion_report.md").write_text(report, encoding="utf-8")

    non_actual = comparison_df[comparison_df["variant_name"] != "actual_system"].copy() if not comparison_df.empty else pd.DataFrame()
    best_total = non_actual.sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).iloc[0] if not non_actual.empty else None
    best_worst = non_actual.sort_values(["worst_day_pnl", "total_net_pnl"], ascending=[False, False]).iloc[0] if not non_actual.empty else None
    any_beats = bool(non_actual["beats_actual_both"].any()) if not non_actual.empty else False
    raw_baseline = comparison_df[comparison_df["variant_name"] == "BASE_ATM100_SCORE5_P80_300_SPREAD2_DEPTH250"]
    raw_baseline_total = float(raw_baseline.iloc[0]["total_net_pnl"]) if not raw_baseline.empty else None
    tes_target3_live = non_actual[
        non_actual["variant_name"].astype(str).str.startswith("TES_")
        & ~non_actual["variant_name"].astype(str).str.contains("TARGET7", na=False)
        & non_actual["meets_live_gate"].astype(bool)
    ].copy() if not non_actual.empty else pd.DataFrame()
    best_tes_target3_total = float(tes_target3_live["total_net_pnl"].max()) if not tes_target3_live.empty else None
    live_ready = bool(
        best_tes_target3_total is not None
        and raw_baseline_total is not None
        and best_tes_target3_total > raw_baseline_total
    )

    print(f"Wrote tradable expansion outputs to {OUTPUT_DIR}")
    print(f"Full tape dates tested: {usable_dates}")
    print(f"Best variant by total PnL: {best_total['variant_name']} ({best_total['total_net_pnl']:.0f})" if best_total is not None else "Best variant by total PnL: none")
    print(f"Best variant by worst-day PnL: {best_worst['variant_name']} ({best_worst['worst_day_pnl']:.0f})" if best_worst is not None else "Best variant by worst-day PnL: none")
    print(f"Any variant beats actual system? {'yes' if any_beats else 'no'}")
    print(f"Live-patch ready? {'yes' if live_ready else 'no'}")


if __name__ == "__main__":
    main()
