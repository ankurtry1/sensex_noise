from __future__ import annotations

from pathlib import Path

CHECKPOINT_SECONDS: tuple[float, ...] = (0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0)
RULE_CHECKPOINT_SECONDS: tuple[float, ...] = (0.5, 1.0, 2.0, 3.0, 5.0)

CONFIDENCE_BUCKETS = ("HIGH", "MEDIUM", "LOW", "UNUSABLE")

DEFAULT_DATE_GLOB = "20??-??-??"

LOGS_DIRNAME = "logs"
TRADES_SUBDIR = "trades"
EVENTS_SUBDIR = "events"
TICKS_SUBDIR = "ticks"
TRADE_TICKS_SUBDIR = "trade_ticks"

REQUIRED_OUTPUT_FILES = (
    "reconciled_trade_inventory.csv",
    "datewise_data_coverage.csv",
    "early_path_features.csv",
    "checkpoint_rule_evaluation.csv",
    "policy_scenario_lab.csv",
    "winner_vs_loser_shape.csv",
    "operational_failure_cases.csv",
    "final_recommendation.md",
    "research_summary.json",
    "baseline_metrics.csv",
    "trade_reconciliation_summary.csv",
    "strategy_reconstruction.md",
    "robustness_validation.csv",
)

FIGURES_DIRNAME = "figures"

OPTIONAL_OUTPUT_FILES = (
    "top_candidate_rules.md",
    "data_quality_warnings.csv",
    "feature_availability_summary.csv",
)


def analysis_path(root: Path, output_dir: Path, name: str) -> Path:
    if output_dir.is_absolute():
        return output_dir / name
    return root / output_dir / name
