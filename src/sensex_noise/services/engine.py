from __future__ import annotations

import logging
import math
import time
from datetime import datetime, time as dt_time, timedelta
from typing import Any

from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException

from sensex_noise.broker.factory import create_broker
from sensex_noise.candle_state import CandleTracker
from sensex_noise.charges import ChargesModel
from sensex_noise.config import Settings
from sensex_noise.models import Position
from sensex_noise.selector import InstrumentSelector
from sensex_noise.services.instruments import InstrumentService
from sensex_noise.services.market_data import MarketDataService
from sensex_noise.services.runtime_control import parse_command, read_control, reset_control
from sensex_noise.services.sizing import calculate_position_quantity
from sensex_noise.services.trade_journal import TradeJournal
from sensex_noise.strategy import Signal, StrategyEvaluator
from sensex_noise.wallet import Wallet

logger = logging.getLogger(__name__)
AUTH_FAILURE_MSG = (
    "Authentication failed: Kite rejected api_key/access_token. Most likely causes: "
    "expired access token, api_key from different app, or wrong .env file loaded. "
    "Run: python scripts/check_kite_auth.py"
)
EXIT_REASON_PRECEDENCE = (
    "MANUAL_EXIT",
    "HARD_STOP_EXIT",
    "EARLY_RISK_EXIT",
    "PATH_RISK_EXIT",
    "MANUAL_LIMIT_HIT",
    "TARGET_HIT",
    "TIME_STOP_AFTER_1PM",
)


class StrategyEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.wallet = Wallet(starting_capital=settings.starting_capital)
        self.charges_model = ChargesModel()
        self.candle_tracker = CandleTracker()
        self.evaluator = StrategyEvaluator(entry_buffer_points=settings.entry_buffer_points)
        self.entry_cutoff_time = dt_time.fromisoformat(settings.entry_cutoff_time)
        self.broker = create_broker(settings)
        self.market_data = MarketDataService(self.broker)
        kite_for_instruments = KiteConnect(api_key=settings.kite_api_key)
        kite_for_instruments.set_access_token(settings.kite_access_token)
        instruments = InstrumentService(
            kite=kite_for_instruments,
            cache_path=settings.instruments_cache_path,
        ).load(force_refresh=False)
        self.selector = InstrumentSelector(instruments)
        self.journal = TradeJournal(
            path=settings.trade_log_path,
            event_path=settings.event_log_path,
            enriched_trade_path=settings.enriched_trade_log_path,
        )

        self.open_position: Position | None = None
        self.open_trade_id: str | None = None
        self.triggered_candle_start = None
        self.attempted_entry_candles: set[datetime] = set()

        self.active_exit_order_type: str | None = None
        self.active_exit_price: float | None = None
        self.active_exit_order_id: str | None = None
        self.active_exit_order_variety: str = "regular"
        self.active_exit_order_sent_time: datetime | None = None
        self.active_exit_order_ack_time: datetime | None = None

        self.pending_post_exit_observations: list[dict[str, Any]] = []
        self.manual_exit_requested: bool = False

    def _after_market_open(self, now: datetime) -> bool:
        return now.time() >= dt_time(hour=9, minute=15)

    def _is_post_1pm(self, moment: datetime) -> bool:
        return moment.time() >= dt_time(hour=13, minute=0)

    def _sleep_with_control_poll(self, seconds: float) -> None:
        # Keep control.json responsive even if main poll interval is > 1s.
        deadline = time.monotonic() + max(0.0, float(seconds))
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(1.0, remaining))
            self._maybe_process_runtime_control()

    def _past_entry_cutoff(self, now: datetime) -> bool:
        return now.time() >= self.entry_cutoff_time

    def _is_same_price(self, a: float | None, b: float | None) -> bool:
        if a is None or b is None:
            return False
        return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=0.01)

    def _startup_auth_check(self) -> bool:
        try:
            self.broker.verify_auth()
            logger.info("Kite authentication check passed")
            return True
        except TokenException:
            logger.error(AUTH_FAILURE_MSG)
            return False

    def _build_trade_id(self, signal: Signal, option_symbol: str, signal_seen_time: datetime) -> str:
        ts = signal_seen_time.strftime("%Y%m%dT%H%M%S")
        signal_kind = getattr(signal, "signal_kind", "UNKNOWN")
        return f"{ts}|{option_symbol}|{signal_kind}|{signal.side.value}"

    def _get_target_points(self, entry_time: datetime, fragile: bool = False) -> float:
        if not fragile or not self.settings.enable_dynamic_risky_target:
            return float(self.settings.target_points)
        if self._is_post_1pm(entry_time):
            return float(self.settings.strict_after_1pm_risky_target_points)
        return float(self.settings.risky_target_points)

    def _get_hard_stop_points(self, signal_kind: str) -> float:
        if signal_kind == "CONTINUATION_CALL":
            return float(self.settings.continuation_call_hard_stop_points)
        return float(self.settings.hard_stop_points)

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.journal.append_event(event_type, payload)

    def _log_signal_generated(
        self,
        signal: Signal,
        signal_time: datetime,
        spot_ltp: float,
        previous_candle: Any,
    ) -> None:
        if not self.settings.enable_signal_logging:
            return
        prev_payload: dict[str, Any] = {}
        if previous_candle is not None:
            prev_payload = {
                "previous_candle_start": previous_candle.start.isoformat(),
                "previous_candle_end": previous_candle.end.isoformat(),
                "previous_candle_open": previous_candle.open,
                "previous_candle_high": previous_candle.high,
                "previous_candle_low": previous_candle.low,
                "previous_candle_close": previous_candle.close,
            }
        self._append_event(
            "SIGNAL_GENERATED",
            {
                "signal_time": signal_time.isoformat(),
                "signal_kind": getattr(signal, "signal_kind", "UNKNOWN"),
                "side": signal.side.value,
                "trigger_price": signal.trigger_price,
                "spot_ltp": spot_ltp,
                "spot_minus_trigger": float(spot_ltp - signal.trigger_price),
                "source_candle_start": signal.source_candle_start.isoformat(),
                **prev_payload,
            },
        )

    def _log_entry_context(
        self,
        trade_id: str,
        signal: Signal,
        choice: Any,
        quantity: int,
        target_points: float,
        spot_at_signal: float,
        spot_at_entry_attempt: float,
        option_quote: dict[str, Any],
    ) -> None:
        if not self.settings.enable_entry_context_logging:
            return
        self._append_event(
            "ENTRY_CONTEXT",
            {
                "trade_id": trade_id,
                "option_symbol": choice.full_symbol,
                "strike": choice.strike,
                "expiry": choice.expiry.isoformat(),
                "signal_kind": getattr(signal, "signal_kind", "UNKNOWN"),
                "spot_at_signal": spot_at_signal,
                "spot_at_entry_attempt": spot_at_entry_attempt,
                "spot_minus_trigger_at_entry": float(spot_at_entry_attempt - signal.trigger_price),
                "option_ltp": float(option_quote.get("ltp", 0.0)),
                "bid": option_quote.get("bid"),
                "ask": option_quote.get("ask"),
                "spread": option_quote.get("spread"),
                "quantity": quantity,
                "target_points": target_points,
            },
        )

    def _cancel_active_exit_order(self, reason: str) -> bool:
        if self.active_exit_order_type is None:
            return True
        cancelled = True
        if self.active_exit_order_id is not None:
            try:
                self.broker.cancel_order(
                    variety=self.active_exit_order_variety,
                    order_id=self.active_exit_order_id,
                )
            except Exception as exc:
                logger.warning("Cancel order failed for %s: %s", self.active_exit_order_id, exc)
                cancelled = False
        logger.info(
            "PENDING EXIT CANCELLED | type=%s | price=%s | order_id=%s | reason=%s",
            self.active_exit_order_type,
            self.active_exit_price,
            self.active_exit_order_id,
            reason,
        )
        self.journal.append(
            "PENDING_EXIT_CANCELLED",
            {
                "trade_id": self.open_trade_id,
                "symbol": self.open_position.option_symbol if self.open_position else None,
                "product": self.open_position.product if self.open_position else None,
                "cancel_reason": reason,
                "cancelled_exit_order_type": self.active_exit_order_type,
                "cancelled_exit_price": self.active_exit_price,
                "cancelled_order_id": self.active_exit_order_id,
                "cancelled": cancelled,
            },
        )
        self.active_exit_order_type = None
        self.active_exit_price = None
        self.active_exit_order_id = None
        self.active_exit_order_variety = "regular"
        self.active_exit_order_sent_time = None
        self.active_exit_order_ack_time = None
        return cancelled

    def _place_target_exit_order(self, trigger_reason: str = "TARGET") -> bool:
        if self.open_position is None:
            return False
        sent_time = datetime.now()
        self._append_event(
            "EXIT_ORDER_SENT",
            {
                "trade_id": self.open_trade_id,
                "order_id": None,
                "symbol": self.open_position.option_symbol,
                "variety": self.active_exit_order_variety,
                "order_type": "LIMIT",
                "transaction_type": "SELL",
                "exit_purpose": "TARGET",
                "requested_price": self.open_position.target_price,
                "quantity": self.open_position.quantity,
                "trigger_reason": trigger_reason,
                "closing": self.open_position.closing,
                "fragile": self.open_position.fragile,
                "sent_time": sent_time.isoformat(),
            },
        )
        try:
            order_id = self.broker.place_exit_limit(
                symbol=self.open_position.option_symbol,
                quantity=self.open_position.quantity,
                price=self.open_position.target_price,
                product=self.settings.order_product,
            )
        except Exception as exc:
            self._append_event(
                "TARGET_ORDER_PLACE_FAILED",
                {
                    "trade_id": self.open_trade_id,
                    "symbol": self.open_position.option_symbol,
                    "requested_price": self.open_position.target_price,
                    "quantity": self.open_position.quantity,
                    "trigger_reason": trigger_reason,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return False
        ack_time = datetime.now()
        self.active_exit_order_type = "TARGET"
        self.active_exit_price = self.open_position.target_price
        self.active_exit_order_id = order_id
        self.active_exit_order_variety = "regular"
        self.active_exit_order_sent_time = sent_time
        self.active_exit_order_ack_time = ack_time
        self._append_event(
            "EXIT_ORDER_ACKED",
            {
                "trade_id": self.open_trade_id,
                "symbol": self.open_position.option_symbol,
                "variety": self.active_exit_order_variety,
                "order_type": "LIMIT",
                "transaction_type": "SELL",
                "exit_purpose": "TARGET",
                "order_id": order_id,
                "requested_price": self.open_position.target_price,
                "trigger_reason": trigger_reason,
                "closing": self.open_position.closing,
                "fragile": self.open_position.fragile,
                "ack_time": ack_time.isoformat(),
            },
        )
        return True

    def _place_manual_limit_exit_order(self, price: float) -> bool:
        if self.open_position is None:
            return False
        sent_time = datetime.now()
        self._append_event(
            "EXIT_ORDER_SENT",
            {
                "trade_id": self.open_trade_id,
                "order_id": None,
                "symbol": self.open_position.option_symbol,
                "variety": self.active_exit_order_variety,
                "order_type": "LIMIT",
                "transaction_type": "SELL",
                "exit_purpose": "MANUAL_LIMIT",
                "requested_price": float(price),
                "quantity": self.open_position.quantity,
                "trigger_reason": "MANUAL_LIMIT",
                "closing": self.open_position.closing,
                "fragile": self.open_position.fragile,
                "sent_time": sent_time.isoformat(),
            },
        )
        try:
            order_id = self.broker.place_exit_limit(
                symbol=self.open_position.option_symbol,
                quantity=self.open_position.quantity,
                price=price,
                product=self.settings.order_product,
            )
        except Exception as exc:
            self._append_event(
                "MANUAL_LIMIT_ORDER_PLACE_FAILED",
                {
                    "trade_id": self.open_trade_id,
                    "symbol": self.open_position.option_symbol,
                    "requested_price": float(price),
                    "quantity": self.open_position.quantity,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return False
        ack_time = datetime.now()
        self.active_exit_order_type = "MANUAL_LIMIT"
        self.active_exit_price = float(price)
        self.active_exit_order_id = order_id
        self.active_exit_order_variety = "regular"
        self.active_exit_order_sent_time = sent_time
        self.active_exit_order_ack_time = ack_time
        self._append_event(
            "EXIT_ORDER_ACKED",
            {
                "trade_id": self.open_trade_id,
                "symbol": self.open_position.option_symbol,
                "variety": self.active_exit_order_variety,
                "order_type": "LIMIT",
                "transaction_type": "SELL",
                "exit_purpose": "MANUAL_LIMIT",
                "order_id": order_id,
                "requested_price": float(price),
                "trigger_reason": "MANUAL_LIMIT",
                "closing": self.open_position.closing,
                "fragile": self.open_position.fragile,
                "ack_time": ack_time.isoformat(),
            },
        )
        return True

    def _resolve_trade_quantity(self, option_ltp: float, lot_size: int) -> int | None:
        if self.settings.position_sizing_mode == "fixed":
            lots = self.settings.trade_qty // lot_size
            quantity = lots * lot_size
            if quantity <= 0:
                logger.warning("Configured TRADE_QTY is below 1 lot. Skipping trade.")
                return None
            return quantity

        available_funds = (
            self.broker.get_available_funds()
            if self.settings.use_kite_funds
            else self.settings.capital_budget
        )
        quantity = calculate_position_quantity(
            option_ltp=option_ltp,
            lot_size=lot_size,
            capital_budget=self.settings.capital_budget,
            available_funds=available_funds,
        )
        if quantity is None:
            usable_capital = min(float(self.settings.capital_budget), float(available_funds))
            cost_per_lot = float(option_ltp) * int(lot_size)
            logger.warning(
                "Sizing failure | usable_capital=%.2f | option_ltp=%.2f | lot_size=%d | cost_per_lot=%.2f",
                usable_capital,
                float(option_ltp),
                int(lot_size),
                cost_per_lot,
            )
            logger.warning("Capital insufficient for even 1 lot. Skipping trade.")
        return quantity

    def _observe_post_exit(self, position: Position) -> None:
        if not self.settings.enable_post_exit_observation:
            position.post_exit_observation_done = True
            return
        if position.exit_time is None:
            position.post_exit_observation_done = True
            return
        if self.settings.post_exit_observation_seconds <= 0:
            position.post_exit_observation_done = True
            return

        interval = max(1, int(self.settings.post_exit_observation_interval_seconds))
        max_seconds = int(self.settings.post_exit_observation_seconds)
        schedule = list(range(interval, max_seconds + 1, interval))
        if not schedule or schedule[-1] != max_seconds:
            schedule.append(max_seconds)

        position.post_exit_observation_done = False
        position.post_exit_observation_seconds = max_seconds
        position.post_exit_path = []
        position.post_exit_points_best_recovery = None
        position.post_exit_points_worst_further_loss = None
        position.post_exit_recovered_above_exit = False
        position.post_exit_max_recovery_second = None
        position.post_exit_max_further_loss_second = None
        position.post_exit_final_delta = None
        self.pending_post_exit_observations.append(
            {
                "trade_id": position.trade_id,
                "option_symbol": position.option_symbol,
                "exit_time": position.exit_time,
                "exit_price": position.exit_price,
                "end_time": position.exit_time + timedelta(seconds=max_seconds),
                "schedule": schedule,
                "emitted": set(),
                "position": position,
            }
        )

    def _finalize_post_exit_observation(self, state: dict[str, Any]) -> None:
        position: Position | None = state.get("position")
        if position is None:
            return

        deltas: list[tuple[int, float]] = []
        for row in position.post_exit_path:
            sec = row.get("seconds_after_exit")
            delta = row.get("delta_from_exit_price")
            if isinstance(sec, int) and isinstance(delta, (int, float)):
                deltas.append((sec, float(delta)))

        if deltas:
            best = max(deltas, key=lambda item: item[1])[1]
            worst = min(deltas, key=lambda item: item[1])[1]
            position.post_exit_points_best_recovery = best
            position.post_exit_points_worst_further_loss = worst
            position.post_exit_recovered_above_exit = any(delta > 0 for _, delta in deltas)
            position.post_exit_max_recovery_second = min(
                sec for sec, delta in deltas if delta == best
            )
            position.post_exit_max_further_loss_second = min(
                sec for sec, delta in deltas if delta == worst
            )
            position.post_exit_final_delta = deltas[-1][1]

        position.post_exit_observation_done = True
        self._append_event(
            "POST_EXIT_OBSERVATION_COMPLETED",
            {
                "trade_id": state.get("trade_id"),
                "option_symbol": state.get("option_symbol"),
                "post_exit_observation_seconds": position.post_exit_observation_seconds,
                "samples_recorded": len(position.post_exit_path),
                "post_exit_points_best_recovery": position.post_exit_points_best_recovery,
                "post_exit_points_worst_further_loss": position.post_exit_points_worst_further_loss,
                "post_exit_recovered_above_exit": position.post_exit_recovered_above_exit,
                "post_exit_max_recovery_second": position.post_exit_max_recovery_second,
                "post_exit_max_further_loss_second": position.post_exit_max_further_loss_second,
                "post_exit_final_delta": position.post_exit_final_delta,
            },
        )
        self.journal.append_trade_summary(
            position=position,
            extra_payload={"summary_version": "post_exit_enriched"},
        )

    def _emit_due_post_exit_observations(self, spot_quote: dict[str, Any]) -> None:
        if not self.pending_post_exit_observations:
            return

        spot_ltp_raw = spot_quote.get("ltp") if isinstance(spot_quote, dict) else None
        try:
            spot_ltp = float(spot_ltp_raw) if spot_ltp_raw is not None else None
        except (TypeError, ValueError):
            spot_ltp = None
        now = spot_quote.get("timestamp", datetime.now()) if isinstance(spot_quote, dict) else datetime.now()
        if not isinstance(now, datetime):
            now = datetime.now()
        remaining: list[dict[str, Any]] = []
        for state in self.pending_post_exit_observations:
            exit_time = state["exit_time"]
            elapsed = (now - exit_time).total_seconds()
            if elapsed < 0:
                remaining.append(state)
                continue

            position: Position | None = state.get("position")
            due = [
                sec
                for sec in state["schedule"]
                if sec <= elapsed and sec not in state["emitted"]
            ]
            if due:
                option_quote: dict[str, Any] = {}
                option_quote_error: Exception | None = None
                try:
                    option_quote = self.market_data.option_quote(state["option_symbol"])
                except Exception as exc:
                    option_quote_error = exc
                    self._append_event(
                        "POST_EXIT_OBSERVATION_ERROR",
                        {
                            "trade_id": state["trade_id"],
                            "option_symbol": state["option_symbol"],
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                            "seconds_due": due,
                        },
                    )

                option_ltp: float | None = None
                observed_at = now
                if option_quote_error is None:
                    ltp_raw = option_quote.get("ltp")
                    try:
                        option_ltp = float(ltp_raw) if ltp_raw is not None else None
                    except (TypeError, ValueError):
                        option_ltp = None
                    observed_at_raw = option_quote.get("timestamp")
                    if isinstance(observed_at_raw, datetime):
                        observed_at = observed_at_raw

                exit_price_raw = state.get("exit_price")
                try:
                    exit_price = float(exit_price_raw) if exit_price_raw is not None else None
                except (TypeError, ValueError):
                    exit_price = None

                for sec in sorted(due):
                    state["emitted"].add(sec)
                    delta_from_exit = None
                    recovered_above_exit = False
                    if option_ltp is not None and exit_price is not None:
                        delta_from_exit = float(option_ltp - exit_price)
                        recovered_above_exit = bool(delta_from_exit > 0)

                    payload = {
                        "trade_id": state["trade_id"],
                        "option_symbol": state["option_symbol"],
                        "seconds_after_exit": sec,
                        "observed_at": observed_at.isoformat(),
                        "option_ltp": option_ltp,
                        "spot_ltp": spot_ltp,
                        "delta_from_exit_price": delta_from_exit,
                        "recovered_above_exit": recovered_above_exit,
                    }
                    self._append_event("POST_EXIT_OBSERVATION", payload)
                    if position is not None:
                        position.post_exit_path.append(
                            {
                                "seconds_after_exit": sec,
                                "observed_at": observed_at.isoformat(),
                                "option_ltp": option_ltp,
                                "spot_ltp": spot_ltp,
                                "delta_from_exit_price": delta_from_exit,
                                "recovered_above_exit": recovered_above_exit,
                            }
                        )
                    if self.settings.enable_post_exit_counterfactual and state.get("exit_price") is not None:
                        self._append_event(
                            "POST_EXIT_COUNTERFACTUAL",
                            {
                                **payload,
                                "counterfactual_pnl_points": delta_from_exit,
                            },
                        )

            all_due_emitted = len(state["emitted"]) == len(state["schedule"])
            if all_due_emitted:
                self._finalize_post_exit_observation(state)
            else:
                remaining.append(state)

        self.pending_post_exit_observations = remaining

    def _update_path_features(
        self,
        position: Position,
        mark_time: datetime,
        option_quote: dict[str, Any],
        spot_quote: dict[str, Any],
    ) -> dict[str, float]:
        option_ltp = float(option_quote["ltp"])
        spot_ltp = float(spot_quote["ltp"])
        pnl_delta = option_ltp - position.entry_price
        duration_seconds = max(0.0, (mark_time - position.entry_time).total_seconds())

        position.current_price = option_ltp
        position.current_spot = spot_ltp
        position.max_favorable_excursion = max(position.max_favorable_excursion, pnl_delta)
        position.max_adverse_excursion = min(position.max_adverse_excursion, pnl_delta)

        spread = option_quote.get("spread")
        if spread is not None:
            position.spread_sum += float(spread)
            position.spread_count += 1

        if not position.price_history or position.price_history[-1][0] != mark_time:
            position.price_history.append((mark_time, option_ltp))

        if position.first_move_direction == "UNKNOWN":
            if pnl_delta > 0:
                position.first_move_direction = "POSITIVE"
            elif pnl_delta < 0:
                position.first_move_direction = "NEGATIVE"

        if position.first_positive_seconds is None and pnl_delta > 0:
            position.first_positive_seconds = duration_seconds
        if position.first_negative_seconds is None and pnl_delta < 0:
            position.first_negative_seconds = duration_seconds

        if position.time_to_minus_1 is None and pnl_delta <= -1.0:
            position.time_to_minus_1 = duration_seconds
        if position.time_to_minus_3 is None and pnl_delta <= -3.0:
            position.time_to_minus_3 = duration_seconds
        if position.time_to_minus_5 is None and pnl_delta <= -5.0:
            position.time_to_minus_5 = duration_seconds
        if position.time_to_plus_1 is None and pnl_delta >= 1.0:
            position.time_to_plus_1 = duration_seconds
        if position.time_to_plus_2 is None and pnl_delta >= 2.0:
            position.time_to_plus_2 = duration_seconds

        if len(position.price_history) >= 2:
            t0, p0 = position.price_history[-2]
            t1, p1 = position.price_history[-1]
            dt = max((t1 - t0).total_seconds(), 1e-6)
            slope = (p1 - p0) / dt
            if position.worst_step_slope is None:
                position.worst_step_slope = slope
            else:
                position.worst_step_slope = min(position.worst_step_slope, slope)

        position.avg_slope_5s = self._window_slope(position=position, now=mark_time, window_seconds=5)
        position.avg_slope_10s = self._window_slope(position=position, now=mark_time, window_seconds=10)

        resolved_thresholds: dict[str, float] = {}
        threshold_keys = {
            "time_to_minus_1": position.time_to_minus_1,
            "time_to_minus_3": position.time_to_minus_3,
            "time_to_minus_5": position.time_to_minus_5,
            "time_to_plus_1": position.time_to_plus_1,
            "time_to_plus_2": position.time_to_plus_2,
        }
        for key, value in threshold_keys.items():
            feature_flag = f"resolved_{key}"
            if value is not None and feature_flag not in position.snapshot_features:
                position.snapshot_features[feature_flag] = True
                resolved_thresholds[key] = value

        return resolved_thresholds

    def _window_slope(self, position: Position, now: datetime, window_seconds: int) -> float | None:
        if len(position.price_history) < 2:
            return None

        newest_time, newest_price = position.price_history[-1]
        cutoff = now.timestamp() - float(window_seconds)
        baseline_time = None
        baseline_price = None
        for ts, price in reversed(position.price_history):
            if ts.timestamp() <= cutoff:
                baseline_time = ts
                baseline_price = price
                break
        if baseline_time is None:
            baseline_time, baseline_price = position.price_history[0]

        dt = max((newest_time - baseline_time).total_seconds(), 1e-6)
        return (newest_price - baseline_price) / dt

    def _emit_due_snapshots(
        self,
        position: Position,
        mark_time: datetime,
        option_quote: dict[str, Any],
        spot_quote: dict[str, Any],
        resolved_thresholds: dict[str, float],
    ) -> None:
        elapsed_seconds = max(0.0, (mark_time - position.entry_time).total_seconds())
        option_ltp = float(option_quote["ltp"])
        current_pnl = option_ltp - position.entry_price
        signal_kind = position.signal_kind

        for sec in self.settings.snapshot_seconds:
            if sec in position.snapshots_emitted:
                continue
            if elapsed_seconds < sec:
                continue

            runup = position.max_favorable_excursion
            drawdown = position.max_adverse_excursion
            below_entry = option_ltp < position.entry_price

            position.snapshot_features[f"runup_{sec}s"] = runup
            position.snapshot_features[f"drawdown_{sec}s"] = drawdown
            position.snapshot_features[f"current_pnl_{sec}s"] = current_pnl
            position.snapshot_features[f"below_entry_{sec}s"] = below_entry

            payload = {
                "trade_id": position.trade_id,
                "seconds_from_entry": sec,
                "option_ltp": option_ltp,
                "spot_ltp": float(spot_quote["ltp"]),
                "bid": option_quote.get("bid"),
                "ask": option_quote.get("ask"),
                "spread": option_quote.get("spread"),
                "current_pnl": current_pnl,
                "mfe": runup,
                "mae": drawdown,
                "below_entry": below_entry,
                "signal_kind": signal_kind,
                "fragile": position.fragile,
                "first_move_direction": position.first_move_direction,
                "resolved_thresholds": resolved_thresholds,
            }
            if self.settings.enable_snapshot_logging:
                self._append_event("TRADE_SNAPSHOT", payload)
            position.snapshots_emitted.append(sec)

    def _maybe_mark_early_suspicion(
        self,
        position: Position,
        mark_time: datetime,
        option_ltp: float,
    ) -> None:
        if not self.settings.enable_early_risk:
            return
        if position.early_risk_suspicion_logged:
            return

        elapsed = (mark_time - position.entry_time).total_seconds()
        if elapsed < self.settings.early_risk_suspicion_seconds:
            return

        current_pnl = option_ltp - position.entry_price
        suspicion_threshold = self.settings.early_risk_suspicion_current_pnl
        if self.settings.early_risk_strict_after_1pm and position.pre_or_post_1pm == "POST_1PM":
            suspicion_threshold += 0.5

        criteria = {
            "current_pnl_condition": current_pnl <= suspicion_threshold,
            "adverse_first_move_condition": (
                position.first_move_direction == "NEGATIVE"
                if self.settings.early_risk_suspicion_require_adverse_first_move
                else True
            ),
        }

        if all(criteria.values()):
            position.fragile = True
            position.early_risk_suspicion_logged = True
            self._append_event(
                "EARLY_RISK_SUSPECTED",
                {
                    "trade_id": position.trade_id,
                    "seconds_from_entry": elapsed,
                    "current_pnl": current_pnl,
                    "suspicion_threshold": suspicion_threshold,
                    "criteria": criteria,
                    "first_move_direction": position.first_move_direction,
                    "pre_or_post_1pm": position.pre_or_post_1pm,
                },
            )
            self._maybe_reprice_target_for_fragile(position=position)

    def _should_early_exit(
        self,
        position: Position,
        mark_time: datetime,
        option_ltp: float,
        record: bool = False,
    ) -> bool:
        if not self.settings.enable_early_risk:
            return False
        if position.early_risk_exit_triggered:
            return False

        elapsed = (mark_time - position.entry_time).total_seconds()
        if elapsed < self.settings.early_risk_exit_seconds:
            return False

        sec = self.settings.early_risk_exit_seconds
        runup = float(position.snapshot_features.get(f"runup_{sec}s", position.max_favorable_excursion))
        drawdown = float(position.snapshot_features.get(f"drawdown_{sec}s", position.max_adverse_excursion))
        current_pnl = option_ltp - position.entry_price

        runup_threshold = self.settings.early_risk_runup_max_for_exit
        drawdown_threshold = self.settings.early_risk_drawdown_min_for_exit
        if self.settings.early_risk_strict_after_1pm and position.pre_or_post_1pm == "POST_1PM":
            runup_threshold += 0.5
            drawdown_threshold += 0.5

        below_entry = option_ltp < position.entry_price
        should_exit = (
            runup < runup_threshold
            and drawdown <= drawdown_threshold
            and (
                below_entry
                if self.settings.early_risk_require_below_entry
                else True
            )
        )

        if should_exit and record:
            position.early_risk_exit_triggered = True
            self._append_event(
                "EARLY_RISK_EXIT",
                {
                    "trade_id": position.trade_id,
                    "seconds_from_entry": elapsed,
                    "runup": runup,
                    "drawdown": drawdown,
                    "current_pnl": current_pnl,
                    "below_entry": below_entry,
                    "runup_threshold": runup_threshold,
                    "drawdown_threshold": drawdown_threshold,
                    "require_below_entry": self.settings.early_risk_require_below_entry,
                },
            )
        return should_exit

    def _should_path_exit(
        self,
        position: Position,
        mark_time: datetime,
        option_ltp: float,
        record: bool = False,
    ) -> bool:
        if not self.settings.enable_path_risk:
            return False
        if position.path_risk_exit_triggered:
            return False

        elapsed = (mark_time - position.entry_time).total_seconds()
        if elapsed < self.settings.path_risk_check_seconds:
            return False

        sec = self.settings.path_risk_check_seconds
        runup = float(position.snapshot_features.get(f"runup_{sec}s", position.max_favorable_excursion))
        current_pnl = option_ltp - position.entry_price

        pnl_threshold = self.settings.path_risk_pnl_min_for_exit
        runup_threshold = self.settings.path_risk_runup_max_for_exit
        strict_flags: list[str] = []

        if self.settings.path_risk_strict_after_1pm and position.pre_or_post_1pm == "POST_1PM":
            pnl_threshold += 0.5
            runup_threshold += 0.5
            strict_flags.append("STRICT_AFTER_1PM")

        if self.settings.path_risk_tighten_if_fragile and position.fragile:
            pnl_threshold += 0.5
            runup_threshold += 0.5
            strict_flags.append("FRAGILE_TIGHTENED")

        should_exit = current_pnl <= pnl_threshold and runup < runup_threshold
        if should_exit and record:
            position.path_risk_exit_triggered = True
            self._append_event(
                "PATH_RISK_EXIT",
                {
                    "trade_id": position.trade_id,
                    "seconds_from_entry": elapsed,
                    "current_pnl": current_pnl,
                    "runup": runup,
                    "pnl_threshold": pnl_threshold,
                    "runup_threshold": runup_threshold,
                    "strict_flags": strict_flags,
                },
            )
        return should_exit

    def _should_hard_stop(
        self,
        position: Position,
        mark_time: datetime,
        option_ltp: float,
        record: bool = False,
    ) -> bool:
        if not self.settings.enable_hard_stop:
            return False
        elapsed = (mark_time - position.entry_time).total_seconds()
        if elapsed < self.settings.hard_stop_arm_after_seconds:
            return False
        current_pnl = option_ltp - position.entry_price
        hard_stop_points = position.hard_stop_points_used or self._get_hard_stop_points(position.signal_kind)
        if current_pnl <= -hard_stop_points:
            if record:
                position.hard_stop_triggered = True
                self._append_event(
                    "HARD_STOP_EXIT",
                    {
                        "trade_id": position.trade_id,
                        "current_pnl": current_pnl,
                        "hard_stop_points": hard_stop_points,
                        "signal_kind": position.signal_kind,
                    },
                )
            return True
        return False

    def _collect_exit_candidates(
        self,
        position: Position,
        option_quote: dict[str, Any],
        mark_time: datetime,
    ) -> list[str]:
        if position.closing:
            return []

        option_ltp = float(option_quote["ltp"])
        candidates: list[str] = []
        if self.manual_exit_requested:
            candidates.append("MANUAL_EXIT")
        if self._should_hard_stop(position, mark_time=mark_time, option_ltp=option_ltp):
            candidates.append("HARD_STOP_EXIT")
        if self._should_early_exit(position, mark_time=mark_time, option_ltp=option_ltp):
            candidates.append("EARLY_RISK_EXIT")
        if self._should_path_exit(position, mark_time=mark_time, option_ltp=option_ltp):
            candidates.append("PATH_RISK_EXIT")
        if self.active_exit_order_type == "MANUAL_LIMIT" and self.active_exit_price is not None:
            if option_ltp >= self.active_exit_price:
                candidates.append("MANUAL_LIMIT_HIT")
        if option_ltp >= position.target_price:
            candidates.append("TARGET_HIT")
        holding_seconds = (mark_time - position.entry_time).total_seconds()
        if (
            position.entry_time.time() >= dt_time(hour=13, minute=0)
            and holding_seconds >= self.settings.post_1pm_time_stop_seconds
        ):
            candidates.append("TIME_STOP_AFTER_1PM")
        return candidates

    def _select_exit_reason(self, candidates: list[str]) -> str | None:
        if not candidates:
            return None
        for reason in EXIT_REASON_PRECEDENCE:
            if reason in candidates:
                return reason
        return None

    def _mark_position_closing(
        self,
        position: Position,
        selected_reason: str,
        candidates: list[str],
        decision_time: datetime,
        trigger_reference_price: float,
    ) -> None:
        position.closing = True
        position.closing_reason = selected_reason
        position.exit_decision_time = decision_time
        position.exit_trigger_reference_price = trigger_reference_price
        position.exit_trigger_reason_candidates = list(candidates)

    def _log_exit_decision_selected(
        self,
        position: Position,
        selected_reason: str,
        candidates: list[str],
        option_ltp: float,
        spot_ltp: float,
        holding_seconds: float,
    ) -> None:
        if not self.settings.enable_exit_decision_logging:
            return
        self._append_event(
            "EXIT_DECISION_SELECTED",
            {
                "trade_id": position.trade_id,
                "candidates": candidates,
                "selected_reason": selected_reason,
                "current_pnl": option_ltp - position.entry_price,
                "option_ltp": option_ltp,
                "spot_ltp": spot_ltp,
                "fragile": position.fragile,
                "holding_seconds": holding_seconds,
                "closing": position.closing,
            },
        )

    def _is_order_state_repriced(self, order_id: str, expected_price: float) -> bool:
        order_state = self.broker.get_order(order_id)
        if order_state is None:
            return False

        status = str(order_state.get("status", "")).upper()
        if status in {"COMPLETE", "CANCELLED", "REJECTED"}:
            return False

        order_price_raw = order_state.get("price")
        if order_price_raw is None:
            return True
        try:
            return self._is_same_price(float(order_price_raw), float(expected_price))
        except (TypeError, ValueError):
            return False

    def _cancel_and_replace_target_order(self, position: Position) -> bool:
        if self.active_exit_order_id is None:
            return self._place_target_exit_order(trigger_reason="TARGET_REPRICE")

        order_state = self.broker.get_order(self.active_exit_order_id)
        order_status = str((order_state or {}).get("status", "")).upper()
        if order_status == "COMPLETE":
            return False
        if order_status in {"CANCELLED", "REJECTED"}:
            self.active_exit_order_type = None
            self.active_exit_price = None
            self.active_exit_order_id = None
            self.active_exit_order_variety = "regular"
            self.active_exit_order_sent_time = None
            self.active_exit_order_ack_time = None
            return self._place_target_exit_order(trigger_reason="TARGET_REPRICE")

        cancelled = self._cancel_active_exit_order(reason="TARGET_REPRICE_CANCEL_REPLACE")
        if not cancelled:
            return False

        return self._place_target_exit_order(trigger_reason="TARGET_REPRICE")

    def _maybe_reprice_target_for_fragile(self, position: Position) -> None:
        if not self.settings.enable_dynamic_risky_target:
            return
        if position.closing or not position.fragile:
            return
        if position.target_reprice_in_progress:
            return

        now = datetime.now()
        if (
            position.target_order_last_modify_time is not None
            and self.settings.target_reprice_debounce_seconds > 0
            and (now - position.target_order_last_modify_time).total_seconds()
            < self.settings.target_reprice_debounce_seconds
        ):
            return

        risky_target = self._get_target_points(entry_time=position.entry_time, fragile=True)
        if risky_target >= position.target_points:
            return

        current_price = position.current_price if position.current_price is not None else position.entry_price
        if current_price >= position.entry_price + risky_target:
            return

        old_target_points = position.target_points
        old_target_price = position.target_price
        new_target_price = position.entry_price + risky_target

        position.target_reprice_in_progress = True
        self._append_event(
            "TARGET_REPRICE_ATTEMPT",
            {
                "trade_id": position.trade_id,
                "old_target_points": old_target_points,
                "new_target_points": risky_target,
                "old_target_price": old_target_price,
                "new_target_price": new_target_price,
                "active_exit_order_type": self.active_exit_order_type,
                "active_exit_order_id": self.active_exit_order_id,
                "fragile": position.fragile,
            },
        )

        try:
            position.target_points = risky_target
            position.target_price = new_target_price
            position.snapshot_features["target_points_used"] = position.target_points

            # No active target order: place one directly.
            if self.active_exit_order_id is None or self.active_exit_order_type is None:
                placed = self._place_target_exit_order(trigger_reason="TARGET_REPRICE")
                if placed:
                    position.target_reprice_count += 1
                    position.target_order_last_modify_time = now
                    self._append_event(
                        "TARGET_REPRICE_CANCEL_REPLACE_SUCCESS",
                        {
                            "trade_id": position.trade_id,
                            "mode": "PLACE_NEW",
                            "order_id": self.active_exit_order_id,
                            "new_target_price": position.target_price,
                            "new_target_points": position.target_points,
                        },
                    )
                    self._append_event(
                        "TARGET_REPRICED",
                        {
                            "trade_id": position.trade_id,
                            "old_target_points": old_target_points,
                            "new_target_points": position.target_points,
                            "old_target_price": old_target_price,
                            "new_target_price": position.target_price,
                            "active_exit_order_type": self.active_exit_order_type,
                            "active_exit_order_id": self.active_exit_order_id,
                            "fragile": position.fragile,
                            "pre_or_post_1pm": position.pre_or_post_1pm,
                        },
                    )
                else:
                    self._append_event(
                        "TARGET_REPRICE_CANCEL_REPLACE_FAILED",
                        {
                            "trade_id": position.trade_id,
                            "mode": "PLACE_NEW",
                            "new_target_price": position.target_price,
                        },
                    )
                    self._append_event(
                        "TARGET_REPRICE_FAILED",
                        {
                            "trade_id": position.trade_id,
                            "reason": "PLACE_NEW_FAILED",
                        },
                    )
                return

            # Active non-target order should not be touched.
            if self.active_exit_order_type != "TARGET":
                self._append_event(
                    "TARGET_REPRICE_MODIFY_FAILED",
                    {
                        "trade_id": position.trade_id,
                        "reason": "ACTIVE_EXIT_NOT_TARGET",
                        "active_exit_order_type": self.active_exit_order_type,
                        "active_exit_order_id": self.active_exit_order_id,
                    },
                )
                return

            order_state = self.broker.get_order(self.active_exit_order_id)
            order_status = str((order_state or {}).get("status", "")).upper()
            if order_status == "COMPLETE":
                self._append_event(
                    "TARGET_REPRICE_MODIFY_FAILED",
                    {
                        "trade_id": position.trade_id,
                        "order_id": self.active_exit_order_id,
                        "reason": "ORDER_ALREADY_COMPLETE",
                    },
                )
                return

            can_modify = (
                self.settings.enable_target_reprice_modify
                and self.broker.is_order_modifiable(
                    order_id=self.active_exit_order_id,
                    variety=self.active_exit_order_variety,
                )
            )
            modify_success = False
            if can_modify:
                try:
                    modified_order_id = self.broker.modify_order(
                        variety=self.active_exit_order_variety,
                        order_id=self.active_exit_order_id,
                        params={
                            "price": float(position.target_price),
                            "quantity": int(position.quantity),
                        },
                    )
                    if modified_order_id:
                        self.active_exit_order_id = str(modified_order_id)
                    modify_success = self._is_order_state_repriced(
                        order_id=self.active_exit_order_id,
                        expected_price=position.target_price,
                    )
                    if modify_success:
                        self.active_exit_price = position.target_price
                        position.target_reprice_count += 1
                        position.target_order_last_modify_time = now
                        self._append_event(
                            "TARGET_REPRICE_MODIFY_SUCCESS",
                            {
                                "trade_id": position.trade_id,
                                "order_id": self.active_exit_order_id,
                                "new_target_price": position.target_price,
                                "new_target_points": position.target_points,
                                "target_reprice_count": position.target_reprice_count,
                            },
                        )
                        self._append_event(
                            "TARGET_REPRICED",
                            {
                                "trade_id": position.trade_id,
                                "old_target_points": old_target_points,
                                "new_target_points": position.target_points,
                                "old_target_price": old_target_price,
                                "new_target_price": position.target_price,
                                "active_exit_order_type": self.active_exit_order_type,
                                "active_exit_order_id": self.active_exit_order_id,
                                "fragile": position.fragile,
                                "pre_or_post_1pm": position.pre_or_post_1pm,
                            },
                        )
                        return
                except Exception as exc:
                    self._append_event(
                        "TARGET_REPRICE_MODIFY_FAILED",
                        {
                            "trade_id": position.trade_id,
                            "order_id": self.active_exit_order_id,
                            "reason": "MODIFY_EXCEPTION",
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
            else:
                self._append_event(
                    "TARGET_REPRICE_MODIFY_FAILED",
                    {
                        "trade_id": position.trade_id,
                        "order_id": self.active_exit_order_id,
                        "reason": "ORDER_NOT_MODIFIABLE_OR_DISABLED",
                    },
                )

            if not modify_success and self.settings.enable_target_reprice_fallback_cancel_replace:
                prior_order_id = self.active_exit_order_id
                replaced = self._cancel_and_replace_target_order(position=position)
                if replaced:
                    position.target_reprice_count += 1
                    position.target_order_last_modify_time = now
                    self._append_event(
                        "TARGET_REPRICE_CANCEL_REPLACE_SUCCESS",
                        {
                            "trade_id": position.trade_id,
                            "old_order_id": prior_order_id,
                            "new_order_id": self.active_exit_order_id,
                            "new_target_price": position.target_price,
                            "new_target_points": position.target_points,
                            "target_reprice_count": position.target_reprice_count,
                        },
                    )
                    self._append_event(
                        "TARGET_REPRICED",
                        {
                            "trade_id": position.trade_id,
                            "old_target_points": old_target_points,
                            "new_target_points": position.target_points,
                            "old_target_price": old_target_price,
                            "new_target_price": position.target_price,
                            "active_exit_order_type": self.active_exit_order_type,
                            "active_exit_order_id": self.active_exit_order_id,
                            "fragile": position.fragile,
                            "pre_or_post_1pm": position.pre_or_post_1pm,
                        },
                    )
                else:
                    self._append_event(
                        "TARGET_REPRICE_CANCEL_REPLACE_FAILED",
                        {
                            "trade_id": position.trade_id,
                            "old_order_id": prior_order_id,
                            "new_target_price": position.target_price,
                            "new_target_points": position.target_points,
                        },
                    )
                    self._append_event(
                        "TARGET_REPRICE_FAILED",
                        {
                            "trade_id": position.trade_id,
                            "reason": "CANCEL_REPLACE_FAILED",
                            "old_order_id": prior_order_id,
                        },
                    )
            elif not modify_success:
                self._append_event(
                    "TARGET_REPRICE_FAILED",
                    {
                        "trade_id": position.trade_id,
                        "reason": "NO_FALLBACK_ENABLED",
                        "order_id": self.active_exit_order_id,
                    },
                )
        finally:
            position.target_reprice_in_progress = False

    def _execute_market_exit(self, exit_reason: str, option_quote: dict[str, Any]) -> bool:
        if self.open_position is None:
            return False

        sent_time = datetime.now()
        self._append_event(
            "EXIT_ORDER_SENT",
            {
                "trade_id": self.open_trade_id,
                "order_id": None,
                "symbol": self.open_position.option_symbol,
                "variety": "regular",
                "order_type": "MARKET",
                "transaction_type": "SELL",
                "exit_reason": exit_reason,
                "quantity": self.open_position.quantity,
                "requested_price": None,
                "trigger_reason": exit_reason,
                "closing": self.open_position.closing,
                "fragile": self.open_position.fragile,
                "sent_time": sent_time.isoformat(),
            },
        )
        try:
            order_id, exit_ltp, exit_time = self.broker.exit_market(
                symbol=self.open_position.option_symbol,
                quantity=self.open_position.quantity,
                product=self.settings.order_product,
            )
        except Exception as exc:
            self._append_event(
                "EXIT_EXECUTION_FAILED",
                {
                    "trade_id": self.open_trade_id,
                    "symbol": self.open_position.option_symbol,
                    "exit_reason": exit_reason,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "closing": self.open_position.closing,
                    "fragile": self.open_position.fragile,
                },
            )
            logger.warning("Exit execution failed | reason=%s | error=%s", exit_reason, exc)
            return False
        ack_time = datetime.now()
        self._append_event(
            "EXIT_ORDER_ACKED",
            {
                "trade_id": self.open_trade_id,
                "symbol": self.open_position.option_symbol,
                "variety": "regular",
                "order_type": "MARKET",
                "transaction_type": "SELL",
                "exit_reason": exit_reason,
                "order_id": order_id,
                "requested_price": None,
                "trigger_reason": exit_reason,
                "closing": self.open_position.closing,
                "fragile": self.open_position.fragile,
                "ack_time": ack_time.isoformat(),
            },
        )
        self._exit_open_position(
            exit_time=exit_time,
            exit_price=exit_ltp,
            exit_reason=exit_reason,
            exit_quote=option_quote,
            exit_order_id=order_id,
            exit_order_sent_time=sent_time,
            exit_order_ack_time=ack_time,
        )
        return True

    def _exit_open_position(
        self,
        exit_time: datetime,
        exit_price: float,
        exit_reason: str,
        exit_quote: dict[str, Any] | None = None,
        exit_order_id: str | None = None,
        exit_order_sent_time: datetime | None = None,
        exit_order_ack_time: datetime | None = None,
    ) -> None:
        if self.open_position is None:
            return

        position = self.open_position
        position.exit_price = float(exit_price)
        position.exit_time = exit_time
        position.exit_reason = exit_reason
        position.exit_order_id = exit_order_id or position.exit_order_id or (self.active_exit_order_id or "")
        position.exit_order_sent_time = (
            exit_order_sent_time
            or self.active_exit_order_sent_time
            or position.exit_order_sent_time
        )
        position.exit_order_ack_time = (
            exit_order_ack_time
            or self.active_exit_order_ack_time
            or position.exit_order_ack_time
        )
        position.exit_fill_time = exit_time
        if position.exit_decision_time is not None:
            position.exit_lag_seconds = (position.exit_fill_time - position.exit_decision_time).total_seconds()
        if self.settings.enable_slippage_logging and position.exit_trigger_reference_price is not None:
            position.exit_slippage_points = position.exit_price - position.exit_trigger_reference_price
        else:
            position.exit_slippage_points = None

        if exit_quote is not None:
            position.exit_bid = exit_quote.get("bid")
            position.exit_ask = exit_quote.get("ask")
            position.exit_spread = exit_quote.get("spread")

        position.gross_pnl = (position.exit_price - position.entry_price) * position.quantity
        charges = self.charges_model.calculate_round_trip(position)
        position.charges = charges.total
        position.net_pnl = position.gross_pnl - charges.total
        position.status = "CLOSED"

        self._append_event(
            "EXIT_FILLED",
            {
                "trade_id": position.trade_id,
                "symbol": position.option_symbol,
                "exit_reason": exit_reason,
                "order_id": position.exit_order_id,
                "variety": "regular",
                "order_type": "MARKET" if exit_reason in {"MANUAL_EXIT", "HARD_STOP_EXIT", "EARLY_RISK_EXIT", "PATH_RISK_EXIT", "TIME_STOP_AFTER_1PM"} else "LIMIT",
                "transaction_type": "SELL",
                "requested_price": position.exit_trigger_reference_price,
                "fill_price": position.exit_price,
                "trigger_reason": position.closing_reason,
                "closing": position.closing,
                "fragile": position.fragile,
                "exit_fill_time": position.exit_fill_time.isoformat(),
                "exit_price": position.exit_price,
                "exit_slippage_points": position.exit_slippage_points,
                "exit_lag_seconds": position.exit_lag_seconds,
                "bid": position.exit_bid,
                "ask": position.exit_ask,
                "spread": position.exit_spread,
            },
        )

        self.wallet.apply_closed_trade(position)
        if self.candle_tracker.current_candle is not None:
            self.evaluator.mark_exit(self.candle_tracker.current_candle.start)

        logger.info(
            "%s | exit=%.2f | gross=%.2f | charges=%.2f | net=%.2f | realized=%.2f",
            exit_reason,
            position.exit_price,
            position.gross_pnl,
            position.charges,
            position.net_pnl,
            self.wallet.realized_pnl,
        )
        self.journal.append(
            "TRADE_EXITED",
            {
                "trade_id": self.open_trade_id,
                "symbol": position.option_symbol,
                "product": position.product,
                "exit_time": position.exit_time.isoformat(),
                "exit_reason": exit_reason,
                "exit_price": position.exit_price,
                "entry_price": position.entry_price,
                "quantity": position.quantity,
                "gross_pnl": position.gross_pnl,
                "charges": position.charges,
                "net_pnl": position.net_pnl,
                "realized_pnl_after_trade": self.wallet.realized_pnl,
            },
        )

        self._observe_post_exit(position)

        self.journal.append_trade_summary(
            position=position,
            extra_payload={
                "realized_pnl_after_trade": self.wallet.realized_pnl,
                "active_exit_order_type_at_close": self.active_exit_order_type,
                "summary_version": "exit_close",
            },
        )

        self.open_position = None
        self.open_trade_id = None
        self.manual_exit_requested = False
        self.active_exit_order_type = None
        self.active_exit_price = None
        self.active_exit_order_id = None
        self.active_exit_order_variety = "regular"
        self.active_exit_order_sent_time = None
        self.active_exit_order_ack_time = None

    def _maybe_process_runtime_control(self) -> None:
        data = read_control(self.settings.control_path)
        cmd = parse_command(data)
        if cmd is None and data.get("action") is not None:
            reset_control(self.settings.control_path)
            return
        if cmd is None:
            return

        try:
            if cmd.action == "EXIT_NOW":
                logger.info("MANUAL_EXIT_REQUESTED")
                self.journal.append(
                    "MANUAL_EXIT_REQUESTED",
                    {
                        "requested_action": "EXIT_NOW",
                        "trade_id": self.open_trade_id,
                        "symbol": self.open_position.option_symbol if self.open_position else None,
                        "product": self.open_position.product if self.open_position else self.settings.order_product,
                    },
                )
                if self.open_position is None:
                    logger.info("Manual exit requested but no open trade exists.")
                    return
                if self.open_position.closing:
                    logger.info("Manual exit requested but position is already closing.")
                    return
                self.manual_exit_requested = True
                self._append_event(
                    "MANUAL_EXIT",
                    {
                        "trade_id": self.open_trade_id,
                        "status": "QUEUED",
                    },
                )
                return

            if cmd.action == "EXIT_LIMIT":
                requested = float(cmd.price)
                if self.open_position is None:
                    logger.info("Manual limit exit requested but no open trade exists.")
                    return
                if self.open_position.closing:
                    logger.info("Manual limit exit requested but position is already closing.")
                    return

                if self.active_exit_order_type == "MANUAL_LIMIT" and self._is_same_price(
                    self.active_exit_price, requested
                ):
                    logger.info("Manual limit exit already active at price %.2f.", requested)
                    self.journal.append(
                        "MANUAL_LIMIT_ALREADY_ACTIVE",
                        {
                            "trade_id": self.open_trade_id,
                            "symbol": self.open_position.option_symbol,
                            "product": self.open_position.product,
                            "price": requested,
                        },
                    )
                    return

                self._cancel_active_exit_order(reason="MANUAL_LIMIT_REPLACE")
                placed = self._place_manual_limit_exit_order(price=requested)
                if placed:
                    logger.info("Manual limit exit placed at price %.2f.", requested)
                    self.journal.append(
                        "MANUAL_LIMIT_EXIT_PLACED",
                        {
                            "trade_id": self.open_trade_id,
                            "symbol": self.open_position.option_symbol,
                            "product": self.open_position.product,
                            "price": requested,
                        },
                    )
                else:
                    self.journal.append(
                        "MANUAL_LIMIT_EXIT_PLACE_FAILED",
                        {
                            "trade_id": self.open_trade_id,
                            "symbol": self.open_position.option_symbol,
                            "product": self.open_position.product,
                            "price": requested,
                        },
                    )
                return
        finally:
            reset_control(self.settings.control_path)

    def run(self) -> None:
        logger.info("Starting Sensex noise paper trading engine")
        logger.info("Starting capital: ₹%.2f", self.wallet.starting_capital)
        logger.info("Trade quantity: %s", self.settings.trade_qty)
        logger.info("Trade journal file: %s", self.settings.trade_log_path)
        logger.info("Event journal file: %s", self.settings.event_log_path)
        logger.info("Enriched trade log file: %s", self.settings.enriched_trade_log_path)
        logger.info("Runtime control file: %s", self.settings.control_path)
        logger.info(
            "Engine started | mode=%s | sizing=%s | capital=%.2f | trade_qty=%s | use_kite_funds=%s",
            self.settings.trading_mode,
            self.settings.position_sizing_mode,
            self.settings.capital_budget,
            self.settings.trade_qty,
            self.settings.use_kite_funds,
        )
        if not self._startup_auth_check():
            return

        # WebSocket-first runtime (market-data polling removed from active path).
        from sensex_noise.runtime.strategy_runtime import StrategyRuntime

        StrategyRuntime(engine=self).run()
        return

        while True:
            try:
                self._maybe_process_runtime_control()
                spot_quote = self.market_data.underlying_quote(self.settings.underlying_symbol)
                tick_time = spot_quote["timestamp"]
                spot_ltp = float(spot_quote["ltp"])

                self._emit_due_post_exit_observations(spot_quote=spot_quote)

                if not self._after_market_open(tick_time):
                    self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                    continue

                self.candle_tracker.update(tick_time, spot_ltp)

                if self.open_position is None:
                    self.manual_exit_requested = False
                    signal = self.evaluator.evaluate(
                        previous_candle=self.candle_tracker.previous_candle,
                        current_candle=self.candle_tracker.current_candle,
                        live_ltp=spot_ltp,
                    )
                    if signal is not None:
                        self._log_signal_generated(
                            signal=signal,
                            signal_time=tick_time,
                            spot_ltp=spot_ltp,
                            previous_candle=self.candle_tracker.previous_candle,
                        )
                        candle_id = signal.source_candle_start
                        if self._past_entry_cutoff(tick_time):
                            logger.info(
                                "Entry blocked: current time past cutoff %s.",
                                self.settings.entry_cutoff_time,
                            )
                            self.journal.append(
                                "ENTRY_BLOCKED_AFTER_CUTOFF",
                                {
                                    "now": tick_time.isoformat(),
                                    "cutoff": self.settings.entry_cutoff_time,
                                },
                            )
                            self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                            continue

                        elapsed_seconds = (tick_time - signal.source_candle_start).total_seconds()
                        if elapsed_seconds > self.settings.entry_window_seconds:
                            logger.info("Skipping entry: outside entry window")
                            self.journal.append(
                                "ENTRY_SKIPPED_OUTSIDE_WINDOW",
                                {
                                    "now": tick_time.isoformat(),
                                    "source_candle_start": signal.source_candle_start.isoformat(),
                                    "elapsed_seconds": elapsed_seconds,
                                    "entry_window_seconds": self.settings.entry_window_seconds,
                                    "side": signal.side.value,
                                    "trigger_price": signal.trigger_price,
                                    "underlying_symbol": self.settings.underlying_symbol,
                                },
                            )
                            self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                            continue

                        if candle_id in self.attempted_entry_candles:
                            logger.info("Entry already attempted for this candle")
                            self.journal.append(
                                "ENTRY_SKIPPED_CANDLE_ALREADY_ATTEMPTED",
                                {
                                    "now": tick_time.isoformat(),
                                    "candle_id": candle_id.isoformat(),
                                    "source_candle_start": candle_id.isoformat(),
                                    "side": signal.side.value,
                                    "trigger_price": signal.trigger_price,
                                },
                            )
                            self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                            continue

                        if self.triggered_candle_start == signal.source_candle_start:
                            self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                            continue

                        self.attempted_entry_candles.add(candle_id)
                        try:
                            signal_kind = getattr(signal, "signal_kind", "UNKNOWN")
                            choice = self.selector.pick_sensex_option(
                                spot=spot_ltp,
                                side=signal.side,
                                now=tick_time,
                            )

                            option_quote = self.market_data.option_quote(choice.full_symbol)
                            option_ltp = float(option_quote["ltp"])
                            quantity = self._resolve_trade_quantity(
                                option_ltp=option_ltp,
                                lot_size=choice.lot_size,
                            )
                            if quantity is None:
                                logger.warning("ENTRY_ATTEMPT_FAILED_CANDLE_LOCKED")
                                self.journal.append(
                                    "ENTRY_ATTEMPT_FAILED_CANDLE_LOCKED",
                                    {
                                        "now": tick_time.isoformat(),
                                        "candle_id": candle_id.isoformat(),
                                        "source_candle_start": candle_id.isoformat(),
                                        "reason": "QUANTITY_UNAVAILABLE",
                                        "symbol": choice.full_symbol,
                                        "side": signal.side.value,
                                    },
                                )
                                self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                                continue

                            trade_id = self._build_trade_id(
                                signal=signal,
                                option_symbol=choice.full_symbol,
                                signal_seen_time=tick_time,
                            )

                            target_points = self._get_target_points(entry_time=tick_time, fragile=False)
                            self._log_entry_context(
                                trade_id=trade_id,
                                signal=signal,
                                choice=choice,
                                quantity=quantity,
                                target_points=target_points,
                                spot_at_signal=spot_ltp,
                                spot_at_entry_attempt=spot_ltp,
                                option_quote=option_quote,
                            )

                            entry_reference_price = float(option_quote["ltp"])
                            entry_decision_time = datetime.now()
                            signal_seen_time = tick_time
                            entry_order_sent_time = datetime.now()
                            self._append_event(
                                "ENTRY_ORDER_SENT",
                                {
                                    "trade_id": trade_id,
                                    "order_id": None,
                                    "symbol": choice.full_symbol,
                                    "variety": "regular",
                                    "order_type": "MARKET",
                                    "transaction_type": "BUY",
                                    "quantity": quantity,
                                    "product": self.settings.order_product,
                                    "requested_price": None,
                                    "trigger_reason": "ENTRY",
                                    "closing": False,
                                    "fragile": False,
                                    "entry_reference_price": entry_reference_price,
                                    "entry_decision_time": entry_decision_time.isoformat(),
                                    "sent_time": entry_order_sent_time.isoformat(),
                                },
                            )

                            entry_order_id, entry_price, entry_time = self.broker.place_entry_market(
                                symbol=choice.full_symbol,
                                quantity=quantity,
                                product=self.settings.order_product,
                            )
                            entry_order_ack_time = datetime.now()
                            self._append_event(
                                "ENTRY_ORDER_ACKED",
                                {
                                    "trade_id": trade_id,
                                    "symbol": choice.full_symbol,
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

                            self.open_position = Position(
                                side=signal.side,
                                option_symbol=choice.full_symbol,
                                product=self.settings.order_product,
                                underlying_spot=spot_ltp,
                                entry_price=entry_price,
                                target_price=entry_price + target_points,
                                quantity=quantity,
                                strike=choice.strike,
                                expiry=choice.expiry,
                                entry_time=entry_time,
                                signal_kind=signal_kind,
                                trade_id=trade_id,
                                signal_time=tick_time,
                                signal_seen_time=tick_time,
                                trigger_price=signal.trigger_price,
                                source_candle_start=signal.source_candle_start,
                                target_points=target_points,
                                hard_stop_points_used=self._get_hard_stop_points(signal_kind),
                                entry_order_id=entry_order_id,
                                entry_order_sent_time=entry_order_sent_time,
                                entry_order_ack_time=entry_order_ack_time,
                                entry_fill_time=entry_time,
                                entry_decision_time=entry_decision_time,
                                entry_reference_price=entry_reference_price,
                                entry_slippage_points=(
                                    (entry_price - entry_reference_price)
                                    if self.settings.enable_slippage_logging
                                    else None
                                ),
                                entry_lag_seconds=(entry_time - signal_seen_time).total_seconds(),
                                entry_bid=option_quote.get("bid"),
                                entry_ask=option_quote.get("ask"),
                                entry_spread=option_quote.get("spread"),
                                current_price=entry_price,
                                current_spot=spot_ltp,
                                pre_or_post_1pm=("POST_1PM" if self._is_post_1pm(entry_time) else "PRE_1PM"),
                            )
                            call_put = "CALL" if signal.side.value == "CALL" else "PUT"
                            cont_rev = "CONTINUATION" if "CONTINUATION" in signal_kind else "REVERSAL"
                            self.open_position.snapshot_features.update(
                                {
                                    "continuation_or_reversal": cont_rev,
                                    "call_or_put": call_put,
                                    "target_points_used": self.open_position.target_points,
                                    "hard_stop_points_used": self.open_position.hard_stop_points_used,
                                    "entry_lag_seconds": self.open_position.entry_lag_seconds,
                                    "entry_slippage_points": self.open_position.entry_slippage_points,
                                }
                            )
                            self.open_trade_id = trade_id
                            self._append_event(
                                "ENTRY_FILLED",
                                {
                                    "trade_id": trade_id,
                                    "symbol": choice.full_symbol,
                                    "order_id": entry_order_id,
                                    "variety": "regular",
                                    "order_type": "MARKET",
                                    "transaction_type": "BUY",
                                    "requested_price": None,
                                    "fill_price": entry_price,
                                    "trigger_reason": "ENTRY",
                                    "closing": self.open_position.closing,
                                    "fragile": self.open_position.fragile,
                                    "entry_fill_time": entry_time.isoformat(),
                                    "entry_price": entry_price,
                                    "entry_reference_price": self.open_position.entry_reference_price,
                                    "entry_slippage_points": self.open_position.entry_slippage_points,
                                    "entry_lag_seconds": self.open_position.entry_lag_seconds,
                                    "bid": option_quote.get("bid"),
                                    "ask": option_quote.get("ask"),
                                    "spread": option_quote.get("spread"),
                                },
                            )
                            target_placed = self._place_target_exit_order()
                            self.journal.append(
                                "TRADE_ENTERED",
                                {
                                    "trade_id": self.open_trade_id,
                                    "symbol": self.open_position.option_symbol,
                                    "side": self.open_position.side.value,
                                    "product": self.open_position.product,
                                    "entry_time": self.open_position.entry_time.isoformat(),
                                    "entry_price": self.open_position.entry_price,
                                    "target_price": self.open_position.target_price,
                                    "quantity": self.open_position.quantity,
                                    "strike": self.open_position.strike,
                                    "expiry": self.open_position.expiry.isoformat(),
                                    "underlying_spot": self.open_position.underlying_spot,
                                    "source_candle_start": signal.source_candle_start.isoformat(),
                                    "trigger_price": signal.trigger_price,
                                    "signal_kind": signal_kind,
                                },
                            )
                            self.triggered_candle_start = signal.source_candle_start
                            if target_placed:
                                logger.info(
                                    "TARGET LIMIT PLACED | %s @ %.2f",
                                    self.open_position.option_symbol,
                                    self.open_position.target_price,
                                )
                                self._append_event(
                                    "TARGET_PLACED",
                                    {
                                        "trade_id": self.open_trade_id,
                                        "symbol": self.open_position.option_symbol,
                                        "product": self.open_position.product,
                                        "target_price": self.open_position.target_price,
                                        "target_points": self.open_position.target_points,
                                        "order_id": self.active_exit_order_id,
                                        "signal_kind": self.open_position.signal_kind,
                                    },
                                )
                            else:
                                logger.warning(
                                    "TARGET LIMIT PLACE FAILED | %s @ %.2f",
                                    self.open_position.option_symbol,
                                    self.open_position.target_price,
                                )
                        except Exception as exc:
                            logger.warning("ENTRY_ATTEMPT_FAILED_CANDLE_LOCKED")
                            self.journal.append(
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
                            raise
                else:
                    option_quote = self.market_data.option_quote(self.open_position.option_symbol)
                    option_tick_time = option_quote["timestamp"]
                    option_ltp = float(option_quote["ltp"])

                    resolved_thresholds = self._update_path_features(
                        position=self.open_position,
                        mark_time=option_tick_time,
                        option_quote=option_quote,
                        spot_quote=spot_quote,
                    )
                    self._emit_due_snapshots(
                        position=self.open_position,
                        mark_time=option_tick_time,
                        option_quote=option_quote,
                        spot_quote=spot_quote,
                        resolved_thresholds=resolved_thresholds,
                    )

                    if self.settings.enable_verbose_trade_logging:
                        logger.info(
                            "OPEN POSITION | %s | entry=%.2f | target=%.2f | ltp=%.2f",
                            self.open_position.option_symbol,
                            self.open_position.entry_price,
                            self.open_position.target_price,
                            option_ltp,
                        )
                        self.journal.append(
                            "OPEN_POSITION_MARK",
                            {
                                "trade_id": self.open_trade_id,
                                "symbol": self.open_position.option_symbol,
                                "product": self.open_position.product,
                                "mark_time": option_tick_time.isoformat(),
                                "entry_price": self.open_position.entry_price,
                                "target_price": self.open_position.target_price,
                                "active_exit_order_type": self.active_exit_order_type,
                                "active_exit_price": self.active_exit_price,
                                "ltp": option_ltp,
                                "spot_ltp": spot_ltp,
                                "signal_kind": self.open_position.signal_kind,
                                "mfe": self.open_position.max_favorable_excursion,
                                "mae": self.open_position.max_adverse_excursion,
                            },
                        )

                    duration_seconds = (option_tick_time - self.open_position.entry_time).total_seconds()
                    if (
                        duration_seconds <= self.settings.early_failure_window_seconds
                        and not self.open_position.early_failure_logged
                        and self.open_position.max_favorable_excursion < self.settings.early_failure_mfe_min
                        and option_ltp <= self.open_position.entry_price
                        and self.open_position.max_adverse_excursion <= self.settings.early_failure_mae_max
                    ):
                        logger.warning("Early failure signal detected")
                        self.journal.append(
                            "EARLY_FAILURE_SIGNAL",
                            {
                                "trade_id": self.open_trade_id,
                                "symbol": self.open_position.option_symbol,
                                "product": self.open_position.product,
                                "signal_kind": self.open_position.signal_kind,
                                "entry_time": self.open_position.entry_time.isoformat(),
                                "mark_time": option_tick_time.isoformat(),
                                "duration_seconds": duration_seconds,
                                "entry_price": self.open_position.entry_price,
                                "current_price": option_ltp,
                                "mfe": self.open_position.max_favorable_excursion,
                                "mae": self.open_position.max_adverse_excursion,
                                "target_price": self.open_position.target_price,
                            },
                        )
                        self.open_position.early_failure_logged = True

                    if not self.open_position.closing:
                        self._maybe_mark_early_suspicion(
                            position=self.open_position,
                            mark_time=option_tick_time,
                            option_ltp=option_ltp,
                        )

                        exit_candidates = self._collect_exit_candidates(
                            position=self.open_position,
                            option_quote=option_quote,
                            mark_time=option_tick_time,
                        )
                        selected_reason = self._select_exit_reason(exit_candidates)
                        if selected_reason is not None:
                            decision_time = datetime.now()
                            self._mark_position_closing(
                                position=self.open_position,
                                selected_reason=selected_reason,
                                candidates=exit_candidates,
                                decision_time=decision_time,
                                trigger_reference_price=option_ltp,
                            )
                            self._log_exit_decision_selected(
                                position=self.open_position,
                                selected_reason=selected_reason,
                                candidates=exit_candidates,
                                option_ltp=option_ltp,
                                spot_ltp=spot_ltp,
                                holding_seconds=duration_seconds,
                            )
                            if selected_reason == "MANUAL_EXIT":
                                self.manual_exit_requested = False

                            if selected_reason in {
                                "MANUAL_EXIT",
                                "HARD_STOP_EXIT",
                                "EARLY_RISK_EXIT",
                                "PATH_RISK_EXIT",
                                "TIME_STOP_AFTER_1PM",
                            }:
                                if selected_reason == "HARD_STOP_EXIT":
                                    self._should_hard_stop(
                                        self.open_position,
                                        mark_time=option_tick_time,
                                        option_ltp=option_ltp,
                                        record=True,
                                    )
                                elif selected_reason == "EARLY_RISK_EXIT":
                                    self._should_early_exit(
                                        self.open_position,
                                        mark_time=option_tick_time,
                                        option_ltp=option_ltp,
                                        record=True,
                                    )
                                elif selected_reason == "PATH_RISK_EXIT":
                                    self._should_path_exit(
                                        self.open_position,
                                        mark_time=option_tick_time,
                                        option_ltp=option_ltp,
                                        record=True,
                                    )
                                if selected_reason == "TIME_STOP_AFTER_1PM":
                                    self._append_event(
                                        "TIME_STOP_AFTER_1PM",
                                        {
                                            "trade_id": self.open_trade_id,
                                            "symbol": self.open_position.option_symbol,
                                            "duration_seconds": duration_seconds,
                                            "time_stop_seconds": self.settings.post_1pm_time_stop_seconds,
                                        },
                                    )
                                self._cancel_active_exit_order(reason=selected_reason)
                                self._execute_market_exit(
                                    exit_reason=selected_reason,
                                    option_quote=option_quote,
                                )
                            elif selected_reason == "MANUAL_LIMIT_HIT":
                                self._append_event(
                                    "MANUAL_LIMIT_HIT",
                                    {
                                        "trade_id": self.open_trade_id,
                                        "symbol": self.open_position.option_symbol,
                                        "price": self.active_exit_price,
                                        "closing": self.open_position.closing,
                                        "fragile": self.open_position.fragile,
                                    },
                                )
                                self._exit_open_position(
                                    exit_time=option_tick_time,
                                    exit_price=self.active_exit_price,
                                    exit_reason="MANUAL_LIMIT_HIT",
                                    exit_quote=option_quote,
                                )
                            elif selected_reason == "TARGET_HIT":
                                self._append_event(
                                    "TARGET_HIT",
                                    {
                                        "trade_id": self.open_trade_id,
                                        "symbol": self.open_position.option_symbol,
                                        "target_price": self.open_position.target_price,
                                        "target_points": self.open_position.target_points,
                                        "closing": self.open_position.closing,
                                        "fragile": self.open_position.fragile,
                                    },
                                )
                                self._exit_open_position(
                                    exit_time=option_tick_time,
                                    exit_price=self.open_position.target_price,
                                    exit_reason="TARGET_HIT",
                                    exit_quote=option_quote,
                                )

                self._sleep_with_control_poll(self.settings.poll_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except TokenException:
                logger.error(AUTH_FAILURE_MSG)
                break
            except Exception as exc:
                logger.exception("Engine error: %s", exc)
                self._sleep_with_control_poll(max(self.settings.poll_interval_seconds, 2))
