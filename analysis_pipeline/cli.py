from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from .baseline import compute_baseline_metrics
from .checkpoint_features import build_checkpoint_features
from .config import PipelineConfig, PipelineRunSummary
from .inventory import apply_reconciliation_coverage, build_inventory, build_research_summary
from .io_utils import ensure_dir, write_df, write_json
from .operational_forensics import identify_operational_failures
from .plots import generate_figures
from .reconciliation import reconcile_trades
from .reporting import write_final_recommendation, write_top_candidate_rules
from .robustness import validate_robustness
from .rule_engine import best_rule_for_checkpoint, evaluate_rules
from .scenario_lab import build_policy_specs, simulate_policies
from .strategy_reconstruction import write_strategy_reconstruction
from .trade_path import TradePathLoader
from .winner_loser import compare_winner_loser_shapes


def _filter_usable_dates(
    inventory_df: pd.DataFrame,
    reconciled_df: pd.DataFrame,
    min_trades_per_day: int,
) -> tuple[list[str], list[str]]:
    if inventory_df.empty or reconciled_df.empty:
        return [], []

    rec = reconciled_df[reconciled_df["match_status"] == "reconciled"].copy()
    counts = rec.groupby("date")["trade_id"].nunique().to_dict()

    usable: list[str] = []
    excluded: list[str] = []
    for _, row in inventory_df.sort_values("date").iterrows():
        d = row["date"]
        trust = str(row.get("confidence_bucket"))
        c = int(counts.get(d, 0))
        if trust in {"HIGH", "MEDIUM", "LOW"} and c >= min_trades_per_day:
            usable.append(d)
        else:
            excluded.append(d)
    return usable, excluded


