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
