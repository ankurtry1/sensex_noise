from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd

from .constants import RULE_CHECKPOINT_SECONDS


@dataclass
class RuleSpec:
    rule_id: str
    checkpoint: float
    rule_definition: str
    implementation_complexity: str
    fn: Callable[[pd.DataFrame], pd.Series]


def _cp_tag(seconds: float) -> str:
    return f"{seconds:g}".replace(".", "p") + "s"


def _profit_factor(pnls: pd.Series) -> float | None:
    wins = pnls[pnls > 0].sum()
    losses = pnls[pnls < 0].sum()
    if losses == 0:
        return None
    return float(wins / abs(losses))


def _num_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(default, index=df.index, dtype=float)


def add_labels(feature_df: pd.DataFrame, tail_quantile: float = 0.10) -> pd.DataFrame:
    df = feature_df.copy()
    if df.empty:
        return df
    df["net_pnl"] = pd.to_numeric(df["net_pnl"], errors="coerce")
    df["final_winner"] = df["net_pnl"] > 0
    df["final_loser"] = df["net_pnl"] < 0

    tail_cut = float(df["net_pnl"].quantile(tail_quantile))
    severe_cut = float(df["net_pnl"].quantile(0.20))
    df["tail_loser"] = df["net_pnl"] <= tail_cut
    df["severe_loser"] = df["net_pnl"] <= min(severe_cut, -3000)

    df["hit_target"] = df["exit_reason"].astype(str).str.upper().eq("TARGET_HIT")
    df["never_hit_target"] = ~df["hit_target"]
    return df


def build_rule_specs(checkpoints: tuple[float, ...] = RULE_CHECKPOINT_SECONDS) -> list[RuleSpec]:
    specs: list[RuleSpec] = []

    for cp in checkpoints:
        t = _cp_tag(cp)
        pnl_col = f"pnl_{t}"
        run_col = f"runup_{t}"
        dd_col = f"drawdown_{t}"
        stale_col = f"stale_quote_{t}"
        spr_col = f"spread_vs_entry_{t}"

        specs.append(
            RuleSpec(
                rule_id=f"R_PNL_LE_0_{t}",
                checkpoint=cp,
                rule_definition=f"{pnl_col} <= 0",
                implementation_complexity="LOW",
                fn=lambda df, c=pnl_col: pd.to_numeric(df[c], errors="coerce") <= 0,
            )
        )
        specs.append(
            RuleSpec(
                rule_id=f"R_PNL_LE_NEG1_{t}",
                checkpoint=cp,
                rule_definition=f"{pnl_col} <= -1",
                implementation_complexity="LOW",
                fn=lambda df, c=pnl_col: pd.to_numeric(df[c], errors="coerce") <= -1,
            )
        )
        specs.append(
            RuleSpec(
                rule_id=f"R_NO_RUNUP_AND_DD_{t}",
                checkpoint=cp,
                rule_definition=f"{run_col} < 1 and {dd_col} <= -2",
                implementation_complexity="LOW",
                fn=lambda df, rc=run_col, dc=dd_col: (
                    pd.to_numeric(df[rc], errors="coerce") < 1
                )
                & (pd.to_numeric(df[dc], errors="coerce") <= -2),
            )
        )
        specs.append(
            RuleSpec(
                rule_id=f"R_ADVERSE_FIRST_AND_NEG_{t}",
                checkpoint=cp,
                rule_definition=f"adverse_before_favorable == 1 and {pnl_col} <= 0",
                implementation_complexity="MEDIUM",
                fn=lambda df, pc=pnl_col: (
                    _num_series(df, "adverse_before_favorable", default=0.0).fillna(0) >= 1
                )
                & (pd.to_numeric(df[pc], errors="coerce") <= 0),
            )
        )
        specs.append(
            RuleSpec(
                rule_id=f"R_STALE_AND_NEG_{t}",
                checkpoint=cp,
                rule_definition=f"{stale_col} == 1 and {pnl_col} <= 0",
                implementation_complexity="MEDIUM",
                fn=lambda df, sc=stale_col, pc=pnl_col: (
                    _num_series(df, sc, default=0.0).fillna(0) >= 1
                )
                & (pd.to_numeric(df[pc], errors="coerce") <= 0),
            )
        )
        specs.append(
            RuleSpec(
                rule_id=f"R_SPREAD_DEGRADE_NEG_{t}",
                checkpoint=cp,
                rule_definition=f"{spr_col} > 2 and {pnl_col} <= 0",
                implementation_complexity="MEDIUM",
                fn=lambda df, sc=spr_col, pc=pnl_col: (
                    _num_series(df, sc, default=np.nan) > 2
                )
                & (_num_series(df, pc, default=np.nan) <= 0),
            )
        )

    # Cross-checkpoint compact rules.
    specs.append(
        RuleSpec(
            rule_id="R_IMMEDIATE_REJECTION_1S",
            checkpoint=1.0,
            rule_definition="immediate_rejection_flag == 1",
            implementation_complexity="LOW",
            fn=lambda df: _num_series(df, "immediate_rejection_flag", default=0.0).fillna(0) >= 1,
        )
    )
    specs.append(
        RuleSpec(
            rule_id="R_NO_CONFIRM_3S",
            checkpoint=3.0,
            rule_definition="runup_3s < 1 and pnl_3s <= 0",
            implementation_complexity="LOW",
            fn=lambda df: (_num_series(df, "runup_3s", default=np.nan) < 1)
            & (_num_series(df, "pnl_3s", default=np.nan) <= 0),
        )
    )

    return specs