def run_pipeline(config: PipelineConfig) -> PipelineRunSummary:
    analysis_dir = config.analysis_dir
    figures_dir = config.figures_dir
    ensure_dir(analysis_dir)
    ensure_dir(figures_dir)

    # Section 0: inventory.
    inventory_df, inventory_summary, inv_warnings = build_inventory(config)

    # Section 1: strategy reconstruction.
    write_strategy_reconstruction(
        repo_root=config.repo_root,
        out_path=analysis_dir / "strategy_reconstruction.md",
    )

    # Section 2: reconciliation + baseline.
    recon = reconcile_trades(config)
    reconciled_df = recon.reconciled_df
    trade_summary_df = recon.summary_df

    inventory_df = apply_reconciliation_coverage(inventory_df, reconciled_df)

    usable_dates, excluded_dates = _filter_usable_dates(
        inventory_df=inventory_df,
        reconciled_df=reconciled_df,
        min_trades_per_day=config.min_trades_per_day,
    )

    usable_reconciled = reconciled_df[
        (reconciled_df["match_status"] == "reconciled")
        & (reconciled_df["date"].isin(usable_dates))
    ].copy()

    baseline_df = compute_baseline_metrics(usable_reconciled)

    # Section 3: early-path features.
    loader = TradePathLoader(logs_dir=config.logs_dir, warnings=[])
    features_df, features_long_df, availability_df = build_checkpoint_features(usable_reconciled, loader)

    # Section 4: rules.
    rule_eval_df, labeled_features_df, rule_specs = evaluate_rules(features_df)

    # Section 5: scenarios.
    policy_specs = build_policy_specs()
    policy_df = simulate_policies(labeled_features_df, policies=policy_specs)

    # Section 6: winner vs loser.
    winner_loser_df = compare_winner_loser_shapes(labeled_features_df)

    # Section 7: operational forensics.
    operational_df = identify_operational_failures(usable_reconciled, labeled_features_df)

    # Section 8: robustness.
    robustness_df = validate_robustness(
        labeled_feature_df=labeled_features_df,
        rule_specs=rule_specs,
        rule_eval_df=rule_eval_df,
        policy_specs=policy_specs,
        policy_df=policy_df,
    )

    # Section 10: plots.
    if not config.skip_plots:
        generate_figures(
            out_dir=figures_dir,
            reconciled_df=usable_reconciled,
            feature_df=labeled_features_df,
            rule_df=rule_eval_df,
            scenario_df=policy_df,
            inventory_df=inventory_df,
        )

    # Section 9: final recommendation.
    rec_meta = write_final_recommendation(
        out_path=analysis_dir / "final_recommendation.md",
        inventory_df=inventory_df,
        baseline_df=baseline_df,
        rule_df=rule_eval_df,
        policy_df=policy_df,
        winner_loser_df=winner_loser_df,
        operational_df=operational_df,
        robustness_df=robustness_df,
    )

    # Optional artifacts.
    write_top_candidate_rules(rule_eval_df, analysis_dir / "top_candidate_rules.md")

    warnings_df = pd.DataFrame({"warning": inv_warnings + recon.warnings + loader.warnings})
    availability_summary = (
        availability_df.groupby("date", dropna=False)
        .agg(
            trade_count=("trade_id", "nunique"),
            has_trade_ticks_ratio=("has_trade_ticks", "mean"),
            has_underlying_ticks_ratio=("has_underlying_ticks", "mean"),
            has_futures_ticks_ratio=("has_futures_ticks", "mean"),
            has_depth_ratio=("has_depth", "mean"),
            has_subsecond_ratio=("has_subsecond_time", "mean"),
        )
        .reset_index()
        if not availability_df.empty
        else pd.DataFrame(
            columns=[
                "date",
                "trade_count",
                "has_trade_ticks_ratio",
                "has_underlying_ticks_ratio",
                "has_futures_ticks_ratio",
                "has_depth_ratio",
                "has_subsecond_ratio",
            ]
        )
    )

    # Required outputs.
    write_df(inventory_df, analysis_dir / "datewise_data_coverage.csv")
    write_df(reconciled_df, analysis_dir / "reconciled_trade_inventory.csv")
    write_df(trade_summary_df, analysis_dir / "trade_reconciliation_summary.csv")
    write_df(baseline_df, analysis_dir / "baseline_metrics.csv")
    write_df(features_df, analysis_dir / "early_path_features.csv")
    write_df(features_long_df, analysis_dir / "early_path_features_long.csv")
    write_df(rule_eval_df, analysis_dir / "checkpoint_rule_evaluation.csv")
    write_df(policy_df, analysis_dir / "policy_scenario_lab.csv")
    write_df(winner_loser_df, analysis_dir / "winner_vs_loser_shape.csv")
    write_df(operational_df, analysis_dir / "operational_failure_cases.csv")
    write_df(robustness_df, analysis_dir / "robustness_validation.csv")

    # Optional helpful outputs.
    write_df(warnings_df, analysis_dir / "data_quality_warnings.csv")
    write_df(availability_summary, analysis_dir / "feature_availability_summary.csv")

    best_1s = best_rule_for_checkpoint(rule_eval_df, checkpoint=1.0)
    best_3s = best_rule_for_checkpoint(rule_eval_df, checkpoint=3.0)
    best_policy = policy_df.iloc[0].to_dict() if not policy_df.empty else None

    summary_json = build_research_summary(
        inventory_df=inventory_df,
        inventory_summary=inventory_summary,
        extra={
            "usable_dates": usable_dates,
            "excluded_dates": excluded_dates,
            "total_trades_seen": int(reconciled_df.trade_id.nunique()) if not reconciled_df.empty else 0,
            "reconciled_closed_trades": int(usable_reconciled.shape[0]),
            "best_simple_1s_rule": best_1s.get("rule_id") if best_1s else None,
            "best_simple_3s_rule": best_3s.get("rule_id") if best_3s else None,
            "best_scenario_policy": best_policy.get("policy_id") if best_policy else None,
            "estimated_tail_loss_reduction": (
                float(best_policy.get("tail_losers_prevented", 0))
                if best_policy is not None
                else None
            ),
            "key_caveat": rec_meta.get("key_caveat"),
        },
    )
    write_json(summary_json, analysis_dir / "research_summary.json")

    run_summary = PipelineRunSummary(
        usable_dates=usable_dates,
        excluded_dates=excluded_dates,
        total_trades_seen=int(reconciled_df.trade_id.nunique()) if not reconciled_df.empty else 0,
        reconciled_closed_trades=int(usable_reconciled.shape[0]),
        best_simple_1s_rule=best_1s.get("rule_id") if best_1s else None,
        best_simple_3s_rule=best_3s.get("rule_id") if best_3s else None,
        best_scenario_policy=best_policy.get("policy_id") if best_policy else None,
        estimated_tail_loss_reduction=(
            float(best_policy.get("tail_losers_prevented", 0)) if best_policy is not None else None
        ),
        key_caveat=rec_meta.get("key_caveat", ""),
    )

    return run_summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run tail-loss research pipeline offline")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--output-dir", default="analysis", help="Output directory")
    parser.add_argument("--start-date", default=None, help="Optional start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="Optional end date YYYY-MM-DD")
    parser.add_argument("--include-archived", action="store_true", help="Include archived zip inventories")
    parser.add_argument("--skip-plots", action="store_true", help="Skip PNG generation")
    parser.add_argument("--min-trades-per-day", type=int, default=1, help="Minimum trades per day to include")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser


def run_pipeline_from_args(args: argparse.Namespace) -> PipelineRunSummary:
    cfg = PipelineConfig(
        repo_root=Path(args.repo_root).resolve(),
        output_dir=Path(args.output_dir),
        start_date=args.start_date,
        end_date=args.end_date,
        include_archived=bool(args.include_archived),
        skip_plots=bool(args.skip_plots),
        min_trades_per_day=max(1, int(args.min_trades_per_day)),
        verbose=bool(args.verbose),
    )
    return run_pipeline(cfg)
