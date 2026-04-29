from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .io_utils import ensure_dir
from .ml_models import LayerTrainingResult, save_model_bundle
from .ml_policy_eval import PolicyEvaluationResult


def render_markdown_table(df: pd.DataFrame, *, decimals: int = 3) -> str:
    if df.empty:
        return "| empty |\n| --- |"
    frame = df.copy()
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]):
            frame[column] = frame[column].map(
                lambda value: ""
                if pd.isna(value)
                else (
                    f"{float(value):.{decimals}f}"
                    if isinstance(value, (int, float, np.integer, np.floating))
                    else value
                )
            )
        else:
            frame[column] = frame[column].fillna("")
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in frame.columns) + " |")
    return "\n".join(lines)


def _classification_report_frame(report: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, metrics in report.items():
        if not isinstance(metrics, dict):
            rows.append({"label": label, "score": metrics})
            continue
        rows.append(
            {
                "label": label,
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1_score": metrics.get("f1-score"),
                "support": metrics.get("support"),
            }
        )
    return pd.DataFrame(rows)


def _folds_frame(training_result: LayerTrainingResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fold_id": fold.fold_id,
                "fit_dates": ",".join(fold.fit_dates),
                "calibration_dates": ",".join(fold.calibration_dates),
                "eval_dates": ",".join(fold.eval_dates),
            }
            for fold in training_result.folds
        ]
    )


def _merge_model_and_policy_metrics(
    training_result: LayerTrainingResult,
    policy_results: dict[str, PolicyEvaluationResult],
) -> pd.DataFrame:
    base = training_result.model_comparison.copy()
    rows: list[dict[str, Any]] = []
    for model_name, policy_result in policy_results.items():
        row = {"model": model_name}
        row.update(policy_result.summary)
        rows.append(row)
    policy_df = pd.DataFrame(rows)
    if base.empty:
        return policy_df
    if policy_df.empty:
        return base
    return base.merge(policy_df, on="model", how="left")


