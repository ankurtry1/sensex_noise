from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _fmt_num(v: Any, nd: int = 2) -> str:
    if v is None:
        return "NA"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if np.isnan(x):
        return "NA"
    return f"{x:.{nd}f}"


def _pick_top_rules(rule_df: pd.DataFrame) -> dict[str, dict[str, Any] | None]:
    if rule_df.empty:
        return {"conservative": None, "balanced": None, "aggressive": None}

    base = rule_df.copy()
    base["winner_preservation_rate"] = pd.to_numeric(base["winner_preservation_rate"], errors="coerce")
    base["tail_capture_rate"] = pd.to_numeric(base["tail_capture_rate"], errors="coerce")
    base["post_rule_net_pnl"] = pd.to_numeric(base["post_rule_net_pnl"], errors="coerce")

    conservative = base.sort_values(
        ["winner_preservation_rate", "post_rule_net_pnl", "tail_capture_rate"],
        ascending=[False, False, False],
    ).iloc[0].to_dict()

    # Balanced score: equal weight tail capture + winner preservation + pnl rank.
    pnl_rank = base["post_rule_net_pnl"].rank(pct=True)
    base["balanced_score"] = (
        base["winner_preservation_rate"].fillna(0)
        + base["tail_capture_rate"].fillna(0)
        + pnl_rank.fillna(0)
    )
    balanced = base.sort_values("balanced_score", ascending=False).iloc[0].to_dict()

    aggressive = base.sort_values(
        ["tail_capture_rate", "post_rule_net_pnl", "winner_preservation_rate"],
        ascending=[False, False, False],
    ).iloc[0].to_dict()

    return {
        "conservative": conservative,
        "balanced": balanced,
        "aggressive": aggressive,
    }


def _pick_top_policies(policy_df: pd.DataFrame) -> dict[str, dict[str, Any] | None]:
    if policy_df.empty:
        return {"conservative": None, "balanced": None, "aggressive": None}

    base = policy_df.copy()
    for col in ("net_pnl", "winners_lost", "tail_losers_prevented"):
        base[col] = pd.to_numeric(base[col], errors="coerce")

    conservative = base.sort_values(["winners_lost", "net_pnl"], ascending=[True, False]).iloc[0].to_dict()
    balanced = base.sort_values(["net_pnl", "tail_losers_prevented"], ascending=[False, False]).iloc[0].to_dict()
    aggressive = base.sort_values(["tail_losers_prevented", "net_pnl"], ascending=[False, False]).iloc[0].to_dict()
    return {
        "conservative": conservative,
        "balanced": balanced,
        "aggressive": aggressive,
    }


