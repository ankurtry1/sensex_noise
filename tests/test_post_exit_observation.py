from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from sensex_noise.models import Position, SignalSide
from sensex_noise.services.engine import StrategyEngine


class _MemoryJournal:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []
        self.summaries: list[tuple[Position, dict | None]] = []

    def append(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def append_event(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def append_trade_summary(self, position: Position, extra_payload: dict | None = None) -> None:
        self.summaries.append((position, extra_payload))


class _SequencedMarketData:
    def __init__(self, prices: list[float], base_time: datetime) -> None:
        self.prices = list(prices)
        self.base_time = base_time
        self.calls = 0

    def option_quote(self, symbol: str) -> dict:
        _ = symbol
        self.calls += 1
        idx = min(self.calls - 1, len(self.prices) - 1)
        return {
            "timestamp": self.base_time + timedelta(seconds=self.calls),
            "ltp": float(self.prices[idx]),
        }


def _build_position() -> Position:
    now = datetime(2026, 3, 22, 10, 0, 0)
    return Position(
        side=SignalSide.CALL,
        option_symbol="BFO:SENSEX26MAR77900CE",
        product="NRML",
        underlying_spot=78000.0,
        entry_price=100.0,
        target_price=103.0,
        quantity=20,
        strike=77900,
        expiry=datetime(2026, 3, 26, 0, 0, 0),
        entry_time=now,
        signal_kind="CONTINUATION_CALL",
        trade_id="T1",
    )


def _build_engine(seconds: int = 15, interval: int = 1, prices: list[float] | None = None) -> StrategyEngine:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = SimpleNamespace(
        enable_post_exit_observation=True,
        post_exit_observation_seconds=seconds,
        post_exit_observation_interval_seconds=interval,
        enable_post_exit_counterfactual=True,
        enable_hard_stop=False,
        enable_early_risk=False,
        enable_path_risk=False,
        post_1pm_time_stop_seconds=60,
    )
    engine.journal = _MemoryJournal()
    engine.pending_post_exit_observations = []
    engine.market_data = _SequencedMarketData(prices or [100.0], datetime(2026, 3, 22, 10, 0, 0))
    engine.active_exit_order_type = None
    engine.active_exit_price = None
    return engine


def test_post_exit_watcher_schedule_is_1_to_n() -> None:
    engine = _build_engine(seconds=15, interval=1)
    position = _build_position()
    position.exit_time = position.entry_time + timedelta(seconds=45)
    position.exit_price = 100.0

    engine._observe_post_exit(position)

    assert len(engine.pending_post_exit_observations) == 1
    watcher = engine.pending_post_exit_observations[0]
    assert watcher["schedule"] == list(range(1, 16))
    assert position.post_exit_observation_done is False


def test_post_exit_observations_append_to_position_path() -> None:
    engine = _build_engine(seconds=3, interval=1, prices=[101.0, 99.0, 102.0])
    position = _build_position()
    position.exit_time = datetime(2026, 3, 22, 10, 0, 0)
    position.exit_price = 100.0
    engine._observe_post_exit(position)

    for sec in (1, 2, 3):
        engine._emit_due_post_exit_observations(
            {"timestamp": position.exit_time + timedelta(seconds=sec), "ltp": 78000.0}
        )

    assert len(position.post_exit_path) == 3
    assert [row["seconds_after_exit"] for row in position.post_exit_path] == [1, 2, 3]
    assert position.post_exit_path[0]["delta_from_exit_price"] == 1.0
    assert position.post_exit_path[1]["delta_from_exit_price"] == -1.0
    assert position.post_exit_path[2]["delta_from_exit_price"] == 2.0


def test_post_exit_summary_metrics_computed() -> None:
    engine = _build_engine(seconds=3, interval=1, prices=[101.0, 99.0, 102.0])
    position = _build_position()
    position.exit_time = datetime(2026, 3, 22, 10, 0, 0)
    position.exit_price = 100.0
    engine._observe_post_exit(position)

    for sec in (1, 2, 3):
        engine._emit_due_post_exit_observations(
            {"timestamp": position.exit_time + timedelta(seconds=sec), "ltp": 78000.0}
        )

    assert position.post_exit_observation_done is True
    assert position.post_exit_points_best_recovery == 2.0
    assert position.post_exit_points_worst_further_loss == -1.0
    assert position.post_exit_recovered_above_exit is True
    assert position.post_exit_max_recovery_second == 3
    assert position.post_exit_max_further_loss_second == 2
    assert position.post_exit_final_delta == 2.0

    summary_calls = engine.journal.summaries
    assert len(summary_calls) == 1
    _, extra_payload = summary_calls[0]
    assert extra_payload is not None
    assert extra_payload.get("summary_version") == "post_exit_enriched"


def test_post_exit_does_not_block_new_trade_logic() -> None:
    engine = _build_engine(seconds=15, interval=1, prices=[100.0] * 20)
    engine.manual_exit_requested = False

    watcher_position = _build_position()
    watcher_position.exit_time = datetime(2026, 3, 22, 10, 0, 0)
    watcher_position.exit_price = 100.0
    engine._observe_post_exit(watcher_position)

    open_position = _build_position()
    open_position.trade_id = "T2"
    open_position.entry_time = datetime(2026, 3, 22, 10, 0, 30)
    open_position.target_price = 101.0
    open_position.closing = False

    # Watcher processing can run while new open-position logic remains available.
    engine._emit_due_post_exit_observations(
        {"timestamp": watcher_position.exit_time + timedelta(seconds=5), "ltp": 78010.0}
    )
    candidates = engine._collect_exit_candidates(
        position=open_position,
        option_quote={"ltp": 101.5},
        mark_time=open_position.entry_time,
    )

    assert "TARGET_HIT" in candidates
    assert len(engine.pending_post_exit_observations) == 1
