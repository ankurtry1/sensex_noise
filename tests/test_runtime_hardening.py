from __future__ import annotations

import queue
import threading
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sensex_noise.errors import QuoteUnavailableError
from sensex_noise.persistence.tick_journal import TickJournal
from sensex_noise.runtime.entry_planner import EntryPlan
from sensex_noise.runtime.strategy_runtime import StrategyRuntime
from sensex_noise.runtime.telemetry import RuntimeTelemetry
from sensex_noise.runtime.watchdog import StreamWatchdog
from sensex_noise.streaming.kite_stream import KiteStream, StreamState
from sensex_noise.streaming.tick_router import TickRouter
from sensex_noise.streaming.tick_store import TickStore
from sensex_noise.strategy import Signal
from sensex_noise.models import InstrumentChoice, SignalSide


class _MemoryJournal:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def append(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def append_event(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))


def _build_signal(ts: datetime) -> Signal:
    return Signal(
        side=SignalSide.CALL,
        trigger_price=78010.0,
        source_candle_start=ts,
        signal_kind="CONTINUATION_CALL",
    )


def test_entry_deferral_does_not_consume_candle_on_quote_unavailable() -> None:
    runtime = StrategyRuntime.__new__(StrategyRuntime)
    now = datetime(2026, 3, 20, 10, 0, 5)
    signal = _build_signal(now.replace(second=0))

    journal = _MemoryJournal()
    engine = SimpleNamespace(
        evaluator=SimpleNamespace(evaluate=lambda **_: signal),
        candle_tracker=SimpleNamespace(previous_candle=object(), current_candle=SimpleNamespace(start=signal.source_candle_start)),
        _log_signal_generated=lambda **_: None,
        _past_entry_cutoff=lambda _: False,
        settings=SimpleNamespace(entry_window_seconds=40, underlying_symbol="BSE:SENSEX", entry_cutoff_time="14:55"),
        attempted_entry_candles=set(),
        triggered_candle_start=None,
        journal=journal,
        open_position=None,
    )
    runtime.engine = engine
    runtime.entry_planner = SimpleNamespace(
        last_failure_reason=None,
        build=lambda **_: (_ for _ in ()).throw(QuoteUnavailableError("BFO:SENSEXOPT")),
    )
    runtime._execute_entry_plan = lambda **_: None

    runtime._maybe_attempt_entry({"timestamp_exchange": now, "ltp": 78020.0})

    assert signal.source_candle_start not in engine.attempted_entry_candles
    assert any(event == "ENTRY_DEFERRED_QUOTE_UNAVAILABLE" for event, _ in journal.events)


def test_entry_consumes_candle_only_after_quote_exists() -> None:
    runtime = StrategyRuntime.__new__(StrategyRuntime)
    now = datetime(2026, 3, 20, 10, 0, 5)
    signal = _build_signal(now.replace(second=0))

    journal = _MemoryJournal()
    engine = SimpleNamespace(
        evaluator=SimpleNamespace(evaluate=lambda **_: signal),
        candle_tracker=SimpleNamespace(previous_candle=object(), current_candle=SimpleNamespace(start=signal.source_candle_start)),
        _log_signal_generated=lambda **_: None,
        _past_entry_cutoff=lambda _: False,
        settings=SimpleNamespace(entry_window_seconds=40, underlying_symbol="BSE:SENSEX", entry_cutoff_time="14:55"),
        attempted_entry_candles=set(),
        triggered_candle_start=None,
        journal=journal,
        open_position=None,
    )
    runtime.engine = engine

    choice = InstrumentChoice(
        exchange="BFO",
        tradingsymbol="SENSEX26MAR78000CE",
        strike=78000,
        expiry=datetime(2026, 3, 26),
        option_type="CE",
        lot_size=20,
    )
    plan = EntryPlan(
        signal=signal,
        choice=choice,
        option_token=12345,
        option_quote={"ltp": 100.0},
        quantity=20,
        target_points=3.0,
        trade_id="T-1",
    )
    runtime.entry_planner = SimpleNamespace(last_failure_reason=None, build=lambda **_: plan)

    calls: list[str] = []
    runtime._execute_entry_plan = lambda **_: calls.append("executed")

    runtime._maybe_attempt_entry({"timestamp_exchange": now, "ltp": 78020.0})

    assert signal.source_candle_start in engine.attempted_entry_candles
    assert calls == ["executed"]


