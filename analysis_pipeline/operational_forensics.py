from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def identify_operational_failures(
    reconciled_df: pd.DataFrame,
    feature_df: pd.DataFrame,
) -> pd.DataFrame:
    if reconciled_df.empty:
        return pd.DataFrame()

    merged = reconciled_df.copy()
    if not feature_df.empty:
        cols = [c for c in feature_df.columns if c.startswith("stale_quote_") or c.startswith("missing_update_")]
        keep = ["trade_id", *cols]
        merged = merged.merge(feature_df[keep], on="trade_id", how="left")

    hold = pd.to_numeric(merged.get("hold_seconds"), errors="coerce")
    long_threshold = float(np.nanquantile(hold, 0.95)) if hold.notna().any() else 60.0
    long_threshold = max(60.0, long_threshold)

    rows: list[dict[str, Any]] = []
    for _, r in merged.iterrows():
        exit_reason = str(r.get("exit_reason") or "")
        manual_flag = "MANUAL" in exit_reason.upper()

        hold_s = r.get("hold_seconds")
        try:
            hold_f = float(hold_s)
        except (TypeError, ValueError):
            hold_f = np.nan
        long_flag = bool(pd.notna(hold_f) and hold_f >= long_threshold)

        stale_cols = [c for c in merged.columns if c.startswith("stale_quote_")]
        miss_cols = [c for c in merged.columns if c.startswith("missing_update_")]

        stale_flag = any(pd.to_numeric(pd.Series([r.get(c)]), errors="coerce").fillna(0).iloc[0] >= 1 for c in stale_cols)
        missing_flag = any(pd.to_numeric(pd.Series([r.get(c)]), errors="coerce").fillna(0).iloc[0] >= 1 for c in miss_cols)

        es = r.get("entry_slippage_points")
        xs = r.get("exit_slippage_points")
        try:
            esf = abs(float(es)) if es is not None else 0.0
        except (TypeError, ValueError):
            esf = 0.0
        try:
            xsf = abs(float(xs)) if xs is not None else 0.0
        except (TypeError, ValueError):
            xsf = 0.0
        execution_flag = bool(esf > 5.0 or xsf > 5.0)

        net = pd.to_numeric(pd.Series([r.get("net_pnl")]), errors="coerce").iloc[0]
        is_loser = bool(pd.notna(net) and net < 0)

        operational_flag = manual_flag or long_flag or stale_flag or missing_flag or execution_flag
        policy_failure_flag = bool(is_loser and not operational_flag)

        notes: list[str] = []
        if manual_flag:
            notes.append("manual exit path")
        if long_flag:
            notes.append(f"long duration >= {long_threshold:.1f}s")
        if stale_flag:
            notes.append("stale quote observed")
        if missing_flag:
            notes.append("missing early updates")
        if execution_flag:
            notes.append("slippage anomaly")
        if policy_failure_flag:
            notes.append("loss looks strategy-policy driven")

        rows.append(
            {
                "trade_id": r.get("trade_id"),
                "date": r.get("date"),
                "exit_reason": r.get("exit_reason"),
                "hold_seconds": hold_f,
                "manual_flag": int(manual_flag),
                "long_duration_flag": int(long_flag),
                "stale_quote_flag": int(stale_flag),
                "missing_updates_flag": int(missing_flag),
                "execution_anomaly_flag": int(execution_flag),
                "policy_failure_flag": int(policy_failure_flag),
                "operational_failure_flag": int(operational_flag),
                "notes": "; ".join(notes),
            }
        )

    out = pd.DataFrame(rows)
    return out.sort_values(["date", "trade_id"]).reset_index(drop=True)
