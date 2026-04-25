from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from sensex_noise.services.microburst import (
    MicroburstFeatures,
    PromotionDiagnostics,
    classify_target,
    compute_promoted_3s_diagnostics,
    layer4_persistence_result,
    promoted_trade_survives_3s,
    score_microburst,
)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        microburst_ind_accel_threshold_1=1.688,
        microburst_ind_accel_threshold_2=3.945,
        microburst_opt_velocity_threshold=1.583,
        microburst_opt_depth_imb_threshold=0.0857,
        microburst_ind_velocity_min=1.646,
        microburst_ind_velocity_max=2.356,
        normal_target_points=3.0,
        promoted_min_score=5,
        promoted_target_points=7.0,
        promoted_3s_min_runup_points=4.0,
        promoted_3s_min_pnl_points=1.5,
        promoted_3s_max_mae_points=3.5,
        promoted_3s_min_velocity_decay_ratio=0.5,
        layer4_required_followthrough_points=4.5,
    )


def test_score_microburst_respects_threshold_boundaries() -> None:
    settings = _settings()
    features = MicroburstFeatures(
        ind_velocity_aligned=1.646,
        ind_accel_aligned=1.688,
        opt_velocity_aligned=1.583,
        opt_depth_imb_mean=0.0857,
        opt_spread_mean=0.5,
        score=0,
        score_components={},
    )

    score, components = score_microburst(features, settings)

    assert score == 0
    assert components == {
        "ind_accel_threshold_1": 0,
        "ind_accel_threshold_2": 0,
        "opt_velocity": 0,
        "opt_depth_imbalance": 0,
        "ind_velocity_band": 0,
    }


def test_score_microburst_accumulates_expected_components() -> None:
    settings = _settings()
    features = MicroburstFeatures(
        ind_velocity_aligned=2.0,
        ind_accel_aligned=4.2,
        opt_velocity_aligned=1.9,
        opt_depth_imb_mean=0.2,
        opt_spread_mean=0.4,
        score=0,
        score_components={},
    )

    score, components = score_microburst(features, settings)

    assert score == 6
    assert components == {
        "ind_accel_threshold_1": 2,
        "ind_accel_threshold_2": 1,
        "opt_velocity": 1,
        "opt_depth_imbalance": 1,
        "ind_velocity_band": 1,
    }


def test_classify_target_uses_score_bands() -> None:
    settings = _settings()

    assert classify_target(3, settings) == ("normal", 3.0)
    assert classify_target(4, settings) == ("normal", 3.0)
    assert classify_target(5, settings) == ("promoted", 7.0)


def test_promoted_trade_survives_3s_only_when_all_checks_pass() -> None:
    settings = _settings()
    diag = PromotionDiagnostics(
        velocity_0_1s=4.0,
        velocity_2_3s=2.5,
        velocity_decay_ratio=0.625,
        runup_3s=5.0,
        pnl_3s=2.0,
        mae_3s=-1.0,
    )

    survived, reason = promoted_trade_survives_3s(diag, settings)

    assert survived is True
    assert reason == "PASS"


def test_promoted_trade_survives_3s_fails_on_each_rule() -> None:
    settings = _settings()

    assert promoted_trade_survives_3s(
        PromotionDiagnostics(4.0, 2.5, 0.625, 3.9, 2.0, -1.0), settings
    ) == (False, "RUNUP_BELOW_MIN")
    assert promoted_trade_survives_3s(
        PromotionDiagnostics(4.0, 2.5, 0.625, 5.0, 1.5, -1.0), settings
    ) == (False, "PNL_BELOW_MIN")
    assert promoted_trade_survives_3s(
        PromotionDiagnostics(4.0, 2.5, 0.625, 5.0, 2.0, -3.5), settings
    ) == (False, "MAE_TOO_NEGATIVE")
    assert promoted_trade_survives_3s(
        PromotionDiagnostics(4.0, 1.0, 0.25, 5.0, 2.0, -1.0), settings
    ) == (False, "VELOCITY_DECAY_TOO_HIGH")


def test_compute_promoted_3s_diagnostics_uses_first_tick_after_checkpoint() -> None:
    entry_time = datetime(2026, 4, 22, 9, 20, 0)
    history = [
        (entry_time + timedelta(seconds=0.5), 102.0),
        (entry_time + timedelta(seconds=1.0), 104.0),
        (entry_time + timedelta(seconds=2.0), 100.0),
        (entry_time + timedelta(seconds=3.2), 102.1),
    ]

    diag = compute_promoted_3s_diagnostics(
        history,
        entry_time=entry_time,
        entry_price=100.0,
        current_time=entry_time + timedelta(seconds=3.2),
        current_price=102.1,
    )

    assert round(diag.velocity_0_1s or 0.0, 2) == 4.0
    assert round(diag.velocity_2_3s or 0.0, 2) == 2.1
    assert round(diag.velocity_decay_ratio or 0.0, 3) == 0.525
    assert round(diag.runup_3s, 2) == 4.0
    assert round(diag.pnl_3s, 2) == 2.1
    assert round(diag.mae_3s, 2) == 0.0


def test_layer4_persistence_passes_on_timely_followthrough() -> None:
    settings = _settings()
    armed = datetime(2026, 4, 22, 9, 20, 4)
    deadline = armed + timedelta(seconds=2)

    state, reason = layer4_persistence_result(
        now=armed + timedelta(seconds=1),
        first_hit_time=armed,
        deadline_time=deadline,
        current_pnl=4.6,
        settings=settings,
    )

    assert state == "pass"
    assert reason == "FOLLOWTHROUGH_REACHED"


def test_layer4_persistence_fails_when_window_expires_without_followthrough() -> None:
    settings = _settings()
    armed = datetime(2026, 4, 22, 9, 20, 4)
    deadline = armed + timedelta(seconds=2)

    state, reason = layer4_persistence_result(
        now=deadline,
        first_hit_time=armed,
        deadline_time=deadline,
        current_pnl=3.8,
        settings=settings,
    )

    assert state == "fail"
    assert reason == "WINDOW_EXPIRED"
