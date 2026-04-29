from __future__ import annotations

import pandas as pd

from analysis_pipeline.ml_policy_eval import evaluate_combined_policy


def test_evaluate_combined_policy_applies_decision_order() -> None:
    canonical = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "date": "2026-04-14",
                "gross_pnl": 1000.0,
                "current_bucket": "keep_3",
                "label_bad_trade": 0,
                "trade_alive_at_1s": True,
                "trade_alive_at_3s": True,
                "exit_cut_points_1s": 0.5,
                "exit_cut_points_3s": 1.0,
                "best_possible_points": 7.0,
                "fallback_hold_points": 4.0,
            },
            {
                "trade_id": "T2",
                "date": "2026-04-14",
                "gross_pnl": -2000.0,
                "current_bucket": "keep_3",
                "label_bad_trade": 1,
                "trade_alive_at_1s": True,
                "trade_alive_at_3s": True,
                "exit_cut_points_1s": -1.0,
                "exit_cut_points_3s": -2.0,
                "best_possible_points": 1.0,
                "fallback_hold_points": -2.0,
            },
            {
                "trade_id": "T3",
                "date": "2026-04-14",
                "gross_pnl": -1500.0,
                "current_bucket": "keep_3",
                "label_bad_trade": 1,
                "trade_alive_at_1s": True,
                "trade_alive_at_3s": True,
                "exit_cut_points_1s": -1.0,
                "exit_cut_points_3s": -0.5,
                "best_possible_points": 1.0,
                "fallback_hold_points": -1.0,
            },
            {
                "trade_id": "T4",
                "date": "2026-04-14",
                "gross_pnl": 1500.0,
                "current_bucket": "keep_3",
                "label_bad_trade": 0,
                "trade_alive_at_1s": True,
                "trade_alive_at_3s": True,
                "exit_cut_points_1s": 0.5,
                "exit_cut_points_3s": 1.0,
                "best_possible_points": 7.0,
                "fallback_hold_points": 4.0,
            },
            {
                "trade_id": "T5",
                "date": "2026-04-14",
                "gross_pnl": -500.0,
                "current_bucket": "keep_3",
                "label_bad_trade": 1,
                "trade_alive_at_1s": False,
                "trade_alive_at_3s": False,
                "exit_cut_points_1s": None,
                "exit_cut_points_3s": None,
                "best_possible_points": 1.0,
                "fallback_hold_points": -1.0,
            },
        ]
    )

    entry_predictions = pd.DataFrame(
        [
            {"trade_id": "T1", "model": "hgb", "predicted_prob_bad": 0.90, "threshold_used": 0.50, "predicted_bad_trade": 1},
            {"trade_id": "T2", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
            {"trade_id": "T3", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
            {"trade_id": "T4", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
            {"trade_id": "T5", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
        ]
    )
    exit_1s_predictions = pd.DataFrame(
        [
            {"trade_id": "T2", "model": "hgb", "predicted_prob_bad": 0.80, "threshold_used": 0.50, "predicted_bad_trade": 1},
            {"trade_id": "T3", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
            {"trade_id": "T4", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
        ]
    )
    exit_3s_predictions = pd.DataFrame(
        [
            {"trade_id": "T2", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
            {"trade_id": "T3", "model": "hgb", "predicted_prob_bad": 0.80, "threshold_used": 0.50, "predicted_bad_trade": 1},
            {"trade_id": "T4", "model": "hgb", "predicted_prob_bad": 0.10, "threshold_used": 0.50, "predicted_bad_trade": 0},
        ]
    )
    target_predictions = pd.DataFrame(
        [
            {
                "trade_id": "T4",
                "model": "hgb",
                "predicted_bucket": "extend_to_7",
                "predicted_confidence": 0.80,
                "used_fallback_to_current_bucket": False,
            }
        ]
    )

    result = evaluate_combined_policy(
        canonical,
        entry_predictions=entry_predictions,
        exit_1s_predictions=exit_1s_predictions,
        exit_3s_predictions=exit_3s_predictions,
        target_predictions=target_predictions,
        selected_entry_model_name="hgb",
        selected_exit_model_name="hgb",
        selected_target_model_name="hgb",
    )
    audit = result.per_trade.set_index("trade_id")

    assert audit.loc["T1", "policy_reason"] == "entry_filtered"
    assert audit.loc["T1", "policy_pnl"] == 0.0
    assert audit.loc["T2", "policy_reason"] == "bad_exit_1s"
    assert audit.loc["T2", "policy_pnl"] == -500.0
    assert audit.loc["T3", "policy_reason"] == "bad_exit_3s"
    assert audit.loc["T3", "policy_pnl"] == -250.0
    assert audit.loc["T4", "policy_reason"] == "target_promotion"
    assert audit.loc["T4", "policy_pnl"] == 3500.0
    assert audit.loc["T5", "policy_reason"] == "actual_realized"
    assert audit.loc["T5", "policy_pnl"] == -500.0
