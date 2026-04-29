from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .ml_dataset import TARGET_CLASS_ORDER

TARGET_POINTS_BY_BUCKET = {"keep_3": 3.0, "extend_to_5": 5.0, "extend_to_7": 7.0}


@dataclass
class PolicyEvaluationResult:
    layer_name: str
    model_name: str
    per_trade: pd.DataFrame
    daywise: pd.DataFrame
    summary: dict[str, Any]


def _safe_numeric(series: pd.Series | Any, index: pd.Index) -> pd.Series:
    if isinstance(series, pd.Series):
        return pd.to_numeric(series, errors="coerce")
    return pd.Series(series, index=index, dtype="float64")


def _with_date_strings(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["date_str"] = out["date"].dt.strftime("%Y-%m-%d")
    return out


def _summarise_daywise(
    frame: pd.DataFrame,
    *,
    baseline_col: str,
    policy_col: str,
) -> pd.DataFrame:
    grouped = (
        frame.groupby("date_str", dropna=False)
        .agg(
            trade_count=("trade_id", "count"),
            baseline_pnl=(baseline_col, "sum"),
            policy_pnl=(policy_col, "sum"),
        )
        .reset_index()
        .rename(columns={"date_str": "date"})
    )
    grouped["delta_pnl"] = grouped["policy_pnl"] - grouped["baseline_pnl"]
    return grouped.sort_values("date").reset_index(drop=True)


def simulate_target_policy_points(
    frame: pd.DataFrame,
    bucket_col: str,
) -> pd.Series:
    target_points = frame[bucket_col].map(TARGET_POINTS_BY_BUCKET).astype("float64")
    best_possible = pd.to_numeric(frame.get("best_possible_points"), errors="coerce")
    fallback_hold = pd.to_numeric(frame.get("fallback_hold_points"), errors="coerce")

    simulated = pd.Series(np.nan, index=frame.index, dtype="float64")
    valid = target_points.notna() & best_possible.notna() & fallback_hold.notna()
    achievable = valid & (best_possible >= target_points)
    fallback = valid & ~achievable
    simulated.loc[achievable] = target_points.loc[achievable]
    simulated.loc[fallback] = np.minimum(fallback_hold.loc[fallback], target_points.loc[fallback])
    return simulated


def evaluate_entry_filter_policy(predictions: pd.DataFrame, *, model_name: str) -> PolicyEvaluationResult:
    frame = _with_date_strings(predictions)
    frame["baseline_pnl"] = pd.to_numeric(frame.get("gross_pnl"), errors="coerce").fillna(0.0)
    frame["accepted_trade"] = frame["predicted_prob_bad"] < frame["threshold_used"]
    frame["policy_pnl"] = np.where(frame["accepted_trade"], frame["baseline_pnl"], 0.0)
    frame["delta_pnl"] = frame["policy_pnl"] - frame["baseline_pnl"]

    baseline_bad_rate = float(pd.to_numeric(frame.get("label_bad_trade"), errors="coerce").fillna(0).mean())
    accepted_mask = frame["accepted_trade"]
    accepted_bad_rate = (
        float(pd.to_numeric(frame.loc[accepted_mask, "label_bad_trade"], errors="coerce").fillna(0).mean())
        if accepted_mask.any()
        else np.nan
    )
    non_bad_mask = pd.to_numeric(frame.get("label_bad_trade"), errors="coerce").fillna(0).astype(int) == 0
    baseline_non_bad_pnl = float(frame.loc[non_bad_mask, "baseline_pnl"].sum())
    policy_non_bad_pnl = float(frame.loc[non_bad_mask, "policy_pnl"].sum())
    daywise = _summarise_daywise(frame, baseline_col="baseline_pnl", policy_col="policy_pnl")

    summary = {
        "model": model_name,
        "baseline_trade_count": int(len(frame)),
        "accepted_trade_count": int(frame["accepted_trade"].sum()),
        "retained_trade_ratio": float(frame["accepted_trade"].mean()) if len(frame) else np.nan,
        "baseline_bad_trade_rate": baseline_bad_rate,
        "accepted_bad_trade_rate": accepted_bad_rate,
        "bad_trade_rate_reduction": (
            (baseline_bad_rate - accepted_bad_rate) / max(baseline_bad_rate, 1e-9)
            if pd.notna(accepted_bad_rate)
            else np.nan
        ),
        "baseline_total_pnl": float(frame["baseline_pnl"].sum()),
        "policy_total_pnl": float(frame["policy_pnl"].sum()),
        "delta_vs_baseline_pnl": float(frame["delta_pnl"].sum()),
        "retained_non_bad_gross_pnl_ratio": policy_non_bad_pnl / max(abs(baseline_non_bad_pnl), 1.0),
        "positive_day_ratio": float((daywise["delta_pnl"] > 0).mean()) if not daywise.empty else np.nan,
        "worst_day_delta_pnl": float(daywise["delta_pnl"].min()) if not daywise.empty else np.nan,
    }
    return PolicyEvaluationResult(
        layer_name="entry_filter",
        model_name=model_name,
        per_trade=frame,
        daywise=daywise,
        summary=summary,
    )


def evaluate_bad_trade_exit_policy(predictions: pd.DataFrame, *, model_name: str) -> PolicyEvaluationResult:
    frame = _with_date_strings(predictions)
    frame["baseline_pnl"] = pd.to_numeric(frame.get("gross_pnl"), errors="coerce").fillna(0.0)
    frame["exit_cut_points"] = pd.to_numeric(frame.get("exit_cut_points"), errors="coerce")
    frame["exit_trade"] = frame["predicted_prob_bad"] >= frame["threshold_used"]
    frame["policy_pnl"] = np.where(
        frame["exit_trade"] & frame["exit_cut_points"].notna(),
        frame["exit_cut_points"] * 500.0,
        frame["baseline_pnl"],
    )
    frame["delta_pnl"] = frame["policy_pnl"] - frame["baseline_pnl"]
    frame["label_bad_trade"] = pd.to_numeric(frame.get("label_bad_trade"), errors="coerce").fillna(0).astype(int)

    bad_mask = frame["label_bad_trade"] == 1
    non_bad_mask = frame["label_bad_trade"] == 0
    baseline_bad_loss = float(-np.minimum(frame.loc[bad_mask, "baseline_pnl"], 0.0).sum())
    policy_bad_loss = float(-np.minimum(frame.loc[bad_mask, "policy_pnl"], 0.0).sum())
    baseline_non_bad_pnl = float(frame.loc[non_bad_mask, "baseline_pnl"].sum())
    policy_non_bad_pnl = float(frame.loc[non_bad_mask, "policy_pnl"].sum())
    winner_giveback = max(baseline_non_bad_pnl - policy_non_bad_pnl, 0.0)
    daywise = _summarise_daywise(frame, baseline_col="baseline_pnl", policy_col="policy_pnl")

    summary = {
        "model": model_name,
        "baseline_total_pnl": float(frame["baseline_pnl"].sum()),
        "policy_total_pnl": float(frame["policy_pnl"].sum()),
        "delta_vs_baseline_pnl": float(frame["delta_pnl"].sum()),
        "exit_rate": float(frame["exit_trade"].mean()) if len(frame) else np.nan,
        "baseline_bad_loss": baseline_bad_loss,
        "policy_bad_loss": policy_bad_loss,
        "bad_loss_reduction": (baseline_bad_loss - policy_bad_loss) / max(baseline_bad_loss, 1.0),
        "winner_giveback_ratio": winner_giveback / max(abs(baseline_non_bad_pnl), 1.0),
        "positive_day_ratio": float((daywise["delta_pnl"] > 0).mean()) if not daywise.empty else np.nan,
        "worst_day_delta_pnl": float(daywise["delta_pnl"].min()) if not daywise.empty else np.nan,
    }
    return PolicyEvaluationResult(
        layer_name="bad_trade_exit",
        model_name=model_name,
        per_trade=frame,
        daywise=daywise,
        summary=summary,
    )


def evaluate_target_promotion_policy(predictions: pd.DataFrame, *, model_name: str) -> PolicyEvaluationResult:
    frame = _with_date_strings(predictions)
    frame["current_policy_points"] = simulate_target_policy_points(frame, "current_bucket")
    frame["model_policy_points"] = simulate_target_policy_points(frame, "predicted_bucket")
    frame["baseline_pnl"] = frame["current_policy_points"] * 500.0
    frame["policy_pnl"] = frame["model_policy_points"] * 500.0
    frame["delta_pnl"] = frame["policy_pnl"] - frame["baseline_pnl"]
    frame["target_points_current"] = frame["current_bucket"].map(TARGET_POINTS_BY_BUCKET).astype("float64")
    frame["target_points_model"] = frame["predicted_bucket"].map(TARGET_POINTS_BY_BUCKET).astype("float64")
    frame["is_promotion"] = frame["target_points_model"] > frame["target_points_current"]
    frame["promotion_gain_pnl"] = np.where(
        frame["is_promotion"] & (frame["delta_pnl"] > 0),
        frame["delta_pnl"],
        0.0,
    )
    frame["promotion_loss_pnl"] = np.where(
        frame["is_promotion"] & (frame["delta_pnl"] < 0),
        -frame["delta_pnl"],
        0.0,
    )
    daywise = _summarise_daywise(frame, baseline_col="baseline_pnl", policy_col="policy_pnl")

    summary = {
        "model": model_name,
        "baseline_total_pnl": float(frame["baseline_pnl"].sum(skipna=True)),
        "policy_total_pnl": float(frame["policy_pnl"].sum(skipna=True)),
        "delta_vs_baseline_pnl": float(frame["delta_pnl"].sum(skipna=True)),
        "positive_day_ratio": float((daywise["delta_pnl"] > 0).mean()) if not daywise.empty else np.nan,
        "over_promotion_losses": float(frame["promotion_loss_pnl"].sum(skipna=True)),
        "runner_capture_gains": float(frame["promotion_gain_pnl"].sum(skipna=True)),
        "worst_day_delta_pnl": float(daywise["delta_pnl"].min()) if not daywise.empty else np.nan,
    }
    return PolicyEvaluationResult(
        layer_name="target_promotion",
        model_name=model_name,
        per_trade=frame,
        daywise=daywise,
        summary=summary,
    )


def evaluate_bad_trade_exit_stack(
    canonical_eval_frame: pd.DataFrame,
    *,
    exit_1s_predictions: pd.DataFrame,
    exit_3s_predictions: pd.DataFrame,
    selected_model_name: str,
) -> PolicyEvaluationResult:
    base = _with_date_strings(canonical_eval_frame)
    base["baseline_pnl"] = pd.to_numeric(base.get("gross_pnl"), errors="coerce").fillna(0.0)

    def _selected(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
        selected = frame.loc[
            frame["model"] == selected_model_name,
            ["trade_id", "predicted_prob_bad", "threshold_used", "predicted_bad_trade"],
        ].copy()
        return selected.rename(
            columns={
                "predicted_prob_bad": f"{prefix}predicted_prob_bad",
                "threshold_used": f"{prefix}threshold_used",
                "predicted_bad_trade": f"{prefix}predicted_bad_trade",
            }
        )

    audit = base.merge(_selected(exit_1s_predictions, "exit1_"), on="trade_id", how="left")
    audit = audit.merge(_selected(exit_3s_predictions, "exit3_"), on="trade_id", how="left")
    audit["exit1_fire"] = (
        audit["trade_alive_at_1s"].fillna(False)
        & audit["exit1_predicted_prob_bad"].notna()
        & (audit["exit1_predicted_prob_bad"] >= audit["exit1_threshold_used"])
    )
    audit["exit3_fire"] = (
        ~audit["exit1_fire"]
        & audit["trade_alive_at_3s"].fillna(False)
        & audit["exit3_predicted_prob_bad"].notna()
        & (audit["exit3_predicted_prob_bad"] >= audit["exit3_threshold_used"])
    )
    exit_1s_pnl = np.where(
        pd.to_numeric(audit.get("exit_cut_points_1s"), errors="coerce").notna(),
        pd.to_numeric(audit.get("exit_cut_points_1s"), errors="coerce") * 500.0,
        audit["baseline_pnl"],
    )
    exit_3s_pnl = np.where(
        pd.to_numeric(audit.get("exit_cut_points_3s"), errors="coerce").notna(),
        pd.to_numeric(audit.get("exit_cut_points_3s"), errors="coerce") * 500.0,
        audit["baseline_pnl"],
    )
    audit["policy_pnl"] = np.select(
        [audit["exit1_fire"], audit["exit3_fire"]],
        [exit_1s_pnl, exit_3s_pnl],
        default=audit["baseline_pnl"],
    )
    audit["delta_pnl"] = audit["policy_pnl"] - audit["baseline_pnl"]
    audit["label_bad_trade"] = pd.to_numeric(audit.get("label_bad_trade"), errors="coerce").fillna(0).astype(int)
    daywise = _summarise_daywise(audit, baseline_col="baseline_pnl", policy_col="policy_pnl")

    bad_mask = audit["label_bad_trade"] == 1
    non_bad_mask = audit["label_bad_trade"] == 0
    baseline_bad_loss = float(-np.minimum(audit.loc[bad_mask, "baseline_pnl"], 0.0).sum())
    policy_bad_loss = float(-np.minimum(audit.loc[bad_mask, "policy_pnl"], 0.0).sum())
    baseline_non_bad_pnl = float(audit.loc[non_bad_mask, "baseline_pnl"].sum())
    policy_non_bad_pnl = float(audit.loc[non_bad_mask, "policy_pnl"].sum())
    winner_giveback = max(baseline_non_bad_pnl - policy_non_bad_pnl, 0.0)

    summary = {
        "model": selected_model_name,
        "baseline_total_pnl": float(audit["baseline_pnl"].sum()),
        "policy_total_pnl": float(audit["policy_pnl"].sum()),
        "delta_vs_baseline_pnl": float(audit["delta_pnl"].sum()),
        "exit_rate_1s": float(audit["exit1_fire"].mean()) if len(audit) else np.nan,
        "exit_rate_3s": float(audit["exit3_fire"].mean()) if len(audit) else np.nan,
        "baseline_bad_loss": baseline_bad_loss,
        "policy_bad_loss": policy_bad_loss,
        "bad_loss_reduction": (baseline_bad_loss - policy_bad_loss) / max(baseline_bad_loss, 1.0),
        "winner_giveback_ratio": winner_giveback / max(abs(baseline_non_bad_pnl), 1.0),
        "positive_day_ratio": float((daywise["delta_pnl"] > 0).mean()) if not daywise.empty else np.nan,
        "worst_day_delta_pnl": float(daywise["delta_pnl"].min()) if not daywise.empty else np.nan,
    }
    return PolicyEvaluationResult(
        layer_name="bad_trade_exit_stack",
        model_name=selected_model_name,
        per_trade=audit,
        daywise=daywise,
        summary=summary,
    )


def evaluate_combined_policy(
    canonical_eval_frame: pd.DataFrame,
    *,
    entry_predictions: pd.DataFrame,
    exit_1s_predictions: pd.DataFrame,
    exit_3s_predictions: pd.DataFrame,
    target_predictions: pd.DataFrame,
    selected_entry_model_name: str,
    selected_exit_model_name: str,
    selected_target_model_name: str,
) -> PolicyEvaluationResult:
    base = _with_date_strings(canonical_eval_frame)
    base["baseline_pnl"] = pd.to_numeric(base.get("gross_pnl"), errors="coerce").fillna(0.0)

    def _join_selected(frame: pd.DataFrame, prefix: str, columns: list[str]) -> pd.DataFrame:
        model_name = {
            "entry_": selected_entry_model_name,
            "exit1_": selected_exit_model_name,
            "exit3_": selected_exit_model_name,
            "target_": selected_target_model_name,
        }[prefix]
        selected = frame.loc[frame["model"] == model_name, ["trade_id"] + columns].copy()
        rename_map = {column: f"{prefix}{column}" for column in columns}
        return selected.rename(columns=rename_map)

    audit = base.copy()
    audit = audit.merge(
        _join_selected(
            entry_predictions,
            "entry_",
            ["predicted_prob_bad", "threshold_used", "predicted_bad_trade"],
        ),
        on="trade_id",
        how="left",
    )
    audit = audit.merge(
        _join_selected(
            exit_1s_predictions,
            "exit1_",
            ["predicted_prob_bad", "threshold_used", "predicted_bad_trade"],
        ),
        on="trade_id",
        how="left",
    )
    audit = audit.merge(
        _join_selected(
            exit_3s_predictions,
            "exit3_",
            ["predicted_prob_bad", "threshold_used", "predicted_bad_trade"],
        ),
        on="trade_id",
        how="left",
    )
    audit = audit.merge(
        _join_selected(
            target_predictions,
            "target_",
            ["predicted_bucket", "predicted_confidence", "used_fallback_to_current_bucket"],
        ),
        on="trade_id",
        how="left",
    )

    audit["entry_accept"] = np.where(
        audit["entry_predicted_prob_bad"].notna(),
        audit["entry_predicted_prob_bad"] < audit["entry_threshold_used"],
        True,
    )
    audit["selected_target_bucket"] = np.where(
        audit["target_predicted_bucket"].notna(),
        audit["target_predicted_bucket"],
        audit["current_bucket"],
    )
    audit["exit1_fire"] = (
        audit["entry_accept"]
        & audit["trade_alive_at_1s"].fillna(False)
        & audit["exit1_predicted_prob_bad"].notna()
        & (audit["exit1_predicted_prob_bad"] >= audit["exit1_threshold_used"])
    )
    audit["exit3_fire"] = (
        audit["entry_accept"]
        & ~audit["exit1_fire"]
        & audit["trade_alive_at_3s"].fillna(False)
        & audit["exit3_predicted_prob_bad"].notna()
        & (audit["exit3_predicted_prob_bad"] >= audit["exit3_threshold_used"])
    )

    audit["policy_reason"] = np.select(
        [
            ~audit["entry_accept"],
            audit["exit1_fire"],
            audit["exit3_fire"],
            (pd.to_numeric(audit.get("label_bad_trade"), errors="coerce").fillna(0).astype(int) == 0),
        ],
        [
            "entry_filtered",
            "bad_exit_1s",
            "bad_exit_3s",
            "target_promotion",
        ],
        default="actual_realized",
    )

    target_policy_points = simulate_target_policy_points(audit, "selected_target_bucket")
    audit["policy_pnl"] = np.select(
        [
            ~audit["entry_accept"],
            audit["exit1_fire"],
            audit["exit3_fire"],
            pd.to_numeric(audit.get("label_bad_trade"), errors="coerce").fillna(0).astype(int) == 0,
        ],
        [
            0.0,
            np.where(
                pd.to_numeric(audit.get("exit_cut_points_1s"), errors="coerce").notna(),
                pd.to_numeric(audit.get("exit_cut_points_1s"), errors="coerce") * 500.0,
                audit["baseline_pnl"],
            ),
            np.where(
                pd.to_numeric(audit.get("exit_cut_points_3s"), errors="coerce").notna(),
                pd.to_numeric(audit.get("exit_cut_points_3s"), errors="coerce") * 500.0,
                audit["baseline_pnl"],
            ),
            target_policy_points * 500.0,
        ],
        default=audit["baseline_pnl"],
    )
    audit["delta_pnl"] = audit["policy_pnl"] - audit["baseline_pnl"]
    daywise = _summarise_daywise(audit, baseline_col="baseline_pnl", policy_col="policy_pnl")

    summary = {
        "entry_model": selected_entry_model_name,
        "exit_model": selected_exit_model_name,
        "target_model": selected_target_model_name,
        "baseline_total_pnl": float(audit["baseline_pnl"].sum()),
        "policy_total_pnl": float(audit["policy_pnl"].sum()),
        "delta_vs_baseline_pnl": float(audit["delta_pnl"].sum()),
        "accepted_trade_ratio": float(audit["entry_accept"].mean()) if len(audit) else np.nan,
        "positive_day_ratio": float((daywise["delta_pnl"] > 0).mean()) if not daywise.empty else np.nan,
        "worst_day_delta_pnl": float(daywise["delta_pnl"].min()) if not daywise.empty else np.nan,
        "last_5_day_delta_pnl": float(daywise.tail(5)["delta_pnl"].sum()) if not daywise.empty else np.nan,
        "last_5_non_negative_days": int((daywise.tail(5)["delta_pnl"] >= 0).sum()) if not daywise.empty else 0,
    }
    return PolicyEvaluationResult(
        layer_name="combined_policy",
        model_name=f"entry={selected_entry_model_name}|exit={selected_exit_model_name}|target={selected_target_model_name}",
        per_trade=audit,
        daywise=daywise,
        summary=summary,
    )


def build_live_readiness_scorecard(
    canonical_eval_frame: pd.DataFrame,
    *,
    entry_eval: PolicyEvaluationResult,
    exit_eval: PolicyEvaluationResult,
    target_eval: PolicyEvaluationResult,
    combined_eval: PolicyEvaluationResult,
    post_patch_start: str,
) -> pd.DataFrame:
    eval_frame = _with_date_strings(canonical_eval_frame)
    post_patch = eval_frame.loc[eval_frame["date"] >= pd.Timestamp(post_patch_start)].copy()
    post_patch_days = int(post_patch["date_str"].nunique()) if not post_patch.empty else 0
    entry_ready_rows = int(pd.to_numeric(post_patch.get("ml_ready_entry_features"), errors="coerce").fillna(0).sum())
    target_rows = int(
        (
            pd.to_numeric(post_patch.get("ml_ready_target_label"), errors="coerce").fillna(0).astype(bool)
            & ~pd.to_numeric(post_patch.get("label_bad_trade"), errors="coerce").fillna(0).astype(bool)
            & post_patch.get("label_target_bucket", pd.Series("", index=post_patch.index)).isin(TARGET_CLASS_ORDER)
        ).sum()
    )

    runner_capture_gains = float(target_eval.summary.get("runner_capture_gains", 0.0))
    over_promotion_losses = float(target_eval.summary.get("over_promotion_losses", 0.0))
    over_promotion_ratio = over_promotion_losses / max(runner_capture_gains, 1.0)

    rows = [
        {
            "gate": "data_post_patch_days",
            "actual": post_patch_days,
            "threshold": ">= 20",
            "passed": post_patch_days >= 20,
            "notes": "Minimum post-patch trading days for live sign-off.",
        },
        {
            "gate": "data_entry_ready_rows",
            "actual": entry_ready_rows,
            "threshold": ">= 1200",
            "passed": entry_ready_rows >= 1200,
            "notes": "Entry filter sample size gate.",
        },
        {
            "gate": "data_target_rows",
            "actual": target_rows,
            "threshold": ">= 500",
            "passed": target_rows >= 500,
            "notes": "Non-bad target-promotion sample size gate.",
        },
        {
            "gate": "entry_bad_rate_reduction",
            "actual": entry_eval.summary.get("bad_trade_rate_reduction"),
            "threshold": ">= 0.20",
            "passed": float(entry_eval.summary.get("bad_trade_rate_reduction", -1.0)) >= 0.20,
            "notes": "Accepted trades should materially reduce bad-trade incidence.",
        },
        {
            "gate": "entry_trade_retention",
            "actual": entry_eval.summary.get("retained_trade_ratio"),
            "threshold": ">= 0.60",
            "passed": float(entry_eval.summary.get("retained_trade_ratio", -1.0)) >= 0.60,
            "notes": "Avoid shrinking the strategy too much.",
        },
        {
            "gate": "entry_non_bad_pnl_retention",
            "actual": entry_eval.summary.get("retained_non_bad_gross_pnl_ratio"),
            "threshold": ">= 0.85",
            "passed": float(entry_eval.summary.get("retained_non_bad_gross_pnl_ratio", -1.0)) >= 0.85,
            "notes": "Good trade gross should mostly survive the filter.",
        },
        {
            "gate": "entry_total_pnl_delta",
            "actual": entry_eval.summary.get("delta_vs_baseline_pnl"),
            "threshold": "> 0",
            "passed": float(entry_eval.summary.get("delta_vs_baseline_pnl", 0.0)) > 0,
            "notes": "Shadow entry filter must add net PnL.",
        },
        {
            "gate": "exit_bad_loss_reduction",
            "actual": exit_eval.summary.get("bad_loss_reduction"),
            "threshold": ">= 0.25",
            "passed": float(exit_eval.summary.get("bad_loss_reduction", -1.0)) >= 0.25,
            "notes": "Bad-trade loss should reduce materially.",
        },
        {
            "gate": "exit_winner_giveback",
            "actual": exit_eval.summary.get("winner_giveback_ratio"),
            "threshold": "<= 0.10",
            "passed": float(exit_eval.summary.get("winner_giveback_ratio", 1.0)) <= 0.10,
            "notes": "Do not kill too much winner gross.",
        },
        {
            "gate": "exit_total_pnl_delta",
            "actual": exit_eval.summary.get("delta_vs_baseline_pnl"),
            "threshold": "> 0",
            "passed": float(exit_eval.summary.get("delta_vs_baseline_pnl", 0.0)) > 0,
            "notes": "Exit layer must add net PnL.",
        },
        {
            "gate": "exit_worst_day",
            "actual": exit_eval.summary.get("worst_day_delta_pnl"),
            "threshold": ">= -10000",
            "passed": float(exit_eval.summary.get("worst_day_delta_pnl", -1e12)) >= -10000.0,
            "notes": "Single-day underperformance guardrail.",
        },
        {
            "gate": "target_total_pnl_delta",
            "actual": target_eval.summary.get("delta_vs_baseline_pnl"),
            "threshold": "> 0",
            "passed": float(target_eval.summary.get("delta_vs_baseline_pnl", 0.0)) > 0,
            "notes": "Promotion layer must improve total counterfactual PnL.",
        },
        {
            "gate": "target_positive_day_ratio",
            "actual": target_eval.summary.get("positive_day_ratio"),
            "threshold": ">= 0.60",
            "passed": float(target_eval.summary.get("positive_day_ratio", -1.0)) >= 0.60,
            "notes": "Promotion gains should be broad, not one-day only.",
        },
        {
            "gate": "target_over_promotion_ratio",
            "actual": over_promotion_ratio,
            "threshold": "<= 0.40",
            "passed": over_promotion_ratio <= 0.40,
            "notes": "Over-promotion losses should stay well below runner gains.",
        },
        {
            "gate": "combined_total_pnl_delta",
            "actual": combined_eval.summary.get("delta_vs_baseline_pnl"),
            "threshold": "> 0",
            "passed": float(combined_eval.summary.get("delta_vs_baseline_pnl", 0.0)) > 0,
            "notes": "End-to-end stack must beat realized baseline.",
        },
        {
            "gate": "combined_positive_day_ratio",
            "actual": combined_eval.summary.get("positive_day_ratio"),
            "threshold": ">= 0.60",
            "passed": float(combined_eval.summary.get("positive_day_ratio", -1.0)) >= 0.60,
            "notes": "Combined stack should improve most days.",
        },
        {
            "gate": "combined_worst_day",
            "actual": combined_eval.summary.get("worst_day_delta_pnl"),
            "threshold": ">= -10000",
            "passed": float(combined_eval.summary.get("worst_day_delta_pnl", -1e12)) >= -10000.0,
            "notes": "Single-day underperformance guardrail.",
        },
        {
            "gate": "combined_last_5_days_stable",
            "actual": combined_eval.summary.get("last_5_non_negative_days"),
            "threshold": ">= 4 of last 5 and total delta >= 0",
            "passed": (
                int(combined_eval.summary.get("last_5_non_negative_days", 0)) >= 4
                and float(combined_eval.summary.get("last_5_day_delta_pnl", -1e12)) >= 0.0
            ),
            "notes": "Simple recent-stability heuristic for shadow sign-off.",
        },
    ]
    return pd.DataFrame(rows)
