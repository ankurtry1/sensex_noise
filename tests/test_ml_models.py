from __future__ import annotations

import numpy as np
import pandas as pd

from analysis_pipeline.ml_models import (
    apply_multiclass_fallback,
    build_preprocessor,
    fit_sigmoid_calibrator,
    generate_walk_forward_folds,
    tune_binary_threshold,
)


def test_generate_walk_forward_folds_are_strictly_date_ordered() -> None:
    df = pd.DataFrame(
        {
            "trade_id": [f"T{i}" for i in range(5)],
            "date": pd.date_range("2026-04-10", periods=5, freq="D").strftime("%Y-%m-%d"),
        }
    )

    folds = generate_walk_forward_folds(df, eval_start_date="2026-04-13", min_train_dates=3)

    assert len(folds) == 2
    assert folds[0].fit_dates == ("2026-04-10", "2026-04-11")
    assert folds[0].calibration_dates == ("2026-04-12",)
    assert folds[0].eval_dates == ("2026-04-13",)
    assert max(folds[1].fit_dates) < folds[1].calibration_dates[0] < folds[1].eval_dates[0]


def test_tune_binary_threshold_entry_respects_retention_constraint() -> None:
    validation = pd.DataFrame(
        {
            "predicted_prob_bad": [0.10, 0.20, 0.90, 0.95],
            "gross_pnl": [100.0, 100.0, -100.0, -100.0],
            "label_bad_trade": [0, 0, 1, 1],
        }
    )

    threshold, sweep = tune_binary_threshold(
        validation,
        layer_name="entry_filter",
        threshold_grid=np.array([0.20, 0.50, 0.95]),
        min_trade_retention=0.60,
    )

    assert threshold == 0.95
    chosen = sweep.loc[sweep["threshold"] == threshold].iloc[0]
    assert bool(chosen["feasible"])
    assert chosen["retained_trade_ratio"] >= 0.60


def test_apply_multiclass_fallback_uses_current_bucket_when_confidence_is_low() -> None:
    frame = pd.DataFrame(
        {
            "current_bucket": ["keep_3", "extend_to_7"],
            "prob_keep_3": [0.40, 0.05],
            "prob_extend_to_5": [0.35, 0.10],
            "prob_extend_to_7": [0.25, 0.85],
        }
    )

    scored = apply_multiclass_fallback(
        frame,
        fallback_bucket_col="current_bucket",
        fallback_confidence=0.55,
    )

    assert scored.loc[0, "predicted_bucket_raw"] == "keep_3"
    assert bool(scored.loc[0, "used_fallback_to_current_bucket"])
    assert scored.loc[0, "predicted_bucket"] == "keep_3"
    assert not bool(scored.loc[1, "used_fallback_to_current_bucket"])
    assert scored.loc[1, "predicted_bucket"] == "extend_to_7"


def test_preprocessor_uses_train_median_for_missing_test_values() -> None:
    train = pd.DataFrame({"x": [1.0, np.nan, 3.0], "kind": ["a", "a", "b"]})
    test = pd.DataFrame({"x": [np.nan], "kind": ["a"]})

    preprocessor = build_preprocessor(["x"], ["kind"], scale_numeric=False)
    preprocessor.fit(train)
    transformed = preprocessor.transform(test)

    assert transformed.shape[0] == 1
    assert transformed[0, 0] == 2.0


def test_sigmoid_calibration_preserves_row_alignment() -> None:
    raw_prob = np.array([0.1, 0.2, 0.8, 0.9], dtype=float)
    labels = pd.Series([0, 0, 1, 1])

    calibrator = fit_sigmoid_calibrator(raw_prob, labels)
    calibrated = calibrator.predict_proba(raw_prob.reshape(-1, 1))[:, 1]

    assert len(calibrated) == len(raw_prob)
    assert calibrated[0] < calibrated[-1]
