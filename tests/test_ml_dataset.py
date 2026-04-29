from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis_pipeline.ml_dataset import build_canonical_ml_dataset, build_ml_dataset_views


def test_build_ml_dataset_views_live_target_excludes_early_path_features() -> None:
    canonical = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "date": "2026-04-14",
                "symbol": "OPT1",
                "signal_kind": "CONTINUATION_CALL",
                "side": "CALL",
                "entry_time": "2026-04-14T09:20:00",
                "exit_time": "2026-04-14T09:20:05",
                "entry_price": 100.0,
                "exit_price": 103.0,
                "gross_pnl": 1500.0,
                "net_pnl": 1400.0,
                "holding_seconds": 5.0,
                "exit_reason": "TARGET_HIT",
                "pre_or_post_1pm": "pre_1pm",
                "continuation_or_reversal": "continuation",
                "call_or_put": "call",
                "burst_score_reconstructed": 6.0,
                "label_bad_trade": False,
                "label_target_bucket": "extend_to_7",
                "ml_ready_entry_features": True,
                "ml_ready_target_label": True,
                "current_bucket": "extend_to_7",
                "actual_points": 3.0,
                "best_possible_points": 7.0,
                "fallback_hold_points": 4.0,
                "trade_alive_at_1s": True,
                "trade_alive_at_3s": True,
                "exit_cut_points_1s": 0.5,
                "exit_cut_points_3s": 1.0,
                "idx_pre_velocity_aligned": 1.2,
                "idx_pre_accel_aligned": 0.3,
                "opt_pre_velocity_5s": 1.1,
                "opt_pre_depth_imb_mean": 0.2,
                "opt_pre_spread_mean": 0.1,
                "pre_entry_option_tick_count": 20,
                "pre_entry_index_tick_count": 30,
                "feat_pnl_1s": 1.0,
                "feat_pnl_3s": 3.0,
            }
        ]
    )

    views = build_ml_dataset_views(canonical)

    assert "feat_pnl_1s" not in views["target_promotion_live"].columns
    assert "feat_pnl_3s" not in views["target_promotion_live"].columns
    assert "feat_pnl_1s" in views["target_promotion_shadow"].columns
    assert bool(views["target_promotion_live"].loc[0, "target_live_trainable"]) is True
    assert bool(views["target_promotion_shadow"].loc[0, "target_shadow_trainable"]) is True


def test_build_canonical_ml_dataset_unifies_schema_era_features(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    analysis_dir = repo_root / "analysis"
    logs_dir = repo_root / "logs" / "trades"
    analysis_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)

    inventory = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "date": "2026-04-10",
                "entry_time": "2026-04-10T09:20:00",
                "exit_time": "2026-04-10T09:20:04",
                "entry_price": 100.0,
                "exit_price": 103.0,
                "gross_pnl": 1500.0,
                "net_pnl": 1450.0,
                "hold_seconds": 4.0,
                "exit_reason": "TARGET_HIT",
                "pre_or_post_1pm": "pre_1pm",
                "continuation_or_reversal": "continuation",
                "call_or_put": "call",
                "post_exit_points_best_recovery": 3.0,
                "post_exit_final_delta_15s": 1.5,
            },
            {
                "trade_id": "T2",
                "date": "2026-04-10",
                "entry_time": "2026-04-10T09:25:00",
                "exit_time": "2026-04-10T09:25:00.500000",
                "entry_price": 100.0,
                "exit_price": 99.0,
                "gross_pnl": -500.0,
                "net_pnl": -550.0,
                "hold_seconds": 0.5,
                "exit_reason": "EARLY_FAIL_1S",
                "pre_or_post_1pm": "pre_1pm",
                "continuation_or_reversal": "reversal",
                "call_or_put": "put",
            },
        ]
    )
    early = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "pnl_1p0s": 1.5,
                "runup_1p0s": 2.5,
                "drawdown_1p0s": -0.5,
                "pnl_3p0s": 3.5,
                "runup_3p0s": 4.5,
                "drawdown_3p0s": -1.0,
                "velocity_0_1s_reconstructed": 2.0,
                "velocity_2_3s_reconstructed": 1.0,
                "burst_score_reconstructed": 4.0,
            }
        ]
    )
    inventory.to_csv(analysis_dir / "reconciled_trade_inventory.csv", index=False)
    early.to_csv(analysis_dir / "early_path_features.csv", index=False)

    canonical = build_canonical_ml_dataset(repo_root, analysis_dir=analysis_dir)
    first = canonical.loc[canonical["trade_id"] == "T1"].iloc[0]
    second = canonical.loc[canonical["trade_id"] == "T2"].iloc[0]

    assert first["feat_pnl_1s"] == 1.5
    assert first["feat_runup_1s"] == 2.5
    assert first["feat_pnl_3s"] == 3.5
    assert first["feat_velocity_decay_ratio"] == 0.5
    assert bool(first["trade_alive_at_1s"]) is True
    assert bool(first["trade_alive_at_3s"]) is True
    assert first["label_target_bucket"] == "extend_to_5"
    assert bool(second["trade_alive_at_1s"]) is False
    assert bool(second["trade_alive_at_3s"]) is False
    assert bool(second["label_bad_trade"]) is True