def test_hybrid_logging_disables_full_day_option_tape_by_default(tmp_path: Path) -> None:
    ts = datetime(2026, 3, 20, 10, 0, 0)
    date_dir = ts.date().isoformat()

    journal = TickJournal(
        logs_root=tmp_path,
        max_queue_size=100,
        flush_interval_seconds=0.1,
        enable_full_option_tape_logging=False,
    )
    journal.start()
    journal.append_market_tick({"timestamp_exchange": ts, "source": "index", "ltp": 78000.0})
    journal.append_market_tick({"timestamp_exchange": ts, "source": "option", "ltp": 110.0})
    journal.append_trade_tick(
        trade_id="T1",
        tick={"timestamp_exchange": ts, "source": "option", "ltp": 110.0, "instrument_token": 123},
        phase="IN_TRADE",
    )
    journal.stop()

    assert (tmp_path / "ticks" / date_dir / "sensex.jsonl").exists()
    assert not (tmp_path / "ticks" / date_dir / "options.jsonl").exists()
    assert (tmp_path / "trade_ticks" / date_dir / "T1.jsonl").exists()


def test_runtime_dequeues_critical_ticks_before_background() -> None:
    runtime = StrategyRuntime.__new__(StrategyRuntime)
    runtime.critical_tick_queue = queue.Queue()
    runtime.background_tick_queue = queue.Queue()
    runtime.telemetry = RuntimeTelemetry()
    runtime.tick_journal = SimpleNamespace(stats_snapshot=lambda: {"queue_size": 0})

    runtime.background_tick_queue.put({"id": "bg"})
    runtime.critical_tick_queue.put({"id": "critical"})

    first = runtime._dequeue_next_tick(timeout_seconds=0.2)
    second = runtime._dequeue_next_tick(timeout_seconds=0.2)

    assert first == {"id": "critical"}
    assert second == {"id": "bg"}


def test_background_queue_overflow_is_counted_and_emitted() -> None:
    telemetry = RuntimeTelemetry()
    events: list[tuple[str, dict]] = []
    router = TickRouter(
        tick_store=TickStore(),
        critical_queue=queue.Queue(maxsize=10),
        background_queue=queue.Queue(maxsize=1),
        is_critical_tick=lambda _: False,
        telemetry=telemetry,
        on_event=lambda event_type, payload: events.append((event_type, payload)),
    )

    tick1 = {
        "source": "option",
        "instrument_token": 1,
        "symbol": "BFO:OPT1",
        "timestamp_receive": datetime.now(),
    }
    tick2 = {
        "source": "option",
        "instrument_token": 2,
        "symbol": "BFO:OPT2",
        "timestamp_receive": datetime.now(),
    }

    assert router.route(tick1) is True
    assert router.route(tick2) is False

    assert telemetry.background_ticks_dropped_total == 1
    assert any(event == "BACKGROUND_TICK_DROP" for event, _ in events)


def test_trade_path_journaling_drop_is_explicit_under_pressure(tmp_path: Path) -> None:
    events: list[str] = []
    journal = TickJournal(
        logs_root=tmp_path,
        max_queue_size=1,
        flush_interval_seconds=1.0,
        enable_full_option_tape_logging=False,
        on_event=lambda event_type, _: events.append(event_type),
    )

    tick = {
        "timestamp_exchange": datetime(2026, 3, 20, 10, 0, 0),
        "source": "option",
        "instrument_token": 123,
    }

    ok_first = journal.append_trade_tick(trade_id="T1", tick=tick, phase="IN_TRADE")
    ok_second = journal.append_trade_tick(trade_id="T1", tick=tick, phase="IN_TRADE")

    stats = journal.stats_snapshot()
    assert ok_first is True
    assert ok_second is False
    assert stats["trade_path_records_dropped_total"] == 1
    assert "JOURNAL_BACKPRESSURE" in events
    assert "JOURNAL_CRITICAL_DROP" in events


