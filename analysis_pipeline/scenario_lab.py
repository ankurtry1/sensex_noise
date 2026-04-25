from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd


@dataclass
class PolicySpec:
    policy_id: str
    policy_name: str
    rule_text: str
    assumptions: str
    chooser: Callable[[pd.Series], float | None]


def _cp_tag(seconds: float) -> str:
    return f"{seconds:g}".replace(".", "p") + "s"


def _num(row: pd.Series, col: str) -> float | None:
    try:
        v = row.get(col)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _profit_factor(pnls: pd.Series) -> float | None:
    wins = pnls[pnls > 0].sum()
    losses = pnls[pnls < 0].sum()
    if losses == 0:
        return None
    return float(wins / abs(losses))


def build_policy_specs() -> list[PolicySpec]:
    return [
        PolicySpec(
            policy_id="A1_QUICKSTOP_1S",
            policy_name="Pure quick-stop 1s",
            rule_text="Exit at 1s if runup_1s < 0.5",
            assumptions="No-confirmation fast invalidation",
            chooser=lambda r: 1.0 if (_num(r, "runup_1s") is not None and _num(r, "runup_1s") < 0.5) else None,
        ),
        PolicySpec(
            policy_id="A2_QUICKSTOP_2S",
            policy_name="Pure quick-stop 2s",
            rule_text="Exit at 2s if runup_2s < 0.75",
            assumptions="Slightly slower confirmation window",
            chooser=lambda r: 2.0 if (_num(r, "runup_2s") is not None and _num(r, "runup_2s") < 0.75) else None,
        ),
        PolicySpec(
            policy_id="B_HYBRID_KEEP_TARGET",
            policy_name="Hybrid retain target",
            rule_text="Exit at 2s if pnl_2s <= 0 and runup_2s < 1",
            assumptions="Only early invalidation changed",
            chooser=lambda r: 2.0
            if ((_num(r, "pnl_2s") is not None and _num(r, "runup_2s") is not None) and (_num(r, "pnl_2s") <= 0 and _num(r, "runup_2s") < 1))
            else None,
        ),
        PolicySpec(
            policy_id="C_FAST_INVALIDATION_HARDSTOP",
            policy_name="Fast invalidation + hard-stop",
            rule_text="Exit at 2s if runup_2s < 0.75; else exit at 5s if drawdown_5s <= -4",
            assumptions="Two-stage risk floor",
            chooser=lambda r: 2.0
            if (_num(r, "runup_2s") is not None and _num(r, "runup_2s") < 0.75)
            else (5.0 if (_num(r, "drawdown_5s") is not None and _num(r, "drawdown_5s") <= -4) else None),
        ),
        PolicySpec(
            policy_id="D_CONFIRM_REQUIRED",
            policy_name="Confirmation-required",
            rule_text="Exit at 3s if runup_3s < 1",
            assumptions="Require minimum favorable excursion",
            chooser=lambda r: 3.0 if (_num(r, "runup_3s") is not None and _num(r, "runup_3s") < 1) else None,
        ),
        PolicySpec(
            policy_id="E_TAIL_DEFENSE",
            policy_name="Tail-defense",
            rule_text="Exit at 1s if drawdown_1s <= -2 else at 2s if pnl_2s <= -2",
            assumptions="Aggressive left-tail clipping",
            chooser=lambda r: 1.0
            if (_num(r, "drawdown_1s") is not None and _num(r, "drawdown_1s") <= -2)
            else (2.0 if (_num(r, "pnl_2s") is not None and _num(r, "pnl_2s") <= -2) else None),
        ),
        PolicySpec(
            policy_id="F_TIMEOFDAY_ADAPTIVE",
            policy_name="Time-of-day adaptive",
            rule_text="PRE_1PM: exit 2s on no-confirmation; POST_1PM: exit 1s on no-confirmation",
            assumptions="Stricter later session",
            chooser=lambda r: (
                1.0
                if (str(r.get("pre_or_post_1pm")) == "POST_1PM" and (_num(r, "runup_1s") is not None and _num(r, "runup_1s") < 0.5))
                else (
                    2.0
                    if (str(r.get("pre_or_post_1pm")) != "POST_1PM" and (_num(r, "runup_2s") is not None and _num(r, "runup_2s") < 1 and (_num(r, "pnl_2s") or 0) <= 0))
                    else None
                )
            ),
        ),
        PolicySpec(
            policy_id="G_SIGNALTYPE_ADAPTIVE",
            policy_name="Signal-type adaptive",
            rule_text="Reversal: 1s invalidation; Continuation: 3s invalidation",
            assumptions="Reversals expected to confirm faster",
            chooser=lambda r: (
                1.0
                if ("REVERSAL" in str(r.get("signal_kind", "")).upper() and (_num(r, "runup_1s") is not None and _num(r, "runup_1s") < 0.5))
                else (
                    3.0
                    if ("CONTINUATION" in str(r.get("signal_kind", "")).upper() and (_num(r, "runup_3s") is not None and _num(r, "runup_3s") < 1))
                    else None
                )
            ),
        ),
        PolicySpec(
            policy_id="H_MICROSTRUCTURE_GATED",
            policy_name="Microstructure-gated",
            rule_text="Exit 1s if stale_quote_1s==1 OR spread_vs_entry_1s>2, with non-positive pnl",
            assumptions="Quote quality must remain supportive",
            chooser=lambda r: 1.0
            if (((_num(r, "stale_quote_1s") or 0) >= 1 or ((_num(r, "spread_vs_entry_1s") or 0) > 2)) and ((_num(r, "pnl_1s") or 0) <= 0))
            else None,
        ),
        PolicySpec(
            policy_id="I_OPERATIONAL_HARDENING",
            policy_name="Operational hardening",
            rule_text="Exit 2s if missing_update_1s==1 OR quote_quality_degradation_flag==1 and pnl_2s<=0",
            assumptions="Fail-safe when feed/quote quality degrades",
            chooser=lambda r: 2.0
            if (((_num(r, "missing_update_1s") or 0) >= 1 or (_num(r, "quote_quality_degradation_flag") or 0) >= 1) and ((_num(r, "pnl_2s") or 0) <= 0))
            else None,
        ),
    ]


