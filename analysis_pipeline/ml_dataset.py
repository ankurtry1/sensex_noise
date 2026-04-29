from __future__ import annotations

import glob
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .io_utils import ensure_dir

TARGET_CLASS_ORDER: list[str] = ["keep_3", "extend_to_5", "extend_to_7"]
PRE_ENTRY_NUMERIC_FEATURES: list[str] = [
    "idx_pre_velocity_aligned",
    "idx_pre_accel_aligned",
    "opt_pre_velocity_5s",
    "opt_pre_depth_imb_mean",
    "opt_pre_spread_mean",
    "burst_score_reconstructed",
    "pre_entry_option_tick_count",
    "pre_entry_index_tick_count",
]
PRE_ENTRY_CATEGORICAL_FEATURES: list[str] = [
    "pre_or_post_1pm",
    "continuation_or_reversal",
    "call_or_put",
]
BAD_EXIT_1S_NUMERIC_FEATURES: list[str] = PRE_ENTRY_NUMERIC_FEATURES + [
    "pnl_0p25s",
    "pnl_0p5s",
    "feat_pnl_1s",
    "feat_runup_1s",
    "feat_drawdown_1s",
]
BAD_EXIT_3S_NUMERIC_FEATURES: list[str] = BAD_EXIT_1S_NUMERIC_FEATURES + [
    "feat_pnl_3s",
    "feat_runup_3s",
    "feat_drawdown_3s",
    "feat_velocity_decay_ratio",
]
TARGET_SHADOW_NUMERIC_FEATURES: list[str] = PRE_ENTRY_NUMERIC_FEATURES + [
    "pnl_0p25s",
    "pnl_0p5s",
    "feat_pnl_1s",
    "feat_runup_1s",
    "feat_drawdown_1s",
    "feat_pnl_3s",
    "feat_runup_3s",
    "feat_drawdown_3s",
    "feat_velocity_decay_ratio",
]
ML_DATASET_FILENAMES: dict[str, str] = {
    "canonical": "canonical_trades_ml_dataset.csv",
    "dictionary": "canonical_trades_ml_dataset_dictionary.csv",
    "coverage": "canonical_trades_ml_dataset_coverage.csv",
    "datewise_coverage": "canonical_trades_ml_dataset_datewise_coverage.csv",
    "entry_filter": "entry_filter_dataset.csv",
    "bad_trade_exit_1s": "bad_trade_exit_1s_dataset.csv",
    "bad_trade_exit_3s": "bad_trade_exit_3s_dataset.csv",
    "target_promotion_live": "target_promotion_live_dataset.csv",
    "target_promotion_shadow": "target_promotion_shadow_dataset.csv",
}

_CHECKPOINTS = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0]
_BAD_REASONS = {
    "EARLY_FAIL_1S",
    "EARLY_FAIL_3S",
    "EARLY_RISK_EXIT",
    "PATH_RISK_EXIT",
    "EDGE_HARD_STOP",
    "HARD_STOP_EXIT",
    "PROMOTED_FAIL_3S",
    "PROMOTION_PERSISTENCE_FAIL",
}
_EARLY_FEATURE_COLUMNS = [
    "feature_extraction_status",
    "has_trade_ticks",
    "has_underlying_ticks",
    "has_futures_ticks",
    "has_depth",
    "has_subsecond_time",
    "fill_method",
    "label_final",
    "pnl_0p25s",
    "runup_0p25s",
    "drawdown_0p25s",
    "tick_velocity_0p25s",
    "spread_0p25s",
    "depth_imbalance_0p25s",
    "underlying_move_0p25s",
    "underlying_velocity_0p25s",
    "pnl_0p5s",
    "runup_0p5s",
    "drawdown_0p5s",
    "tick_velocity_0p5s",
    "spread_0p5s",
    "depth_imbalance_0p5s",
    "underlying_move_0p5s",
    "underlying_velocity_0p5s",
    "pnl_1s",
    "runup_1s",
    "drawdown_1s",
    "pnl_1p0s",
    "runup_1p0s",
    "drawdown_1p0s",
    "tick_velocity_1s",
    "spread_1s",
    "depth_imbalance_1s",
    "underlying_move_1s",
    "underlying_velocity_1s",
    "pnl_2s",
    "runup_2s",
    "drawdown_2s",
    "tick_velocity_2s",
    "spread_2s",
    "depth_imbalance_2s",
    "underlying_move_2s",
    "underlying_velocity_2s",
    "pnl_3s",
    "runup_3s",
    "drawdown_3s",
    "pnl_3p0s",
    "runup_3p0s",
    "drawdown_3p0s",
    "tick_velocity_3s",
    "spread_3s",
    "depth_imbalance_3s",
    "underlying_move_3s",
    "underlying_velocity_3s",
    "pnl_5s",
    "runup_5s",
    "drawdown_5s",
    "tick_velocity_5s",
    "spread_5s",
    "depth_imbalance_5s",
    "underlying_move_5s",
    "underlying_velocity_5s",
    "counterfactual_exit_pnl_1s",
    "counterfactual_exit_pnl_3s",
    "counterfactual_exit_pnl_5s",
    "velocity_0_1s_reconstructed",
    "velocity_2_3s_reconstructed",
    "velocity_decay_ratio_3s_reconstructed",
    "burst_score_reconstructed",
    "immediate_confirmation_flag",
    "immediate_rejection_flag",
    "quote_quality_degradation_flag",
]