def test_watchdog_degraded_blocks_entries_and_recovers() -> None:
    watchdog = StreamWatchdog(max_idle_seconds=1, hard_reconnect_seconds=2)
    now = datetime(2026, 3, 20, 10, 0, 0)

    alert = watchdog.evaluate(
        now=now,
        stream_connected=True,
        market_session_active=True,
        last_index_receive_ts=now - timedelta(seconds=3),
    )
    recovered = watchdog.evaluate(
        now=now,
        stream_connected=True,
        market_session_active=True,
        last_index_receive_ts=now,
    )

    runtime = StrategyRuntime.__new__(StrategyRuntime)
    runtime.engine = SimpleNamespace(
        _emit_due_post_exit_observations=lambda **_: None,
        open_position=None,
        _after_market_open=lambda _: True,
        candle_tracker=SimpleNamespace(update=lambda *_: None),
        journal=_MemoryJournal(),
    )
    runtime.stream = SimpleNamespace(
        current_atm=None,
        rebase_if_needed=lambda **_: False,
        option_lattice_size=0,
        subscribed_token_count=2,
        degraded=False,
        reconnect_in_progress=False,
        health_snapshot=lambda **_: {"degraded": True},
    )
    runtime.registry = SimpleNamespace(token_for_symbol=lambda _: None)
    runtime._watchdog_degraded = True
    runtime._entries_blocked_due_to_disconnect = False
    runtime._sync_subscription_telemetry = lambda: None
    called = {"entry": 0}
    runtime._maybe_attempt_entry = lambda **_: called.__setitem__("entry", called["entry"] + 1)

    runtime._handle_index_tick({"timestamp_exchange": now, "ltp": 78000.0})

    assert alert.degraded is True and alert.event_type == "WATCHDOG_ALERT"
    assert alert.should_reconnect is True
    assert recovered.degraded is False and recovered.event_type == "WATCHDOG_RECOVERED"
    assert called["entry"] == 0
    assert any(event == "ENTRY_BLOCKED_STREAM_DEGRADED" for event, _ in runtime.engine.journal.events)


def test_open_trade_token_retained_on_lattice_rebase() -> None:
    class _FakeTicker:
        MODE_FULL = "full"

        def __init__(self) -> None:
            self.unsubscribed: list[list[int]] = []
            self.subscribed: list[list[int]] = []
            self.mode_sets: list[tuple[str, list[int]]] = []

        def unsubscribe(self, tokens: list[int]) -> None:
            self.unsubscribed.append(list(tokens))

        def subscribe(self, tokens: list[int]) -> None:
            self.subscribed.append(list(tokens))

        def set_mode(self, mode: str, tokens: list[int]) -> None:
            self.mode_sets.append((mode, list(tokens)))

    class _Meta:
        def __init__(self, instrument_token: int) -> None:
            self.instrument_token = instrument_token

    class _Registry:
        @staticmethod
        def round_to_100(_: float) -> int:
            return 78200

        @staticmethod
        def option_lattice_for_atm(atm: int, now: datetime) -> list[_Meta]:
            _ = (atm, now)
            return [_Meta(4), _Meta(5)]

    stream = KiteStream.__new__(KiteStream)
    stream.registry = _Registry()
    stream.ticker = _FakeTicker()
    stream._lock = threading.Lock()
    stream._state = StreamState.LIVE
    stream._state_entered_at = datetime.now()
    stream._active_generation_id = 1
    stream._generations = {1: SimpleNamespace(ticker=stream.ticker)}
    stream._retiring_generation_ids = set()
    stream._retired_generation_ids = set()
    stream._last_reconnect_start_ts = None
    stream._last_reconnect_success_ts = None
    stream._last_reconnect_attempt = None
    stream._forced_reconnect_reason = None
    stream._forced_reconnect_details = {}
    stream._last_error_code = None
    stream._last_error_reason = None
    stream._last_reconnect_attempt = None
    stream._current_atm = 78100
    stream._desired_option_tokens = {1, 2, 3}
    stream._applied_option_tokens = {1, 2, 3}
    stream._subscriptions_applied_generation = 1
    stream._last_tick_at_any = None
    stream._last_tick_at_index = None
    stream._last_tick_at_future = None
    stream._last_tick_at_option = None
    stream._stale_since = None
    stream._last_close_code = None
    stream._last_close_reason = None
    stream._rebase_candidate_atm = None
    stream._rebase_candidate_count = 0
    stream._last_rebase_ts = None
    stream.rebase_min_move_points = 100
    stream.rebase_persist_ticks = 1
    stream.rebase_cooldown_seconds = 0
    stream._emit_event = lambda *_args, **_kwargs: None

    changed = stream.rebase_if_needed(spot_ltp=78220.0, keep_tokens={3})

    assert changed is True
    assert stream._option_tokens == {3, 4, 5}
    assert {1, 2} == set(stream.ticker.unsubscribed[0])
    assert {4, 5} == set(stream.ticker.subscribed[0])


