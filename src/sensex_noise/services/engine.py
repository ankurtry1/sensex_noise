from __future__ import annotations

import logging
import math
import time
from datetime import datetime, time as dt_time

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
from sensex_noise.services.trade_journal import TradeJournal
from sensex_noise.services.runtime_control import parse_command, read_control, reset_control
from sensex_noise.services.sizing import calculate_position_quantity
from sensex_noise.strategy import StrategyEvaluator
from sensex_noise.wallet import Wallet

logger = logging.getLogger(__name__)
AUTH_FAILURE_MSG = (
    "Authentication failed: Kite rejected api_key/access_token. Most likely causes: "
    "expired access token, api_key from different app, or wrong .env file loaded. "
    "Run: python scripts/check_kite_auth.py"
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
        self.journal = TradeJournal(settings.trade_log_path)
        self.open_position = None
        self.open_trade_id = None
        self.triggered_candle_start = None
        self.active_exit_order_type: str | None = None
        self.active_exit_price: float | None = None
        self.active_exit_order_id: str | None = None

    def _after_market_open(self, now: datetime) -> bool:
        return now.time() >= dt_time(hour=9, minute=15)

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

    def _cancel_active_exit_order(self, reason: str) -> None:
        if self.active_exit_order_type is None:
            return
        if self.active_exit_order_id is not None:
            try:
                self.broker.cancel_order(self.active_exit_order_id)
            except Exception as exc:
                logger.warning("Cancel order failed for %s: %s", self.active_exit_order_id, exc)
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
            },
        )
        self.active_exit_order_type = None
        self.active_exit_price = None
        self.active_exit_order_id = None

    def _place_target_exit_order(self) -> None:
        order_id = self.broker.place_exit_limit(
            symbol=self.open_position.option_symbol,
            quantity=self.open_position.quantity,
            price=self.open_position.target_price,
            product=self.settings.order_product,
        )
        self.active_exit_order_type = "TARGET"
        self.active_exit_price = self.open_position.target_price
        self.active_exit_order_id = order_id

    def _place_manual_limit_exit_order(self, price: float) -> None:
        order_id = self.broker.place_exit_limit(
            symbol=self.open_position.option_symbol,
            quantity=self.open_position.quantity,
            price=price,
            product=self.settings.order_product,
        )
        self.active_exit_order_type = "MANUAL_LIMIT"
        self.active_exit_price = float(price)
        self.active_exit_order_id = order_id

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

    def _exit_open_position(self, exit_time: datetime, exit_price: float, exit_reason: str) -> None:
        self.open_position.exit_price = float(exit_price)
        self.open_position.exit_time = exit_time
        self.open_position.gross_pnl = (
            self.open_position.exit_price - self.open_position.entry_price
        ) * self.open_position.quantity
        charges = self.charges_model.calculate_round_trip(self.open_position)
        self.open_position.charges = charges.total
        self.open_position.net_pnl = self.open_position.gross_pnl - charges.total
        self.open_position.status = "CLOSED"
        self.wallet.apply_closed_trade(self.open_position)
        if self.candle_tracker.current_candle is not None:
            self.evaluator.mark_exit(self.candle_tracker.current_candle.start)
        logger.info(
            "%s | exit=%.2f | gross=%.2f | charges=%.2f | net=%.2f | realized=%.2f",
            exit_reason,
            self.open_position.exit_price,
            self.open_position.gross_pnl,
            self.open_position.charges,
            self.open_position.net_pnl,
            self.wallet.realized_pnl,
        )
        self.journal.append(
            "TRADE_EXITED",
            {
                "trade_id": self.open_trade_id,
                "symbol": self.open_position.option_symbol,
                "product": self.open_position.product,
                "exit_time": self.open_position.exit_time.isoformat(),
                "exit_reason": exit_reason,
                "exit_price": self.open_position.exit_price,
                "entry_price": self.open_position.entry_price,
                "quantity": self.open_position.quantity,
                "gross_pnl": self.open_position.gross_pnl,
                "charges": self.open_position.charges,
                "net_pnl": self.open_position.net_pnl,
                "realized_pnl_after_trade": self.wallet.realized_pnl,
            },
        )
        self.open_position = None
        self.open_trade_id = None
        self.active_exit_order_type = None
        self.active_exit_price = None
        self.active_exit_order_id = None

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
                self._cancel_active_exit_order(reason="MANUAL_EXIT")
                _, exit_ltp, exit_time = self.broker.exit_market(
                    symbol=self.open_position.option_symbol,
                    quantity=self.open_position.quantity,
                    product=self.settings.order_product,
                )
                self._exit_open_position(
                    exit_time=exit_time,
                    exit_price=exit_ltp,
                    exit_reason="MANUAL_EXIT",
                )
                return

            if cmd.action == "EXIT_LIMIT":
                requested = float(cmd.price)
                if self.open_position is None:
                    logger.info("Manual limit exit requested but no open trade exists.")
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
                self._place_manual_limit_exit_order(price=requested)
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
                return
        finally:
            reset_control(self.settings.control_path)

    def run(self) -> None:
        logger.info("Starting Sensex noise paper trading engine")
        logger.info("Starting capital: ₹%.2f", self.wallet.starting_capital)
        logger.info("Trade quantity: %s", self.settings.trade_qty)
        logger.info("Trade journal file: %s", self.settings.trade_log_path)
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

        while True:
            try:
                self._maybe_process_runtime_control()
                tick_time, spot_ltp = self.market_data.underlying_tick(self.settings.underlying_symbol)
                if not self._after_market_open(tick_time):
                    self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                    continue

                self.candle_tracker.update(tick_time, spot_ltp)

                if self.open_position is None:
                    signal = self.evaluator.evaluate(
                        previous_candle=self.candle_tracker.previous_candle,
                        current_candle=self.candle_tracker.current_candle,
                        live_ltp=spot_ltp,
                    )
                    if signal is not None:
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

                        if self.triggered_candle_start == signal.source_candle_start:
                            self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                            continue

                        choice = self.selector.pick_sensex_option(
                            spot=spot_ltp,
                            side=signal.side,
                            now=tick_time,
                        )

                        _, option_ltp = self.market_data.option_tick(choice.full_symbol)
                        quantity = self._resolve_trade_quantity(
                            option_ltp=option_ltp,
                            lot_size=choice.lot_size,
                        )
                        if quantity is None:
                            self._sleep_with_control_poll(self.settings.poll_interval_seconds)
                            continue

                        _, entry_price, entry_time = self.broker.place_entry_market(
                            symbol=choice.full_symbol,
                            quantity=quantity,
                            product=self.settings.order_product,
                        )
                        self.open_position = Position(
                            side=signal.side,
                            option_symbol=choice.full_symbol,
                            product=self.settings.order_product,
                            underlying_spot=spot_ltp,
                            entry_price=entry_price,
                            target_price=entry_price + self.settings.target_points,
                            quantity=quantity,
                            strike=choice.strike,
                            expiry=choice.expiry,
                            entry_time=entry_time,
                        )
                        self.open_trade_id = (
                            f"{self.open_position.option_symbol}|{self.open_position.entry_time.isoformat()}"
                        )
                        self._place_target_exit_order()
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
                            },
                        )
                        self.triggered_candle_start = signal.source_candle_start
                        logger.info("TARGET LIMIT PLACED | %s @ %.2f", self.open_position.option_symbol, self.open_position.target_price)
                        self.journal.append(
                            "TARGET_PLACED",
                            {
                                "trade_id": self.open_trade_id,
                                "symbol": self.open_position.option_symbol,
                                "product": self.open_position.product,
                                "target_price": self.open_position.target_price,
                                "order_id": self.active_exit_order_id,
                            },
                        )
                else:
                    option_tick_time, option_ltp = self.market_data.option_tick(self.open_position.option_symbol)
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
                        },
                    )
                    if self.active_exit_order_type == "MANUAL_LIMIT" and self.active_exit_price is not None:
                        if option_ltp >= self.active_exit_price:
                            self._exit_open_position(
                                exit_time=option_tick_time,
                                exit_price=self.active_exit_price,
                                exit_reason="MANUAL_LIMIT_HIT",
                            )
                    elif option_ltp >= self.open_position.target_price:
                        self._exit_open_position(
                            exit_time=option_tick_time,
                            exit_price=self.open_position.target_price,
                            exit_reason="TARGET_HIT",
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
