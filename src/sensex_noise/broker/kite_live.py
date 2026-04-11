from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from kiteconnect import KiteConnect

from sensex_noise.broker.base import TradingBroker

logger = logging.getLogger(__name__)


class KiteLiveBroker(TradingBroker):
    MODIFIABLE_STATUSES = {
        "OPEN",
        "TRIGGER PENDING",
        "AMO REQ RECEIVED",
        "AMO REQ PENDING",
        "MODIFY VALIDATION PENDING",
        "PUT ORDER REQ RECEIVED",
    }

    def __init__(self, api_key: str, access_token: str) -> None:
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    @staticmethod
    def _split_symbol(full_symbol: str) -> tuple[str, str]:
        parts = full_symbol.split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid symbol format: {full_symbol!r}")
        return parts[0], parts[1]

    @staticmethod
    def _as_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _fetch_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        data = self.kite.ltp([full_symbol])
        if full_symbol not in data:
            raise ValueError(f"LTP missing for symbol: {full_symbol}")
        return datetime.now(), float(data[full_symbol]["last_price"])

    def _fetch_quote(self, full_symbol: str) -> dict[str, Any]:
        try:
            data = self.kite.quote([full_symbol])
            quote_data = data.get(full_symbol, {}) if isinstance(data, dict) else {}
        except Exception as exc:
            logger.debug("Quote fetch failed for %s, falling back to LTP: %s", full_symbol, exc)
            quote_data = {}

        if quote_data:
            ltp_raw = quote_data.get("last_price")
            ltp = float(ltp_raw) if ltp_raw is not None else None
            depth = quote_data.get("depth") if isinstance(quote_data, dict) else None
            bid = None
            ask = None
            if isinstance(depth, dict):
                buy = depth.get("buy") or []
                sell = depth.get("sell") or []
                if buy and isinstance(buy[0], dict) and buy[0].get("price") is not None:
                    bid = float(buy[0]["price"])
                if sell and isinstance(sell[0], dict) and sell[0].get("price") is not None:
                    ask = float(sell[0]["price"])

            spread = (ask - bid) if bid is not None and ask is not None else None
            timestamp = self._as_datetime(quote_data.get("timestamp")) or datetime.now()
            last_trade_time = self._as_datetime(quote_data.get("last_trade_time"))
            if ltp is not None:
                return {
                    "timestamp": timestamp,
                    "ltp": ltp,
                    "bid": bid,
                    "ask": ask,
                    "spread": spread,
                    "last_trade_time": last_trade_time,
                }

        timestamp, ltp = self._fetch_ltp(full_symbol)
        return {
            "timestamp": timestamp,
            "ltp": float(ltp),
            "bid": None,
            "ask": None,
            "spread": None,
            "last_trade_time": None,
        }

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

    def _get_orders(self) -> list[dict[str, Any]]:
        try:
            data = self.kite.orders() or []
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.debug("Failed to fetch orders list: %s", exc)
        return []

    def verify_auth(self) -> dict:
        return self.kite.profile()

    def fetch_underlying_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        quote = self.fetch_underlying_quote(full_symbol)
        return quote["timestamp"], float(quote["ltp"])

    def fetch_option_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        quote = self.fetch_option_quote(full_symbol)
        return quote["timestamp"], float(quote["ltp"])

    def fetch_underlying_quote(self, full_symbol: str) -> dict[str, Any]:
        return self._fetch_quote(full_symbol)

    def fetch_option_quote(self, full_symbol: str) -> dict[str, Any]:
        return self._fetch_quote(full_symbol)

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

    def modify_order(self, variety: str, order_id: str, params: dict[str, Any]) -> str:
        response = self.kite.modify_order(variety=variety, order_id=order_id, **params)
        modified_order_id = str(response) if response is not None else str(order_id)
        logger.info(
            "LIVE MODIFY ORDER | order_id=%s | variety=%s | params=%s | response=%s",
            order_id,
            variety,
            params,
            modified_order_id,
        )
        return modified_order_id

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        orders = self._get_orders()
        for order in reversed(orders):
            if str(order.get("order_id")) == str(order_id):
                return order
        return None

    def get_order_history(self, order_id: str) -> list[dict[str, Any]]:
        try:
            history = self.kite.order_history(order_id=order_id) or []
            if isinstance(history, list):
                return history
        except Exception as exc:
            logger.debug("Failed to fetch order history for %s: %s", order_id, exc)
        return []

    def is_order_modifiable(self, order_id: str, variety: str) -> bool:
        order = self.get_order(order_id)
        if order is None:
            return False

        status = str(order.get("status", "")).upper()
        if status not in self.MODIFIABLE_STATUSES:
            return False

        pending_quantity = int(order.get("pending_quantity") or 0)
        filled_quantity = int(order.get("filled_quantity") or 0)
        quantity = int(order.get("quantity") or 0)
        if pending_quantity <= 0:
            return False
        if quantity > 0 and filled_quantity >= quantity:
            return False
        return True

    def cancel_order(self, variety: str, order_id: str) -> str:
        response = self.kite.cancel_order(variety=variety, order_id=order_id)
        cancelled_order_id = str(response) if response is not None else str(order_id)
        logger.info("LIVE CANCEL ORDER | order_id=%s | variety=%s", order_id, variety)
        return cancelled_order_id

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