def test_force_reconnect_is_idempotent_while_in_progress() -> None:
    class _FakeTicker:
        def close(self) -> None:
            return

        def connect(self, threaded: bool = True) -> None:
            _ = threaded
            return

    stream = KiteStream.__new__(KiteStream)
    stream._lock = threading.Lock()
    stream._state = StreamState.RECONNECTING
    stream._last_reconnect_start_ts = None
    stream.reconnect_cooldown_seconds = 10
    stream._forced_reconnect_reason = None
    stream._forced_reconnect_details = {}
    stream._last_error_code = None
    stream._last_error_reason = None
    stream.ticker = _FakeTicker()
    stream._emit_event = lambda *_args, **_kwargs: None

    assert stream.force_reconnect(reason="TEST") is False


def test_rebase_hysteresis_requires_persistence() -> None:
    class _FakeTicker:
        MODE_FULL = "full"

        def __init__(self) -> None:
            self.subscribed: list[list[int]] = []
            self.mode_sets: list[tuple[str, list[int]]] = []

        def unsubscribe(self, tokens: list[int]) -> None:
            _ = tokens

        def subscribe(self, tokens: list[int]) -> None:
            self.subscribed.append(list(tokens))

        def set_mode(self, mode: str, tokens: list[int]) -> None:
            self.mode_sets.append((mode, list(tokens)))

    class _Meta:
        def __init__(self, instrument_token: int) -> None:
            self.instrument_token = instrument_token

    class _Registry:
        @staticmethod
        def round_to_100(_: float) -> int:
            return 77400

        @staticmethod
        def option_lattice_for_atm(atm: int, now: datetime) -> list[_Meta]:
            _ = (atm, now)
            return [_Meta(10), _Meta(11)]

    events: list[tuple[str, dict]] = []
    stream = KiteStream.__new__(KiteStream)
    stream.registry = _Registry()
    stream.ticker = _FakeTicker()
    stream._lock = threading.Lock()
    stream._state = StreamState.LIVE
    stream._state_entered_at = datetime.now()
    stream._active_generation_id = 1
    stream._generations = {1: SimpleNamespace(ticker=stream.ticker)}
    stream._retiring_generation_ids = set()
    stream._retired_generation_ids = set()
    stream._last_reconnect_start_ts = None
    stream._last_reconnect_success_ts = None
    stream._last_reconnect_attempt = None
    stream._forced_reconnect_reason = None
    stream._forced_reconnect_details = {}
    stream._last_error_code = None
    stream._last_error_reason = None
    stream._current_atm = 77300
    stream._desired_option_tokens = {8, 9}
    stream._applied_option_tokens = {8, 9}
    stream._subscriptions_applied_generation = 1
    stream._last_tick_at_any = None
    stream._last_tick_at_index = None
    stream._last_tick_at_future = None
    stream._last_tick_at_option = None
    stream._stale_since = None
    stream._last_close_code = None
    stream._last_close_reason = None
    stream._rebase_candidate_atm = None
    stream._rebase_candidate_count = 0
    stream._last_rebase_ts = None
    stream.rebase_min_move_points = 100
    stream.rebase_persist_ticks = 3
    stream.rebase_cooldown_seconds = 0
    stream._emit_event = lambda event_type, payload: events.append((event_type, payload))

    assert stream.rebase_if_needed(spot_ltp=77412.0) is False
    assert stream.rebase_if_needed(spot_ltp=77415.0) is False
    assert stream.rebase_if_needed(spot_ltp=77422.0) is True
    assert any(event == "LATTICE_REBASE_SKIPPED_PERSISTENCE" for event, _ in events)


