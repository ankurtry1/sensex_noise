from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .constants import RULE_CHECKPOINT_SECONDS


def _cp_tag(cp: float) -> str:
    return f"{cp:g}".replace(".", "p") + "s"


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def generate_figures(
    out_dir: Path,
    reconciled_df: pd.DataFrame,
    feature_df: pd.DataFrame,
    rule_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []

    if not reconciled_df.empty:
        df = reconciled_df[reconciled_df["match_status"] == "reconciled"].copy()
        df["net_pnl"] = pd.to_numeric(df["net_pnl"], errors="coerce")
        df = df[df["net_pnl"].notna()].copy()

        if not df.empty:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.hist(df["net_pnl"], bins=30, color="#1f77b4", edgecolor="black")
            ax.set_title("PnL Distribution")
            ax.set_xlabel("Net PnL")
            ax.set_ylabel("Trade Count")
            p = out_dir / "pnl_distribution.png"
            _save(fig, p)
            files.append(p)

            fig, ax = plt.subplots(figsize=(8, 4))
            df_sorted = df.sort_values(["date", "entry_time"]).reset_index(drop=True)
            cum = df_sorted["net_pnl"].cumsum()
            ax.plot(np.arange(len(cum)), cum, color="#2ca02c")
            ax.set_title("Cumulative PnL by Trade Order")
            ax.set_xlabel("Trade Index")
            ax.set_ylabel("Cumulative Net PnL")
            p = out_dir / "cumulative_pnl_by_trade_order.png"
            _save(fig, p)
            files.append(p)

            fig, ax = plt.subplots(figsize=(8, 4))
            sorted_pnl = df["net_pnl"].sort_values()
            xs = [1, 3, 5, 10]
            ys = [sorted_pnl.head(min(x, len(sorted_pnl))).sum() for x in xs]
            ax.bar([str(x) for x in xs], ys, color="#d62728")
            ax.set_title("Tail Concentration (Worst-N PnL Sum)")
            ax.set_xlabel("Worst N trades")
            ax.set_ylabel("Sum Net PnL")
            p = out_dir / "tail_concentration_bar.png"
            _save(fig, p)
            files.append(p)

            if "exit_reason" in df.columns and "hold_seconds" in df.columns:
                fig, ax = plt.subplots(figsize=(9, 4))
                g = (
                    df.groupby("exit_reason", dropna=False)["hold_seconds"]
                    .mean()
                    .sort_values(ascending=False)
                )
                ax.bar(g.index.astype(str), g.values, color="#9467bd")
                ax.set_title("Mean Hold Time by Exit Reason")
                ax.set_xlabel("Exit Reason")
                ax.set_ylabel("Mean Hold Seconds")
                ax.tick_params(axis="x", rotation=30)
                p = out_dir / "hold_time_by_exit_reason.png"
                _save(fig, p)
                files.append(p)

    if not feature_df.empty:
        fig, ax = plt.subplots(figsize=(9, 4))
        cps = []
        runups = []
        drawdowns = []
        for cp in RULE_CHECKPOINT_SECONDS:
            tag = _cp_tag(cp)
            rcol = f"runup_{tag}"
            dcol = f"drawdown_{tag}"
            if rcol in feature_df.columns and dcol in feature_df.columns:
                cps.append(cp)
                runups.append(pd.to_numeric(feature_df[rcol], errors="coerce").mean())
                drawdowns.append(pd.to_numeric(feature_df[dcol], errors="coerce").mean())
        if cps:
            ax.plot(cps, runups, marker="o", label="Mean runup")
            ax.plot(cps, drawdowns, marker="o", label="Mean drawdown")
            ax.set_title("Runup/Drawdown at Checkpoints")
            ax.set_xlabel("Checkpoint (s)")
            ax.set_ylabel("Points")
            ax.legend()
            p = out_dir / "runup_drawdown_checkpoints.png"
            _save(fig, p)
            files.append(p)
        else:
            plt.close(fig)

        w = feature_df[pd.to_numeric(feature_df.get("net_pnl"), errors="coerce") > 0]
        l = feature_df[pd.to_numeric(feature_df.get("net_pnl"), errors="coerce") < 0]
        if not w.empty and not l.empty:
            cps = []
            wp = []
            lp = []
            for cp in RULE_CHECKPOINT_SECONDS:
                tag = _cp_tag(cp)
                col = f"pnl_{tag}"
                if col in feature_df.columns:
                    cps.append(cp)
                    wp.append(pd.to_numeric(w[col], errors="coerce").mean())
                    lp.append(pd.to_numeric(l[col], errors="coerce").mean())
            if cps:
                fig, ax = plt.subplots(figsize=(9, 4))
                ax.plot(cps, wp, marker="o", label="Winners")
                ax.plot(cps, lp, marker="o", label="Losers")
                ax.axhline(0, color="black", linewidth=0.8)
                ax.set_title("Winner vs Loser Early Checkpoint PnL")
                ax.set_xlabel("Checkpoint (s)")
                ax.set_ylabel("Mean PnL at checkpoint")
                ax.legend()
                p = out_dir / "winner_loser_checkpoint_comparison.png"
                _save(fig, p)
                files.append(p)

    if not rule_df.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        x = pd.to_numeric(rule_df["winner_preservation_rate"], errors="coerce")
        y = pd.to_numeric(rule_df["tail_capture_rate"], errors="coerce")
        c = pd.to_numeric(rule_df["post_rule_net_pnl"], errors="coerce")
        sc = ax.scatter(x, y, c=c, cmap="viridis", alpha=0.8)
        ax.set_title("Rule Frontier: Winner Preservation vs Tail Capture")
        ax.set_xlabel("Winner preservation")
        ax.set_ylabel("Tail capture")
        fig.colorbar(sc, ax=ax, label="Post-rule net PnL")
        p = out_dir / "rule_frontier_scatter.png"
        _save(fig, p)
        files.append(p)

    if not scenario_df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        top = scenario_df.head(10)
        ax.bar(top["policy_id"], top["net_pnl"], color="#17becf")
        ax.set_title("Scenario Comparison (Net PnL)")
        ax.set_xlabel("Policy")
        ax.set_ylabel("Simulated net PnL")
        ax.tick_params(axis="x", rotation=30)
        p = out_dir / "scenario_comparison_bar.png"
        _save(fig, p)
        files.append(p)

    if not inventory_df.empty:
        fig, ax = plt.subplots(figsize=(9, 4))
        inv = inventory_df.sort_values("date")
        ax.bar(inv["date"], inv["data_trust_score"], color="#8c564b")
        ax.set_title("Date-wise Data Trust / Coverage")
        ax.set_xlabel("Date")
        ax.set_ylabel("Trust score")
        ax.tick_params(axis="x", rotation=30)
        p = out_dir / "datewise_data_trust_coverage.png"
        _save(fig, p)
        files.append(p)

    return files
