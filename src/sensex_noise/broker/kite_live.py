from __future__ import annotations

import logging
from datetime import datetime

from kiteconnect import KiteConnect

from sensex_noise.broker.base import TradingBroker

logger = logging.getLogger(__name__)


class KiteLiveBroker(TradingBroker):
    def __init__(self, api_key: str, access_token: str) -> None:
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    @staticmethod
    def _split_symbol(full_symbol: str) -> tuple[str, str]:
        parts = full_symbol.split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid symbol format: {full_symbol!r}")
        return parts[0], parts[1]

    def _fetch_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        data = self.kite.ltp([full_symbol])
        if full_symbol not in data:
            raise ValueError(f"LTP missing for symbol: {full_symbol}")
        return datetime.now(), float(data[full_symbol]["last_price"])

    def _resolve_fill_price(self, order_id: str, symbol: str) -> tuple[float, datetime]:
        try:
            trades = self.kite.order_trades(order_id=order_id) or []
        except Exception:
            trades = []
        if trades:
            last_trade = trades[-1]
            trade_price = last_trade.get("average_price") or last_trade.get("fill_price") or last_trade.get("price")
            if trade_price:
                return float(trade_price), datetime.now()
        ts, ltp = self.fetch_option_ltp(symbol)
        return ltp, ts

    def verify_auth(self) -> dict:
        return self.kite.profile()

    def fetch_underlying_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        return self._fetch_ltp(full_symbol)

    def fetch_option_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        return self._fetch_ltp(full_symbol)

    def place_entry_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        exchange, tradingsymbol = self._split_symbol(symbol)
        order_id = self.kite.place_order(
            variety="regular",
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type="BUY",
            quantity=quantity,
            product=product,
            order_type="MARKET",
        )
        fill_price, fill_time = self._resolve_fill_price(order_id=order_id, symbol=symbol)
        logger.info(
            "LIVE ENTRY MARKET | %s | product=%s | qty=%s | price=%.2f | order_id=%s",
            symbol,
            product,
            quantity,
            fill_price,
            order_id,
        )
        return order_id, fill_price, fill_time

    def place_exit_limit(self, symbol: str, quantity: int, price: float, product: str) -> str:
        exchange, tradingsymbol = self._split_symbol(symbol)
        order_id = self.kite.place_order(
            variety="regular",
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type="SELL",
            quantity=quantity,
            product=product,
            order_type="LIMIT",
            price=float(price),
        )
        logger.info(
            "LIVE EXIT LIMIT | %s | product=%s | qty=%s | price=%.2f | order_id=%s",
            symbol,
            product,
            quantity,
            price,
            order_id,
        )
        return order_id

    def cancel_order(self, order_id: str) -> None:
        self.kite.cancel_order(variety="regular", order_id=order_id)
        logger.info("LIVE CANCEL ORDER | order_id=%s", order_id)

    def exit_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        exchange, tradingsymbol = self._split_symbol(symbol)
        order_id = self.kite.place_order(
            variety="regular",
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type="SELL",
            quantity=quantity,
            product=product,
            order_type="MARKET",
        )
        fill_price, fill_time = self._resolve_fill_price(order_id=order_id, symbol=symbol)
        logger.info(
            "LIVE EXIT MARKET | %s | product=%s | qty=%s | price=%.2f | order_id=%s",
            symbol,
            product,
            quantity,
            fill_price,
            order_id,
        )
        return order_id, fill_price, fill_time

    def get_available_funds(self) -> float:
        margins = self.kite.margins() or {}
        logger.info("Funds debug | raw margins response: %s", margins)

        equity = margins.get("equity", {}) if isinstance(margins, dict) else {}
        available = equity.get("available", {}) if isinstance(equity, dict) else {}

        funds = (
            equity.get("net")
            or available.get("live_balance")
            or available.get("opening_balance")
            or 0.0
        )
        funds = float(funds)
        logger.info("Funds debug | usable funds resolved = %.2f", funds)
        return funds