def test_stale_generation_close_is_ignored_after_reconnect_generation_switch() -> None:
    class _Meta:
        def __init__(self, instrument_token: int) -> None:
            self.instrument_token = instrument_token

    class _Registry:
        index_meta = SimpleNamespace(instrument_token=265)
        future_meta = SimpleNamespace(instrument_token=999)

        @staticmethod
        def initial_tokens() -> list[int]:
            return [265, 999]

        @staticmethod
        def initial_atm_hint() -> int:
            return 77400

        @staticmethod
        def option_lattice_for_atm(atm: int, now: datetime) -> list[_Meta]:
            _ = (atm, now)
            return [_Meta(1), _Meta(2)]

        @staticmethod
        def round_to_100(_: float) -> int:
            return 77400

    class _WS:
        MODE_QUOTE = "quote"
        MODE_FULL = "full"

        def subscribe(self, _tokens: list[int]) -> None:
            return

        def set_mode(self, _mode: str, _tokens: list[int]) -> None:
            return

    events: list[tuple[str, dict]] = []
    stream = KiteStream.__new__(KiteStream)
    stream.registry = _Registry()
    stream.normalizer = SimpleNamespace(normalize=lambda raw_tick, timestamp_receive: raw_tick)
    stream.router = SimpleNamespace(route=lambda _tick: True)
    stream.on_disconnect_cb = None
    stream.on_reconnect_cb = None
    stream.on_connect_state_cb = None
    stream.on_event = lambda event_type, payload: events.append((event_type, payload))
    stream.reconnect_cooldown_seconds = 10
    stream.rebase_persist_ticks = 3
    stream.rebase_cooldown_seconds = 3
    stream.rebase_min_move_points = 100
    stream._lock = threading.Lock()
    stream._state = StreamState.RECONNECTING
    stream._state_entered_at = datetime.now()
    stream._generation_seq = 2
    stream._active_generation_id = 2
    stream._generations = {
        1: SimpleNamespace(generation_id=1, ticker=SimpleNamespace(close=lambda: None), first_tick_at=None, subscriptions_ready=False),
        2: SimpleNamespace(generation_id=2, ticker=SimpleNamespace(close=lambda: None), first_tick_at=None, subscriptions_ready=False, connected_at=None, subscriptions_applied_at=None),
    }
    stream._retiring_generation_ids = {1}
    stream._retired_generation_ids = set()
    stream._last_reconnect_start_ts = datetime.now()
    stream._last_reconnect_success_ts = None
    stream._last_reconnect_attempt = None
    stream._forced_reconnect_reason = "WATCHDOG_STALE_FEED"
    stream._forced_reconnect_details = {}
    stream._last_tick_at_any = None
    stream._last_tick_at_index = None
    stream._last_tick_at_future = None
    stream._last_tick_at_option = None
    stream._stale_since = None
    stream._last_close_code = None
    stream._last_close_reason = None
    stream._last_error_code = None
    stream._last_error_reason = None
    stream._current_atm = 77400
    stream._desired_option_tokens = {1, 2}
    stream._applied_option_tokens = set()
    stream._subscriptions_applied_generation = None
    stream._rebase_candidate_atm = None
    stream._rebase_candidate_count = 0
    stream._last_rebase_ts = None
    stream._emit_event = lambda event_type, payload: events.append((event_type, payload))

    ws = _WS()
    stream._handle_on_connect(ws=ws, response={}, generation_id=2)
    assert stream.state == StreamState.CONNECTED_PENDING_FIRST_TICK

    stream._handle_on_close(ws=ws, code=1006, reason="old close", generation_id=1)
    assert stream.state == StreamState.CONNECTED_PENDING_FIRST_TICK

    tick = {
        "source": "index",
        "instrument_token": 265,
        "symbol": "BSE:SENSEX",
        "timestamp_exchange": datetime.now(),
        "timestamp_receive": datetime.now(),
        "ltp": 77412.0,
    }
    stream._handle_on_ticks(ws=ws, ticks=[tick], generation_id=2)
    assert stream.state == StreamState.LIVE
    assert any(evt == "FORCED_STREAM_RECONNECT_SUCCESS" for evt, _ in events)


