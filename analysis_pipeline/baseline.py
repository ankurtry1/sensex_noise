from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _profit_factor(pnls: pd.Series) -> float | None:
    wins = pnls[pnls > 0].sum()
    losses = pnls[pnls < 0].sum()
    if losses == 0:
        return None
    return float(wins / abs(losses))


def _summary_for_slice(df: pd.DataFrame, label: str) -> list[dict[str, Any]]:
    if df.empty:
        return [{"scope": label, "metric": "trade_count", "value": 0}]

    pnls = df["net_pnl"].astype(float)
    holds = df["hold_seconds"].astype(float)

    rows = [
        {"scope": label, "metric": "trade_count", "value": int(len(df))},
        {"scope": label, "metric": "win_rate", "value": float((pnls > 0).mean())},
        {"scope": label, "metric": "gross_profit", "value": float(pnls[pnls > 0].sum())},
        {"scope": label, "metric": "gross_loss", "value": float(pnls[pnls < 0].sum())},
        {"scope": label, "metric": "net_pnl", "value": float(pnls.sum())},
        {"scope": label, "metric": "average_pnl", "value": float(pnls.mean())},
        {"scope": label, "metric": "median_pnl", "value": float(pnls.median())},
        {"scope": label, "metric": "max_gain", "value": float(pnls.max())},
        {"scope": label, "metric": "max_loss", "value": float(pnls.min())},
        {"scope": label, "metric": "profit_factor", "value": _profit_factor(pnls)},
        {"scope": label, "metric": "expectancy", "value": float(pnls.mean())},
        {"scope": label, "metric": "hold_time_mean", "value": float(holds.mean())},
        {"scope": label, "metric": "hold_time_median", "value": float(holds.median())},
    ]

    if "mfe" in df.columns:
        rows.append({"scope": label, "metric": "mfe_mean", "value": float(df["mfe"].astype(float).mean())})
    if "mae" in df.columns:
        rows.append({"scope": label, "metric": "mae_mean", "value": float(df["mae"].astype(float).mean())})

    sorted_pnl = pnls.sort_values()
    for n in (1, 3, 5, 10):
        n_eff = min(n, len(sorted_pnl))
        rows.append(
            {
                "scope": label,
                "metric": f"loss_concentration_worst_{n_eff}",
                "value": float(sorted_pnl.head(n_eff).sum()),
            }
        )

    return rows


def compute_baseline_metrics(reconciled_df: pd.DataFrame) -> pd.DataFrame:
    if reconciled_df.empty:
        return pd.DataFrame(columns=["scope", "metric", "value"])

    df = reconciled_df.copy()
    df = df[df["match_status"] == "reconciled"].copy()
    if df.empty:
        return pd.DataFrame(columns=["scope", "metric", "value"])

    # Ensure numeric.
    for col in ("net_pnl", "gross_pnl", "hold_seconds", "mfe", "mae"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    rows: list[dict[str, Any]] = []
    rows.extend(_summary_for_slice(df, "overall"))

    for col in ("date", "side", "signal_kind", "exit_reason", "pre_or_post_1pm"):
        if col not in df.columns:
            continue
        for key, g in df.groupby(col, dropna=False):
            label = f"{col}={key}"
            rows.extend(_summary_for_slice(g, label))

    # Hold-time buckets.
    bins = [-np.inf, 1, 3, 5, 10, 30, 60, np.inf]
    labels = ["<=1s", "1-3s", "3-5s", "5-10s", "10-30s", "30-60s", ">60s"]
    df["hold_bucket"] = pd.cut(df["hold_seconds"], bins=bins, labels=labels)
    for key, g in df.groupby("hold_bucket", dropna=False, observed=False):
        rows.extend(_summary_for_slice(g, f"hold_bucket={key}"))

    return pd.DataFrame(rows)