def evaluate_rules(feature_df: pd.DataFrame, specs: list[RuleSpec] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list[RuleSpec]]:
    if feature_df.empty:
        return pd.DataFrame(), feature_df.copy(), []

    labeled = add_labels(feature_df)
    specs = specs or build_rule_specs()

    total = len(labeled)
    winners_total = int(labeled["final_winner"].sum())
    losers_total = int(labeled["final_loser"].sum())
    tail_total = int(labeled["tail_loser"].sum())

    rows: list[dict[str, Any]] = []

    for spec in specs:
        try:
            mask = spec.fn(labeled).fillna(False)
        except KeyError:
            continue
        if mask.dtype != bool:
            mask = mask.astype(bool)

        # Rule availability sample size: rows where referenced checkpoint pnl exists.
        cp_tag = _cp_tag(spec.checkpoint)
        cp_col = f"pnl_{cp_tag}"
        if cp_col in labeled.columns:
            sample_size = int(pd.to_numeric(labeled[cp_col], errors="coerce").notna().sum())
        else:
            sample_size = total

        trades_killed = int(mask.sum())
        winners_killed = int((mask & labeled["final_winner"]).sum())
        losers_captured = int((mask & labeled["final_loser"]).sum())
        tail_captured = int((mask & labeled["tail_loser"]).sum())

        winner_pres = (
            float((winners_total - winners_killed) / winners_total) if winners_total > 0 else np.nan
        )
        tail_capture = float(tail_captured / tail_total) if tail_total > 0 else np.nan

        post = labeled["net_pnl"].copy()
        # Classification rules interpreted as "kill/avoid trade" before large loss.
        post.loc[mask] = 0.0

        pf = _profit_factor(post)
        max_loss = float(post.min()) if len(post) > 0 else np.nan
        expectancy = float(post.mean()) if len(post) > 0 else np.nan

        robustness_note = "sample_small" if sample_size < 20 else "sample_ok"

        rows.append(
            {
                "rule_id": spec.rule_id,
                "checkpoint": spec.checkpoint,
                "rule_definition": spec.rule_definition,
                "sample_size": sample_size,
                "trades_killed": trades_killed,
                "losers_captured": losers_captured,
                "tail_losers_captured": tail_captured,
                "winners_killed": winners_killed,
                "winner_preservation_rate": winner_pres,
                "tail_capture_rate": tail_capture,
                "post_rule_net_pnl": float(post.sum()),
                "post_rule_expectancy": expectancy,
                "post_rule_profit_factor": pf,
                "post_rule_max_loss": max_loss,
                "implementation_complexity": spec.implementation_complexity,
                "robustness_note": robustness_note,
                "losers_total": losers_total,
                "tail_total": tail_total,
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(
            ["tail_capture_rate", "winner_preservation_rate", "post_rule_net_pnl"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

    return out, labeled, specs


def best_rule_for_checkpoint(rule_df: pd.DataFrame, checkpoint: float) -> dict[str, Any] | None:
    if rule_df.empty:
        return None
    cand = rule_df[rule_df["checkpoint"] == checkpoint]
    if cand.empty:
        return None
    cand = cand.sort_values(
        ["tail_capture_rate", "winner_preservation_rate", "post_rule_net_pnl"],
        ascending=[False, False, False],
    )
    return cand.iloc[0].to_dict()
