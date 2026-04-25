from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .constants import RULE_CHECKPOINT_SECONDS


def _cp_tag(seconds: float) -> str:
    return f"{seconds:g}".replace(".", "p") + "s"


def compare_winner_loser_shapes(feature_df: pd.DataFrame) -> pd.DataFrame:
    if feature_df.empty:
        return pd.DataFrame()

    df = feature_df.copy()
    df["net_pnl"] = pd.to_numeric(df["net_pnl"], errors="coerce")
    winners = df[df["net_pnl"] > 0]
    losers = df[df["net_pnl"] < 0]

    rows: list[dict[str, Any]] = []

    def push(metric: str, w: float | None, l: float | None) -> None:
        rows.append(
            {
                "metric": metric,
                "winners": w,
                "losers": l,
                "delta_w_minus_l": (
                    (float(w) - float(l)) if w is not None and l is not None and not (np.isnan(w) or np.isnan(l)) else np.nan
                ),
            }
        )

    if not winners.empty:
        push("winner_count", float(len(winners)), float(len(losers)))
        push(
            "time_to_first_favorable_median",
            float(pd.to_numeric(winners.get("time_to_first_favorable"), errors="coerce").median()),
            float(pd.to_numeric(losers.get("time_to_first_favorable"), errors="coerce").median()) if not losers.empty else np.nan,
        )
        push(
            "time_to_first_adverse_median",
            float(pd.to_numeric(winners.get("time_to_first_adverse"), errors="coerce").median()),
            float(pd.to_numeric(losers.get("time_to_first_adverse"), errors="coerce").median()) if not losers.empty else np.nan,
        )
        push(
            "adverse_before_favorable_rate",
            float(pd.to_numeric(winners.get("adverse_before_favorable"), errors="coerce").fillna(0).mean()),
            float(pd.to_numeric(losers.get("adverse_before_favorable"), errors="coerce").fillna(0).mean()) if not losers.empty else np.nan,
        )

    for cp in RULE_CHECKPOINT_SECONDS:
        tag = _cp_tag(cp)
        for base in ("pnl", "runup", "drawdown", "underlying_move", "futures_move", "tick_velocity", "spread"):
            col = f"{base}_{tag}"
            if col not in df.columns:
                continue
            wv = pd.to_numeric(winners[col], errors="coerce") if not winners.empty else pd.Series(dtype=float)
            lv = pd.to_numeric(losers[col], errors="coerce") if not losers.empty else pd.Series(dtype=float)
            push(f"{col}_mean", float(wv.mean()) if not wv.empty else np.nan, float(lv.mean()) if not lv.empty else np.nan)

        pnl_col = f"pnl_{tag}"
        if pnl_col in df.columns:
            w_pos = (
                float((pd.to_numeric(winners[pnl_col], errors="coerce") > 0).mean()) if not winners.empty else np.nan
            )
            l_pos = (
                float((pd.to_numeric(losers[pnl_col], errors="coerce") > 0).mean()) if not losers.empty else np.nan
            )
            push(f"positive_pnl_rate_{tag}", w_pos, l_pos)

    # Fast vs slow winners.
    if "time_to_first_favorable" in winners.columns and not winners.empty:
        ttf = pd.to_numeric(winners["time_to_first_favorable"], errors="coerce")
        fast = winners[ttf <= 1.0]
        slow = winners[ttf > 1.0]
        push("fast_winner_share", float(len(fast) / len(winners)) if len(winners) else np.nan, np.nan)
        push("slow_winner_share", float(len(slow) / len(winners)) if len(winners) else np.nan, np.nan)
        push(
            "slow_winner_avg_pnl",
            float(pd.to_numeric(slow["net_pnl"], errors="coerce").mean()) if not slow.empty else np.nan,
            np.nan,
        )

    out = pd.DataFrame(rows)
    return out