def write_binary_layer_outputs(
    output_dir: Path,
    *,
    title: str,
    training_result: LayerTrainingResult,
    policy_results: dict[str, PolicyEvaluationResult],
) -> None:
    ensure_dir(output_dir)
    training_result.feature_mapping.to_csv(output_dir / "feature_mapping.csv", index=False)
    _folds_frame(training_result).to_csv(output_dir / "walk_forward_folds.csv", index=False)
    comparison = _merge_model_and_policy_metrics(training_result, policy_results)
    comparison.to_csv(output_dir / "model_comparison.csv", index=False)

    lines = [f"# {title}", "", "## Model Comparison", "", render_markdown_table(comparison), ""]
    used_features = training_result.feature_mapping.loc[
        training_result.feature_mapping["status"] == "used", "feature"
    ].tolist()
    lines.append("## Features")
    lines.append("")
    lines.extend([f"- `{feature}`" for feature in used_features] or ["- None"])

    for model_name, model_result in training_result.model_results.items():
        predictions_path = output_dir / f"predictions_{model_name}.csv"
        threshold_path = output_dir / f"threshold_sweep_{model_name}.csv"
        confusion_path = output_dir / f"confusion_matrix_{model_name}.csv"
        report_path = output_dir / f"classification_report_{model_name}.csv"
        daywise_path = output_dir / f"policy_daywise_{model_name}.csv"
        bundle_path = output_dir / f"model_bundle_{model_name}.joblib"

        model_result.predictions.to_csv(predictions_path, index=False)
        model_result.threshold_sweep.to_csv(threshold_path, index=False)
        if model_result.confusion_matrix is not None:
            model_result.confusion_matrix.to_csv(confusion_path)
        if model_result.classification_report is not None:
            _classification_report_frame(model_result.classification_report).to_csv(report_path, index=False)
        if model_name in policy_results:
            policy_results[model_name].daywise.to_csv(daywise_path, index=False)
        save_model_bundle(model_result.final_model_bundle, bundle_path)

        lines.extend(
            [
                "",
                f"## {model_name.title()}",
                "",
                render_markdown_table(pd.DataFrame([model_result.model_metrics])),
                "",
                "Policy summary:",
                "",
                render_markdown_table(pd.DataFrame([policy_results[model_name].summary])),
            ]
        )
        if model_result.confusion_matrix is not None:
            lines.extend(["", "Confusion matrix:", "", render_markdown_table(model_result.confusion_matrix.reset_index())])

    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_multiclass_layer_outputs(
    output_dir: Path,
    *,
    title: str,
    training_result: LayerTrainingResult,
    policy_results: dict[str, PolicyEvaluationResult],
) -> None:
    ensure_dir(output_dir)
    training_result.feature_mapping.to_csv(output_dir / "feature_mapping.csv", index=False)
    _folds_frame(training_result).to_csv(output_dir / "walk_forward_folds.csv", index=False)
    comparison = _merge_model_and_policy_metrics(training_result, policy_results)
    comparison.to_csv(output_dir / "model_comparison.csv", index=False)

    lines = [f"# {title}", "", "## Model Comparison", "", render_markdown_table(comparison), ""]
    used_features = training_result.feature_mapping.loc[
        training_result.feature_mapping["status"] == "used", "feature"
    ].tolist()
    lines.append("## Features")
    lines.append("")
    lines.extend([f"- `{feature}`" for feature in used_features] or ["- None"])

    for model_name, model_result in training_result.model_results.items():
        predictions_path = output_dir / f"predictions_{model_name}.csv"
        confusion_path = output_dir / f"confusion_matrix_{model_name}.csv"
        report_path = output_dir / f"classification_report_{model_name}.csv"
        daywise_path = output_dir / f"policy_daywise_{model_name}.csv"
        bundle_path = output_dir / f"model_bundle_{model_name}.joblib"

        model_result.predictions.to_csv(predictions_path, index=False)
        if model_result.confusion_matrix is not None:
            model_result.confusion_matrix.to_csv(confusion_path)
        if model_result.classification_report is not None:
            _classification_report_frame(model_result.classification_report).to_csv(report_path, index=False)
        if model_name in policy_results:
            policy_results[model_name].daywise.to_csv(daywise_path, index=False)
        save_model_bundle(model_result.final_model_bundle, bundle_path)

        lines.extend(
            [
                "",
                f"## {model_name.title()}",
                "",
                render_markdown_table(pd.DataFrame([model_result.model_metrics])),
                "",
                "Policy summary:",
                "",
                render_markdown_table(pd.DataFrame([policy_results[model_name].summary])),
            ]
        )
        if model_result.confusion_matrix is not None:
            lines.extend(["", "Confusion matrix:", "", render_markdown_table(model_result.confusion_matrix.reset_index())])

    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_combined_policy_outputs(
    output_dir: Path,
    *,
    combined_eval: PolicyEvaluationResult,
    live_readiness_scorecard: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    ensure_dir(output_dir)
    combined_eval.per_trade.to_csv(output_dir / "combined_policy_trade_audit.csv", index=False)
    combined_eval.daywise.to_csv(output_dir / "combined_policy_daywise.csv", index=False)
    live_readiness_scorecard.to_csv(output_dir / "live_readiness_scorecard.csv", index=False)
    (output_dir / "combined_policy_metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    scorecard_lines = [
        "# Live Readiness Scorecard",
        "",
        render_markdown_table(live_readiness_scorecard),
        "",
    ]
    (output_dir / "live_readiness_scorecard.md").write_text(
        "\n".join(scorecard_lines),
        encoding="utf-8",
    )

    report_lines = [
        "# Combined Shadow ML Policy",
        "",
        "## Summary",
        "",
        render_markdown_table(pd.DataFrame([combined_eval.summary])),
        "",
        "## Day-wise PnL",
        "",
        render_markdown_table(combined_eval.daywise),
        "",
        "## Live Readiness",
        "",
        render_markdown_table(live_readiness_scorecard),
        "",
    ]
    (output_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")
