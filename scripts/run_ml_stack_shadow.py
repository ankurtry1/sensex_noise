from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_pipeline.io_utils import ensure_dir
from analysis_pipeline.ml_dataset import (
    BAD_EXIT_1S_NUMERIC_FEATURES,
    BAD_EXIT_3S_NUMERIC_FEATURES,
    PRE_ENTRY_CATEGORICAL_FEATURES,
    PRE_ENTRY_NUMERIC_FEATURES,
    TARGET_SHADOW_NUMERIC_FEATURES,
    write_ml_datasets,
)
from analysis_pipeline.ml_models import train_binary_layer, train_multiclass_layer
from analysis_pipeline.ml_policy_eval import (
    build_live_readiness_scorecard,
    evaluate_bad_trade_exit_policy,
    evaluate_bad_trade_exit_stack,
    evaluate_combined_policy,
    evaluate_entry_filter_policy,
    evaluate_target_promotion_policy,
)
from analysis_pipeline.ml_reporting import (
    write_binary_layer_outputs,
    write_combined_policy_outputs,
    write_multiclass_layer_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the shadow ML stack end-to-end.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--analysis-dir", default="analysis", help="Analysis artifact directory.")
    parser.add_argument(
        "--output-dir",
        default="analysis/ml_stack_results",
        help="Directory where ML stack outputs should be written.",
    )
    parser.add_argument("--post-patch-start", default="2026-04-13", help="Post-patch boundary date.")
    parser.add_argument(
        "--eval-start-date",
        default=None,
        help="Optional walk-forward evaluation start date. Defaults to post-patch start.",
    )
    parser.add_argument(
        "--refresh-analysis",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh analysis artifacts before ML training.",
    )
    parser.add_argument(
        "--skip-plots",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip analysis plot generation during refresh.",
    )
    parser.add_argument(
        "--selected-target-policy-model",
        choices=["logistic", "hgb"],
        default="hgb",
        help="Target-promotion model used in the final combined shadow policy.",
    )
    return parser.parse_args()


def _resolve_path(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (repo_root / path)


def _concat_model_predictions(training_result) -> pd.DataFrame:
    frames = [result.predictions for result in training_result.model_results.values()]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    analysis_dir = _resolve_path(repo_root, args.analysis_dir)
    output_dir = _resolve_path(repo_root, args.output_dir)
    eval_start_date = args.eval_start_date or args.post_patch_start

    ensure_dir(analysis_dir)
    ensure_dir(output_dir)

    if args.refresh_analysis:
        from analysis_pipeline.cli import run_pipeline_from_args

        run_pipeline_from_args(
            argparse.Namespace(
                repo_root=str(repo_root),
                output_dir=str(analysis_dir),
                start_date=None,
                end_date=None,
                include_archived=False,
                skip_plots=bool(args.skip_plots),
                min_trades_per_day=1,
                verbose=False,
            )
        )

    dataset_paths = write_ml_datasets(repo_root, analysis_dir, analysis_dir=analysis_dir)
    canonical = pd.read_csv(dataset_paths["canonical"], low_memory=False)
    entry_dataset = pd.read_csv(dataset_paths["entry_filter"], low_memory=False)
    exit_1s_dataset = pd.read_csv(dataset_paths["bad_trade_exit_1s"], low_memory=False)
    exit_3s_dataset = pd.read_csv(dataset_paths["bad_trade_exit_3s"], low_memory=False)
    target_live_dataset = pd.read_csv(dataset_paths["target_promotion_live"], low_memory=False)

    exit_1s_dataset["exit_cut_points"] = pd.to_numeric(
        exit_1s_dataset.get("exit_cut_points_1s"),
        errors="coerce",
    )
    exit_3s_dataset["exit_cut_points"] = pd.to_numeric(
        exit_3s_dataset.get("exit_cut_points_3s"),
        errors="coerce",
    )
    target_live_train = target_live_dataset.loc[
        pd.to_numeric(target_live_dataset.get("target_live_trainable"), errors="coerce").fillna(0).astype(bool)
    ].copy()

    entry_training = train_binary_layer(
        entry_dataset,
        layer_name="entry_filter",
        label_col="label_bad_trade_int",
        numeric_candidates=PRE_ENTRY_NUMERIC_FEATURES,
        categorical_candidates=PRE_ENTRY_CATEGORICAL_FEATURES,
        eval_start_date=eval_start_date,
    )
    exit_1s_training = train_binary_layer(
        exit_1s_dataset,
        layer_name="bad_trade_exit",
        label_col="label_exit_bad_trade",
        numeric_candidates=BAD_EXIT_1S_NUMERIC_FEATURES,
        categorical_candidates=PRE_ENTRY_CATEGORICAL_FEATURES,
        eval_start_date=eval_start_date,
    )
    exit_3s_training = train_binary_layer(
        exit_3s_dataset,
        layer_name="bad_trade_exit",
        label_col="label_exit_bad_trade",
        numeric_candidates=BAD_EXIT_3S_NUMERIC_FEATURES,
        categorical_candidates=PRE_ENTRY_CATEGORICAL_FEATURES,
        eval_start_date=eval_start_date,
    )
    target_training = train_multiclass_layer(
        target_live_train,
        layer_name="target_promotion",
        label_col="label_target_bucket",
        numeric_candidates=PRE_ENTRY_NUMERIC_FEATURES,
        categorical_candidates=PRE_ENTRY_CATEGORICAL_FEATURES,
        eval_start_date=eval_start_date,
    )

    entry_policy_results = {
        model_name: evaluate_entry_filter_policy(model_result.predictions, model_name=model_name)
        for model_name, model_result in entry_training.model_results.items()
    }
    exit_1s_policy_results = {
        model_name: evaluate_bad_trade_exit_policy(model_result.predictions, model_name=model_name)
        for model_name, model_result in exit_1s_training.model_results.items()
    }
    exit_3s_policy_results = {
        model_name: evaluate_bad_trade_exit_policy(model_result.predictions, model_name=model_name)
        for model_name, model_result in exit_3s_training.model_results.items()
    }
    target_policy_results = {
        model_name: evaluate_target_promotion_policy(model_result.predictions, model_name=model_name)
        for model_name, model_result in target_training.model_results.items()
    }

    selected_entry_model = "hgb" if "hgb" in entry_training.model_results else next(iter(entry_training.model_results))
    selected_exit_model = "hgb" if "hgb" in exit_1s_training.model_results else next(iter(exit_1s_training.model_results))
    selected_target_model = (
        args.selected_target_policy_model
        if args.selected_target_policy_model in target_training.model_results
        else next(iter(target_training.model_results))
    )

    canonical_eval = canonical.loc[pd.to_datetime(canonical["date"], errors="coerce") >= pd.Timestamp(eval_start_date)].copy()
    all_entry_predictions = _concat_model_predictions(entry_training)
    all_exit_1s_predictions = _concat_model_predictions(exit_1s_training)
    all_exit_3s_predictions = _concat_model_predictions(exit_3s_training)
    all_target_predictions = _concat_model_predictions(target_training)

    exit_stack_eval = evaluate_bad_trade_exit_stack(
        canonical_eval,
        exit_1s_predictions=all_exit_1s_predictions,
        exit_3s_predictions=all_exit_3s_predictions,
        selected_model_name=selected_exit_model,
    )
    combined_eval = evaluate_combined_policy(
        canonical_eval,
        entry_predictions=all_entry_predictions,
        exit_1s_predictions=all_exit_1s_predictions,
        exit_3s_predictions=all_exit_3s_predictions,
        target_predictions=all_target_predictions,
        selected_entry_model_name=selected_entry_model,
        selected_exit_model_name=selected_exit_model,
        selected_target_model_name=selected_target_model,
    )
    scorecard = build_live_readiness_scorecard(
        canonical_eval,
        entry_eval=entry_policy_results[selected_entry_model],
        exit_eval=exit_stack_eval,
        target_eval=target_policy_results[selected_target_model],
        combined_eval=combined_eval,
        post_patch_start=args.post_patch_start,
    )

    write_binary_layer_outputs(
        output_dir / "entry_filter",
        title="Entry Filter Shadow Model",
        training_result=entry_training,
        policy_results=entry_policy_results,
    )
    write_binary_layer_outputs(
        output_dir / "bad_trade_exit" / "checkpoint_1s",
        title="Bad Trade Exit Shadow Model (1s)",
        training_result=exit_1s_training,
        policy_results=exit_1s_policy_results,
    )
    write_binary_layer_outputs(
        output_dir / "bad_trade_exit" / "checkpoint_3s",
        title="Bad Trade Exit Shadow Model (3s)",
        training_result=exit_3s_training,
        policy_results=exit_3s_policy_results,
    )
    write_multiclass_layer_outputs(
        output_dir / "target_promotion",
        title="Target Promotion Shadow Model",
        training_result=target_training,
        policy_results=target_policy_results,
    )
    write_combined_policy_outputs(
        output_dir / "combined_policy",
        combined_eval=combined_eval,
        live_readiness_scorecard=scorecard,
        metadata={
            "repo_root": str(repo_root),
            "analysis_dir": str(analysis_dir),
            "eval_start_date": eval_start_date,
            "post_patch_start": args.post_patch_start,
            "selected_entry_model": selected_entry_model,
            "selected_exit_model": selected_exit_model,
            "selected_target_model": selected_target_model,
            "entry_dataset_rows": int(len(entry_dataset)),
            "exit_1s_dataset_rows": int(len(exit_1s_dataset)),
            "exit_3s_dataset_rows": int(len(exit_3s_dataset)),
            "target_live_train_rows": int(len(target_live_train)),
            "dataset_files": {name: str(path) for name, path in dataset_paths.items()},
        },
    )
    exit_stack_eval.per_trade.to_csv(output_dir / "bad_trade_exit" / "stack_selected_per_trade.csv", index=False)
    exit_stack_eval.daywise.to_csv(output_dir / "bad_trade_exit" / "stack_selected_daywise.csv", index=False)
    pd.DataFrame([exit_stack_eval.summary]).to_csv(
        output_dir / "bad_trade_exit" / "stack_selected_summary.csv",
        index=False,
    )

    summary = {
        "analysis_dir": str(analysis_dir),
        "output_dir": str(output_dir),
        "selected_entry_model": selected_entry_model,
        "selected_exit_model": selected_exit_model,
        "selected_target_model": selected_target_model,
        "combined_delta_vs_baseline_pnl": combined_eval.summary["delta_vs_baseline_pnl"],
        "combined_policy_total_pnl": combined_eval.summary["policy_total_pnl"],
        "combined_baseline_total_pnl": combined_eval.summary["baseline_total_pnl"],
        "live_gates_passed": int(scorecard["passed"].sum()),
        "live_gates_total": int(len(scorecard)),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