def write_top_candidate_rules(rule_df: pd.DataFrame, out_path: Path) -> None:
    tops = _pick_top_rules(rule_df)
    lines = ["# Top Candidate Rules", ""]
    for name, row in tops.items():
        lines.append(f"## {name.title()}")
        if row is None:
            lines.append("No candidate available.")
            lines.append("")
            continue
        lines.append(f"- Rule: `{row.get('rule_id')}`")
        lines.append(f"- Definition: {row.get('rule_definition')}")
        lines.append(f"- Winner preservation: {_fmt_num(row.get('winner_preservation_rate'))}")
        lines.append(f"- Tail capture: {_fmt_num(row.get('tail_capture_rate'))}")
        lines.append(f"- Post-rule net PnL: {_fmt_num(row.get('post_rule_net_pnl'))}")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_final_recommendation(
    out_path: Path,
    inventory_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    rule_df: pd.DataFrame,
    policy_df: pd.DataFrame,
    winner_loser_df: pd.DataFrame,
    operational_df: pd.DataFrame,
    robustness_df: pd.DataFrame,
) -> dict[str, Any]:
    tops_rules = _pick_top_rules(rule_df)
    tops_policies = _pick_top_policies(policy_df)

    overall = baseline_df[baseline_df["scope"] == "overall"] if not baseline_df.empty else pd.DataFrame()
    metric_map = {}
    if not overall.empty:
        metric_map = dict(zip(overall["metric"], overall["value"]))

    trust_counts = (
        inventory_df["confidence_bucket"].value_counts().to_dict() if not inventory_df.empty else {}
    )

    op_share = (
        float(pd.to_numeric(operational_df.get("operational_failure_flag"), errors="coerce").fillna(0).mean())
        if not operational_df.empty
        else np.nan
    )

    key_caveat = "Small sample size on some dates may overstate rule robustness."
    if not robustness_df.empty and (robustness_df["stability_flag"] == "FRAGILE").mean() > 0.4:
        key_caveat = "Many top candidates are fragile in day-wise holdout checks."

    lines = ["# Final Recommendation", ""]
    lines.append("## Executive conclusion")
    lines.append(
        "Evidence supports a faster invalidation framework for left-tail control, but only with explicit safeguards on winner preservation and data-quality gating."
    )
    lines.append("")

    lines.append("## Data coverage and trust summary")
    lines.append(f"- Dates analyzed: {int(inventory_df.shape[0]) if not inventory_df.empty else 0}")
    lines.append(f"- Confidence buckets: {trust_counts}")
    lines.append("")

    lines.append("## Strategy reconstruction summary")
    lines.append("- Signal generation is candle-color based continuation/reversal with entry buffer triggers.")
    lines.append("- Exit precedence prioritizes manual/hard-stop/early-risk/path-risk before target/time-stop.")
    lines.append("- Runtime is event-driven websocket with tick-based path metrics.")
    lines.append("")

    lines.append("## Baseline performance summary")
    lines.append(f"- Trade count: {_fmt_num(metric_map.get('trade_count'), 0)}")
    lines.append(f"- Win rate: {_fmt_num(metric_map.get('win_rate'))}")
    lines.append(f"- Net PnL: {_fmt_num(metric_map.get('net_pnl'))}")
    lines.append(f"- Profit factor: {_fmt_num(metric_map.get('profit_factor'))}")
    lines.append(f"- Max loss: {_fmt_num(metric_map.get('max_loss'))}")
    lines.append("")

    lines.append("## Tail concentration summary")
    lines.append(f"- Worst-1 loss concentration: {_fmt_num(metric_map.get('loss_concentration_worst_1'))}")
    lines.append(f"- Worst-3 loss concentration: {_fmt_num(metric_map.get('loss_concentration_worst_3'))}")
    lines.append(f"- Worst-5 loss concentration: {_fmt_num(metric_map.get('loss_concentration_worst_5'))}")
    lines.append("")

    lines.append("## Top rule table")
    for name in ("conservative", "balanced", "aggressive"):
        r = tops_rules.get(name)
        lines.append(f"### {name.title()} rule")
        if r is None:
            lines.append("No candidate available.")
            continue
        lines.append(f"- Rule id: `{r.get('rule_id')}`")
        lines.append(f"- Definition: {r.get('rule_definition')}")
        lines.append(f"- Checkpoint: {_fmt_num(r.get('checkpoint'))}s")
        lines.append(f"- Winner preservation: {_fmt_num(r.get('winner_preservation_rate'))}")
        lines.append(f"- Tail capture: {_fmt_num(r.get('tail_capture_rate'))}")
        lines.append(f"- Post-rule net PnL: {_fmt_num(r.get('post_rule_net_pnl'))}")

    lines.append("")
    lines.append("## Policy shortlist")
    for name in ("conservative", "balanced", "aggressive"):
        p = tops_policies.get(name)
        lines.append(f"### Best {name} policy")
        if p is None:
            lines.append("No candidate available.")
            continue
        lines.append(f"- Policy id: `{p.get('policy_id')}`")
        lines.append(f"- Rule: {p.get('exact_rule_text')}")
        lines.append(f"- Net PnL: {_fmt_num(p.get('net_pnl'))}")
        lines.append(f"- Winners lost: {_fmt_num(p.get('winners_lost'), 0)}")
        lines.append(f"- Tail losers prevented: {_fmt_num(p.get('tail_losers_prevented'), 0)}")

    lines.append("")
    lines.append("## Winner vs loser early-shape takeaway")
    if winner_loser_df.empty:
        lines.append("Insufficient feature coverage for shape comparison.")
    else:
        key_rows = winner_loser_df[winner_loser_df["metric"].str.contains("positive_pnl_rate|adverse_before_favorable_rate", na=False)]
        for _, r in key_rows.head(6).iterrows():
            lines.append(
                f"- {r['metric']}: winners={_fmt_num(r['winners'])}, losers={_fmt_num(r['losers'])}, delta={_fmt_num(r['delta_w_minus_l'])}"
            )

    lines.append("")
    lines.append("## Operational forensics summary")
    lines.append(f"- Operational-failure share: {_fmt_num(op_share)}")
    if not operational_df.empty:
        top_notes = (
            operational_df["notes"].dropna().value_counts().head(3).index.tolist()
            if "notes" in operational_df
            else []
        )
        for note in top_notes:
            if note:
                lines.append(f"- Frequent issue: {note}")

    lines.append("")
    lines.append("## Implementation blueprint")
    lines.append("1. Start with conservative checkpoint rule in shadow mode.")
    lines.append("2. Gate only left-tail candidates while monitoring winner preservation daily.")
    lines.append("3. Promote to active only if day-wise holdouts remain stable.")

    lines.append("")
    lines.append("## Limitations")
    lines.append(f"- {key_caveat}")
    lines.append("- Some dates lack full-depth option tape; fallback relies on trade-scoped capture.")

    lines.append("")
    lines.append("## Next logging improvements needed")
    lines.append("- Ensure consistent full lifecycle event IDs for every trade.")
    lines.append("- Preserve per-checkpoint quote freshness counters in enriched output.")
    lines.append("- Store explicit counterfactual fill confidence per simulated checkpoint.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "best_rule_conservative": (tops_rules.get("conservative") or {}).get("rule_id"),
        "best_rule_balanced": (tops_rules.get("balanced") or {}).get("rule_id"),
        "best_rule_aggressive": (tops_rules.get("aggressive") or {}).get("rule_id"),
        "best_policy": (tops_policies.get("balanced") or {}).get("policy_id"),
        "key_caveat": key_caveat,
    }
