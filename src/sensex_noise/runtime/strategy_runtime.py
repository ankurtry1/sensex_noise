from __future__ import annotations

import logging
import queue
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta
from typing import Any

from kiteconnect.exceptions import TokenException

from sensex_noise.errors import QuoteUnavailableError
from sensex_noise.models import Position
from sensex_noise.persistence.tick_journal import TickJournal
from sensex_noise.runtime.candle_engine import CandleEngine
from sensex_noise.runtime.entry_planner import EntryPlan, EntryPlanner
from sensex_noise.runtime.exit_runtime import ExitRuntime
from sensex_noise.runtime.position_tracker import PositionTracker
from sensex_noise.runtime.telemetry import RuntimeTelemetry
from sensex_noise.runtime.watchdog import StreamWatchdog
from sensex_noise.services.entry_window import EntryWindowBuffer
from sensex_noise.services.market_data import MarketDataService
from sensex_noise.services.trade_journal import TradeJournal
from sensex_noise.streaming.kite_stream import KiteStream, StreamState
from sensex_noise.streaming.tick_normalizer import TickNormalizer
from sensex_noise.streaming.tick_router import TickRouter
from sensex_noise.streaming.tick_store import TickStore
from sensex_noise.streaming.token_registry import TokenRegistry

logger = logging.getLogger(__name__)


@dataclass
class TradeCaptureState:
    trade_id: str
    option_token: int
    index_token: int
    future_token: int
    post_exit_until: datetime | None = None

    @property
    def watched_tokens(self) -> set[int]:
        return {self.option_token, self.index_token, self.future_token}


