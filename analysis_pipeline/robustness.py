from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .rule_engine import RuleSpec
from .scenario_lab import PolicySpec, simulate_policies


def _evaluate_rule_on_slice(df: pd.DataFrame, spec: RuleSpec) -> dict[str, float]:
    if df.empty:
        return {
            "winner_preservation_rate": np.nan,
            "tail_capture_rate": np.nan,
            "net_pnl_delta": np.nan,
            "max_loss_delta": np.nan,
        }

    mask = spec.fn(df).fillna(False)
    winners_total = int((df["final_winner"] == True).sum())
    winners_killed = int((mask & (df["final_winner"] == True)).sum())
    tail_total = int((df["tail_loser"] == True).sum())
    tail_captured = int((mask & (df["tail_loser"] == True)).sum())

    post = df["net_pnl"].copy()
    post.loc[mask] = 0.0

    return {
        "winner_preservation_rate": (winners_total - winners_killed) / winners_total if winners_total > 0 else np.nan,
        "tail_capture_rate": tail_captured / tail_total if tail_total > 0 else np.nan,
        "net_pnl_delta": float(post.sum() - df["net_pnl"].sum()),
        "max_loss_delta": float(post.min() - df["net_pnl"].min()),
    }


def validate_robustness(
    labeled_feature_df: pd.DataFrame,
    rule_specs: list[RuleSpec],
    rule_eval_df: pd.DataFrame,
    policy_specs: list[PolicySpec],
    policy_df: pd.DataFrame,
) -> pd.DataFrame:
    if labeled_feature_df.empty:
        return pd.DataFrame()

    df = labeled_feature_df.copy()
    df = df[pd.to_numeric(df["net_pnl"], errors="coerce").notna()].copy()
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    dates = sorted(d for d in df["date"].dropna().unique())
    if len(dates) < 2:
        return pd.DataFrame(
            [
                {
                    "candidate_id": "N/A",
                    "train_dates": "",
                    "test_dates": ",".join(dates),
                    "test_trade_count": int(len(df)),
                    "winner_preservation_rate": np.nan,
                    "tail_capture_rate": np.nan,
                    "net_pnl_delta": np.nan,
                    "max_loss_delta": np.nan,
                    "stability_flag": "INSUFFICIENT_DATES",
                    "fragility_note": "Need at least two dates for holdout robustness.",
                }
            ]
        )

    # Top rules by frontier ranking.
    top_rule_ids = (
        rule_eval_df.sort_values(["tail_capture_rate", "winner_preservation_rate"], ascending=[False, False])["rule_id"].head(5).tolist()
        if not rule_eval_df.empty
        else []
    )
    rule_spec_map = {s.rule_id: s for s in rule_specs}

    top_policy_ids = (
        policy_df.sort_values(["net_pnl", "tail_losers_prevented"], ascending=[False, False])["policy_id"].head(3).tolist()
        if not policy_df.empty
        else []
    )
    policy_spec_map = {p.policy_id: p for p in policy_specs}

    rows: list[dict[str, Any]] = []

    # Leave-one-day-out for rules.
    for rid in top_rule_ids:
        spec = rule_spec_map.get(rid)
        if spec is None:
            continue
        for test_date in dates:
            train = df[df["date"] != test_date]
            test = df[df["date"] == test_date]
            metrics = _evaluate_rule_on_slice(test, spec)
            rows.append(
                {
                    "candidate_id": f"RULE::{rid}",
                    "train_dates": ",".join(sorted(train["date"].dropna().unique())),
                    "test_dates": test_date,
                    "test_trade_count": int(len(test)),
                    "winner_preservation_rate": metrics["winner_preservation_rate"],
                    "tail_capture_rate": metrics["tail_capture_rate"],
                    "net_pnl_delta": metrics["net_pnl_delta"],
                    "max_loss_delta": metrics["max_loss_delta"],
                    "stability_flag": "PASS"
                    if (pd.notna(metrics["winner_preservation_rate"]) and pd.notna(metrics["tail_capture_rate"]) and metrics["winner_preservation_rate"] >= 0.65)
                    else "FRAGILE",
                    "fragility_note": "winner preservation below threshold or sparse tails"
                    if (pd.isna(metrics["winner_preservation_rate"]) or metrics["winner_preservation_rate"] < 0.65)
                    else "",
                }
            )

    # Leave-one-day-out for policies.
    for pid in top_policy_ids:
        spec = policy_spec_map.get(pid)
        if spec is None:
            continue
        for test_date in dates:
            test = df[df["date"] == test_date]
            sim = simulate_policies(test, [spec])
            if sim.empty:
                continue
            s = sim.iloc[0]
            rows.append(
                {
                    "candidate_id": f"POLICY::{pid}",
                    "train_dates": ",".join([d for d in dates if d != test_date]),
                    "test_dates": test_date,
                    "test_trade_count": int(len(test)),
                    "winner_preservation_rate": np.nan,
                    "tail_capture_rate": np.nan,
                    "net_pnl_delta": float(s["net_pnl"] - test["net_pnl"].sum()),
                    "max_loss_delta": float(s["max_loss"] - test["net_pnl"].min()) if pd.notna(s["max_loss"]) else np.nan,
                    "stability_flag": "PASS" if float(s["net_pnl"]) >= float(test["net_pnl"].sum()) else "FRAGILE",
                    "fragility_note": "policy underperformed baseline on this holdout day"
                    if float(s["net_pnl"]) < float(test["net_pnl"].sum())
                    else "",
                }
            )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["candidate_id", "test_dates"]).reset_index(drop=True)
    return out
