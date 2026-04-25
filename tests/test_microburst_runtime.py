from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from types import SimpleNamespace

from sensex_noise.models import InstrumentChoice, Position, SignalSide
from sensex_noise.runtime.entry_planner import EntryPlanner
from sensex_noise.runtime.exit_runtime import ExitRuntime
from sensex_noise.runtime.position_tracker import PositionTracker
from sensex_noise.runtime.strategy_runtime import StrategyRuntime
from sensex_noise.services.engine import StrategyEngine
from sensex_noise.services.entry_window import EntryWindowBuffer
from sensex_noise.services.microburst import MicroburstFeatures
from sensex_noise.strategy import Signal


class _MemoryJournal:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def append(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def append_event(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def append_trade_summary(self, position: Position, extra_payload: dict | None = None) -> None:
        payload = {"trade_id": position.trade_id}
        if extra_payload:
            payload.update(extra_payload)
        self.events.append(("TRADE_CLOSED_SUMMARY", payload))


class _ExitBroker:
    def __init__(self) -> None:
        self.cancel_calls = 0
        self.exit_calls = 0
        self.next_exit_price = 100.0
        self.next_exit_time = datetime(2026, 4, 22, 9, 20, 10)

    def cancel_order(self, variety: str, order_id: str) -> str:
        self.cancel_calls += 1
        return order_id

    def exit_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        self.exit_calls += 1
        return "EXIT-1", self.next_exit_price, self.next_exit_time

    def get_order(self, order_id: str) -> dict | None:
        return {"order_id": order_id, "status": "OPEN", "price": 107.0}


def _microburst_settings(**overrides: object) -> SimpleNamespace:
    base = dict(
        enable_microburst_gate=True,
        microburst_min_score=3,
        normal_target_points=3.0,
        promoted_min_score=5,
        promoted_target_points=7.0,
        entry_feature_lookback_seconds=5.0,
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
        edge_invalidation_hard_stop_enabled=False,
        edge_invalidation_hard_stop_points=6.0,
        edge_invalidation_stale_quote_max_seconds=1.5,
        edge_invalidation_kill_on_stale_quotes=False,
        edge_invalidation_require_subsecond_precision=False,
        prefer_edge_invalidation_over_legacy_early_risk=True,
        promoted_3s_min_runup_points=4.0,
        promoted_3s_min_pnl_points=1.5,
        promoted_3s_max_mae_points=3.5,
        promoted_3s_min_velocity_decay_ratio=0.5,
        layer4_enabled=True,
        layer4_trigger_points=3.0,
        layer4_required_followthrough_points=4.5,
        layer4_window_seconds=2.0,
        enable_hard_stop=False,
        hard_stop_arm_after_seconds=30,
        enable_early_risk=False,
        enable_path_risk=False,
        post_1pm_time_stop_seconds=60,
        session_square_off_enabled=False,
        enable_verbose_trade_logging=False,
        enable_exit_decision_logging=False,
        enable_snapshot_logging=False,
        snapshot_seconds=(1, 3),
        early_failure_window_seconds=15,
        early_failure_mfe_min=1.5,
        early_failure_mae_max=-1.5,
        enable_post_exit_observation=False,
        post_exit_observation_seconds=0,
        post_exit_observation_interval_seconds=1,
        enable_slippage_logging=False,
        enable_dynamic_risky_target=True,
        risky_target_points=2.0,
        strict_after_1pm_risky_target_points=2.0,
        enable_target_reprice_modify=True,
        enable_target_reprice_fallback_cancel_replace=True,
        target_reprice_debounce_seconds=0,
        order_product="MIS",
        entry_window_seconds=40,
        underlying_symbol="BSE:SENSEX",
        entry_cutoff_time="14:55",
        entry_window_max_seconds=10.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _choice() -> InstrumentChoice:
    return InstrumentChoice(
        exchange="BFO",
        tradingsymbol="SENSEX26APR77000CE",
        strike=77000,
        expiry=datetime(2026, 4, 30),
        option_type="CE",
        lot_size=20,
    )


def _signal(ts: datetime) -> Signal:
    return Signal(
        side=SignalSide.CALL,
        trigger_price=78010.0,
        source_candle_start=ts.replace(second=0, microsecond=0),
        signal_kind="CONTINUATION_CALL",
    )


def _entry_engine(settings: SimpleNamespace | None = None) -> SimpleNamespace:
    now = datetime(2026, 4, 22, 9, 20, 5)
    settings = settings or _microburst_settings()
    journal = _MemoryJournal()
    engine = SimpleNamespace(
        settings=settings,
        journal=journal,
        selector=SimpleNamespace(pick_sensex_option=lambda **_: _choice()),
        market_data=SimpleNamespace(
            option_quote=lambda symbol: {
                "timestamp": now,
                "ltp": 100.0,
                "bid": 99.5,
                "ask": 100.5,
                "spread": 1.0,
            }
        ),
        entry_window_buffer=EntryWindowBuffer(max_seconds=10.0),
        _build_trade_id=lambda **_: "T-MICRO",
        _resolve_trade_quantity=lambda **_: 20,
        _get_target_points=lambda **_: 2.0,
        tick_store=SimpleNamespace(token_for_symbol=lambda symbol: 1234),
        registry=SimpleNamespace(token_for_symbol=lambda symbol: 1234),
    )
    engine.entry_window_buffer.add_underlying_tick({"timestamp": now, "ltp": 78020.0})
    return engine


def _runtime_for_entry(engine: SimpleNamespace, signal: Signal) -> StrategyRuntime:
    runtime = StrategyRuntime.__new__(StrategyRuntime)
    runtime.engine = SimpleNamespace(
        evaluator=SimpleNamespace(evaluate=lambda **_: signal),
        candle_tracker=SimpleNamespace(previous_candle=object(), current_candle=SimpleNamespace(start=signal.source_candle_start)),
        _log_signal_generated=lambda **_: None,
        _past_entry_cutoff=lambda _: False,
        settings=engine.settings,
        attempted_entry_candles=set(),
        triggered_candle_start=None,
        journal=engine.journal,
        open_position=None,
        selector=engine.selector,
        market_data=engine.market_data,
        entry_window_buffer=engine.entry_window_buffer,
        _build_trade_id=engine._build_trade_id,
        _resolve_trade_quantity=engine._resolve_trade_quantity,
        _get_target_points=engine._get_target_points,
        tick_store=engine.tick_store,
        registry=engine.registry,
    )
    runtime.entry_planner = EntryPlanner(engine=runtime.engine)
    runtime._execute_entry_plan_calls: list[object] = []
    runtime._execute_entry_plan = lambda **kwargs: runtime._execute_entry_plan_calls.append(kwargs)
    return runtime


def _build_engine_for_exit(settings: SimpleNamespace | None = None) -> tuple[StrategyEngine, _ExitBroker, _MemoryJournal]:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = settings or _microburst_settings()
    engine.journal = _MemoryJournal()
    engine.broker = _ExitBroker()
    engine.wallet = SimpleNamespace(apply_closed_trade=lambda position: None, realized_pnl=0.0)
    engine.charges_model = SimpleNamespace(calculate_round_trip=lambda position: SimpleNamespace(total=0.0))
    engine.candle_tracker = SimpleNamespace(current_candle=None)
    engine.evaluator = SimpleNamespace(mark_exit=lambda *_: None)
    engine.manual_exit_requested = False
    engine.active_exit_order_type = "TARGET"
    engine.active_exit_price = 107.0
    engine.active_exit_order_id = "TARGET-1"
    engine.active_exit_order_variety = "regular"
    engine.active_exit_order_sent_time = None
    engine.active_exit_order_ack_time = None
    engine.pending_post_exit_observations = []
    engine.open_trade_id = "PROMO-1"
    engine.session_square_off_time = dt_time(15, 15)
    return engine, engine.broker, engine.journal


def _promoted_position(entry_time: datetime) -> Position:
    return Position(
        side=SignalSide.CALL,
        option_symbol="BFO:SENSEX26APR77000CE",
        product="MIS",
        underlying_spot=78000.0,
        entry_price=100.0,
        target_price=107.0,
        quantity=20,
        strike=77000,
        expiry=datetime(2026, 4, 30),
        entry_time=entry_time,
        signal_kind="CONTINUATION_CALL",
        trade_id="PROMO-1",
        target_points=7.0,
        base_target_points=3.0,
        promoted_target_points=7.0,
        burst_score=5,
        is_promoted_candidate=True,
        pre_or_post_1pm="PRE_1PM",
    )


def _quote(ts: datetime, ltp: float) -> dict:
    return {"timestamp": ts, "ltp": ltp, "bid": ltp - 0.5, "ask": ltp + 0.5, "spread": 1.0}


def test_entry_blocked_when_microburst_score_below_min(monkeypatch) -> None:
    from sensex_noise.runtime import entry_planner as entry_planner_module

    low_features = MicroburstFeatures(
        ind_velocity_aligned=0.2,
        ind_accel_aligned=0.3,
        opt_velocity_aligned=0.1,
        opt_depth_imb_mean=0.01,
        opt_spread_mean=1.0,
        score=2,
        score_components={"low": 2},
    )
    monkeypatch.setattr(entry_planner_module, "compute_pre_entry_features", lambda **_: low_features)

    now = datetime(2026, 4, 22, 9, 20, 5)
    signal = _signal(now)
    runtime = _runtime_for_entry(_entry_engine(), signal)

    runtime._maybe_attempt_entry({"timestamp_exchange": now, "ltp": 78020.0})

    assert runtime._execute_entry_plan_calls == []
    assert any(event == "ENTRY_BLOCKED_MICROBURST_GATE" for event, _ in runtime.engine.journal.events)


def test_normal_trade_score_three_keeps_normal_target(monkeypatch) -> None:
    from sensex_noise.runtime import entry_planner as entry_planner_module

    features = MicroburstFeatures(2.0, 2.0, 1.7, 0.01, 1.0, 3, {"score": 3})
    monkeypatch.setattr(entry_planner_module, "compute_pre_entry_features", lambda **_: features)

    planner = EntryPlanner(engine=_entry_engine())
    plan = planner.build(
        signal=_signal(datetime(2026, 4, 22, 9, 20, 5)),
        tick_time=datetime(2026, 4, 22, 9, 20, 5),
        spot_ltp=78020.0,
    )

    assert plan is not None
    assert plan.target_points == 3.0
    assert plan.is_promoted_candidate is False
    assert plan.base_target_points == 3.0
    assert plan.promoted_target_points == 0.0


def test_promoted_trade_score_five_gets_promoted_target(monkeypatch) -> None:
    from sensex_noise.runtime import entry_planner as entry_planner_module

    features = MicroburstFeatures(2.0, 4.0, 1.7, 0.2, 1.0, 5, {"score": 5})
    monkeypatch.setattr(entry_planner_module, "compute_pre_entry_features", lambda **_: features)

    planner = EntryPlanner(engine=_entry_engine())
    plan = planner.build(
        signal=_signal(datetime(2026, 4, 22, 9, 20, 5)),
        tick_time=datetime(2026, 4, 22, 9, 20, 5),
        spot_ltp=78020.0,
    )

    assert plan is not None
    assert plan.target_points == 7.0
    assert plan.is_promoted_candidate is True
    assert plan.promoted_target_points == 7.0


def test_promoted_trade_fails_at_3s_and_exits() -> None:
    entry_time = datetime(2026, 4, 22, 9, 20, 0)
    engine, broker, journal = _build_engine_for_exit()
    engine.open_position = _promoted_position(entry_time)
    engine.open_trade_id = engine.open_position.trade_id
    tracker = PositionTracker(engine=engine, exit_runtime=ExitRuntime(engine=engine))

    ticks = [
        (entry_time + timedelta(seconds=0.5), 102.0),
        (entry_time + timedelta(seconds=1.0), 104.0),
        (entry_time + timedelta(seconds=2.0), 104.4),
        (entry_time + timedelta(seconds=3.2), 104.8),
    ]
    broker.next_exit_price = 104.8
    broker.next_exit_time = ticks[-1][0]

    reason = None
    for ts, ltp in ticks:
        reason = tracker.on_option_tick(option_quote=_quote(ts, ltp), spot_quote=_quote(ts, 78000.0))

    assert reason == "PROMOTED_FAIL_3S"
    assert broker.cancel_calls == 1
    assert broker.exit_calls == 1
    assert any(event == "PROMOTED_3S_FAIL" for event, _ in journal.events)


def test_promoted_trade_passes_3s_then_fails_persistence() -> None:
    entry_time = datetime(2026, 4, 22, 9, 20, 0)
    engine, broker, journal = _build_engine_for_exit()
    engine.open_position = _promoted_position(entry_time)
    engine.open_trade_id = engine.open_position.trade_id
    tracker = PositionTracker(engine=engine, exit_runtime=ExitRuntime(engine=engine))

    ticks = [
        (entry_time + timedelta(seconds=0.5), 102.0),
        (entry_time + timedelta(seconds=1.0), 104.0),
        (entry_time + timedelta(seconds=2.0), 100.0),
        (entry_time + timedelta(seconds=3.2), 102.1),
        (entry_time + timedelta(seconds=4.0), 103.0),
        (entry_time + timedelta(seconds=5.5), 103.8),
        (entry_time + timedelta(seconds=6.1), 103.2),
    ]
    broker.next_exit_price = 103.2
    broker.next_exit_time = ticks[-1][0]

    reason = None
    for ts, ltp in ticks:
        reason = tracker.on_option_tick(option_quote=_quote(ts, ltp), spot_quote=_quote(ts, 78000.0))

    assert reason == "PROMOTION_PERSISTENCE_FAIL"
    assert broker.cancel_calls == 1
    assert broker.exit_calls == 1
    assert any(event == "PROMOTION_ARMED_AT_3PTS" for event, _ in journal.events)
    assert any(event == "PROMOTION_PERSISTENCE_FAIL" for event, _ in journal.events)


def test_promoted_trade_passes_3s_and_persistence_stays_open() -> None:
    entry_time = datetime(2026, 4, 22, 9, 20, 0)
    engine, broker, journal = _build_engine_for_exit()
    engine.open_position = _promoted_position(entry_time)
    engine.open_trade_id = engine.open_position.trade_id
    tracker = PositionTracker(engine=engine, exit_runtime=ExitRuntime(engine=engine))

    ticks = [
        (entry_time + timedelta(seconds=0.5), 102.0),
        (entry_time + timedelta(seconds=1.0), 104.0),
        (entry_time + timedelta(seconds=2.0), 100.0),
        (entry_time + timedelta(seconds=3.2), 102.1),
        (entry_time + timedelta(seconds=4.0), 103.0),
        (entry_time + timedelta(seconds=5.0), 104.6),
    ]

    reason = None
    for ts, ltp in ticks:
        reason = tracker.on_option_tick(option_quote=_quote(ts, ltp), spot_quote=_quote(ts, 78000.0))

    assert reason is None
    assert engine.open_position is not None
    assert engine.open_position.promotion_persistence_passed is True
    assert broker.cancel_calls == 0
    assert broker.exit_calls == 0
    assert any(event == "PROMOTED_3S_PASS" for event, _ in journal.events)
    assert any(event == "PROMOTION_PERSISTENCE_PASS" for event, _ in journal.events)


def test_backward_compatibility_when_microburst_gate_disabled() -> None:
    settings = _microburst_settings(enable_microburst_gate=False, layer4_enabled=False)
    planner = EntryPlanner(engine=_entry_engine(settings=settings))

    plan = planner.build(
        signal=_signal(datetime(2026, 4, 22, 9, 20, 5)),
        tick_time=datetime(2026, 4, 22, 9, 20, 5),
        spot_ltp=78020.0,
    )

    assert plan is not None
    assert plan.target_points == 2.0
    assert plan.is_promoted_candidate is False
    assert plan.burst_score == 0