class StrategyRuntime:
    """Event-driven execution loop using websocket ticks as the sole market-data source."""

    HEALTH_EVENT_INTERVAL_SECONDS = 5.0

    def __init__(self, engine: object) -> None:
        self.engine = engine

        self.critical_tick_queue: queue.Queue[dict[str, Any]] = queue.Queue(
            maxsize=self.engine.settings.critical_tick_queue_maxsize
        )
        self.background_tick_queue: queue.Queue[dict[str, Any]] = queue.Queue(
            maxsize=self.engine.settings.background_tick_queue_maxsize
        )
        self.state_queue: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue(maxsize=2048)

        self.registry = TokenRegistry(
            instruments=self.engine.selector.instruments,
            underlying_symbol=self.engine.settings.underlying_symbol,
        )
        self.tick_store = TickStore(max_buffer_ticks=2048)
        self.normalizer = TickNormalizer(registry=self.registry)

        self.telemetry = RuntimeTelemetry()
        self.watchdog = StreamWatchdog(
            max_idle_seconds=self.engine.settings.stream_watchdog_max_idle_seconds,
            hard_reconnect_seconds=self.engine.settings.watchdog_hard_reconnect_seconds,
        )

        self.router = TickRouter(
            tick_store=self.tick_store,
            critical_queue=self.critical_tick_queue,
            background_queue=self.background_tick_queue,
            is_critical_tick=self._is_critical_tick,
            telemetry=self.telemetry,
            on_event=self._queue_runtime_event,
        )
        self.tick_journal = TickJournal(
            logs_root=self.engine.settings.logs_dir,
            max_queue_size=self.engine.settings.journal_queue_maxsize,
            flush_interval_seconds=self.engine.settings.journal_flush_interval_seconds,
            enable_full_option_tape_logging=self.engine.settings.enable_full_option_tape_logging,
            enable_sensex_option_tape_recorder=self.engine.settings.enable_sensex_option_tape_recorder,
            sensex_tape_log_dir=self.engine.settings.sensex_tape_log_dir,
            sensex_tape_write_legacy_options_log=self.engine.settings.sensex_tape_write_legacy_options_log,
            on_event=self._queue_runtime_event,
        )

        self.stream = KiteStream(
            api_key=self.engine.settings.kite_api_key,
            access_token=self.engine.settings.kite_access_token,
            registry=self.registry,
            normalizer=self.normalizer,
            router=self.router,
            on_disconnect=self._on_disconnect,
            on_reconnect=self._on_reconnect,
            on_connect_state=self._on_connect,
            on_event=self._queue_runtime_event,
            reconnect_cooldown_seconds=self.engine.settings.stream_reconnect_cooldown_seconds,
            rebase_persist_ticks=self.engine.settings.rebase_persist_ticks,
            rebase_cooldown_seconds=self.engine.settings.rebase_cooldown_seconds,
            rebase_min_move_points=self.engine.settings.rebase_min_move_points,
            enable_sensex_option_tape_recorder=self.engine.settings.enable_sensex_option_tape_recorder,
            sensex_tape_strike_range_points=self.engine.settings.sensex_tape_strike_range_points,
            sensex_tape_strike_step_points=self.engine.settings.sensex_tape_strike_step_points,
            sensex_tape_expiry_mode=self.engine.settings.sensex_tape_expiry_mode,
            sensex_tape_include_ce=self.engine.settings.sensex_tape_include_ce,
            sensex_tape_include_pe=self.engine.settings.sensex_tape_include_pe,
            sensex_tape_rebase_on_atm_move_points=self.engine.settings.sensex_tape_rebase_on_atm_move_points,
        )

        self.entry_planner = EntryPlanner(engine=self.engine)
        self.exit_runtime = ExitRuntime(engine=self.engine)
        self.position_tracker = PositionTracker(engine=self.engine, exit_runtime=self.exit_runtime)

        self.latest_index_tick: dict[str, Any] | None = None
        self.latest_future_tick: dict[str, Any] | None = None
        self.trade_capture: TradeCaptureState | None = None
        self._running = False
        self._entries_blocked_due_to_disconnect = True
        self._last_control_poll = 0.0
        self._last_health_emit = 0.0
        self._watchdog_degraded = False
        self._had_disconnect = False
        self._reconnect_attempted_in_stale_episode = False
        self._stream_connect_timeout_seconds = float(
            self.engine.settings.stream_connect_timeout_seconds
        )
        self._stream_first_tick_timeout_seconds = float(
            self.engine.settings.stream_first_tick_timeout_seconds
        )
        self._heartbeat_log_interval_seconds = float(
            self.engine.settings.heartbeat_log_interval_seconds
        )
        self._last_heartbeat_emit = 0.0

        # Compatibility layer: same MarketDataService interface backed by TickStore.
        self.engine.market_data = MarketDataService(
            broker=self.engine.broker,
            tick_store=self.tick_store,
            token_registry=self.registry,
        )
        if getattr(self.engine, "entry_window_buffer", None) is None:
            self.engine.entry_window_buffer = EntryWindowBuffer(
                max_seconds=float(getattr(self.engine.settings, "entry_window_max_seconds", 10.0))
            )
        # Expose runtime stores for planner/runtime helper access.
        self.engine.tick_store = self.tick_store
        self.engine.registry = self.registry

        # Candles now come strictly from SENSEX stream ticks.
        self.engine.candle_tracker = CandleEngine()

        self._maybe_enable_daily_trade_journal()

    def run(self) -> None:
        self.tick_journal.start()
        self.stream.start()
        self._running = True
        logger.info("Strategy runtime started in websocket event-driven mode")

        try:
            while self._running:
                self._safe_runtime_step(self._process_state_events, "PROCESS_STATE_EVENTS")
                self._safe_runtime_step(self._periodic_control_poll, "CONTROL_POLL")
                self._safe_runtime_step(self._run_watchdog, "WATCHDOG")
                self._safe_runtime_step(self._emit_health_event_if_due, "HEALTH_EVENT")
                self._safe_runtime_step(self._emit_runtime_heartbeat_if_due, "RUNTIME_HEARTBEAT")
                self._safe_runtime_step(self._finalize_capture_if_due, "FINALIZE_CAPTURE")

                tick = self._dequeue_next_tick(timeout_seconds=0.5)
                if tick is None:
                    continue

                try:
                    self._handle_tick(tick)
                except Exception as exc:
                    logger.exception("Tick handler failed | source=%s | token=%s | symbol=%s", tick.get("source"), tick.get("instrument_token"), tick.get("symbol"))
                    self.engine.journal.append_event(
                        "TICK_HANDLER_ERROR",
                        {
                            "timestamp": datetime.now().isoformat(),
                            "source": tick.get("source"),
                            "instrument_token": tick.get("instrument_token"),
                            "symbol": tick.get("symbol"),
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                        },
                    )
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except TokenException:
            logger.error(
                "Authentication failed during runtime. Check KITE_API_KEY/KITE_ACCESS_TOKEN pairing."
            )
            self.engine.journal.append_event(
                "FATAL_RUNTIME_ERROR",
                {
                    "timestamp": datetime.now().isoformat(),
                    "error_type": "TokenException",
                    "error": "Authentication failed",
                },
            )
        except Exception as exc:
            logger.exception("Fatal runtime error; shutting down strategy loop")
            self.engine.journal.append_event(
                "FATAL_RUNTIME_ERROR",
                {
                    "timestamp": datetime.now().isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
        finally:
            self._running = False
            self.stream.stop()
            self.tick_journal.stop()

    def _dequeue_next_tick(self, timeout_seconds: float) -> dict[str, Any] | None:
        deadline = time.monotonic() + max(0.01, float(timeout_seconds))
        while time.monotonic() < deadline:
            try:
                return self.critical_tick_queue.get_nowait()
            except queue.Empty:
                pass

            try:
                return self.background_tick_queue.get_nowait()
            except queue.Empty:
                time.sleep(0.01)

        self._sync_telemetry_from_journal()
        self.telemetry.mark_queue_sizes(
            critical_size=self.critical_tick_queue.qsize(),
            background_size=self.background_tick_queue.qsize(),
            journal_size=self.tick_journal.stats_snapshot().get("queue_size", 0),
        )
        return None

    def _handle_tick(self, tick: dict[str, Any]) -> None:
        self.tick_journal.append_market_tick(tick)
        self._record_trade_tick_if_needed(tick)

        source = str(tick.get("source", "")).lower()
        if source == "index":
            self.latest_index_tick = tick
            self._handle_index_tick(tick)
        elif source == "future":
            self.latest_future_tick = tick
        elif source == "option":
            self._handle_option_tick(tick)

        self.telemetry.mark_tick_processed()

    def _handle_index_tick(self, tick: dict[str, Any]) -> None:
        tick_time = tick["timestamp_exchange"]
        spot_ltp = float(tick["ltp"])
        entry_window_buffer = getattr(self.engine, "entry_window_buffer", None)
        if entry_window_buffer is not None:
            entry_window_buffer.add_underlying_tick(tick)

        self.engine._emit_due_post_exit_observations(
            spot_quote=self._quote_from_tick(tick)
        )

        # Dynamic ATM lattice rebasing on each index tick.
        keep_tokens: set[int] = set()
        if self.engine.open_position is not None:
            keep_token = self.registry.token_for_symbol(self.engine.open_position.option_symbol)
            if keep_token is not None:
                keep_tokens.add(int(keep_token))

        prev_atm = self.stream.current_atm
        rebased = self.stream.rebase_if_needed(spot_ltp=spot_ltp, keep_tokens=keep_tokens)
        if rebased:
            self._queue_runtime_event(
                "LATTICE_REBASE",
                {
                    "timestamp": tick_time.isoformat(),
                    "old_atm": prev_atm,
                    "new_atm": self.stream.current_atm,
                    "option_lattice_size": self.stream.option_lattice_size,
                    "subscribed_token_count": self.stream.subscribed_token_count,
                    "kept_tokens": sorted(keep_tokens),
                },
            )
            self._maybe_record_tape_subscription_state(reason="LATTICE_REBASE", tick_time=tick_time)
        self._sync_subscription_telemetry()

        if not self.engine._after_market_open(tick_time):
            return

        self.engine.candle_tracker.update(tick_time, spot_ltp)

        if self.engine.open_position is not None:
            return

        if self._is_degraded():
            if not self._entries_blocked_due_to_disconnect:
                self._entries_blocked_due_to_disconnect = True
                self.engine.journal.append_event(
                    "ENTRY_BLOCKED_STREAM_DEGRADED",
                    {
                        "timestamp": tick_time.isoformat(),
                        "reason": "STREAM_DEGRADED",
                    },
                )
            return

        self._entries_blocked_due_to_disconnect = False
        self._maybe_attempt_entry(spot_tick=tick)

    def _maybe_attempt_entry(self, spot_tick: dict[str, Any]) -> None:
        tick_time = spot_tick["timestamp_exchange"]
        spot_ltp = float(spot_tick["ltp"])
        signal = self.engine.evaluator.evaluate(
            previous_candle=self.engine.candle_tracker.previous_candle,
            current_candle=self.engine.candle_tracker.current_candle,
            live_ltp=spot_ltp,
        )
        if signal is None:
            return

        self.engine._log_signal_generated(
            signal=signal,
            signal_time=tick_time,
            spot_ltp=spot_ltp,
            previous_candle=self.engine.candle_tracker.previous_candle,
        )
        candle_id = signal.source_candle_start

        if self.engine._past_entry_cutoff(tick_time):
            self.engine.journal.append(
                "ENTRY_BLOCKED_AFTER_CUTOFF",
                {
                    "now": tick_time.isoformat(),
                    "cutoff": self.engine.settings.entry_cutoff_time,
                },
            )
            return

        elapsed_seconds = (tick_time - signal.source_candle_start).total_seconds()
        if elapsed_seconds > self.engine.settings.entry_window_seconds:
            self.engine.journal.append(
                "ENTRY_SKIPPED_OUTSIDE_WINDOW",
                {
                    "now": tick_time.isoformat(),
                    "source_candle_start": signal.source_candle_start.isoformat(),
                    "elapsed_seconds": elapsed_seconds,
                    "entry_window_seconds": self.engine.settings.entry_window_seconds,
                    "side": signal.side.value,
                    "trigger_price": signal.trigger_price,
                    "underlying_symbol": self.engine.settings.underlying_symbol,
                },
            )
            return

        if candle_id in self.engine.attempted_entry_candles:
            self.engine.journal.append(
                "ENTRY_SKIPPED_CANDLE_ALREADY_ATTEMPTED",
                {
                    "now": tick_time.isoformat(),
                    "candle_id": candle_id.isoformat(),
                    "source_candle_start": candle_id.isoformat(),
                    "side": signal.side.value,
                    "trigger_price": signal.trigger_price,
                },
            )
            return

        if self.engine.triggered_candle_start == signal.source_candle_start:
            return

        try:
            plan = self.entry_planner.build(signal=signal, tick_time=tick_time, spot_ltp=spot_ltp)
        except QuoteUnavailableError as exc:
            self.engine.journal.append_event(
                "ENTRY_DEFERRED_QUOTE_UNAVAILABLE",
                {
                    "timestamp": tick_time.isoformat(),
                    "source_candle_start": signal.source_candle_start.isoformat(),
                    "side": signal.side.value,
                    "trigger_price": signal.trigger_price,
                    "option_symbol": exc.symbol,
                    "reason": "QUOTE_UNAVAILABLE",
                },
            )
            return

        if plan is None:
            if self.entry_planner.last_failure_reason == "MICROBURST_GATE_BLOCKED":
                return
            self.engine.journal.append_event(
                "ENTRY_DEFERRED_NOT_READY",
                {
                    "timestamp": tick_time.isoformat(),
                    "source_candle_start": signal.source_candle_start.isoformat(),
                    "side": signal.side.value,
                    "trigger_price": signal.trigger_price,
                    "reason": self.entry_planner.last_failure_reason,
                },
            )
            return

        # Entry attempt is now committed: token exists, quote exists, quantity resolved.
        self.engine.attempted_entry_candles.add(candle_id)
        try:
            self._execute_entry_plan(plan=plan, spot_ltp=spot_ltp, tick_time=tick_time, signal=signal)
        except Exception as exc:
            self.engine.journal.append(
                "ENTRY_ATTEMPT_FAILED_CANDLE_LOCKED",
                {
                    "now": tick_time.isoformat(),
                    "candle_id": candle_id.isoformat(),
                    "source_candle_start": candle_id.isoformat(),
                    "reason": "ENTRY_ATTEMPT_EXCEPTION",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "side": signal.side.value,
                },
            )
            return

    def _execute_entry_plan(self, plan: EntryPlan, spot_ltp: float, tick_time: datetime, signal: Any) -> None:
        option_quote = plan.option_quote
        signal_kind = getattr(signal, "signal_kind", "UNKNOWN")

        self.engine._log_entry_context(
            trade_id=plan.trade_id,
            signal=signal,
            choice=plan.choice,
            quantity=plan.quantity,
            target_points=plan.target_points,
            spot_at_signal=spot_ltp,
            spot_at_entry_attempt=spot_ltp,
            option_quote=option_quote,
        )

        entry_reference_price = float(option_quote["ltp"])
        entry_decision_time = datetime.now()
        signal_seen_time = tick_time
        entry_order_sent_time = datetime.now()

        self.engine._append_event(
            "ENTRY_ORDER_SENT",
            {
                "trade_id": plan.trade_id,
                "order_id": None,
                "symbol": plan.choice.full_symbol,
                "variety": "regular",
                "order_type": "MARKET",
                "transaction_type": "BUY",
                "quantity": plan.quantity,
                "product": self.engine.settings.order_product,
                "requested_price": None,
                "trigger_reason": "ENTRY",
                "closing": False,
                "fragile": False,
                "entry_reference_price": entry_reference_price,
                "entry_decision_time": entry_decision_time.isoformat(),
                "sent_time": entry_order_sent_time.isoformat(),
            },
        )

        entry_order_id, entry_price, entry_time = self.engine.broker.place_entry_market(
            symbol=plan.choice.full_symbol,
            quantity=plan.quantity,
            product=self.engine.settings.order_product,
        )
        entry_order_ack_time = datetime.now()

        self.engine._append_event(
            "ENTRY_ORDER_ACKED",
            {
                "trade_id": plan.trade_id,
                "symbol": plan.choice.full_symbol,
                "order_id": entry_order_id,
                "variety": "regular",
                "order_type": "MARKET",
                "transaction_type": "BUY",
                "requested_price": None,
                "trigger_reason": "ENTRY",
                "closing": False,
                "fragile": False,
                "ack_time": entry_order_ack_time.isoformat(),
            },
        )

        self.engine.open_position = Position(
            side=signal.side,
            option_symbol=plan.choice.full_symbol,
            product=self.engine.settings.order_product,
            underlying_spot=spot_ltp,
            entry_price=entry_price,
            target_price=entry_price + plan.target_points,
            quantity=plan.quantity,
            strike=plan.choice.strike,
            expiry=plan.choice.expiry,
            entry_time=entry_time,
            signal_kind=signal_kind,
            trade_id=plan.trade_id,
            signal_time=tick_time,
            signal_seen_time=tick_time,
            trigger_price=signal.trigger_price,
            source_candle_start=signal.source_candle_start,
            target_points=plan.target_points,
            base_target_points=plan.base_target_points,
            promoted_target_points=plan.promoted_target_points,
            hard_stop_points_used=self.engine._get_hard_stop_points(signal_kind),
            burst_score=plan.burst_score,
            burst_features=plan.burst_features,
            is_promoted_candidate=plan.is_promoted_candidate,
            entry_order_id=entry_order_id,
            entry_order_sent_time=entry_order_sent_time,
            entry_order_ack_time=entry_order_ack_time,
            entry_fill_time=entry_time,
            entry_decision_time=entry_decision_time,
            entry_reference_price=entry_reference_price,
            entry_slippage_points=(
                (entry_price - entry_reference_price)
                if self.engine.settings.enable_slippage_logging
                else None
            ),
            entry_lag_seconds=(entry_time - signal_seen_time).total_seconds(),
            entry_bid=option_quote.get("bid"),
            entry_ask=option_quote.get("ask"),
            entry_spread=option_quote.get("spread"),
            current_price=entry_price,
            current_spot=spot_ltp,
            pre_or_post_1pm=("POST_1PM" if self.engine._is_post_1pm(entry_time) else "PRE_1PM"),
        )
        self.engine.open_position.edge_has_subsecond_timestamps = (
            self.engine.open_position.entry_time.microsecond > 0
        )

        call_put = "CALL" if signal.side.value == "CALL" else "PUT"
        cont_rev = "CONTINUATION" if "CONTINUATION" in signal_kind else "REVERSAL"
        self.engine.open_position.snapshot_features.update(
            {
                "continuation_or_reversal": cont_rev,
                "call_or_put": call_put,
                "burst_score": self.engine.open_position.burst_score,
                "is_promoted_candidate": self.engine.open_position.is_promoted_candidate,
                "target_points_used": self.engine.open_position.target_points,
                "base_target_points": self.engine.open_position.base_target_points,
                "promoted_target_points": self.engine.open_position.promoted_target_points,
                "hard_stop_points_used": self.engine.open_position.hard_stop_points_used,
                "entry_lag_seconds": self.engine.open_position.entry_lag_seconds,
                "entry_slippage_points": self.engine.open_position.entry_slippage_points,
            }
        )

        self.engine.open_trade_id = plan.trade_id
        self.engine._append_event(
            "ENTRY_FILLED",
            {
                "trade_id": plan.trade_id,
                "symbol": plan.choice.full_symbol,
                "order_id": entry_order_id,
                "variety": "regular",
                "order_type": "MARKET",
                "transaction_type": "BUY",
                "requested_price": None,
                "fill_price": entry_price,
                "trigger_reason": "ENTRY",
                "closing": self.engine.open_position.closing,
                "fragile": self.engine.open_position.fragile,
                "entry_fill_time": entry_time.isoformat(),
                "entry_price": entry_price,
                "entry_reference_price": self.engine.open_position.entry_reference_price,
                "entry_slippage_points": self.engine.open_position.entry_slippage_points,
                "entry_lag_seconds": self.engine.open_position.entry_lag_seconds,
                "bid": option_quote.get("bid"),
                "ask": option_quote.get("ask"),
                "spread": option_quote.get("spread"),
                "burst_score": self.engine.open_position.burst_score,
                "is_promoted_candidate": self.engine.open_position.is_promoted_candidate,
            },
        )

        target_placed = self.engine._place_target_exit_order()
        futures_quote = self._latest_future_quote()
        trade_payload = {
            "trade_id": self.engine.open_trade_id,
            "symbol": self.engine.open_position.option_symbol,
            "side": self.engine.open_position.side.value,
            "product": self.engine.open_position.product,
            "entry_time": self.engine.open_position.entry_time.isoformat(),
            "entry_price": self.engine.open_position.entry_price,
            "target_price": self.engine.open_position.target_price,
            "quantity": self.engine.open_position.quantity,
            "strike": self.engine.open_position.strike,
            "expiry": self.engine.open_position.expiry.isoformat(),
            "underlying_spot": self.engine.open_position.underlying_spot,
            "source_candle_start": signal.source_candle_start.isoformat(),
            "trigger_price": signal.trigger_price,
            "signal_kind": signal_kind,
            "burst_score": self.engine.open_position.burst_score,
            "burst_features": self.engine.open_position.burst_features,
            "is_promoted_candidate": self.engine.open_position.is_promoted_candidate,
            "base_target_points": self.engine.open_position.base_target_points,
            "promoted_target_points": self.engine.open_position.promoted_target_points,
        }
        if futures_quote is not None:
            trade_payload["futures_ltp"] = float(futures_quote["ltp"])
            trade_payload["futures_timestamp"] = futures_quote["timestamp"].isoformat()
        self.engine.journal.append("TRADE_ENTERED", trade_payload)

        self.engine.triggered_candle_start = signal.source_candle_start
        if target_placed:
            self.engine._append_event(
                "TARGET_PLACED",
                {
                    "trade_id": self.engine.open_trade_id,
                    "symbol": self.engine.open_position.option_symbol,
                    "product": self.engine.open_position.product,
                    "target_price": self.engine.open_position.target_price,
                    "target_points": self.engine.open_position.target_points,
                    "burst_score": self.engine.open_position.burst_score,
                    "is_promoted_candidate": self.engine.open_position.is_promoted_candidate,
                    "order_id": self.engine.active_exit_order_id,
                    "signal_kind": self.engine.open_position.signal_kind,
                },
            )

        self._start_trade_capture(
            trade_id=self.engine.open_trade_id,
            option_token=plan.option_token,
            entry_time=self.engine.open_position.entry_time,
        )

    def _handle_option_tick(self, tick: dict[str, Any]) -> None:
        symbol = str(tick.get("symbol", ""))
        entry_window_buffer = getattr(self.engine, "entry_window_buffer", None)
        if symbol and entry_window_buffer is not None:
            entry_window_buffer.add_option_tick(symbol, tick)
        if self.engine.open_position is None:
            return

        open_symbol = self.engine.open_position.option_symbol
        open_token = self.registry.token_for_symbol(open_symbol)
        if open_token is None or int(tick["instrument_token"]) != int(open_token):
            return

        spot_quote = self._latest_spot_quote()
        if spot_quote is None:
            return

        option_quote = self._quote_from_tick(tick)
        future_quote = self._latest_future_quote()

        position_ref = self.engine.open_position
        reason = self.position_tracker.on_option_tick(
            option_quote=option_quote,
            spot_quote=spot_quote,
            future_quote=future_quote,
        )

        if reason is not None and position_ref is not None and position_ref.exit_time is not None:
            self._mark_post_exit_capture(trade_id=position_ref.trade_id, exit_time=position_ref.exit_time)

    def _start_trade_capture(self, trade_id: str, option_token: int, entry_time: datetime) -> None:
        state = TradeCaptureState(
            trade_id=trade_id,
            option_token=int(option_token),
            index_token=self.registry.index_meta.instrument_token,
            future_token=self.registry.future_meta.instrument_token,
        )
        self.trade_capture = state

        symbols = [
            self.registry.index_meta.full_symbol,
            self.registry.future_meta.full_symbol,
            self.registry.symbol_for_token(option_token) or "",
        ]
        pre_ticks = self.tick_store.slice_symbols_last_seconds(
            symbols=[s for s in symbols if s],
            seconds=5,
            now=entry_time,
        )
        self.tick_journal.append_trade_ticks(
            trade_id=trade_id,
            ticks=pre_ticks,
            phase="PRE_ENTRY",
            extra={"capture_window_seconds": 5},
        )

    def _mark_post_exit_capture(self, trade_id: str, exit_time: datetime) -> None:
        if self.trade_capture is None or self.trade_capture.trade_id != trade_id:
            return
        self.trade_capture.post_exit_until = exit_time + timedelta(seconds=15)

    def _record_trade_tick_if_needed(self, tick: dict[str, Any]) -> None:
        state = self.trade_capture
        if state is None:
            return

        token = int(tick["instrument_token"])
        if token not in state.watched_tokens:
            return

        ts = tick.get("timestamp_exchange")
        if not isinstance(ts, datetime):
            return

        phase = "IN_TRADE"
        if state.post_exit_until is not None:
            if ts > state.post_exit_until:
                self.trade_capture = None
                return
            phase = "POST_EXIT"

        ok = self.tick_journal.append_trade_tick(
            trade_id=state.trade_id,
            tick=tick,
            phase=phase,
        )
        if not ok:
            self._queue_runtime_event(
                "TRADE_TICK_CAPTURE_DROP",
                {
                    "timestamp": datetime.now().isoformat(),
                    "trade_id": state.trade_id,
                    "phase": phase,
                    "instrument_token": token,
                    "symbol": tick.get("symbol"),
                },
            )

    def _finalize_capture_if_due(self) -> None:
        state = self.trade_capture
        if state is None or state.post_exit_until is None:
            return
        if datetime.now() > state.post_exit_until + timedelta(seconds=1):
            self.trade_capture = None

    def _latest_spot_quote(self) -> dict[str, Any] | None:
        if self.latest_index_tick is None:
            return None
        return self._quote_from_tick(self.latest_index_tick)

    def _latest_future_quote(self) -> dict[str, Any] | None:
        if self.latest_future_tick is None:
            return None
        return self._quote_from_tick(self.latest_future_tick)

    @staticmethod
    def _quote_from_tick(tick: dict[str, Any]) -> dict[str, Any]:
        return {
            "timestamp": tick["timestamp_exchange"],
            "ltp": float(tick["ltp"]),
            "bid": tick.get("best_bid"),
            "ask": tick.get("best_ask"),
            "spread": tick.get("spread"),
            "last_trade_time": tick.get("timestamp_exchange"),
        }

    def _periodic_control_poll(self) -> None:
        now = time.monotonic()
        if now - self._last_control_poll < 1.0:
            return
        self._last_control_poll = now
        self.engine._maybe_process_runtime_control()

    def _on_disconnect(self, code: int | None, reason: str | None) -> None:
        self._queue_runtime_event(
            "STREAM_DISCONNECTED",
            {
                "code": code,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def _on_reconnect(self, attempt: int) -> None:
        self._queue_runtime_event(
            "STREAM_RECONNECT",
            {
                "attempt": attempt,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def _on_connect(self) -> None:
        self._queue_runtime_event(
            "STREAM_CONNECTED",
            {"timestamp": datetime.now().isoformat()},
        )
        self._maybe_record_tape_subscription_state(
            reason="STREAM_CONNECTED",
            tick_time=datetime.now(),
        )

    def _maybe_record_tape_subscription_state(self, reason: str, tick_time: datetime) -> None:
        if not bool(getattr(self.engine.settings, "enable_sensex_option_tape_recorder", False)):
            return

        snapshot = self.stream.health_snapshot(now=tick_time)
        day = tick_time.date().isoformat()
        payload = {
            "timestamp": tick_time.isoformat(),
            "reason": reason,
            "current_atm": snapshot.get("current_atm_reference"),
            "current_tape_atm": snapshot.get("current_tape_atm_reference"),
            "strategy_option_lattice_size": snapshot.get("strategy_option_lattice_size"),
            "tape_option_lattice_size": snapshot.get("tape_option_lattice_size"),
            "combined_option_token_count": snapshot.get("current_option_lattice_size"),
            "current_subscribed_token_count": snapshot.get("current_subscribed_token_count"),
        }
        self.tick_journal.append_tape_subscription_snapshot(day=day, snapshot=payload)

        manifest = {
            "date": day,
            "underlying": "SENSEX",
            "enabled": True,
            "strike_range_points": self.engine.settings.sensex_tape_strike_range_points,
            "strike_step_points": self.engine.settings.sensex_tape_strike_step_points,
            "expiry_mode": self.engine.settings.sensex_tape_expiry_mode,
            "include_ce": self.engine.settings.sensex_tape_include_ce,
            "include_pe": self.engine.settings.sensex_tape_include_pe,
            "current_atm": snapshot.get("current_atm_reference"),
            "current_tape_atm": snapshot.get("current_tape_atm_reference"),
            "strategy_option_lattice_size": snapshot.get("strategy_option_lattice_size"),
            "tape_option_lattice_size": snapshot.get("tape_option_lattice_size"),
            "combined_option_token_count": snapshot.get("current_option_lattice_size"),
            "current_subscribed_token_count": snapshot.get("current_subscribed_token_count"),
            "last_updated_at": datetime.now().isoformat(),
            "write_format": "jsonl",
            "path": str(self.engine.settings.sensex_tape_log_dir / day / "options.jsonl"),
        }
        self.tick_journal.write_tape_manifest(day=day, manifest=manifest)

    def _queue_runtime_event(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            self.state_queue.put_nowait((event_type, payload))
        except queue.Full:
            logger.warning("state_queue full; dropping runtime event %s", event_type)

    def _safe_runtime_step(self, fn: Any, name: str) -> None:
        try:
            fn()
        except Exception as exc:
            logger.exception("Runtime maintenance step failed | step=%s", name)
            self.engine.journal.append_event(
                "RUNTIME_STEP_ERROR",
                {
                    "timestamp": datetime.now().isoformat(),
                    "step": name,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )

    def _process_state_events(self) -> None:
        while True:
            try:
                event_type, payload = self.state_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "STREAM_DISCONNECTED":
                self._entries_blocked_due_to_disconnect = True
                self._had_disconnect = True
            elif event_type == "FORCED_STREAM_RECONNECT_SUCCESS":
                self._had_disconnect = False

            self.engine.journal.append_event(event_type, payload)

        stream_health = self.stream.health_snapshot()
        self.telemetry.set_stream_state(
            connected=bool(stream_health.get("connected")),
            degraded=bool(stream_health.get("degraded")),
            reconnect_in_progress=bool(stream_health.get("reconnecting")),
            state=str(stream_health.get("stream_state")),
            generation_id=stream_health.get("generation_id"),
        )

    def _run_watchdog(self) -> None:
        now = datetime.now()
        market_session_active = dt_time(hour=9, minute=15) <= now.time() <= dt_time(hour=15, minute=30)
        stream_health = self.stream.health_snapshot(now=now)
        stream_state = str(stream_health.get("stream_state"))

        if stream_state == StreamState.RECONNECTING.value:
            return
        if stream_state == StreamState.DISCONNECTED.value:
            if market_session_active:
                self.stream.force_reconnect(
                    reason="STREAM_DISCONNECTED",
                    details={"timestamp": now.isoformat()},
                )
            return

        if stream_state == StreamState.CONNECTING.value:
            seconds_in_state = float(stream_health.get("seconds_in_state") or 0.0)
            if seconds_in_state > self._stream_connect_timeout_seconds:
                self.stream.force_reconnect(
                    reason="STREAM_CONNECT_TIMEOUT",
                    details={
                        "seconds_in_state": seconds_in_state,
                        "connect_timeout_seconds": self._stream_connect_timeout_seconds,
                    },
                )
            return

        if stream_state == StreamState.CONNECTED_PENDING_FIRST_TICK.value:
            seconds_in_state = float(stream_health.get("seconds_in_state") or 0.0)
            if seconds_in_state > self._stream_first_tick_timeout_seconds:
                self.stream.force_reconnect(
                    reason="STREAM_FIRST_TICK_TIMEOUT",
                    details={
                        "seconds_in_state": seconds_in_state,
                        "first_tick_timeout_seconds": self._stream_first_tick_timeout_seconds,
                    },
                )
            return

        status = self.watchdog.evaluate(
            now=now,
            stream_connected=bool(stream_health.get("connected")),
            market_session_active=market_session_active,
            last_index_receive_ts=self.telemetry.last_index_receive_ts(),
        )
        self._watchdog_degraded = bool(status.degraded)
        if status.event_type is not None and status.payload is not None:
            payload = dict(status.payload)
            payload.setdefault("timestamp", now.isoformat())
            self._queue_runtime_event(status.event_type, payload)
        if status.degraded:
            self.stream.mark_stale(reason=status.stale_reason or "WATCHDOG_STALE", idle_seconds=status.idle_seconds)
        else:
            self._reconnect_attempted_in_stale_episode = False
            self.stream.mark_recovered_from_stale(reason="WATCHDOG_RECOVERED")
        if status.should_reconnect:
            if not self._reconnect_attempted_in_stale_episode:
                details = {
                    "stale_reason": status.stale_reason,
                    "idle_seconds": status.idle_seconds,
                    "hard_reconnect_seconds": self.engine.settings.watchdog_hard_reconnect_seconds,
                }
                started = self.stream.force_reconnect(reason="WATCHDOG_STALE_FEED", details=details)
                if started:
                    self._reconnect_attempted_in_stale_episode = True

    def _emit_health_event_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_health_emit < self.HEALTH_EVENT_INTERVAL_SECONDS:
            return
        self._last_health_emit = now

        self._sync_subscription_telemetry()
        self._sync_telemetry_from_journal()
        self.telemetry.set_active_trade_id(self.engine.open_trade_id)
        stream_health = self.stream.health_snapshot()
        self.telemetry.set_stream_state(
            connected=bool(stream_health.get("connected")),
            degraded=bool(stream_health.get("degraded")),
            reconnect_in_progress=bool(stream_health.get("reconnecting")),
            state=str(stream_health.get("stream_state")),
            generation_id=stream_health.get("generation_id"),
        )

        self.engine.journal.append_event("RUNTIME_HEALTH", self.telemetry.snapshot())

    def _emit_runtime_heartbeat_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_heartbeat_emit < self._heartbeat_log_interval_seconds:
            return
        self._last_heartbeat_emit = now

        self._sync_subscription_telemetry()
        self._sync_telemetry_from_journal()
        stream_health = self.stream.health_snapshot()
        self.telemetry.set_stream_state(
            connected=bool(stream_health.get("connected")),
            degraded=bool(stream_health.get("degraded")),
            reconnect_in_progress=bool(stream_health.get("reconnecting")),
            state=str(stream_health.get("stream_state")),
            generation_id=stream_health.get("generation_id"),
        )

        snapshot = self.telemetry.snapshot()
        now_dt = datetime.now()
        last_index_ts = self.telemetry.last_index_receive_ts()
        last_any_ts = self.telemetry.last_any_receive_ts()
        index_idle = (now_dt - last_index_ts).total_seconds() if last_index_ts is not None else None
        any_idle = (now_dt - last_any_ts).total_seconds() if last_any_ts is not None else None

        logger.info(
            "Runtime heartbeat | state=%s gen=%s connected=%s degraded=%s reconnecting=%s first_tick_ready=%s subscriptions_ready=%s retiring=%s idle_index=%.2fs idle_any=%.2fs atm=%s subscribed=%s qcrit=%s qbg=%s qjrnl=%s drops_journal=%s",
            stream_health.get("stream_state"),
            stream_health.get("generation_id"),
            snapshot.get("stream_connected"),
            snapshot.get("stream_degraded"),
            snapshot.get("stream_reconnect_in_progress"),
            stream_health.get("active_generation_has_first_tick"),
            stream_health.get("active_generation_subscriptions_ready"),
            stream_health.get("retiring_generations_count"),
            index_idle if index_idle is not None else -1.0,
            any_idle if any_idle is not None else -1.0,
            snapshot.get("current_atm_reference"),
            snapshot.get("current_subscribed_token_count"),
            self.critical_tick_queue.qsize(),
            self.background_tick_queue.qsize(),
            snapshot.get("journal_queue_max_size_seen"),
            snapshot.get("journal_records_dropped_total"),
        )
        self.engine.journal.append_event(
            "RUNTIME_HEARTBEAT",
            {
                "timestamp": now_dt.isoformat(),
                "stream_connected": snapshot.get("stream_connected"),
                "stream_degraded": snapshot.get("stream_degraded"),
                "stream_reconnect_in_progress": snapshot.get("stream_reconnect_in_progress"),
                "stream_state": stream_health.get("stream_state"),
                "stream_generation_id": stream_health.get("generation_id"),
                "active_generation_has_first_tick": stream_health.get("active_generation_has_first_tick"),
                "active_generation_subscriptions_ready": stream_health.get("active_generation_subscriptions_ready"),
                "retiring_generations_count": stream_health.get("retiring_generations_count"),
                "seconds_since_last_index_tick": index_idle,
                "seconds_since_last_any_tick": any_idle,
                "current_atm_reference": snapshot.get("current_atm_reference"),
                "current_subscribed_token_count": snapshot.get("current_subscribed_token_count"),
                "critical_queue_size": self.critical_tick_queue.qsize(),
                "background_queue_size": self.background_tick_queue.qsize(),
                "journal_queue_size": self.tick_journal.stats_snapshot().get("queue_size", 0),
                "journal_records_dropped_total": snapshot.get("journal_records_dropped_total"),
            },
        )

    def _sync_subscription_telemetry(self) -> None:
        self.telemetry.set_subscription_state(
            subscribed_token_count=self.stream.subscribed_token_count,
            option_lattice_size=self.stream.option_lattice_size,
            current_atm_reference=self.stream.current_atm,
        )

    def _sync_telemetry_from_journal(self) -> None:
        stats = self.tick_journal.stats_snapshot()
        self.telemetry.sync_journal_stats(stats)
        self.telemetry.mark_queue_sizes(
            critical_size=self.critical_tick_queue.qsize(),
            background_size=self.background_tick_queue.qsize(),
            journal_size=stats.get("queue_size", 0),
        )

    def _is_degraded(self) -> bool:
        return bool(self.stream.health_snapshot().get("degraded"))

    def _is_critical_tick(self, tick: dict[str, Any]) -> bool:
        source = str(tick.get("source", "")).lower()
        if source in {"index", "future"}:
            return True

        token_raw = tick.get("instrument_token")
        try:
            token = int(token_raw)
        except (TypeError, ValueError):
            return False

        if self.trade_capture is not None and token in self.trade_capture.watched_tokens:
            return True

        if self.engine.open_position is not None:
            open_token = self.registry.token_for_symbol(self.engine.open_position.option_symbol)
            if open_token is not None and int(open_token) == token:
                return True
        return False

    def _maybe_enable_daily_trade_journal(self) -> None:
        now_day = datetime.now().date().isoformat()

        trade_path = self.engine.settings.trade_log_path
        if trade_path.name == "trades.jsonl":
            trade_path = self.engine.settings.logs_dir / "trades" / f"{now_day}.trades.jsonl"

        event_path = self.engine.settings.event_log_path
        if event_path.name == "events.jsonl":
            event_path = self.engine.settings.logs_dir / "events" / f"{now_day}.events.jsonl"

        enriched_path = self.engine.settings.enriched_trade_log_path
        if enriched_path.name == "trades_enriched.jsonl":
            enriched_path = self.engine.settings.logs_dir / "trades" / f"{now_day}.trades_enriched.jsonl"

        self.engine.journal = TradeJournal(
            path=trade_path,
            event_path=event_path,
            enriched_trade_path=enriched_path,
        )
