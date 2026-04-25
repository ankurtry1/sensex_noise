from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from sensex_noise.models import Position, SignalSide
from sensex_noise.services.engine import StrategyEngine


class _Journal:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def append(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def append_event(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))


def _base_settings(**overrides: object) -> SimpleNamespace:
    base = dict(
        enable_edge_invalidation=True,
        edge_invalidation_1s_enabled=True,
        edge_invalidation_3s_enabled=True,
        edge_invalidation_1s_check_seconds=1.0,
        edge_invalidation_3s_check_seconds=3.0,
        edge_invalidation_1s_min_runup_points=1.0,
        edge_invalidation_1s_max_pnl_points=0.0,
        edge_invalidation_3s_min_runup_points=2.0,
        edge_invalidation_3s_max_drawdown_points=4.0,
        edge_invalidation_3s_pinned_pnl_abs_points=1.0,
        edge_invalidation_hard_stop_enabled=True,
        edge_invalidation_hard_stop_points=6.0,
        edge_invalidation_stale_quote_max_seconds=1.5,
        edge_invalidation_kill_on_stale_quotes=False,
        edge_invalidation_require_subsecond_precision=False,
        edge_invalidation_use_underlying_confirmation=False,
        edge_invalidation_use_spread_filter=False,
        prefer_edge_invalidation_over_legacy_early_risk=True,
        enable_hard_stop=True,
        hard_stop_arm_after_seconds=30,
        enable_early_risk=False,
        enable_path_risk=False,
        post_1pm_time_stop_seconds=60,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _build_position(entry_time: datetime) -> Position:
    return Position(
        side=SignalSide.CALL,
        option_symbol="BFO:SENSEX26APR77000CE",
        product="MIS",
        underlying_spot=77000.0,
        entry_price=100.0,
        target_price=103.0,
        quantity=20,
        strike=77000,
        expiry=datetime(2026, 4, 16),
        entry_time=entry_time,
        signal_kind="CONTINUATION_CALL",
        trade_id="T-EDGE",
        pre_or_post_1pm="PRE_1PM",
    )


def _build_engine(settings: SimpleNamespace | None = None) -> StrategyEngine:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = settings or _base_settings()
    engine.journal = _Journal()
    engine.manual_exit_requested = False
    engine.active_exit_order_type = None
    engine.active_exit_price = None
    return engine


def _quote(ltp: float, spread: float = 1.0) -> dict:
    return {
        "ltp": ltp,
        "bid": ltp - spread / 2,
        "ask": ltp + spread / 2,
        "spread": spread,
    }


def test_edge_invalidation_1s_fail() -> None:
    engine = _build_engine()
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    t = pos.entry_time + timedelta(seconds=1.2)
    engine.update_edge_invalidation_state(pos, t, _quote(99.5))

    assert engine.evaluate_edge_invalidation_checkpoint_1s(pos, t, 99.5, record=True) is True


def test_edge_invalidation_1s_pass() -> None:
    engine = _build_engine()
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    engine.update_edge_invalidation_state(pos, pos.entry_time + timedelta(seconds=0.2), _quote(101.6))
    t = pos.entry_time + timedelta(seconds=1.1)
    engine.update_edge_invalidation_state(pos, t, _quote(100.2))

    assert engine.evaluate_edge_invalidation_checkpoint_1s(pos, t, 100.2, record=True) is False


def test_edge_invalidation_3s_fail_low_runup() -> None:
    engine = _build_engine()
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    t = pos.entry_time + timedelta(seconds=3.2)
    engine.update_edge_invalidation_state(pos, t, _quote(100.1))

    assert engine.evaluate_edge_invalidation_checkpoint_3s(pos, t, 100.1, record=True) is True


def test_edge_invalidation_3s_fail_drawdown() -> None:
    engine = _build_engine()
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    t = pos.entry_time + timedelta(seconds=3.1)
    engine.update_edge_invalidation_state(pos, t, _quote(95.0))

    assert engine.evaluate_edge_invalidation_checkpoint_3s(pos, t, 95.0, record=True) is True


def test_edge_invalidation_3s_fail_pinned_pnl() -> None:
    engine = _build_engine()
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    engine.update_edge_invalidation_state(pos, pos.entry_time + timedelta(seconds=0.4), _quote(102.5))
    t = pos.entry_time + timedelta(seconds=3.2)
    engine.update_edge_invalidation_state(pos, t, _quote(100.2))

    assert engine.evaluate_edge_invalidation_checkpoint_3s(pos, t, 100.2, record=True) is True


def test_edge_hard_stop_precedence() -> None:
    engine = _build_engine()
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    t = pos.entry_time + timedelta(seconds=0.3)
    engine.update_edge_invalidation_state(pos, t, _quote(93.0))
    candidates = engine._collect_exit_candidates(pos, _quote(93.0), t)

    assert "EDGE_HARD_STOP" in candidates
    assert engine._select_exit_reason(candidates) == "EDGE_HARD_STOP"


def test_edge_no_duplicate_checkpoint_exit_requests() -> None:
    engine = _build_engine()
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    t1 = pos.entry_time + timedelta(seconds=1.3)
    engine.update_edge_invalidation_state(pos, t1, _quote(99.0))
    first = engine._collect_edge_invalidation_candidates(pos, _quote(99.0), t1)

    t2 = pos.entry_time + timedelta(seconds=1.6)
    engine.update_edge_invalidation_state(pos, t2, _quote(99.1))
    second = engine._collect_edge_invalidation_candidates(pos, _quote(99.1), t2)

    assert "EARLY_FAIL_1S" in first
    assert "EARLY_FAIL_1S" not in second


def test_edge_feature_disabled_preserves_legacy_path() -> None:
    engine = _build_engine(_base_settings(enable_edge_invalidation=False))
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    t = pos.entry_time + timedelta(seconds=1.2)
    engine.update_edge_invalidation_state(pos, t, _quote(99.0))
    candidates = engine._collect_edge_invalidation_candidates(pos, _quote(99.0), t)

    assert candidates == []
    assert pos.edge_has_checked_1s is False


def test_edge_stale_quote_failsafe() -> None:
    engine = _build_engine(
        _base_settings(edge_invalidation_kill_on_stale_quotes=True)
    )
    pos = _build_position(datetime(2026, 4, 10, 9, 20, 0))

    t0 = pos.entry_time + timedelta(seconds=0.2)
    engine.update_edge_invalidation_state(pos, t0, _quote(100.2))
    t1 = t0 + timedelta(seconds=2.2)
    engine.update_edge_invalidation_state(pos, t1, _quote(100.1))

    candidates = engine._collect_edge_invalidation_candidates(pos, _quote(100.1), t1)
    assert "STALE_QUOTE_FAILSAFE" in candidates