def parse_dt_fast(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        try:
            return pd.to_datetime(value).to_pydatetime()
        except Exception:
            return None


def safe_num(value: Any) -> float:
    if value is None or value == "":
        return np.nan
    try:
        return float(value)
    except Exception:
        return np.nan


def _nonnull_count(row: dict[str, Any]) -> int:
    count = 0
    for value in row.values():
        if value is None or value == "" or value == []:
            continue
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        count += 1
    return count


def _load_best_jsonl(pattern: str) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for file_path in glob.glob(pattern):
        with open(file_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                trade_id = obj.get("trade_id")
                if not trade_id:
                    continue
                if trade_id not in best or _nonnull_count(obj) > _nonnull_count(best[trade_id]):
                    best[trade_id] = obj
    return best


def _qsum(levels: Any) -> float:
    if not isinstance(levels, list):
        return np.nan
    total = 0.0
    ok = False
    for level in levels:
        try:
            total += float((level or {}).get("quantity"))
            ok = True
        except Exception:
            pass
    return total if ok else np.nan


def _vel_parts(records: list[tuple[datetime, float]]) -> dict[str, float] | None:
    if len(records) < 2:
        return None
    records.sort(key=lambda item: item[0])
    t0, p0 = records[0]
    t1, p1 = records[-1]
    duration = (t1 - t0).total_seconds()
    total = (p1 - p0) / duration if duration > 0 else np.nan
    midpoint = t0 + (t1 - t0) / 2
    first_half = [item for item in records if item[0] <= midpoint]
    second_half = [item for item in records if item[0] > midpoint]

    def _half_velocity(items: list[tuple[datetime, float]]) -> float:
        if len(items) < 2:
            return np.nan
        delta = (items[-1][0] - items[0][0]).total_seconds()
        return (items[-1][1] - items[0][1]) / delta if delta > 0 else np.nan

    v1 = _half_velocity(first_half)
    v2 = _half_velocity(second_half)
    return {
        "first": p0,
        "last": p1,
        "move": p1 - p0,
        "vel": total,
        "v1": v1,
        "v2": v2,
        "acc": v2 - v1 if not np.isnan(v1) and not np.isnan(v2) else np.nan,
    }


def compute_tick_features(
    path: Path,
    side: Any,
    entry_time: datetime | None,
    entry_price: float,
    need_intratrade: bool,
) -> dict[str, Any]:
    option_pre: list[tuple[datetime, float, float, float, float, float]] = []
    index_pre: list[tuple[datetime, float]] = []
    option_in: list[tuple[datetime, float, float, float, float, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            ts = parse_dt_fast(obj.get("timestamp_exchange") or obj.get("timestamp_receive"))
            if ts is None:
                continue
            ltp = safe_num(obj.get("ltp"))
            phase = obj.get("phase")
            source = obj.get("source")
            if np.isnan(ltp):
                continue
            if phase == "PRE_ENTRY":
                if source == "option":
                    bid_q = _qsum(obj.get("bid[5]"))
                    ask_q = _qsum(obj.get("ask[5]"))
                    imbalance = (
                        np.nan
                        if np.isnan(bid_q) or np.isnan(ask_q) or bid_q + ask_q <= 0
                        else (bid_q - ask_q) / (bid_q + ask_q)
                    )
                    spread = safe_num(obj.get("spread"))
                    option_pre.append((ts, ltp, spread, imbalance, bid_q, ask_q))
                elif source in {"index", "underlying"}:
                    index_pre.append((ts, ltp))
            elif need_intratrade and phase == "IN_TRADE" and source == "option":
                bid_q = _qsum(obj.get("bid[5]"))
                ask_q = _qsum(obj.get("ask[5]"))
                imbalance = (
                    np.nan
                    if np.isnan(bid_q) or np.isnan(ask_q) or bid_q + ask_q <= 0
                    else (bid_q - ask_q) / (bid_q + ask_q)
                )
                spread = safe_num(obj.get("spread"))
                option_in.append((ts, ltp, spread, imbalance, bid_q, ask_q))

    row: dict[str, Any] = {
        "has_trade_ticks": True,
        "pre_entry_option_tick_count": len(option_pre),
        "pre_entry_index_tick_count": len(index_pre),
    }

    option_parts = _vel_parts([(ts, price) for ts, price, *_ in option_pre]) if len(option_pre) >= 2 else None
    if option_parts:
        spreads = np.array([item[2] for item in option_pre], dtype=float)
        imbalances = np.array([item[3] for item in option_pre], dtype=float)
        bids = np.array([item[4] for item in option_pre], dtype=float)
        asks = np.array([item[5] for item in option_pre], dtype=float)
        row.update(
            {
                "opt_pre_ltp_first": option_parts["first"],
                "opt_pre_ltp_last": option_parts["last"],
                "opt_pre_move_5s": option_parts["move"],
                "opt_pre_velocity_5s": option_parts["vel"],
                "opt_pre_velocity_first_half": option_parts["v1"],
                "opt_pre_velocity_second_half": option_parts["v2"],
                "opt_pre_accel": option_parts["acc"],
                "opt_pre_spread_mean": np.nanmean(spreads),
                "opt_pre_spread_std": np.nanstd(spreads),
                "opt_pre_depth_imb_mean": np.nanmean(imbalances),
                "opt_pre_depth_imb_std": np.nanstd(imbalances),
                "opt_pre_bid_qty5_mean": np.nanmean(bids),
                "opt_pre_ask_qty5_mean": np.nanmean(asks),
            }
        )

    index_parts = _vel_parts(index_pre) if len(index_pre) >= 2 else None
    if index_parts:
        align = 1.0 if str(side).upper() == "CALL" else -1.0
        row.update(
            {
                "idx_pre_ltp_first": index_parts["first"],
                "idx_pre_ltp_last": index_parts["last"],
                "idx_pre_move_5s": index_parts["move"],
                "idx_pre_velocity_5s": index_parts["vel"],
                "idx_pre_velocity_first_half": index_parts["v1"],
                "idx_pre_velocity_second_half": index_parts["v2"],
                "idx_pre_accel_raw": index_parts["acc"],
                "idx_pre_move_aligned": index_parts["move"] * align,
                "idx_pre_velocity_aligned": index_parts["vel"] * align
                if not np.isnan(index_parts["vel"])
                else np.nan,
                "idx_pre_accel_aligned": index_parts["acc"] * align
                if not np.isnan(index_parts["acc"])
                else np.nan,
            }
        )

    burst_score = 0
    burst_components: dict[str, int] = {}
    accel = row.get("idx_pre_accel_aligned", np.nan)
    if not np.isnan(accel) and accel > 1.688:
        burst_score += 2
        burst_components["ind_accel_thr1"] = 2
        if accel > 3.945:
            burst_score += 1
            burst_components["ind_accel_thr2"] = 1
    option_velocity = row.get("opt_pre_velocity_5s", np.nan)
    if not np.isnan(option_velocity) and option_velocity > 1.583:
        burst_score += 1
        burst_components["opt_vel"] = 1
    imbalance = row.get("opt_pre_depth_imb_mean", np.nan)
    if not np.isnan(imbalance) and imbalance > 0.0857:
        burst_score += 1
        burst_components["depth_imb"] = 1
    index_velocity = row.get("idx_pre_velocity_aligned", np.nan)
    if not np.isnan(index_velocity) and 1.646 < index_velocity <= 2.356:
        burst_score += 1
        burst_components["ind_vel_band"] = 1
    row["burst_score_reconstructed"] = burst_score
    row["burst_score_components"] = json.dumps(burst_components, sort_keys=True)

    if not need_intratrade or entry_time is None or np.isnan(entry_price) or not option_in:
        return row

    option_in.sort(key=lambda item: item[0])
    prices = [item[1] for item in option_in]
    times = [item[0] for item in option_in]
    cursor = 0
    for checkpoint in _CHECKPOINTS:
        tag = str(checkpoint).replace(".", "p")
        target_ts = entry_time + timedelta(seconds=checkpoint)
        while cursor + 1 < len(times) and times[cursor + 1] <= target_ts:
            cursor += 1
        selected_index = cursor if times and times[0] <= target_ts else -1
        row[f"ckpt_{tag}_available"] = selected_index >= 0
        if selected_index < 0:
            continue
        point = option_in[selected_index]
        values = prices[: selected_index + 1]
        row[f"pnl_{tag}s"] = point[1] - entry_price
        row[f"runup_{tag}s"] = max(values) - entry_price
        row[f"drawdown_{tag}s"] = min(values) - entry_price
        row[f"spread_{tag}s"] = point[2]
        row[f"depth_imbalance_{tag}s"] = point[3]
        row[f"num_price_changes_{tag}s"] = len(set(values)) - 1

    def _price_before(target_ts: datetime) -> float:
        last = np.nan
        for ts, price, *_ in option_in:
            if ts <= target_ts:
                last = price
            else:
                break
        return last

    price_0 = _price_before(entry_time)
    price_1 = _price_before(entry_time + timedelta(seconds=1))
    price_2 = _price_before(entry_time + timedelta(seconds=2))
    price_3 = _price_before(entry_time + timedelta(seconds=3))
    velocity_01 = (price_1 - price_0) if not np.isnan(price_0) and not np.isnan(price_1) else np.nan
    velocity_23 = (price_3 - price_2) if not np.isnan(price_2) and not np.isnan(price_3) else np.nan
    row["velocity_0_1s_reconstructed"] = velocity_01
    row["velocity_2_3s_reconstructed"] = velocity_23
    row["velocity_decay_ratio_3s_reconstructed"] = (
        velocity_23 / velocity_01
        if not np.isnan(velocity_01) and velocity_01 != 0 and not np.isnan(velocity_23)
        else np.nan
    )
    return row


def _combine_first_numeric(df: pd.DataFrame, left: str, right: str) -> pd.Series:
    left_series = pd.to_numeric(df[left], errors="coerce") if left in df.columns else pd.Series(np.nan, index=df.index)
    right_series = pd.to_numeric(df[right], errors="coerce") if right in df.columns else pd.Series(np.nan, index=df.index)
    return left_series.combine_first(right_series)


def build_canonical_ml_dataset(repo_root: Path, analysis_dir: Path | None = None) -> pd.DataFrame:
    analysis_root = analysis_dir if analysis_dir is not None else repo_root / "analysis"
    best_enriched = _load_best_jsonl(str(repo_root / "logs" / "trades" / "*.trades_enriched.jsonl"))

    inventory_path = analysis_root / "reconciled_trade_inventory.csv"
    early_path = analysis_root / "early_path_features.csv"
    inventory = pd.read_csv(inventory_path, low_memory=False) if inventory_path.exists() else pd.DataFrame()
    early = pd.read_csv(early_path, low_memory=False) if early_path.exists() else pd.DataFrame()
    inv_by_id = {row["trade_id"]: row for _, row in inventory.iterrows()} if "trade_id" in inventory.columns else {}
    early_by_id = {row["trade_id"]: row for _, row in early.iterrows()} if "trade_id" in early.columns else {}
    all_ids = sorted(set(best_enriched) | set(inv_by_id) | set(early_by_id))

    trade_tick_index: dict[str, Path] = {}
    trade_ticks_root = repo_root / "logs" / "trade_ticks"
    if trade_ticks_root.exists():
        for day_dir in trade_ticks_root.glob("*"):
            if not day_dir.is_dir():
                continue
            for file_path in day_dir.glob("*.jsonl"):
                with file_path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        trade_tick_index[json.loads(line)["trade_id"]] = file_path
                        break

    rows: list[dict[str, Any]] = []
    for trade_id in all_ids:
        enriched = best_enriched.get(trade_id, {})
        inv = inv_by_id.get(trade_id)
        ep = early_by_id.get(trade_id)
        row: dict[str, Any] = {
            "trade_id": trade_id,
            "source_has_enriched": trade_id in best_enriched,
            "source_has_inventory": trade_id in inv_by_id,
            "source_has_early_path": trade_id in early_by_id,
            "source_has_trade_ticks": trade_id in trade_tick_index,
        }

        for key in ["symbol", "signal_kind", "side"]:
            value = enriched.get(key)
            if (value is None or value == "") and inv is not None and key in inv.index and pd.notna(inv[key]):
                value = inv[key]
            if (value is None or value == "") and ep is not None and key in ep.index and pd.notna(ep[key]):
                value = ep[key]
            row[key] = value

        enriched_dt = parse_dt_fast(enriched.get("entry_fill_time") or enriched.get("signal_time")) if enriched else None
        row["date"] = (
            enriched_dt.date().isoformat()
            if enriched_dt
            else (
                str(inv["date"])
                if inv is not None and "date" in inv.index
                else (str(ep["date"]) if ep is not None and "date" in ep.index else None)
            )
        )
        row["data_patch_era"] = "post_1s3s_patch" if row["date"] and str(row["date"]) >= "2026-04-13" else "pre_1s3s_patch"

        def _from_sources(fields: list[str]) -> Any:
            for field in fields:
                if field in enriched and enriched.get(field) not in [None, ""]:
                    return enriched.get(field)
                if inv is not None and field in inv.index and pd.notna(inv[field]):
                    return inv[field]
                if ep is not None and field in ep.index and pd.notna(ep[field]):
                    return ep[field]
            return None

        for output_name, input_names in [
            ("entry_time", ["entry_fill_time", "entry_time"]),
            ("exit_time", ["exit_fill_time", "exit_time"]),
            ("signal_time", ["signal_time"]),
            ("source_candle_start", ["source_candle_start"]),
            ("trigger_price", ["trigger_price"]),
            ("entry_price", ["entry_price"]),
            ("exit_price", ["exit_price"]),
            ("gross_pnl", ["gross_pnl"]),
            ("net_pnl", ["net_pnl"]),
            ("charges", ["charges"]),
            ("exit_reason", ["closing_reason", "exit_reason"]),
            ("holding_seconds", ["holding_seconds", "hold_seconds"]),
            ("mfe", ["mfe"]),
            ("mae", ["mae"]),
            ("entry_spread", ["entry_spread"]),
            ("exit_spread", ["exit_spread"]),
            ("entry_slippage_points", ["entry_slippage_points"]),
            ("exit_slippage_points", ["exit_slippage_points"]),
            ("underlying_spot_at_entry", ["underlying_spot_at_entry"]),
            ("target_points_used", ["target_points_used"]),
            ("hard_stop_points_used", ["hard_stop_points_used"]),
            ("fragile", ["fragile"]),
            ("pre_or_post_1pm", ["pre_or_post_1pm"]),
            ("continuation_or_reversal", ["continuation_or_reversal"]),
            ("call_or_put", ["call_or_put"]),
            ("summary_version", ["summary_version"]),
            ("post_exit_points_best_recovery", ["post_exit_points_best_recovery"]),
            ("post_exit_points_worst_further_loss", ["post_exit_points_worst_further_loss"]),
            ("post_exit_recovered_above_exit", ["post_exit_recovered_above_exit"]),
            ("post_exit_final_delta_15s", ["post_exit_final_delta_15s"]),
            ("first_move_direction", ["first_move_direction"]),
            ("first_positive_seconds", ["first_positive_seconds"]),
            ("first_negative_seconds", ["first_negative_seconds"]),
            ("time_to_plus_1", ["time_to_plus_1"]),
            ("time_to_plus_2", ["time_to_plus_2"]),
            ("time_to_minus_1", ["time_to_minus_1"]),
            ("time_to_minus_3", ["time_to_minus_3"]),
            ("time_to_minus_5", ["time_to_minus_5"]),
        ]:
            row[output_name] = _from_sources(input_names)

        if ep is not None:
            for column in _EARLY_FEATURE_COLUMNS:
                if column in ep.index:
                    row[column] = ep[column]

        if trade_id in trade_tick_index:
            need_intratrade = not row["source_has_early_path"]
            row.update(
                compute_tick_features(
                    trade_tick_index[trade_id],
                    row["side"],
                    parse_dt_fast(row["entry_time"]),
                    safe_num(row["entry_price"]),
                    bool(need_intratrade),
                )
            )

        gross = safe_num(row.get("gross_pnl"))
        recovery = safe_num(row.get("post_exit_points_best_recovery"))
        row["label_bad_trade"] = bool((not np.isnan(gross) and gross <= 0) or row.get("exit_reason") in _BAD_REASONS)
        row["label_target_bucket"] = (
            "bad_trade"
            if row["label_bad_trade"]
            else (
                "unknown"
                if np.isnan(recovery)
                else ("keep_3" if recovery < 2.0 else ("extend_to_5" if recovery < 4.0 else "extend_to_7"))
            )
        )
        row["has_post_exit_recovery"] = not np.isnan(recovery)
        row["has_pre_entry_microburst_features"] = not np.isnan(safe_num(row.get("burst_score_reconstructed")))
        row["ml_ready_entry_features"] = bool(
            row["source_has_trade_ticks"]
            and row["has_pre_entry_microburst_features"]
            and parse_dt_fast(row.get("entry_time")) is not None
            and not np.isnan(safe_num(row.get("entry_price")))
        )
        row["ml_ready_target_label"] = bool(row["label_target_bucket"] != "unknown")
        rows.append(row)

    canonical = pd.DataFrame(rows)
    if canonical.empty:
        return canonical

    canonical["date_sort"] = pd.to_datetime(canonical["date"], errors="coerce")
    canonical = canonical.sort_values(["date_sort", "trade_id"]).drop(columns=["date_sort"]).reset_index(drop=True)

    for column in [
        "gross_pnl",
        "net_pnl",
        "holding_seconds",
        "post_exit_points_best_recovery",
        "post_exit_final_delta_15s",
        "burst_score_reconstructed",
        "counterfactual_exit_pnl_1s",
        "counterfactual_exit_pnl_3s",
        "pnl_0p25s",
        "pnl_0p5s",
        "pnl_1s",
        "pnl_1p0s",
        "runup_1s",
        "runup_1p0s",
        "drawdown_1s",
        "drawdown_1p0s",
        "pnl_3s",
        "pnl_3p0s",
        "runup_3s",
        "runup_3p0s",
        "drawdown_3s",
        "drawdown_3p0s",
        "tick_velocity_1s",
        "tick_velocity_3s",
        "velocity_0_1s_reconstructed",
        "velocity_2_3s_reconstructed",
        "time_to_plus_1",
        "time_to_plus_2",
    ]:
        if column in canonical.columns:
            canonical[column] = pd.to_numeric(canonical[column], errors="coerce")

    canonical["feat_pnl_1s"] = _combine_first_numeric(canonical, "pnl_1s", "pnl_1p0s")
    canonical["feat_runup_1s"] = _combine_first_numeric(canonical, "runup_1s", "runup_1p0s")
    canonical["feat_drawdown_1s"] = _combine_first_numeric(canonical, "drawdown_1s", "drawdown_1p0s")
    canonical["feat_pnl_3s"] = _combine_first_numeric(canonical, "pnl_3s", "pnl_3p0s")
    canonical["feat_runup_3s"] = _combine_first_numeric(canonical, "runup_3s", "runup_3p0s")
    canonical["feat_drawdown_3s"] = _combine_first_numeric(canonical, "drawdown_3s", "drawdown_3p0s")

    preferred_ratio = _combine_first_numeric(canonical, "tick_velocity_3s", "tick_velocity_3s")
    preferred_denom = _combine_first_numeric(canonical, "tick_velocity_1s", "tick_velocity_1s")
    fallback_num = _combine_first_numeric(canonical, "velocity_2_3s_reconstructed", "velocity_2_3s_reconstructed")
    fallback_denom = _combine_first_numeric(canonical, "velocity_0_1s_reconstructed", "velocity_0_1s_reconstructed")
    canonical["feat_velocity_decay_ratio"] = np.where(
        preferred_denom.notna() & (preferred_denom != 0) & preferred_ratio.notna(),
        preferred_ratio / preferred_denom,
        np.where(
            fallback_denom.notna() & (fallback_denom != 0) & fallback_num.notna(),
            fallback_num / fallback_denom,
            np.nan,
        ),
    )

    canonical["current_bucket"] = np.where(
        pd.to_numeric(canonical["burst_score_reconstructed"], errors="coerce") >= 5.0,
        "extend_to_7",
        "keep_3",
    )
    canonical["actual_points"] = pd.to_numeric(canonical["gross_pnl"], errors="coerce") / 500.0
    canonical["best_possible_points"] = canonical["actual_points"] + pd.to_numeric(
        canonical["post_exit_points_best_recovery"], errors="coerce"
    )
    canonical["fallback_hold_points"] = canonical["actual_points"] + pd.to_numeric(
        canonical["post_exit_final_delta_15s"], errors="coerce"
    )
    canonical["exit_cut_points_1s"] = _combine_first_numeric(canonical, "counterfactual_exit_pnl_1s", "feat_pnl_1s")
    canonical["exit_cut_points_3s"] = _combine_first_numeric(canonical, "counterfactual_exit_pnl_3s", "feat_pnl_3s")
    canonical["trade_alive_at_1s"] = pd.to_numeric(canonical["holding_seconds"], errors="coerce") >= 1.0
    canonical["trade_alive_at_3s"] = pd.to_numeric(canonical["holding_seconds"], errors="coerce") >= 3.0

    for numeric_column in PRE_ENTRY_NUMERIC_FEATURES + BAD_EXIT_1S_NUMERIC_FEATURES + BAD_EXIT_3S_NUMERIC_FEATURES + TARGET_SHADOW_NUMERIC_FEATURES + [
        "exit_cut_points_1s",
        "exit_cut_points_3s",
        "actual_points",
        "best_possible_points",
        "fallback_hold_points",
    ]:
        if numeric_column in canonical.columns:
            canonical[numeric_column] = pd.to_numeric(canonical[numeric_column], errors="coerce")

    return canonical


def build_ml_dataset_views(canonical: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if canonical.empty:
        return {
            "entry_filter": canonical.copy(),
            "bad_trade_exit_1s": canonical.copy(),
            "bad_trade_exit_3s": canonical.copy(),
            "target_promotion_live": canonical.copy(),
            "target_promotion_shadow": canonical.copy(),
        }

    entry_keep_columns = [
        "trade_id",
        "date",
        "symbol",
        "signal_kind",
        "side",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "gross_pnl",
        "net_pnl",
        "holding_seconds",
        "exit_reason",
        "pre_or_post_1pm",
        "continuation_or_reversal",
        "call_or_put",
        "burst_score_reconstructed",
        "label_bad_trade",
        "label_target_bucket",
        "ml_ready_entry_features",
        "ml_ready_target_label",
        "current_bucket",
        "actual_points",
        "best_possible_points",
        "fallback_hold_points",
        "trade_alive_at_1s",
        "trade_alive_at_3s",
        "exit_cut_points_1s",
        "exit_cut_points_3s",
    ] + PRE_ENTRY_NUMERIC_FEATURES + PRE_ENTRY_CATEGORICAL_FEATURES
    entry_keep_columns = [column for column in dict.fromkeys(entry_keep_columns) if column in canonical.columns]

    entry_view = canonical.loc[canonical["ml_ready_entry_features"].fillna(False), entry_keep_columns].copy()
    entry_view["label_entry_keep"] = (~entry_view["label_bad_trade"].astype(bool)).astype(int)
    entry_view["label_bad_trade_int"] = entry_view["label_bad_trade"].astype(int)

    exit_keep_columns = [
        "trade_id",
        "date",
        "symbol",
        "signal_kind",
        "side",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "gross_pnl",
        "net_pnl",
        "holding_seconds",
        "exit_reason",
        "pre_or_post_1pm",
        "continuation_or_reversal",
        "call_or_put",
        "burst_score_reconstructed",
        "label_bad_trade",
        "label_target_bucket",
        "ml_ready_entry_features",
        "ml_ready_target_label",
        "current_bucket",
        "actual_points",
        "best_possible_points",
        "fallback_hold_points",
        "trade_alive_at_1s",
        "trade_alive_at_3s",
        "exit_cut_points_1s",
        "exit_cut_points_3s",
    ] + BAD_EXIT_1S_NUMERIC_FEATURES + BAD_EXIT_3S_NUMERIC_FEATURES + PRE_ENTRY_CATEGORICAL_FEATURES
    exit_keep_columns = [column for column in dict.fromkeys(exit_keep_columns) if column in canonical.columns]

    exit_base_view = canonical.loc[canonical["ml_ready_entry_features"].fillna(False), exit_keep_columns].copy()

    exit_1s_view = exit_base_view.loc[exit_base_view["trade_alive_at_1s"].fillna(False)].copy()
    exit_1s_view["label_exit_bad_trade"] = exit_1s_view["label_bad_trade"].astype(int)
    exit_1s_view["checkpoint"] = "1s"

    exit_3s_view = exit_base_view.loc[exit_base_view["trade_alive_at_3s"].fillna(False)].copy()
    exit_3s_view["label_exit_bad_trade"] = exit_3s_view["label_bad_trade"].astype(int)
    exit_3s_view["checkpoint"] = "3s"

    target_live_view = entry_view.copy()
    target_live_view["target_live_trainable"] = (
        (~target_live_view["label_bad_trade"].astype(bool))
        & target_live_view["label_target_bucket"].isin(TARGET_CLASS_ORDER)
    )

    target_shadow_view = canonical.loc[canonical["ml_ready_target_label"].fillna(False)].copy()
    target_shadow_view["target_shadow_trainable"] = (
        (~target_shadow_view["label_bad_trade"].astype(bool))
        & target_shadow_view["label_target_bucket"].isin(TARGET_CLASS_ORDER)
    )

    return {
        "entry_filter": entry_view,
        "bad_trade_exit_1s": exit_1s_view,
        "bad_trade_exit_3s": exit_3s_view,
        "target_promotion_live": target_live_view,
        "target_promotion_shadow": target_shadow_view,
    }


def write_ml_datasets(
    repo_root: Path,
    output_dir: Path,
    *,
    analysis_dir: Path | None = None,
) -> dict[str, Path]:
    ensure_dir(output_dir)
    canonical = build_canonical_ml_dataset(repo_root=repo_root, analysis_dir=analysis_dir)
    views = build_ml_dataset_views(canonical)

    canonical_path = output_dir / ML_DATASET_FILENAMES["canonical"]
    canonical.to_csv(canonical_path, index=False)

    dictionary_rows: list[dict[str, Any]] = []
    for column in canonical.columns:
        series = canonical[column]
        non_null = series.dropna()
        dictionary_rows.append(
            {
                "column": column,
                "non_null_count": int(series.notna().sum()),
                "dtype": str(series.dtype),
                "example": None if non_null.empty else str(non_null.iloc[0])[:140],
            }
        )
    dictionary_path = output_dir / ML_DATASET_FILENAMES["dictionary"]
    pd.DataFrame(dictionary_rows).to_csv(dictionary_path, index=False)

    coverage_path = output_dir / ML_DATASET_FILENAMES["coverage"]
    pd.DataFrame(
        [
            {
                "rows_total": int(len(canonical)),
                "unique_trade_ids": int(canonical["trade_id"].nunique()) if not canonical.empty else 0,
                "date_min": canonical["date"].min() if not canonical.empty else None,
                "date_max": canonical["date"].max() if not canonical.empty else None,
                "source_has_enriched": int(canonical["source_has_enriched"].sum()) if "source_has_enriched" in canonical else 0,
                "source_has_inventory": int(canonical["source_has_inventory"].sum()) if "source_has_inventory" in canonical else 0,
                "source_has_early_path": int(canonical["source_has_early_path"].sum()) if "source_has_early_path" in canonical else 0,
                "source_has_trade_ticks": int(canonical["source_has_trade_ticks"].sum()) if "source_has_trade_ticks" in canonical else 0,
                "has_post_exit_recovery": int(canonical["has_post_exit_recovery"].sum()) if "has_post_exit_recovery" in canonical else 0,
                "ml_ready_entry_features": int(canonical["ml_ready_entry_features"].sum()) if "ml_ready_entry_features" in canonical else 0,
                "ml_ready_target_label": int(canonical["ml_ready_target_label"].sum()) if "ml_ready_target_label" in canonical else 0,
                "bad_trade_count": int(canonical["label_bad_trade"].sum()) if "label_bad_trade" in canonical else 0,
            }
        ]
    ).to_csv(coverage_path, index=False)

    datewise_path = output_dir / ML_DATASET_FILENAMES["datewise_coverage"]
    (
        canonical.groupby("date")
        .agg(
            trades=("trade_id", "count"),
            enriched=("source_has_enriched", "sum"),
            inventory=("source_has_inventory", "sum"),
            early_path=("source_has_early_path", "sum"),
            trade_ticks=("source_has_trade_ticks", "sum"),
            post_exit_recovery=("has_post_exit_recovery", "sum"),
            ml_ready_entry=("ml_ready_entry_features", "sum"),
            ml_ready_target=("ml_ready_target_label", "sum"),
            bad_trades=("label_bad_trade", "sum"),
        )
        .reset_index()
        .to_csv(datewise_path, index=False)
    )

    output_paths: dict[str, Path] = {
        "canonical": canonical_path,
        "dictionary": dictionary_path,
        "coverage": coverage_path,
        "datewise_coverage": datewise_path,
    }
    for key, frame in views.items():
        path = output_dir / ML_DATASET_FILENAMES[key]
        frame.to_csv(path, index=False)
        output_paths[key] = path
    return output_paths
