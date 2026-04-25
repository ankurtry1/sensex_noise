import pytest

from sensex_noise.config import load_settings


_REQUIRED = {
    "KITE_API_KEY": "x",
    "KITE_ACCESS_TOKEN": "y",
}


def _seed_required(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _REQUIRED.items():
        monkeypatch.setenv(key, value)


def test_snapshot_seconds_are_sorted_and_unique(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.setenv("SNAPSHOT_SECONDS", "10,3,3,1,30")

    settings = load_settings()

    assert settings.snapshot_seconds == (1, 3, 10, 30)


def test_invalid_risk_windows_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.setenv("EARLY_RISK_SUSPICION_SECONDS", "10")
    monkeypatch.setenv("EARLY_RISK_EXIT_SECONDS", "10")

    with pytest.raises(ValueError, match="EARLY_RISK_EXIT_SECONDS"):
        load_settings()


def test_hard_stop_arm_after_seconds_defaults_to_30(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.delenv("HARD_STOP_ARM_AFTER_SECONDS", raising=False)

    settings = load_settings()

    assert settings.hard_stop_arm_after_seconds == 30


def test_negative_hard_stop_arm_after_seconds_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.setenv("HARD_STOP_ARM_AFTER_SECONDS", "-1")

    with pytest.raises(ValueError, match="HARD_STOP_ARM_AFTER_SECONDS"):
        load_settings()


def test_hardening_runtime_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    settings = load_settings()

    assert settings.enable_microburst_gate is True
    assert settings.microburst_min_score == 3
    assert settings.microburst_ind_accel_threshold_1 == 1.688
    assert settings.microburst_ind_accel_threshold_2 == 3.945
    assert settings.microburst_opt_velocity_threshold == 1.583
    assert settings.microburst_opt_depth_imb_threshold == 0.0857
    assert settings.microburst_ind_velocity_min == 1.646
    assert settings.microburst_ind_velocity_max == 2.356
    assert settings.normal_target_points == 3.0
    assert settings.promoted_min_score == 5
    assert settings.promoted_target_points == 7.0
    assert settings.promoted_3s_min_runup_points == 4.0
    assert settings.promoted_3s_min_pnl_points == 1.5
    assert settings.promoted_3s_max_mae_points == 3.5
    assert settings.promoted_3s_min_velocity_decay_ratio == 0.5
    assert settings.layer4_enabled is True
    assert settings.layer4_trigger_points == 3.0
    assert settings.layer4_required_followthrough_points == 4.5
    assert settings.layer4_window_seconds == 2.0
    assert settings.entry_window_max_seconds == 10.0
    assert settings.entry_feature_lookback_seconds == 5.0
    assert settings.enable_edge_invalidation is True
    assert settings.edge_invalidation_1s_enabled is True
    assert settings.edge_invalidation_3s_enabled is True
    assert settings.edge_invalidation_1s_check_seconds == 1.0
    assert settings.edge_invalidation_3s_check_seconds == 3.0
    assert settings.edge_invalidation_1s_min_runup_points == 1.0
    assert settings.edge_invalidation_1s_max_pnl_points == 0.0
    assert settings.edge_invalidation_3s_min_runup_points == 2.0
    assert settings.edge_invalidation_3s_max_drawdown_points == 4.0
    assert settings.edge_invalidation_3s_pinned_pnl_abs_points == 1.0
    assert settings.edge_invalidation_hard_stop_enabled is True
    assert settings.edge_invalidation_hard_stop_points == 6.0
    assert settings.edge_invalidation_stale_quote_max_seconds == 1.5
    assert settings.edge_invalidation_kill_on_stale_quotes is False
    assert settings.prefer_edge_invalidation_over_legacy_early_risk is True
    assert settings.enable_full_option_tape_logging is False
    assert settings.stream_watchdog_max_idle_seconds == 5
    assert settings.watchdog_hard_reconnect_seconds == 8
    assert settings.stream_reconnect_cooldown_seconds == 10
    assert settings.stream_connect_timeout_seconds == 10
    assert settings.stream_first_tick_timeout_seconds == 8
    assert settings.heartbeat_log_interval_seconds == 30
    assert settings.rebase_persist_ticks == 3
    assert settings.rebase_cooldown_seconds == 3
    assert settings.rebase_min_move_points == 100
    assert settings.critical_tick_queue_maxsize == 5000
    assert settings.background_tick_queue_maxsize == 20000
    assert settings.journal_queue_maxsize == 50000
    assert settings.journal_flush_interval_seconds == 1


def test_invalid_runtime_queue_size_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.setenv("CRITICAL_TICK_QUEUE_MAXSIZE", "0")

    with pytest.raises(ValueError, match="CRITICAL_TICK_QUEUE_MAXSIZE"):
        load_settings()


def test_invalid_edge_invalidation_checkpoint_order_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.setenv("EDGE_INVALIDATION_1S_CHECK_SECONDS", "3")
    monkeypatch.setenv("EDGE_INVALIDATION_3S_CHECK_SECONDS", "2")

    with pytest.raises(ValueError, match="EDGE_INVALIDATION_3S_CHECK_SECONDS"):
        load_settings()


def test_invalid_promoted_target_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.setenv("NORMAL_TARGET_POINTS", "3.0")
    monkeypatch.setenv("PROMOTED_TARGET_POINTS", "3.0")

    with pytest.raises(ValueError, match="PROMOTED_TARGET_POINTS"):
        load_settings()


def test_invalid_entry_feature_lookback_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_required(monkeypatch)
    monkeypatch.setenv("ENTRY_WINDOW_MAX_SECONDS", "5")
    monkeypatch.setenv("ENTRY_FEATURE_LOOKBACK_SECONDS", "6")

    with pytest.raises(ValueError, match="ENTRY_FEATURE_LOOKBACK_SECONDS"):
        load_settings()
