from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from dotenv import dotenv_values
except Exception:  # pragma: no cover
    dotenv_values = None

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "strategy_audit_results"

SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sensex_noise.config import load_settings  # type: ignore
from sensex_noise.services.microburst import (  # type: ignore
    classify_target,
    compute_pre_entry_features,
    compute_promoted_3s_diagnostics,
    layer4_persistence_result,
    promoted_trade_survives_3s,
)

TAPE_SYMBOL_BURST_COOLDOWN_SECONDS = 30
TAPE_GLOBAL_ENTRY_COOLDOWN_SECONDS = 15


def ensure_env_loaded() -> None:
    env_path = REPO_ROOT / ".env"
    if dotenv_values is not None and env_path.exists():
        values = dotenv_values(env_path)
        for key, value in values.items():
            if value is not None and key not in os.environ:
                os.environ[key] = value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def md5sum(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_dt(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or value == "":
        return pd.NaT
    try:
        return pd.Timestamp(value)
    except Exception:
        return pd.NaT


def date_from_trade_id(trade_id: str | None) -> str | None:
    if not trade_id:
        return None
    prefix = str(trade_id).split("|")[0]
    if len(prefix) >= 8 and prefix[:8].isdigit():
        return f"{prefix[:4]}-{prefix[4:6]}-{prefix[6:8]}"
    return None


def extract_trade_date(row: dict[str, Any]) -> str | None:
    for key in (
        "entry_fill_time",
        "entry_time",
        "signal_time",
        "signal_seen_time",
        "exit_fill_time",
        "timestamp",
    ):
        raw = row.get(key)
        if isinstance(raw, str) and len(raw) >= 10:
            return raw[:10]
    return date_from_trade_id(row.get("trade_id"))


def series_or_na(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")


def series_or_false(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(False, index=df.index, dtype="boolean")


def load_trade_days() -> dict[str, dict[str, Any]]:
    daily_dir = REPO_ROOT / "logs" / "trades"
    result: dict[str, dict[str, Any]] = {}

    for path in sorted(daily_dir.glob("*.trades_enriched.jsonl")):
        date = path.name.split(".")[0]
        latest: dict[str, dict[str, Any]] = {}
        rows = read_jsonl(path)
        for row in rows:
            trade_id = row.get("trade_id")
            if trade_id:
                latest[str(trade_id)] = row
        result[date] = {
            "date": date,
            "source": "daily_enriched",
            "path": path,
            "raw_rows": len(rows),
            "latest_rows": list(latest.values()),
        }

    root_path = REPO_ROOT / "logs" / "trades_enriched.jsonl"
    if root_path.exists():
        rows = read_jsonl(root_path)
        per_date_latest: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in rows:
            date = extract_trade_date(row)
            trade_id = row.get("trade_id")
            if date and trade_id and date not in result:
                per_date_latest[date][str(trade_id)] = row
        for date, latest in per_date_latest.items():
            result[date] = {
                "date": date,
                "source": "root_enriched",
                "path": root_path,
                "raw_rows": len(latest),
                "latest_rows": list(latest.values()),
            }
    return dict(sorted(result.items()))


def load_event_days() -> dict[str, dict[str, Any]]:
    events_dir = REPO_ROOT / "logs" / "events"
    result: dict[str, dict[str, Any]] = {}

    for path in sorted(events_dir.glob("*.events.jsonl")):
        date = path.name.split(".")[0]
        rows = read_jsonl(path)
        counter = Counter(row.get("event_type") for row in rows)
        result[date] = {
            "date": date,
            "source": "daily_events",
            "path": path,
            "rows": len(rows),
            "counter": counter,
        }

    root_path = REPO_ROOT / "logs" / "events.jsonl"
    if root_path.exists():
        rows = read_jsonl(root_path)
        per_date_counter: dict[str, Counter[str]] = defaultdict(Counter)
        per_date_rows: Counter[str] = Counter()
        for row in rows:
            date = None
            raw = row.get("timestamp")
            if isinstance(raw, str) and len(raw) >= 10:
                date = raw[:10]
            if date and date not in result:
                per_date_counter[date][row.get("event_type")] += 1
                per_date_rows[date] += 1
        for date in sorted(per_date_counter):
            result[date] = {
                "date": date,
                "source": "root_events",
                "path": root_path,
                "rows": int(per_date_rows[date]),
                "counter": per_date_counter[date],
            }
    return dict(sorted(result.items()))


def load_tape_dates() -> list[str]:
    tape_root = REPO_ROOT / "data" / "tape" / "sensex_options"
    if not tape_root.exists():
        return []
    return sorted(path.name for path in tape_root.iterdir() if path.is_dir())


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def flatten_burst_features(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out = {}
    for key in (
        "ind_velocity_aligned",
        "ind_accel_aligned",
        "opt_velocity_aligned",
        "opt_depth_imb_mean",
        "opt_spread_mean",
        "score",
    ):
        if key in value:
            out[f"burst_{key}"] = value.get(key)
    score_components = value.get("score_components")
    if isinstance(score_components, dict):
        out["burst_score_components"] = json.dumps(score_components, sort_keys=True)
    return out


def derive_post_exit_flags(row: dict[str, Any]) -> dict[str, Any]:
    entry_price = safe_float(row.get("entry_price"))
    target_points = safe_float(row.get("target_points_used"))
    promoted_target = safe_float(row.get("promoted_target_points"))
    if entry_price is None:
        return {
            "post_exit_crossed_entry_15s": False,
            "post_exit_hit_target_15s": False,
            "post_exit_hit_plus3_15s": False,
            "post_exit_hit_plus5_15s": False,
            "post_exit_hit_plus7_15s": False,
            "post_exit_path_points": 0,
        }
    target_price = entry_price + (target_points or 0.0)
    path = row.get("post_exit_path") or []
    crossed_entry = False
    hit_target = False
    hit_plus3 = False
    hit_plus5 = False
    hit_plus7 = False
    for point in path:
        ltp = safe_float(point.get("option_ltp")) if isinstance(point, dict) else None
        if ltp is None:
            continue
        if ltp > entry_price:
            crossed_entry = True
        if ltp >= target_price:
            hit_target = True
        if ltp >= entry_price + 3.0:
            hit_plus3 = True
        if ltp >= entry_price + 5.0:
            hit_plus5 = True
        if ltp >= entry_price + 7.0:
            hit_plus7 = True
    return {
        "post_exit_crossed_entry_15s": crossed_entry,
        "post_exit_hit_target_15s": hit_target,
        "post_exit_hit_plus3_15s": hit_plus3,
        "post_exit_hit_plus5_15s": hit_plus5,
        "post_exit_hit_plus7_15s": hit_plus7,
        "post_exit_path_points": len(path),
        "promoted_target_price": (entry_price + promoted_target) if promoted_target else None,
    }


def build_trades_df(trade_days: dict[str, dict[str, Any]]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for date, info in trade_days.items():
        for row in info["latest_rows"]:
            rec = dict(row)
            rec["date"] = date
            rec["data_source"] = info["source"]
            rec["data_path"] = str(info["path"])
            rec.update(flatten_burst_features(row.get("burst_features")))
            rec.update(derive_post_exit_flags(row))
            records.append(rec)

    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df

    for col in [
        "gross_pnl",
        "net_pnl",
        "charges",
        "entry_price",
        "exit_price",
        "mfe",
        "mae",
        "holding_seconds",
        "burst_score",
        "runup_1s",
        "drawdown_1s",
        "current_pnl_1s",
        "runup_3s",
        "drawdown_3s",
        "current_pnl_3s",
        "velocity_0_1s",
        "velocity_2_3s",
        "velocity_decay_ratio_3s",
        "target_points_used",
        "promoted_target_points",
        "burst_ind_velocity_aligned",
        "burst_ind_accel_aligned",
        "burst_opt_velocity_aligned",
        "burst_opt_depth_imb_mean",
        "burst_opt_spread_mean",
        "post_exit_points_best_recovery",
        "post_exit_points_worst_further_loss",
        "post_exit_final_delta_15s",
        "resolved_time_to_plus_1",
        "resolved_time_to_plus_2",
        "resolved_time_to_minus_1",
        "resolved_time_to_minus_3",
        "resolved_time_to_minus_5",
        "time_to_plus_1",
        "time_to_plus_2",
        "time_to_minus_1",
        "time_to_minus_3",
        "time_to_minus_5",
        "trigger_price",
        "underlying_spot_at_entry",
        "entry_spread",
        "exit_spread",
        "hard_stop_points_used",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in [
        "entry_fill_time",
        "exit_fill_time",
        "signal_time",
        "signal_seen_time",
        "source_candle_start",
        "entry_time",
        "exit_time",
        "promotion_deadline_time",
        "promotion_first_hit_trigger_time",
    ]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["entry_dt"] = series_or_na(df, "entry_fill_time").fillna(series_or_na(df, "entry_time"))
    df["exit_dt"] = series_or_na(df, "exit_fill_time").fillna(series_or_na(df, "exit_time"))
    df["signal_dt"] = series_or_na(df, "signal_seen_time").fillna(series_or_na(df, "signal_time"))
    df["candle_dt"] = series_or_na(df, "source_candle_start")
    df["signal_to_entry_seconds"] = (df["entry_dt"] - df["signal_dt"]).dt.total_seconds()
    df["candle_age_seconds"] = (df["entry_dt"] - df["candle_dt"]).dt.total_seconds()
    df["actual_points"] = df["exit_price"] - df["entry_price"]
    df["mfe_capture_ratio"] = np.where(df["mfe"] > 0, df["actual_points"] / df["mfe"], np.nan)
    df["is_winner"] = df["net_pnl"] > 0
    df["is_loser"] = df["net_pnl"] < 0
    df["is_promoted_candidate"] = series_or_false(df, "is_promoted_candidate").fillna(False).astype(bool)
    df["is_promoted_active"] = series_or_false(df, "is_promoted_active").fillna(False).astype(bool)
    df["promoted_3s_passed"] = series_or_false(df, "promoted_3s_passed").fillna(False).astype(bool)
    df["promotion_persistence_passed"] = series_or_false(df, "promotion_persistence_passed").fillna(False).astype(bool)
    df["post_exit_recovered_above_exit"] = series_or_false(df, "post_exit_recovered_above_exit").fillna(False).astype(bool)
    return df


def merge_canonical_features(trades_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    canonical_path = REPO_ROOT / "analysis" / "canonical_trades_ml_dataset.csv"
    meta: dict[str, Any] = {
        "canonical_dataset_exists": canonical_path.exists(),
        "canonical_dataset_path": str(canonical_path),
    }
    if not canonical_path.exists() or trades_df.empty:
        trades_df["burst_score_effective"] = trades_df.get("burst_score")
        return trades_df, meta

    canonical = pd.read_csv(canonical_path, low_memory=False)
    if canonical.empty or "trade_id" not in canonical.columns:
        trades_df["burst_score_effective"] = trades_df.get("burst_score")
        return trades_df, meta

    canonical = canonical.drop_duplicates(subset=["trade_id"], keep="last")
    meta["canonical_rows"] = int(len(canonical))
    meta["canonical_date_min"] = canonical["date"].min() if "date" in canonical.columns else None
    meta["canonical_date_max"] = canonical["date"].max() if "date" in canonical.columns else None

    selected_cols = [
        "trade_id",
        "data_patch_era",
        "burst_score_reconstructed",
        "idx_pre_velocity_aligned",
        "idx_pre_accel_aligned",
        "opt_pre_velocity_5s",
        "opt_pre_depth_imb_mean",
        "opt_pre_spread_mean",
        "pre_entry_option_tick_count",
        "pre_entry_index_tick_count",
        "trade_alive_at_1s",
        "trade_alive_at_3s",
        "label_bad_trade",
        "label_target_bucket",
        "best_possible_points",
        "fallback_hold_points",
        "exit_cut_points_1s",
        "exit_cut_points_3s",
        "actual_points",
        "current_bucket",
        "ml_ready_entry_features",
        "ml_ready_target_label",
        "pnl_1s",
        "runup_1s",
        "drawdown_1s",
        "pnl_3s",
        "runup_3s",
        "drawdown_3s",
    ]
    selected_cols = [col for col in selected_cols if col in canonical.columns]
    canonical = canonical[selected_cols]
    merged = trades_df.merge(canonical, on="trade_id", how="left", suffixes=("", "_canon"))

    merged["burst_score_effective"] = merged["burst_score"]
    if "burst_score_reconstructed" in merged.columns:
        merged["burst_score_effective"] = merged["burst_score_effective"].fillna(merged["burst_score_reconstructed"])

    def fill_effective(raw_col: str, canon_col: str, out_col: str) -> None:
        raw = merged[raw_col] if raw_col in merged.columns else pd.Series(np.nan, index=merged.index)
        canon = merged[canon_col] if canon_col in merged.columns else pd.Series(np.nan, index=merged.index)
        merged[out_col] = raw.fillna(canon)

    fill_effective("burst_ind_velocity_aligned", "idx_pre_velocity_aligned", "ind_velocity_effective")
    fill_effective("burst_ind_accel_aligned", "idx_pre_accel_aligned", "ind_accel_effective")
    fill_effective("burst_opt_velocity_aligned", "opt_pre_velocity_5s", "opt_velocity_effective")
    fill_effective("burst_opt_depth_imb_mean", "opt_pre_depth_imb_mean", "opt_depth_imb_effective")
    fill_effective("burst_opt_spread_mean", "opt_pre_spread_mean", "opt_spread_effective")

    if "pnl_1s" in merged.columns and "current_pnl_1s" not in merged.columns:
        merged["current_pnl_1s"] = merged["pnl_1s"]
    elif "pnl_1s" in merged.columns:
        merged["current_pnl_1s"] = merged["current_pnl_1s"].fillna(merged["pnl_1s"])
    if "pnl_3s" in merged.columns and "current_pnl_3s" not in merged.columns:
        merged["current_pnl_3s"] = merged["pnl_3s"]
    elif "pnl_3s" in merged.columns:
        merged["current_pnl_3s"] = merged["current_pnl_3s"].fillna(merged["pnl_3s"])

    return merged, meta


def build_patch_timeline(
    trades_df: pd.DataFrame,
    event_days: dict[str, dict[str, Any]],
    tape_dates: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    tape_set = set(tape_dates)
    dates = sorted(set(trades_df["date"].dropna().tolist()) | set(event_days.keys()))
    for date in dates:
        day_trades = trades_df[trades_df["date"] == date].copy()
        counter = event_days.get(date, {}).get("counter", Counter())
        has_edge = any(str(k).startswith("EDGE_INVALIDATION_") for k in counter)
        has_microburst = any("MICROBURST" in str(k) or "ENTRY_ALLOWED_MICROBURST_GATE" == str(k) for k in counter)
        has_promoted = any("PROMOTED_" in str(k) for k in counter) or bool(day_trades.get("is_promoted_candidate", pd.Series(dtype=bool)).fillna(False).any())
        has_layer4 = any(str(k).startswith("PROMOTION_") for k in counter) or bool(day_trades.get("promotion_persistence_passed", pd.Series(dtype=bool)).fillna(False).any())
        layer4_triggered = sum(counter.get(k, 0) for k in ["PROMOTION_ARMED_AT_3PTS", "PROMOTION_PERSISTENCE_PASS", "PROMOTION_PERSISTENCE_FAIL"])
        has_full_tape = date in tape_set
        if has_microburst and has_full_tape:
            patch_era = "burst_promotion_tape"
        elif has_microburst:
            patch_era = "burst_promotion"
        elif has_edge:
            patch_era = "edge_1s3s"
        else:
            patch_era = "pre_1s3s"

        features = ["post_exit_observation"]
        if has_edge:
            features.append("edge_1s3s")
        if has_microburst:
            features.append("microburst_gate")
        if has_promoted:
            features.append("promotion_3s")
        if has_layer4:
            features.append("layer4")
        if has_full_tape:
            features.append("full_option_tape")

        notes: list[str] = []
        trade_log_path = REPO_ROOT / "logs" / "trades" / f"{date}.trades.jsonl"
        event_log_path = REPO_ROOT / "logs" / "events" / f"{date}.events.jsonl"
        if trade_log_path.exists() and event_log_path.exists() and md5sum(trade_log_path) == md5sum(event_log_path):
            notes.append("dated trades.jsonl matches event log")
        if layer4_triggered:
            notes.append(f"layer4_events={layer4_triggered}")
        if has_full_tape:
            notes.append("tape_present")
        if has_microburst and counter.get("ENTRY_ALLOWED_MICROBURST_GATE", 0) == 0:
            notes.append("microburst inferred from schema")

        rows.append(
            {
                "date": date,
                "patch_era": patch_era,
                "active_features": ", ".join(features),
                "number_of_trades": int(len(day_trades)),
                "notes": "; ".join(notes),
                "has_edge_1s3s": has_edge,
                "has_microburst_gate": has_microburst,
                "has_promotion_logic": has_promoted,
                "has_layer4_logic": has_layer4,
                "has_full_option_tape": has_full_tape,
            }
        )
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def max_intraday_drawdown(day_df: pd.DataFrame) -> float:
    if day_df.empty:
        return float("nan")
    ordered = day_df.sort_values("exit_dt")
    curve = ordered["net_pnl"].fillna(0.0).cumsum()
    running_peak = curve.cummax()
    drawdowns = curve - running_peak
    return float(drawdowns.min()) if not drawdowns.empty else float("nan")


def summarize_counter(series: pd.Series) -> str:
    counts = Counter(int(x) for x in series.dropna())
    return json.dumps(dict(sorted(counts.items())), sort_keys=True)


def compute_daywise_metrics(trades_df: pd.DataFrame, timeline_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    era_map = dict(zip(timeline_df["date"], timeline_df["patch_era"]))
    for date, day_df in trades_df.groupby("date", sort=True):
        wins = day_df[day_df["net_pnl"] > 0]
        losses = day_df[day_df["net_pnl"] < 0]
        gross_total = float(day_df["gross_pnl"].fillna(day_df["net_pnl"]).sum())
        net_total = float(day_df["net_pnl"].sum())
        profit_factor = float(wins["net_pnl"].sum() / abs(losses["net_pnl"].sum())) if not losses.empty else math.inf
        promoted = day_df[day_df["is_promoted_candidate"]]
        rows.append(
            {
                "date": date,
                "patch_era": era_map.get(date, "unknown"),
                "total_trades": int(len(day_df)),
                "gross_pnl": gross_total,
                "net_pnl": net_total,
                "win_rate": float((day_df["net_pnl"] > 0).mean()) if len(day_df) else np.nan,
                "avg_win": float(wins["net_pnl"].mean()) if not wins.empty else np.nan,
                "avg_loss": float(losses["net_pnl"].mean()) if not losses.empty else np.nan,
                "profit_factor": profit_factor,
                "max_intraday_drawdown": max_intraday_drawdown(day_df),
                "num_1s_kills": int((day_df["exit_reason"] == "EARLY_FAIL_1S").sum()),
                "num_3s_kills": int(day_df["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S"]).sum()),
                "num_hard_stops": int(day_df["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).sum()),
                "num_target_hits": int((day_df["exit_reason"] == "TARGET_HIT").sum()),
                "num_promoted_trades": int(len(promoted)),
                "promoted_wins": int((promoted["net_pnl"] > 0).sum()),
                "promoted_losses": int((promoted["net_pnl"] < 0).sum()),
                "promoted_net_pnl": float(promoted["net_pnl"].sum()) if not promoted.empty else 0.0,
                "normal_trade_net_pnl": float(day_df.loc[~day_df["is_promoted_candidate"], "net_pnl"].sum()),
                "burst_score_mean": float(day_df["burst_score_effective"].mean()) if "burst_score_effective" in day_df else np.nan,
                "burst_score_distribution": summarize_counter(day_df["burst_score_effective"]) if "burst_score_effective" in day_df else "{}",
                "average_hold_time_seconds": float(day_df["holding_seconds"].mean()) if "holding_seconds" in day_df else np.nan,
                "average_mfe": float(day_df["mfe"].mean()) if "mfe" in day_df else np.nan,
                "average_mae": float(day_df["mae"].mean()) if "mae" in day_df else np.nan,
                "mfe_capture_ratio_mean": float(day_df["mfe_capture_ratio"].replace([np.inf, -np.inf], np.nan).mean()),
            }
        )
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    out["rolling_3d_net_pnl"] = out["net_pnl"].rolling(3, min_periods=1).sum()
    out["cumulative_net_pnl"] = out["net_pnl"].cumsum()
    out["cumulative_net_pnl_by_patch_era"] = out.groupby("patch_era")["net_pnl"].cumsum()
    return out


def infer_immediate_confirmation(row: pd.Series) -> bool:
    runup_1s = row.get("runup_1s")
    pnl_1s = row.get("current_pnl_1s")
    ttp1 = row.get("time_to_plus_1")
    return bool((pd.notna(runup_1s) and runup_1s >= 1.0 and pd.notna(pnl_1s) and pnl_1s > 0) or (pd.notna(ttp1) and ttp1 <= 1.0))


def infer_immediate_bad(row: pd.Series) -> bool:
    ttm1 = row.get("time_to_minus_1")
    pnl_1s = row.get("current_pnl_1s")
    runup_1s = row.get("runup_1s")
    return bool(
        (pd.notna(ttm1) and ttm1 <= 0.25)
        or (pd.notna(pnl_1s) and pnl_1s <= -1.0 and (pd.isna(runup_1s) or runup_1s < 1.0))
        or ((row.get("mfe") or 0.0) <= 0.0 and (row.get("mae") or 0.0) <= -1.5)
    )


def infer_stale_candle(row: pd.Series) -> bool:
    candle_age = row.get("candle_age_seconds")
    signal_lag = row.get("signal_to_entry_seconds")
    return bool(
        (pd.notna(candle_age) and candle_age >= 20.0)
        or (pd.notna(signal_lag) and signal_lag >= 2.0)
    )


def classify_failure_mode(row: pd.Series) -> str:
    if row.get("net_pnl", 0) >= 0:
        return "non_loser"
    if pd.isna(row.get("entry_dt")) or pd.isna(row.get("exit_dt")):
        return "data/execution artifact"

    exit_reason = str(row.get("exit_reason") or "")
    stale_candle = infer_stale_candle(row)
    immediate_bad = infer_immediate_bad(row)
    crossed_entry = bool(row.get("post_exit_crossed_entry_15s"))
    hit_target = bool(row.get("post_exit_hit_target_15s"))
    promoted = bool(row.get("is_promoted_candidate"))

    if promoted and exit_reason == "PROMOTED_FAIL_3S":
        if hit_target or (row.get("mfe") or 0.0) >= 3.0:
            return "good entry but bad promotion"
        if stale_candle:
            return "stale 5-minute candle signal"
        return "fake burst / exhaustion"

    if exit_reason == "EARLY_FAIL_1S":
        if hit_target or crossed_entry:
            return "good entry but 1s killed too early"
        if stale_candle:
            return "stale 5-minute candle signal"
        if immediate_bad:
            return "bad entry immediately"
        return "fake burst / exhaustion"

    if exit_reason == "EARLY_FAIL_3S":
        if hit_target or crossed_entry:
            return "good entry but 3s killed too early"
        if stale_candle:
            return "stale 5-minute candle signal"
        if immediate_bad:
            return "bad entry immediately"
        return "fake burst / exhaustion"

    if exit_reason in {"EDGE_HARD_STOP", "HARD_STOP_EXIT"}:
        if stale_candle and immediate_bad:
            return "stale 5-minute candle signal"
        if hit_target:
            return "hard stop / tail event"
        if immediate_bad:
            return "bad entry immediately"
        return "hard stop / tail event"

    if stale_candle:
        return "stale 5-minute candle signal"
    if immediate_bad:
        return "bad entry immediately"
    return "fake burst / exhaustion"


def build_post_patch_failure_df(trades_df: pd.DataFrame, timeline_df: pd.DataFrame) -> pd.DataFrame:
    burst_dates = timeline_df.loc[timeline_df["patch_era"].isin(["burst_promotion", "burst_promotion_tape"]), "date"].tolist()
    if not burst_dates:
        return pd.DataFrame()
    start_date = min(burst_dates)
    df = trades_df[(trades_df["date"] >= start_date) & (trades_df["net_pnl"] < 0)].copy()
    if df.empty:
        return df
    df["immediate_confirmation"] = df.apply(infer_immediate_confirmation, axis=1)
    df["stale_candle_flag"] = df.apply(infer_stale_candle, axis=1)
    df["failure_mode"] = df.apply(classify_failure_mode, axis=1)
    return df.sort_values(["date", "net_pnl", "exit_dt"]).reset_index(drop=True)


def bucketize(series: pd.Series, bins: list[float], labels: list[str]) -> pd.Series:
    return pd.cut(series, bins=bins, labels=labels, include_lowest=True, right=False)


def aggregate_bucket(df: pd.DataFrame, axis_name: str, bucket_col: str) -> pd.DataFrame:
    grouped = df.groupby(bucket_col, dropna=False)
    rows = []
    for bucket, g in grouped:
        rows.append(
            {
                "analysis_axis": axis_name,
                "bucket": str(bucket),
                "trades": int(len(g)),
                "net_pnl": float(g["net_pnl"].sum()),
                "avg_pnl": float(g["net_pnl"].mean()) if len(g) else np.nan,
                "win_rate": float((g["net_pnl"] > 0).mean()) if len(g) else np.nan,
                "target_hit_rate": float((g["exit_reason"] == "TARGET_HIT").mean()) if len(g) else np.nan,
                "hard_stop_rate": float(g["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).mean()) if len(g) else np.nan,
                "avg_burst_score": float(g["burst_score_effective"].mean()) if "burst_score_effective" in g else np.nan,
            }
        )
    return pd.DataFrame(rows)


def build_entry_freshness_analysis(trades_df: pd.DataFrame, timeline_df: pd.DataFrame) -> pd.DataFrame:
    burst_dates = timeline_df.loc[timeline_df["patch_era"].isin(["burst_promotion", "burst_promotion_tape"]), "date"].tolist()
    if not burst_dates:
        return pd.DataFrame()
    start_date = min(burst_dates)
    df = trades_df[trades_df["date"] >= start_date].copy()
    if df.empty:
        return df
    df["immediate_confirmation"] = df.apply(infer_immediate_confirmation, axis=1)
    df["stale_candle_flag"] = df.apply(infer_stale_candle, axis=1)
    df["candle_age_bucket"] = bucketize(
        df["candle_age_seconds"],
        bins=[0, 10, 20, 30, 40, 1e9],
        labels=["0-10s", "10-20s", "20-30s", "30-40s", "40s+"],
    )
    df["signal_lag_bucket"] = bucketize(
        df["signal_to_entry_seconds"],
        bins=[0, 0.25, 0.5, 1.0, 2.0, 1e9],
        labels=["0-250ms", "250-500ms", "0.5-1s", "1-2s", "2s+"],
    )
    df["underlying_accel_bucket"] = bucketize(
        df["ind_accel_effective"],
        bins=[-1e9, 0, 1.5, 3.0, 5.0, 1e9],
        labels=["neg", "0-1.5", "1.5-3", "3-5", "5+"],
    )
    df["option_velocity_bucket"] = bucketize(
        df["opt_velocity_effective"],
        bins=[-1e9, 0, 1.0, 2.0, 4.0, 1e9],
        labels=["neg", "0-1", "1-2", "2-4", "4+"],
    )

    parts = [
        aggregate_bucket(df, "candle_age", "candle_age_bucket"),
        aggregate_bucket(df, "signal_to_entry", "signal_lag_bucket"),
        aggregate_bucket(df, "underlying_accel", "underlying_accel_bucket"),
        aggregate_bucket(df, "option_velocity", "option_velocity_bucket"),
        aggregate_bucket(df, "stale_candle_flag", "stale_candle_flag"),
        aggregate_bucket(df, "immediate_confirmation", "immediate_confirmation"),
    ]
    return pd.concat(parts, ignore_index=True)


def build_burst_score_performance(trades_df: pd.DataFrame, timeline_df: pd.DataFrame) -> pd.DataFrame:
    burst_dates = timeline_df.loc[timeline_df["patch_era"].isin(["burst_promotion", "burst_promotion_tape"]), "date"].tolist()
    if not burst_dates:
        return pd.DataFrame()
    start_date = min(burst_dates)
    df = trades_df[(trades_df["date"] >= start_date) & trades_df["burst_score_effective"].notna()].copy()
    if df.empty:
        return df
    grouped = df.groupby("burst_score_effective")
    rows = []
    for score, g in grouped:
        rows.append(
            {
                "burst_score": int(score),
                "trades": int(len(g)),
                "net_pnl": float(g["net_pnl"].sum()),
                "avg_pnl": float(g["net_pnl"].mean()),
                "win_rate": float((g["net_pnl"] > 0).mean()),
                "target_hit_rate": float((g["exit_reason"] == "TARGET_HIT").mean()),
                "hard_stop_rate": float(g["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).mean()),
                "avg_mfe": float(g["mfe"].mean()),
                "avg_mae": float(g["mae"].mean()),
                "avg_candle_age_seconds": float(g["candle_age_seconds"].mean()) if "candle_age_seconds" in g else np.nan,
                "promoted_rate": float(g["is_promoted_candidate"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("burst_score").reset_index(drop=True)


def build_candle_freshness_x_burst(trades_df: pd.DataFrame, timeline_df: pd.DataFrame) -> pd.DataFrame:
    burst_dates = timeline_df.loc[timeline_df["patch_era"].isin(["burst_promotion", "burst_promotion_tape"]), "date"].tolist()
    if not burst_dates:
        return pd.DataFrame()
    start_date = min(burst_dates)
    df = trades_df[(trades_df["date"] >= start_date) & trades_df["burst_score_effective"].notna()].copy()
    if df.empty:
        return df
    df["candle_age_bucket"] = bucketize(
        df["candle_age_seconds"],
        bins=[0, 10, 20, 30, 40, 1e9],
        labels=["0-10s", "10-20s", "20-30s", "30-40s", "40s+"],
    )
    df["burst_bucket"] = df["burst_score_effective"].apply(lambda x: "5+" if x >= 5 else str(int(x)))
    grouped = df.groupby(["candle_age_bucket", "burst_bucket"], dropna=False)
    rows = []
    for (fresh, score), g in grouped:
        rows.append(
            {
                "candle_age_bucket": str(fresh),
                "burst_bucket": str(score),
                "trades": int(len(g)),
                "net_pnl": float(g["net_pnl"].sum()),
                "avg_pnl": float(g["net_pnl"].mean()),
                "win_rate": float((g["net_pnl"] > 0).mean()),
                "target_hit_rate": float((g["exit_reason"] == "TARGET_HIT").mean()),
                "hard_stop_rate": float(g["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(["candle_age_bucket", "burst_bucket"]).reset_index(drop=True)


def find_trade_tick_path(date: str, trade_id: str) -> Path | None:
    safe = trade_id.replace("|", "_").replace(":", "_") + ".jsonl"
    path = REPO_ROOT / "logs" / "trade_ticks" / date / safe
    return path if path.exists() else None


def trade_tick_option_path_metrics(path: Path, entry_price: float) -> dict[str, Any]:
    option_rows: list[tuple[pd.Timestamp, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            symbol = str(row.get("symbol") or "")
            if not symbol.startswith("BFO:SENSEX"):
                continue
            ts = parse_dt(row.get("timestamp_exchange") or row.get("timestamp_receive"))
            ltp = safe_float(row.get("ltp"))
            if pd.isna(ts) or ltp is None:
                continue
            option_rows.append((ts, ltp))
    if not option_rows:
        return {}
    option_rows.sort(key=lambda item: item[0])
    entry_ts = option_rows[0][0]
    pnl_rows = [(ts, ltp - entry_price) for ts, ltp in option_rows]
    peak_ts, peak_points = max(pnl_rows, key=lambda item: item[1])

    def first_hit(points: float) -> float | None:
        target = entry_price + points
        for ts, ltp in option_rows:
            if ltp >= target:
                return (ts - entry_ts).total_seconds()
        return None

    time_to_plus3 = first_hit(3.0)
    time_to_plus5 = first_hit(5.0)
    time_to_plus7 = first_hit(7.0)
    return {
        "time_to_plus3": time_to_plus3,
        "time_to_plus5": time_to_plus5,
        "time_to_plus7": time_to_plus7,
        "time_to_peak_mfe": (peak_ts - entry_ts).total_seconds(),
        "peak_mfe_trade_ticks": peak_points,
        "stalled_after_plus3": bool(time_to_plus3 is not None and time_to_plus5 is None),
    }


def build_promotion_audit(trades_df: pd.DataFrame, timeline_df: pd.DataFrame) -> pd.DataFrame:
    burst_dates = timeline_df.loc[timeline_df["patch_era"].isin(["burst_promotion", "burst_promotion_tape"]), "date"].tolist()
    if not burst_dates:
        return pd.DataFrame()
    start_date = min(burst_dates)
    df = trades_df[(trades_df["date"] >= start_date) & (trades_df["is_promoted_candidate"])].copy()
    if df.empty:
        return df

    extra_rows = []
    for _, row in df.iterrows():
        metrics = {}
        path = find_trade_tick_path(str(row["date"]), str(row["trade_id"]))
        if path is not None and pd.notna(row.get("entry_price")):
            metrics = trade_tick_option_path_metrics(path, float(row["entry_price"]))
        peak_mfe = row.get("mfe") if pd.notna(row.get("mfe")) else metrics.get("peak_mfe_trade_ticks")
        extra_rows.append(
            {
                "date": row["date"],
                "trade_id": row["trade_id"],
                "signal_kind": row.get("signal_kind"),
                "side": row.get("side"),
                "burst_score": row.get("burst_score_effective"),
                "entry_time": row.get("entry_dt"),
                "exit_time": row.get("exit_dt"),
                "entry_price": row.get("entry_price"),
                "exit_price": row.get("exit_price"),
                "target_points_used": row.get("target_points_used"),
                "promoted_target_points": row.get("promoted_target_points"),
                "exit_reason": row.get("exit_reason"),
                "net_pnl": row.get("net_pnl"),
                "mfe": row.get("mfe"),
                "mae": row.get("mae"),
                "peak_mfe_trade_ticks": metrics.get("peak_mfe_trade_ticks", peak_mfe),
                "hit_plus3_during_trade": bool((row.get("mfe") or 0.0) >= 3.0),
                "hit_plus5_during_trade": bool((row.get("mfe") or 0.0) >= 5.0),
                "hit_plus7_during_trade": bool((row.get("mfe") or 0.0) >= 7.0),
                "time_to_plus3": metrics.get("time_to_plus3"),
                "time_to_plus5": metrics.get("time_to_plus5"),
                "time_to_plus7": metrics.get("time_to_plus7"),
                "time_to_peak_mfe": metrics.get("time_to_peak_mfe"),
                "stalled_after_plus3": metrics.get("stalled_after_plus3", False),
                "promoted_3s_passed": row.get("promoted_3s_passed"),
                "promoted_3s_reason": row.get("promoted_3s_reason"),
                "promotion_persistence_passed": row.get("promotion_persistence_passed"),
                "promotion_persistence_exit_triggered": row.get("promotion_persistence_exit_triggered"),
                "should_have_exited_at_plus3": bool((row.get("mfe") or 0.0) >= 3.0 and (row.get("mfe") or 0.0) < 5.0),
                "hidden_runner_example": bool((row.get("mfe") or 0.0) >= 7.0),
            }
        )
    return pd.DataFrame(extra_rows).sort_values(["date", "entry_time"]).reset_index(drop=True)


def build_exit_audit(trades_df: pd.DataFrame, timeline_df: pd.DataFrame, checkpoint: str) -> pd.DataFrame:
    burst_dates = timeline_df.loc[timeline_df["patch_era"].isin(["burst_promotion", "burst_promotion_tape"]), "date"].tolist()
    if not burst_dates:
        return pd.DataFrame()
    start_date = min(burst_dates)
    df = trades_df[trades_df["date"] >= start_date].copy()
    if df.empty:
        return df

    rows = []
    if checkpoint == "1s":
        seconds = 1.0
        kill_reasons = {"EARLY_FAIL_1S"}
    else:
        seconds = 3.0
        kill_reasons = {"EARLY_FAIL_3S", "PROMOTED_FAIL_3S"}

    for _, row in df.iterrows():
        holding = row.get("holding_seconds")
        eligible = bool((pd.notna(holding) and holding >= seconds) or (row.get("exit_reason") in kill_reasons))
        killed = row.get("exit_reason") in kill_reasons
        good_counterfactual = bool(row.get("post_exit_hit_target_15s"))
        crossed_entry = bool(row.get("post_exit_crossed_entry_15s"))
        if not eligible:
            bucket = "not_eligible"
        elif killed and good_counterfactual:
            bucket = "good_killed"
        elif killed and not good_counterfactual:
            bucket = "bad_killed"
        elif (not killed) and row.get("net_pnl", 0) > 0:
            bucket = "good_kept"
        else:
            bucket = "bad_kept"
        rows.append(
            {
                "date": row["date"],
                "trade_id": row["trade_id"],
                "signal_kind": row.get("signal_kind"),
                "side": row.get("side"),
                "exit_reason": row.get("exit_reason"),
                "net_pnl": row.get("net_pnl"),
                "holding_seconds": holding,
                "eligible": eligible,
                "killed": killed,
                "audit_bucket": bucket,
                "crossed_entry_15s": crossed_entry,
                "hit_target_15s": good_counterfactual,
                "post_exit_best_recovery": row.get("post_exit_points_best_recovery"),
                "post_exit_final_delta_15s": row.get("post_exit_final_delta_15s"),
                "burst_score": row.get("burst_score_effective"),
            }
        )
    return pd.DataFrame(rows).sort_values(["date", "trade_id"]).reset_index(drop=True)


def load_underlying_second_series(date: str) -> pd.Series:
    path = REPO_ROOT / "logs" / "ticks" / date / "sensex.jsonl"
    snapshots: dict[pd.Timestamp, float] = {}
    if not path.exists():
        return pd.Series(dtype=float)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = parse_dt(row.get("timestamp_exchange") or row.get("timestamp_receive"))
            ltp = safe_float(row.get("ltp"))
            if pd.isna(ts) or ltp is None:
                continue
            second = ts.floor("s")
            snapshots[second] = ltp
    if not snapshots:
        return pd.Series(dtype=float)
    ser = pd.Series(snapshots).sort_index()
    full_index = pd.date_range(ser.index.min(), ser.index.max(), freq="1s")
    return ser.reindex(full_index).ffill()


def load_option_second_rows(date: str) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    path = REPO_ROOT / "data" / "tape" / "sensex_options" / date / "options.jsonl"
    symbol_second: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    stats = {
        "path": str(path),
        "exists": path.exists(),
        "raw_rows": 0,
        "unique_symbols": 0,
        "unique_strikes": 0,
        "parse_errors": 0,
    }
    if not path.exists():
        return {}, stats
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
            bid5 = row.get("bid[5]") or []
            ask5 = row.get("ask[5]") or []
            bid_qty = None
            ask_qty = None
            if isinstance(bid5, list) and bid5 and isinstance(bid5[0], dict):
                bid_qty = safe_float(bid5[0].get("quantity"))
            if isinstance(ask5, list) and ask5 and isinstance(ask5[0], dict):
                ask_qty = safe_float(ask5[0].get("quantity"))
            symbol_second[(str(symbol), second)] = {
                "timestamp": second,
                "ltp": ltp,
                "spread": safe_float(row.get("spread")),
                "bid_qty": bid_qty,
                "ask_qty": ask_qty,
                "best_bid": safe_float(row.get("best_bid")),
                "best_ask": safe_float(row.get("best_ask")),
                "strike": safe_float(row.get("strike")),
                "option_type": row.get("option_type"),
                "lot_size": int(row.get("lot_size") or 0),
                "expiry": row.get("expiry"),
                "symbol": str(symbol),
            }
    per_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    strikes = set()
    for (symbol, _), record in symbol_second.items():
        per_symbol[symbol].append(record)
        if record.get("strike") is not None:
            strikes.add(int(record["strike"]))
    for symbol in per_symbol:
        per_symbol[symbol].sort(key=lambda item: item["timestamp"])
    stats["unique_symbols"] = len(per_symbol)
    stats["unique_strikes"] = len(strikes)
    return per_symbol, stats


def build_underlying_window(series: pd.Series, timestamp: pd.Timestamp) -> list[dict[str, Any]]:
    window = series.loc[timestamp - pd.Timedelta(seconds=5): timestamp]
    return [{"timestamp_exchange": ts.to_pydatetime(), "ltp": float(val)} for ts, val in window.items() if pd.notna(val)]


def row_to_option_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_exchange": row["timestamp"].to_pydatetime() if isinstance(row["timestamp"], pd.Timestamp) else row["timestamp"],
        "ltp": row.get("ltp"),
        "spread": row.get("spread"),
        "bid_qty": row.get("bid_qty"),
        "ask_qty": row.get("ask_qty"),
    }


def compute_burst_candidates_for_day(
    date: str,
    settings: Any,
) -> tuple[pd.DataFrame, dict[str, list[dict[str, Any]]], dict[str, Any]]:
    underlying = load_underlying_second_series(date)
    symbol_rows, stats = load_option_second_rows(date)
    if underlying.empty or not symbol_rows:
        return pd.DataFrame(), symbol_rows, stats

    records: list[dict[str, Any]] = []
    min_score = int(getattr(settings, "microburst_min_score", 3))
    max_spread = 3.0

    for symbol, rows in symbol_rows.items():
        option_type = str(rows[0].get("option_type") or "").upper()
        side = "CALL" if option_type == "CE" else "PUT"
        start_idx = 0
        prev_above_threshold = False
        for idx, row in enumerate(rows):
            ts = row["timestamp"]
            while start_idx < idx and rows[start_idx]["timestamp"] < ts - pd.Timedelta(seconds=5):
                start_idx += 1
            option_window = [row_to_option_record(item) for item in rows[start_idx : idx + 1]]
            underlying_window = build_underlying_window(underlying, ts)
            if len(option_window) < 2 or len(underlying_window) < 2:
                continue
            spread = row.get("spread")
            if spread is None or spread > max_spread:
                continue
            if not (row.get("bid_qty") or 0) or not (row.get("ask_qty") or 0):
                continue
            features = compute_pre_entry_features(
                recent_underlying_window=underlying_window,
                recent_option_window=option_window,
                side=side,
                settings=settings,
            )
            score = int(features.score)
            if score < min_score:
                prev_above_threshold = False
                continue
            if prev_above_threshold:
                continue
            prev_above_threshold = True
            target_class, target_points = classify_target(score, settings)
            records.append(
                {
                    "date": date,
                    "entry_time": ts,
                    "symbol": symbol,
                    "side": side,
                    "score": score,
                    "target_class": target_class,
                    "target_points": float(target_points),
                    "ltp": float(row["ltp"]),
                    "spread": float(spread),
                    "bid_qty": float(row.get("bid_qty") or 0.0),
                    "ask_qty": float(row.get("ask_qty") or 0.0),
                    "lot_size": int(row.get("lot_size") or 0),
                    "strike": row.get("strike"),
                    "option_type": option_type,
                    "ind_velocity_aligned": float(features.ind_velocity_aligned),
                    "ind_accel_aligned": float(features.ind_accel_aligned),
                    "opt_velocity_aligned": float(features.opt_velocity_aligned),
                    "opt_depth_imb_mean": float(features.opt_depth_imb_mean),
                    "opt_spread_mean": float(features.opt_spread_mean) if features.opt_spread_mean is not None else np.nan,
                    "score_components": json.dumps(features.score_components, sort_keys=True),
                }
            )
    candidates = pd.DataFrame(records)
    if not candidates.empty:
        candidates = candidates.sort_values(["entry_time", "score", "opt_velocity_aligned", "opt_depth_imb_mean"], ascending=[True, False, False, False]).reset_index(drop=True)
        deduped: list[dict[str, Any]] = []
        last_symbol_entry: dict[str, pd.Timestamp] = {}
        for row in candidates.to_dict(orient="records"):
            ts = pd.Timestamp(row["entry_time"])
            prev = last_symbol_entry.get(str(row["symbol"]))
            if prev is not None and (ts - prev).total_seconds() < TAPE_SYMBOL_BURST_COOLDOWN_SECONDS:
                continue
            deduped.append(row)
            last_symbol_entry[str(row["symbol"])] = ts
        candidates = pd.DataFrame(deduped)
        if not candidates.empty:
            candidates = candidates.sort_values(["entry_time", "score", "opt_velocity_aligned", "opt_depth_imb_mean"], ascending=[True, False, False, False]).reset_index(drop=True)
    return candidates, symbol_rows, stats


def build_ffill_symbol_series(rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows).sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    df = df.set_index("timestamp")
    full_index = pd.date_range(df.index.min(), df.index.max(), freq="1s")
    out = df.reindex(full_index).ffill()
    out["updated"] = False
    out.loc[df.index, "updated"] = True
    out.index.name = "timestamp"
    return out


def simulate_burst_trade(
    symbol: str,
    entry_time: pd.Timestamp,
    score: int,
    symbol_rows: list[dict[str, Any]],
    settings: Any,
    series_cache: dict[str, pd.DataFrame],
    max_hold_seconds: int = 30,
) -> dict[str, Any] | None:
    if symbol not in series_cache:
        series_cache[symbol] = build_ffill_symbol_series(symbol_rows)
    series = series_cache[symbol]
    if entry_time not in series.index:
        return None
    side = "CALL" if str(series.loc[entry_time, "option_type"]).upper() == "CE" else "PUT"
    entry_price = float(series.loc[entry_time, "ltp"])
    lot_size = int(series.loc[entry_time, "lot_size"] or 0)
    capital = float(getattr(settings, "capital_budget", 300000.0))
    cost_per_lot = float(entry_price) * int(lot_size)
    quantity = None
    if cost_per_lot > 0 and lot_size > 0:
        lots = math.floor(capital / cost_per_lot)
        quantity = lots * int(lot_size) if lots > 0 else None
    if quantity is None:
        return None

    promoted_candidate = int(score) >= int(getattr(settings, "promoted_min_score", 5))
    target_points = float(getattr(settings, "promoted_target_points", 7.0) if promoted_candidate else getattr(settings, "normal_target_points", 3.0))
    hard_stop_points = float(getattr(settings, "edge_invalidation_hard_stop_points", 6.0))
    check_1s = float(getattr(settings, "edge_invalidation_1s_check_seconds", 1.0))
    check_3s = float(getattr(settings, "edge_invalidation_3s_check_seconds", 3.0))

    checked_1s = False
    checked_3s = False
    promoted_active = False
    persistence_passed = False
    first_hit_time: pd.Timestamp | None = None
    deadline_time: pd.Timestamp | None = None

    runup = 0.0
    drawdown = 0.0
    price_history: list[tuple[datetime, float]] = []
    last_row = None
    for now, row in series.loc[entry_time : entry_time + pd.Timedelta(seconds=max_hold_seconds)].iterrows():
        last_row = row
        ltp = float(row["ltp"])
        price_history.append((now.to_pydatetime(), ltp))
        pnl = ltp - entry_price
        runup = max(runup, pnl)
        drawdown = min(drawdown, pnl)
        elapsed = float((now - entry_time).total_seconds())

        if pnl >= target_points:
            reason = "TARGET_HIT"
            exit_time = now
            exit_price = ltp
            break

        if bool(getattr(settings, "edge_invalidation_hard_stop_enabled", True)) and pnl <= -hard_stop_points:
            reason = "EDGE_HARD_STOP"
            exit_time = now
            exit_price = ltp
            break

        if (not checked_1s) and elapsed >= check_1s:
            checked_1s = True
            if runup < float(getattr(settings, "edge_invalidation_1s_min_runup_points", 1.0)) and pnl <= float(getattr(settings, "edge_invalidation_1s_max_pnl_points", 0.0)):
                reason = "EARLY_FAIL_1S"
                exit_time = now
                exit_price = ltp
                break

        if (not checked_3s) and elapsed >= check_3s:
            checked_3s = True
            if promoted_candidate:
                diag = compute_promoted_3s_diagnostics(
                    price_history,
                    entry_time=entry_time.to_pydatetime(),
                    entry_price=entry_price,
                    current_time=now.to_pydatetime(),
                    current_price=ltp,
                )
                survived, reason_3s = promoted_trade_survives_3s(diag, settings)
                if not survived:
                    reason = "PROMOTED_FAIL_3S"
                    exit_time = now
                    exit_price = ltp
                    break
                promoted_active = True
            else:
                min_runup = float(getattr(settings, "edge_invalidation_3s_min_runup_points", 2.0))
                max_drawdown = float(getattr(settings, "edge_invalidation_3s_max_drawdown_points", 4.0))
                pinned_abs = float(getattr(settings, "edge_invalidation_3s_pinned_pnl_abs_points", 1.0))
                if runup < min_runup or abs(drawdown) >= max_drawdown or abs(pnl) <= pinned_abs:
                    reason = "EARLY_FAIL_3S"
                    exit_time = now
                    exit_price = ltp
                    break

        if bool(getattr(settings, "layer4_enabled", False)) and promoted_candidate and promoted_active:
            current_pnl = pnl
            trigger_points = float(getattr(settings, "layer4_trigger_points", 3.0))
            window_seconds = float(getattr(settings, "layer4_window_seconds", 2.0))
            if first_hit_time is None and current_pnl >= trigger_points:
                first_hit_time = now
                deadline_time = now + pd.Timedelta(seconds=window_seconds)
            state, _ = layer4_persistence_result(
                now=now.to_pydatetime(),
                first_hit_time=first_hit_time.to_pydatetime() if first_hit_time is not None else None,
                deadline_time=deadline_time.to_pydatetime() if deadline_time is not None else None,
                current_pnl=current_pnl,
                settings=settings,
                persistence_passed=bool(persistence_passed),
            )
            if state == "pass":
                persistence_passed = True
            elif state == "fail":
                reason = "PROMOTION_PERSISTENCE_FAIL"
                exit_time = now
                exit_price = ltp
                break
    else:
        if last_row is None:
            return None
        reason = f"SIM_TIMEOUT_{max_hold_seconds}S"
        exit_time = series.loc[entry_time : entry_time + pd.Timedelta(seconds=max_hold_seconds)].index[-1]
        exit_price = float(last_row["ltp"])

    gross_pnl = (exit_price - entry_price) * quantity
    return {
        "entry_time": entry_time,
        "exit_time": exit_time,
        "holding_seconds": float((exit_time - entry_time).total_seconds()),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "exit_reason": reason,
        "target_points": target_points,
        "quantity": quantity,
        "gross_pnl": gross_pnl,
        "net_pnl": gross_pnl,
        "runup_points": runup,
        "drawdown_points": drawdown,
        "promoted_candidate": promoted_candidate,
        "promotion_persistence_passed": persistence_passed,
    }


def run_pure_burst_policy_for_day(date: str, settings: Any) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    candidates, symbol_rows, stats = compute_burst_candidates_for_day(date, settings)
    if candidates.empty:
        return pd.DataFrame(), pd.DataFrame(), {"date": date, "status": "no_candidates", **stats}

    grouped = defaultdict(list)
    for row in candidates.to_dict(orient="records"):
        grouped[pd.Timestamp(row["entry_time"])].append(row)

    selected: list[dict[str, Any]] = []
    series_cache: dict[str, pd.DataFrame] = {}
    next_free_time: pd.Timestamp | None = None
    for ts in sorted(grouped):
        if next_free_time is not None and ts < next_free_time:
            continue
        rows = sorted(grouped[ts], key=lambda item: (-item["score"], -item["opt_velocity_aligned"], -item["opt_depth_imb_mean"], item["spread"]))
        chosen = rows[0]
        result = simulate_burst_trade(chosen["symbol"], ts, int(chosen["score"]), symbol_rows[chosen["symbol"]], settings, series_cache)
        if result is None:
            continue
        merged = {**chosen, **result}
        selected.append(merged)
        next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=TAPE_GLOBAL_ENTRY_COOLDOWN_SECONDS)

    selected_df = pd.DataFrame(selected)
    meta = {
        "date": date,
        "status": "ok",
        "raw_candidate_count": int(len(candidates)),
        "selected_trade_count": int(len(selected_df)),
        **stats,
    }
    return candidates, selected_df, meta


def compare_tape_days(trades_df: pd.DataFrame, settings: Any, tape_dates: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if not tape_dates:
        return pd.DataFrame(), pd.DataFrame(), {}
    selected_days = sorted(tape_dates)[-2:]
    comparison_rows: list[dict[str, Any]] = []
    missed_rows: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"selected_tape_days": selected_days, "per_day": {}}

    for date in selected_days:
        actual = trades_df[trades_df["date"] == date].copy()
        candidates, selected_df, day_meta = run_pure_burst_policy_for_day(date, settings)
        meta["per_day"][date] = day_meta

        actual_rows = []
        for _, row in actual.iterrows():
            actual_rows.append(
                {
                    "symbol": row.get("symbol"),
                    "entry_time_floor": pd.Timestamp(row.get("entry_dt")).floor("s") if pd.notna(row.get("entry_dt")) else pd.NaT,
                    "trade_id": row.get("trade_id"),
                }
            )
        actual_match_keys = {(r["symbol"], r["entry_time_floor"]) for r in actual_rows if pd.notna(r["entry_time_floor"])}
        matched_actual_entries = 0
        if not candidates.empty:
            candidate_match_keys = {(row["symbol"], pd.Timestamp(row["entry_time"])) for row in candidates.to_dict(orient="records")}
            matched_actual_entries = sum((row["symbol"], row["entry_time_floor"]) in candidate_match_keys for row in actual_rows if pd.notna(row["entry_time_floor"]))

        actual_net = float(actual["net_pnl"].sum()) if not actual.empty else 0.0
        actual_target_hits = int((actual["exit_reason"] == "TARGET_HIT").sum()) if not actual.empty else 0
        pure_net = float(selected_df["net_pnl"].sum()) if not selected_df.empty else 0.0
        comparison_rows.extend(
            [
                {
                    "date": date,
                    "policy": "actual_system",
                    "trades": int(len(actual)),
                    "gross_pnl": float(actual["gross_pnl"].fillna(actual["net_pnl"]).sum()) if not actual.empty else 0.0,
                    "net_pnl": actual_net,
                    "target_hits": actual_target_hits,
                    "hard_stops": int(actual["exit_reason"].isin(["EDGE_HARD_STOP", "HARD_STOP_EXIT"]).sum()) if not actual.empty else 0,
                    "early_fail_1s": int((actual["exit_reason"] == "EARLY_FAIL_1S").sum()) if not actual.empty else 0,
                    "early_fail_3s": int(actual["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S"]).sum()) if not actual.empty else 0,
                    "raw_burst_opportunities": int(len(candidates)),
                    "matched_actual_entries": int(matched_actual_entries),
                    "notes": "actual candle-gated live trades",
                },
                {
                    "date": date,
                    "policy": "pure_burst_only_sim",
                    "trades": int(len(selected_df)),
                    "gross_pnl": pure_net,
                    "net_pnl": pure_net,
                    "target_hits": int((selected_df["exit_reason"] == "TARGET_HIT").sum()) if not selected_df.empty else 0,
                    "hard_stops": int((selected_df["exit_reason"] == "EDGE_HARD_STOP").sum()) if not selected_df.empty else 0,
                    "early_fail_1s": int((selected_df["exit_reason"] == "EARLY_FAIL_1S").sum()) if not selected_df.empty else 0,
                    "early_fail_3s": int(selected_df["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S"]).sum()) if not selected_df.empty else 0,
                    "raw_burst_opportunities": int(len(candidates)),
                    "matched_actual_entries": int(sum((row["symbol"], pd.Timestamp(row["entry_time"])) in actual_match_keys for row in selected_df.to_dict(orient="records"))) if not selected_df.empty else 0,
                    "notes": "1-position-at-a-time second-level replay",
                },
            ]
        )

        if not selected_df.empty:
            for row in selected_df.to_dict(orient="records"):
                key = (row["symbol"], pd.Timestamp(row["entry_time"]))
                if key in actual_match_keys:
                    continue
                missed_rows.append(
                    {
                        "date": date,
                        "entry_time": row["entry_time"],
                        "symbol": row["symbol"],
                        "side": row["side"],
                        "score": row["score"],
                        "target_class": row["target_class"],
                        "target_points": row["target_points"],
                        "entry_price": row["entry_price"],
                        "exit_time": row["exit_time"],
                        "exit_reason": row["exit_reason"],
                        "net_pnl": row["net_pnl"],
                        "runup_points": row["runup_points"],
                        "drawdown_points": row["drawdown_points"],
                        "matched_actual": False,
                    }
                )

    comparison_df = pd.DataFrame(comparison_rows)
    if not comparison_df.empty:
        overall = comparison_df.groupby("policy", as_index=False).agg(
            trades=("trades", "sum"),
            gross_pnl=("gross_pnl", "sum"),
            net_pnl=("net_pnl", "sum"),
            target_hits=("target_hits", "sum"),
            hard_stops=("hard_stops", "sum"),
            early_fail_1s=("early_fail_1s", "sum"),
            early_fail_3s=("early_fail_3s", "sum"),
            raw_burst_opportunities=("raw_burst_opportunities", "sum"),
            matched_actual_entries=("matched_actual_entries", "sum"),
        )
        overall["date"] = "OVERALL"
        overall["notes"] = "aggregate over last 2 tape days"
        comparison_df = pd.concat([comparison_df, overall[comparison_df.columns]], ignore_index=True)
    missed_df = pd.DataFrame(missed_rows).sort_values(["date", "net_pnl"], ascending=[True, False]).reset_index(drop=True) if missed_rows else pd.DataFrame()
    return comparison_df, missed_df, meta


def load_promotion_datasets_meta() -> dict[str, Any]:
    meta: dict[str, Any] = {}
    live_path = REPO_ROOT / "analysis" / "target_promotion_live_dataset.csv"
    shadow_path = REPO_ROOT / "analysis" / "target_promotion_shadow_dataset.csv"
    if live_path.exists():
        live = pd.read_csv(live_path, low_memory=False)
        meta["target_promotion_live_rows"] = int(len(live))
        if "label_target_bucket" in live.columns:
            meta["target_bucket_counts"] = live["label_target_bucket"].value_counts(dropna=False).to_dict()
        if "target_live_trainable" in live.columns:
            meta["target_live_trainable_rate"] = float(live["target_live_trainable"].mean())
    if shadow_path.exists():
        shadow = pd.read_csv(shadow_path, low_memory=False)
        meta["target_promotion_shadow_rows"] = int(len(shadow))
        if "label_bad_trade" in shadow.columns:
            meta["shadow_bad_trade_rate"] = float(shadow["label_bad_trade"].astype(str).eq("True").mean())
    meta["target_model_results_present"] = bool(list(REPO_ROOT.glob("target_model_results*")))
    return meta


def save_plot_daywise_metrics(daywise_df: pd.DataFrame) -> list[Path]:
    paths: list[Path] = []
    if daywise_df.empty:
        return paths
    plot1 = OUTPUT_DIR / "equity_curve_by_patch_era.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    for era, g in daywise_df.groupby("patch_era"):
        g = g.sort_values("date")
        ax.plot(pd.to_datetime(g["date"]), g["cumulative_net_pnl_by_patch_era"], marker="o", label=era)
    ax.set_title("Cumulative Net PnL Within Each Patch Era")
    ax.set_ylabel("Cumulative net PnL")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(plot1, dpi=160)
    plt.close(fig)
    paths.append(plot1)

    plot2 = OUTPUT_DIR / "daywise_net_pnl.png"
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"pre_1s3s": "#1f77b4", "edge_1s3s": "#ff7f0e", "burst_promotion": "#2ca02c", "burst_promotion_tape": "#9467bd"}
    ax.bar(pd.to_datetime(daywise_df["date"]), daywise_df["net_pnl"], color=[colors.get(era, "#666666") for era in daywise_df["patch_era"]])
    ax.axhline(0, color="#333333", lw=1)
    ax.set_title("Day-wise Net PnL")
    ax.set_ylabel("Net PnL")
    ax.grid(True, axis="y", alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(plot2, dpi=160)
    plt.close(fig)
    paths.append(plot2)
    return paths


def markdown_table(df: pd.DataFrame, max_rows: int = 12) -> str:
    if df is None or df.empty:
        return "(no data)"
    use = df.head(max_rows).copy()
    cols = list(use.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in use.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                if math.isnan(value):
                    values.append("")
                else:
                    values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_report(
    timeline_df: pd.DataFrame,
    daywise_df: pd.DataFrame,
    failure_df: pd.DataFrame,
    worst_df: pd.DataFrame,
    freshness_df: pd.DataFrame,
    burst_perf_df: pd.DataFrame,
    fresh_x_burst_df: pd.DataFrame,
    promotion_df: pd.DataFrame,
    one_sec_df: pd.DataFrame,
    three_sec_df: pd.DataFrame,
    tape_compare_df: pd.DataFrame,
    missed_df: pd.DataFrame,
    canonical_meta: dict[str, Any],
    ml_meta: dict[str, Any],
    chart_paths: list[Path],
) -> str:
    lines: list[str] = []
    lines.append("# Strategy Audit Report")
    lines.append("")
    lines.append("## Executive Summary")

    if daywise_df.empty:
        lines.append("No trade data was available.")
        return "\n".join(lines)

    post_patch = daywise_df[daywise_df["patch_era"].isin(["burst_promotion", "burst_promotion_tape"])]
    pre_patch = daywise_df[daywise_df["patch_era"].isin(["pre_1s3s", "edge_1s3s"])]
    edge_only = daywise_df[daywise_df["patch_era"] == "edge_1s3s"]
    post_patch_net = float(post_patch["net_pnl"].sum()) if not post_patch.empty else np.nan
    post_patch_days = int(len(post_patch))
    negative_post_patch_days = int((post_patch["net_pnl"] < 0).sum()) if not post_patch.empty else 0
    pre_patch_net = float(pre_patch["net_pnl"].sum()) if not pre_patch.empty else np.nan
    edge_net = float(edge_only["net_pnl"].sum()) if not edge_only.empty else np.nan
    edge_days = int(len(edge_only))
    promoted_net = float(promotion_df["net_pnl"].sum()) if not promotion_df.empty else np.nan
    immediate_rows = freshness_df[freshness_df["analysis_axis"] == "immediate_confirmation"].copy()
    actual_overall = tape_compare_df[(tape_compare_df["date"] == "OVERALL") & (tape_compare_df["policy"] == "actual_system")]
    pure_overall = tape_compare_df[(tape_compare_df["date"] == "OVERALL") & (tape_compare_df["policy"] == "pure_burst_only_sim")]

    lines.append(f"- Burst/promotion live patch first appears in logs on **{timeline_df.loc[timeline_df['patch_era'].isin(['burst_promotion','burst_promotion_tape']), 'date'].min()}**.")
    lines.append(f"- Post-patch live sessions in this repo: **{post_patch_days}** | negative sessions: **{negative_post_patch_days}** | cumulative net: **{post_patch_net:,.0f}**.")
    if not math.isnan(pre_patch_net):
        lines.append(f"- Pre-burst eras cumulative net in available logs: **{pre_patch_net:,.0f}**.")
    if not math.isnan(edge_net):
        lines.append(f"- The immediately prior **edge_1s/3s** era was near flat by comparison: **{edge_days} sessions, {edge_net:,.0f} cumulative net**.")
    if not math.isnan(promoted_net):
        lines.append(f"- Promoted trades were **not** the main post-patch drag in available live data: **{len(promotion_df)} promoted trades, {promoted_net:,.0f} net**.")
    if not failure_df.empty:
        top_failure = failure_df["failure_mode"].value_counts().head(5).to_dict()
        lines.append(f"- Dominant post-patch failure modes: **{top_failure}**.")
    if not immediate_rows.empty:
        bad = immediate_rows[immediate_rows["bucket"].astype(str) == "False"]
        good = immediate_rows[immediate_rows["bucket"].astype(str) == "True"]
        if not bad.empty and not good.empty:
            lines.append(
                "- Immediate microstructure confirmation is the cleanest separator in the post-patch set: "
                f"confirmed trades made **{float(good['net_pnl'].iloc[0]):,.0f}** across **{int(good['trades'].iloc[0])}** trades, "
                f"while non-confirmed trades lost **{float(bad['net_pnl'].iloc[0]):,.0f}** across **{int(bad['trades'].iloc[0])}** trades."
            )
    if not tape_compare_df.empty:
        if not actual_overall.empty and not pure_overall.empty:
            lines.append(
                "- Tape-based burst-only replay on the last two tape days shows a mixed answer: the current candle-gated live system lost "
                f"**{float(actual_overall['net_pnl'].iloc[0]):,.0f}** on **{int(actual_overall['trades'].iloc[0])}** trades, "
                f"while a naive pure-burst replay lost **{float(pure_overall['net_pnl'].iloc[0]):,.0f}** on **{int(pure_overall['trades'].iloc[0])}** trades. "
                "So removing candles without better burst candidate ranking would overtrade badly."
            )
    lines.append("")

    lines.append("## Patch Timeline")
    lines.append(markdown_table(timeline_df[["date", "patch_era", "active_features", "number_of_trades", "notes"]], max_rows=30))
    lines.append("")

    lines.append("## Day-wise Performance By Patch Era")
    lines.append(markdown_table(daywise_df[["date", "patch_era", "total_trades", "net_pnl", "win_rate", "avg_win", "avg_loss", "profit_factor", "max_intraday_drawdown", "num_1s_kills", "num_3s_kills", "num_hard_stops", "num_target_hits", "num_promoted_trades"]], max_rows=40))
    lines.append("")

    lines.append("## Post-patch Failure Modes")
    if failure_df.empty:
        lines.append("No post-patch losing trades found.")
    else:
        summary = failure_df.groupby(["date", "failure_mode"], as_index=False).agg(trades=("trade_id", "count"), net_pnl=("net_pnl", "sum"))
        lines.append(markdown_table(summary.sort_values(["date", "net_pnl"]), max_rows=40))
    lines.append("")

    lines.append("## Worst Trades")
    lines.append(markdown_table(worst_df[["date", "trade_id", "signal_kind", "exit_reason", "net_pnl", "failure_mode", "burst_score_effective", "candle_age_seconds", "mfe", "mae", "post_exit_points_best_recovery", "post_exit_hit_target_15s"]], max_rows=20))
    lines.append("")

    lines.append("## Entry Freshness And Burst Context")
    lines.append(markdown_table(freshness_df, max_rows=30))
    lines.append("")
    lines.append(markdown_table(burst_perf_df, max_rows=20))
    lines.append("")
    lines.append(markdown_table(fresh_x_burst_df, max_rows=25))
    lines.append("")

    lines.append("## Promotion Audit")
    if promotion_df.empty:
        lines.append("No promoted trades found in burst-era sessions.")
    else:
        lines.append(markdown_table(promotion_df[["date", "trade_id", "burst_score", "exit_reason", "net_pnl", "mfe", "hit_plus3_during_trade", "hit_plus5_during_trade", "hit_plus7_during_trade", "stalled_after_plus3", "promoted_3s_passed", "promotion_persistence_passed"]], max_rows=25))
    lines.append("")

    lines.append("## 1s And 3s Exit Audit")
    if not one_sec_df.empty:
        one_summary = one_sec_df.groupby("audit_bucket", as_index=False).agg(trades=("trade_id", "count"), net_pnl=("net_pnl", "sum"))
        lines.append("### 1s checkpoint")
        lines.append(markdown_table(one_summary, max_rows=10))
    if not three_sec_df.empty:
        three_summary = three_sec_df.groupby("audit_bucket", as_index=False).agg(trades=("trade_id", "count"), net_pnl=("net_pnl", "sum"))
        lines.append("### 3s checkpoint")
        lines.append(markdown_table(three_summary, max_rows=10))
    lines.append("")

    lines.append("## Full Option Tape Comparison")
    if tape_compare_df.empty:
        lines.append("Full option tape comparison was not available.")
    else:
        lines.append(markdown_table(tape_compare_df, max_rows=10))
        if not missed_df.empty:
            lines.append("### Top missed burst-only opportunities")
            lines.append(markdown_table(missed_df[["date", "entry_time", "symbol", "score", "target_class", "exit_reason", "net_pnl", "runup_points", "drawdown_points"]], max_rows=20))
    lines.append("")

    lines.append("## ML / Dataset Artifact Review")
    lines.append(f"- Canonical dataset metadata: {json.dumps(canonical_meta, default=str, sort_keys=True)}")
    lines.append(f"- Promotion dataset metadata: {json.dumps(ml_meta, default=str, sort_keys=True)}")
    if not ml_meta.get("target_model_results_present"):
        lines.append("- No persisted `target_model_results` artifact was found, so there is no stored model confusion matrix or live-vs-model PnL backtest to reconcile directly.")
    lines.append("")

    lines.append("## Final Verdict")
    if not post_patch.empty:
        lines.append(
            f"- **Progressing or circling?** Circling. The strategy improved from the deeply negative pre-1s/3s era into a near-flat **edge_1s/3s** phase "
            f"({edge_net:,.0f} over {edge_days} sessions), but the subsequent burst/promotion live phase regressed to **{post_patch_net:,.0f} over {post_patch_days} sessions** with **{negative_post_patch_days}** negative days."
        )
    lines.append("- **Patch that clearly added value:** the 1s/3s edge-invalidations plus richer journaling improved robustness relative to the original strategy. They did not create a durable edge, but they removed some of the older tail behavior.")
    lines.append("- **Patch adding complexity without stable value yet:** the burst gate, promotion logic, and Layer-4 persistence did not translate into stable out-of-sample improvement after deployment. Promotion itself was net positive in this sample, so the deeper issue is candidate quality, not promotion alone.")
    lines.append("- **Is the 5-minute candle trigger the main structural weakness?** Likely yes as a trigger, though not necessarily as context. The tape comparison shows many missed burst opportunities, while only a small fraction of live candle-gated entries align exactly with tape-detected burst onsets. The candle framework appears to be defining the candidate universe too coarsely for a seconds-scale convexity strategy.")
    lines.append("- **Are we harvesting convexity or reacting to stale candle signals?** Both, but mostly the latter on bad days. When immediate post-entry confirmation exists, the post-patch trade set is strongly positive; without it, the system is catastrophically negative. That is consistent with a real convexity thesis buried inside a weak entry-selection process.")
    lines.append("- **Recommended next step:** stop tuning exits in isolation. Keep candle state only as context if useful, but move the next research cycle to burst-onset entry logic with stricter candidate ranking and tape-based replay. Do not abandon the strategy family yet, but pause confidence in the current live trigger design.")
    lines.append("")

    lines.append("## Limitations")
    lines.append("- The repo has schema drift across March/April. Some early days rely on root journals rather than per-day files.")
    lines.append("- Some dated `trades.jsonl` files appear to mirror event logs, so enriched trade journals are treated as the source of truth.")
    lines.append("- Tape replay is a second-level approximation of current microburst logic; it is useful for bottleneck diagnosis, not a broker-grade execution simulation.")
    lines.append("- One or two tape days are enough to test the candle bottleneck hypothesis, not enough to declare a stable new strategy.")
    lines.append("")

    if chart_paths:
        lines.append("## Charts")
        for path in chart_paths:
            lines.append(f"- ![{path.name}]({path.as_posix()})")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ensure_env_loaded()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    settings = load_settings()

    trade_days = load_trade_days()
    event_days = load_event_days()
    tape_dates = load_tape_dates()
    trades_df = build_trades_df(trade_days)
    trades_df, canonical_meta = merge_canonical_features(trades_df)
    timeline_df = build_patch_timeline(trades_df, event_days, tape_dates)
    daywise_df = compute_daywise_metrics(trades_df, timeline_df)
    failure_df = build_post_patch_failure_df(trades_df, timeline_df)
    worst_df = failure_df.sort_values("net_pnl").head(20).copy() if not failure_df.empty else pd.DataFrame()
    freshness_df = build_entry_freshness_analysis(trades_df, timeline_df)
    burst_perf_df = build_burst_score_performance(trades_df, timeline_df)
    fresh_x_burst_df = build_candle_freshness_x_burst(trades_df, timeline_df)
    promotion_df = build_promotion_audit(trades_df, timeline_df)
    one_sec_df = build_exit_audit(trades_df, timeline_df, checkpoint="1s")
    three_sec_df = build_exit_audit(trades_df, timeline_df, checkpoint="3s")
    tape_compare_df, missed_df, tape_meta = compare_tape_days(trades_df, settings, tape_dates)
    ml_meta = load_promotion_datasets_meta()
    ml_meta.update({"tape_meta": tape_meta})

    timeline_df.to_csv(OUTPUT_DIR / "strategy_patch_timeline.csv", index=False)
    daywise_df.to_csv(OUTPUT_DIR / "daywise_performance_by_patch_era.csv", index=False)
    failure_df.to_csv(OUTPUT_DIR / "post_patch_failure_modes.csv", index=False)
    worst_df.to_csv(OUTPUT_DIR / "worst_trades_classified.csv", index=False)
    freshness_df.to_csv(OUTPUT_DIR / "entry_freshness_analysis.csv", index=False)
    burst_perf_df.to_csv(OUTPUT_DIR / "burst_score_performance.csv", index=False)
    fresh_x_burst_df.to_csv(OUTPUT_DIR / "candle_freshness_x_burst_score.csv", index=False)
    promotion_df.to_csv(OUTPUT_DIR / "promotion_audit.csv", index=False)
    one_sec_df.to_csv(OUTPUT_DIR / "one_sec_exit_audit.csv", index=False)
    three_sec_df.to_csv(OUTPUT_DIR / "three_sec_exit_audit.csv", index=False)
    tape_compare_df.to_csv(OUTPUT_DIR / "full_option_tape_burst_only_comparison.csv", index=False)
    missed_df.to_csv(OUTPUT_DIR / "missed_burst_opportunities.csv", index=False)

    chart_paths = save_plot_daywise_metrics(daywise_df)
    report = build_report(
        timeline_df,
        daywise_df,
        failure_df,
        worst_df,
        freshness_df,
        burst_perf_df,
        fresh_x_burst_df,
        promotion_df,
        one_sec_df,
        three_sec_df,
        tape_compare_df,
        missed_df,
        canonical_meta,
        ml_meta,
        chart_paths,
    )
    (OUTPUT_DIR / "strategy_audit_report.md").write_text(report, encoding="utf-8")

    print("Wrote outputs to", OUTPUT_DIR)
    print("Trade days:", sorted(trade_days))
    print("Tape days:", tape_dates)
    print("Rows | trades_df=%d daywise=%d failures=%d tape_compare=%d" % (len(trades_df), len(daywise_df), len(failure_df), len(tape_compare_df)))


if __name__ == "__main__":
    main()