def simulate_policies(feature_df: pd.DataFrame, policies: list[PolicySpec] | None = None) -> pd.DataFrame:
    if feature_df.empty:
        return pd.DataFrame()

    policies = policies or build_policy_specs()
    df = feature_df.copy()
    df["net_pnl"] = pd.to_numeric(df["net_pnl"], errors="coerce")
    tail_cut = float(df["net_pnl"].quantile(0.10))
    df["tail_loser"] = df["net_pnl"] <= tail_cut
    df["final_winner"] = df["net_pnl"] > 0

    rows: list[dict[str, Any]] = []

    for policy in policies:
        results: list[float] = []
        cp_used: list[float | None] = []
        triggered_mask: list[bool] = []
        evaluable_mask: list[bool] = []

        for _, r in df.iterrows():
            orig = float(r["net_pnl"]) if pd.notna(r["net_pnl"]) else 0.0
            cp = policy.chooser(r)
            cp_used.append(cp)
            if cp is None:
                results.append(orig)
                triggered_mask.append(False)
                evaluable_mask.append(True)
                continue

            tag = _cp_tag(cp)
            cf_col = f"counterfactual_exit_pnl_{tag}"
            cf = _num(r, cf_col)
            if cf is None:
                # scenario unavailable for this triggered trade
                results.append(orig)
                triggered_mask.append(True)
                evaluable_mask.append(False)
                continue

            results.append(float(cf))
            triggered_mask.append(True)
            evaluable_mask.append(True)

        sim = pd.Series(results, index=df.index)
        triggered = pd.Series(triggered_mask, index=df.index)
        evaluable = pd.Series(evaluable_mask, index=df.index)
        cp_series = pd.Series(cp_used, index=df.index)

        eval_df = df[evaluable].copy()
        sim_eval = sim[evaluable]
        if eval_df.empty:
            continue

        winners_lost = int(((eval_df["final_winner"]) & (triggered[evaluable])).sum())
        losers_prevented = int(((eval_df["net_pnl"] < 0) & (sim_eval > eval_df["net_pnl"])).sum())
        tail_prevented = int(((eval_df["tail_loser"]) & (sim_eval > eval_df["net_pnl"])).sum())

        rows.append(
            {
                "policy_id": policy.policy_id,
                "policy_name": policy.policy_name,
                "exact_rule_text": policy.rule_text,
                "assumptions": policy.assumptions,
                "simulation_method": "checkpoint counterfactual using nearest observed price at/after checkpoint",
                "trade_count": int(len(df)),
                "evaluable_trade_count": int(evaluable.sum()),
                "net_pnl": float(sim_eval.sum()),
                "avg_pnl": float(sim_eval.mean()),
                "median_pnl": float(sim_eval.median()),
                "max_loss": float(sim_eval.min()),
                "max_gain": float(sim_eval.max()),
                "profit_factor": _profit_factor(sim_eval),
                "expectancy": float(sim_eval.mean()),
                "winners_lost": winners_lost,
                "losers_prevented": losers_prevented,
                "tail_losers_prevented": tail_prevented,
                "killed_before_1s": int(((triggered) & (cp_series <= 1)).sum()),
                "killed_before_2s": int(((triggered) & (cp_series <= 2)).sum()),
                "killed_before_3s": int(((triggered) & (cp_series <= 3)).sum()),
                "killed_before_5s": int(((triggered) & (cp_series <= 5)).sum()),
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["net_pnl", "tail_losers_prevented", "winners_lost"], ascending=[False, False, True]).reset_index(drop=True)
    return out