def test_stream_health_snapshot_flags_follow_state_machine() -> None:
    stream = KiteStream.__new__(KiteStream)
    stream._lock = threading.Lock()
    stream._state = StreamState.CONNECTED_PENDING_FIRST_TICK
    stream._state_entered_at = datetime.now()
    stream._active_generation_id = 7
    stream._generations = {7: SimpleNamespace(first_tick_at=None, subscriptions_ready=True)}
    stream._retiring_generation_ids = set()
    stream._retired_generation_ids = set()
    stream._last_tick_at_any = None
    stream._last_tick_at_index = None
    stream._last_tick_at_future = None
    stream._last_tick_at_option = None
    stream._current_atm = 77400
    stream._desired_option_tokens = {1, 2}
    stream._applied_option_tokens = {1, 2}
    stream._subscriptions_applied_generation = 7

    snap = stream.health_snapshot()
    assert snap["stream_state"] == StreamState.CONNECTED_PENDING_FIRST_TICK.value
    assert snap["connected"] is True
    assert snap["degraded"] is True
    assert snap["reconnecting"] is False
    assert snap["active_generation_has_first_tick"] is False
    assert snap["active_generation_subscriptions_ready"] is True


def test_active_generation_error_transitions_to_stale() -> None:
    stream = KiteStream.__new__(KiteStream)
    stream._lock = threading.Lock()
    stream._state = StreamState.LIVE
    stream._state_entered_at = datetime.now()
    stream._active_generation_id = 4
    stream._generations = {4: SimpleNamespace(first_tick_at=datetime.now(), subscriptions_ready=True)}
    stream._retiring_generation_ids = set()
    stream._retired_generation_ids = set()
    stream._last_reconnect_attempt = None
    stream._last_error_code = None
    stream._last_error_reason = None
    stream._stale_since = None
    stream._emit_event = lambda *_args, **_kwargs: None

    stream._handle_on_error(ws=SimpleNamespace(), code=1006, reason="boom", generation_id=4)
    assert stream.state == StreamState.STALE


def test_watchdog_reconnect_only_once_per_stale_episode() -> None:
    runtime = StrategyRuntime.__new__(StrategyRuntime)
    runtime._stream_connect_timeout_seconds = 10
    runtime._stream_first_tick_timeout_seconds = 8
    runtime._reconnect_attempted_in_stale_episode = False
    runtime.engine = SimpleNamespace(settings=SimpleNamespace(watchdog_hard_reconnect_seconds=8))
    runtime.telemetry = SimpleNamespace(last_index_receive_ts=lambda: datetime.now() - timedelta(seconds=10))
    runtime._queue_runtime_event = lambda *_args, **_kwargs: None
    runtime._watchdog_degraded = False

    calls = {"force": 0}

    class _Stream:
        def health_snapshot(self, now: datetime | None = None) -> dict:
            _ = now
            return {"stream_state": StreamState.LIVE.value, "connected": True}

        def mark_stale(self, reason: str, idle_seconds: float | None = None) -> None:
            _ = (reason, idle_seconds)

        def mark_recovered_from_stale(self, reason: str) -> None:
            _ = reason

        def force_reconnect(self, reason: str, details: dict | None = None) -> bool:
            _ = (reason, details)
            calls["force"] += 1
            return True

    runtime.stream = _Stream()
    runtime.watchdog = SimpleNamespace(
        evaluate=lambda **_: SimpleNamespace(
            degraded=True,
            event_type=None,
            payload=None,
            should_reconnect=True,
            stale_reason="INDEX_TICK_IDLE",
            idle_seconds=10.0,
        )
    )

    runtime._run_watchdog()
    runtime._run_watchdog()
    assert calls["force"] == 1
