from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from kiteconnect import KiteConnect

from sensex_noise.broker.base import TradingBroker

logger = logging.getLogger(__name__)


class KitePaperBroker(TradingBroker):
    MODIFIABLE_STATUSES = {"OPEN", "TRIGGER PENDING", "AMO REQ RECEIVED", "AMO REQ PENDING"}

    def __init__(self, api_key: str, access_token: str, capital_budget: float) -> None:
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        self.capital_budget = float(capital_budget)
        self._next_order_id = 1
        self._orders: dict[str, dict[str, Any]] = {}

    def _new_order_id(self, prefix: str) -> str:
        order_id = f"PAPER-{prefix}-{self._next_order_id}"
        self._next_order_id += 1
        return order_id

    def _record_order(self, order: dict[str, Any]) -> None:
        self._orders[str(order["order_id"])] = order

    def _fetch_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        data = self.kite.ltp([full_symbol])
        if full_symbol not in data:
            raise ValueError(f"LTP missing for symbol: {full_symbol}")
        return datetime.now(), float(data[full_symbol]["last_price"])

    def _quote_from_ltp(self, full_symbol: str) -> dict[str, Any]:
        timestamp, ltp = self._fetch_ltp(full_symbol)
        return {
            "timestamp": timestamp,
            "ltp": float(ltp),
            "bid": None,
            "ask": None,
            "spread": None,
            "last_trade_time": None,
        }

    def fetch_underlying_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        quote = self.fetch_underlying_quote(full_symbol)
        return quote["timestamp"], float(quote["ltp"])

    def fetch_option_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        quote = self.fetch_option_quote(full_symbol)
        return quote["timestamp"], float(quote["ltp"])

    def fetch_underlying_quote(self, full_symbol: str) -> dict[str, Any]:
        return self._quote_from_ltp(full_symbol)

    def fetch_option_quote(self, full_symbol: str) -> dict[str, Any]:
        return self._quote_from_ltp(full_symbol)

    def verify_auth(self) -> dict:
        """Validate that auth is usable for authenticated Kite endpoints."""
        return self.kite.profile()

    def place_entry_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        ts, entry_price = self.fetch_option_ltp(symbol)
        order_id = self._new_order_id("ENTRY")
        self._record_order(
            {
                "order_id": order_id,
                "variety": "regular",
                "status": "COMPLETE",
                "tradingsymbol": symbol,
                "transaction_type": "BUY",
                "order_type": "MARKET",
                "price": 0.0,
                "average_price": float(entry_price),
                "filled_quantity": int(quantity),
                "pending_quantity": 0,
                "quantity": int(quantity),
                "order_timestamp": ts,
                "exchange_timestamp": ts,
                "history": [
                    {
                        "status": "COMPLETE",
                        "timestamp": ts,
                        "average_price": float(entry_price),
                    }
                ],
            }
        )
        logger.info(
            "PAPER ENTRY MARKET | %s | product=%s | qty=%s | price=%.2f | order_id=%s",
            symbol,
            product,
            quantity,
            entry_price,
            order_id,
        )
        return order_id, entry_price, ts

    def place_exit_limit(self, symbol: str, quantity: int, price: float, product: str) -> str:
        order_id = self._new_order_id("EXIT")
        ts = datetime.now()
        self._record_order(
            {
                "order_id": order_id,
                "variety": "regular",
                "status": "OPEN",
                "tradingsymbol": symbol,
                "transaction_type": "SELL",
                "order_type": "LIMIT",
                "price": float(price),
                "average_price": 0.0,
                "filled_quantity": 0,
                "pending_quantity": int(quantity),
                "quantity": int(quantity),
                "order_timestamp": ts,
                "exchange_timestamp": ts,
                "history": [
                    {
                        "status": "OPEN",
                        "timestamp": ts,
                        "price": float(price),
                    }
                ],
            }
        )
        logger.info(
            "PAPER EXIT LIMIT | %s | product=%s | qty=%s | price=%.2f | order_id=%s",
            symbol,
            product,
            quantity,
            price,
            order_id,
        )
        return order_id

    def modify_order(self, variety: str, order_id: str, params: dict[str, Any]) -> str:
        order = self._orders.get(order_id)
        if order is None:
            raise ValueError(f"Order not found: {order_id}")
        if not self.is_order_modifiable(order_id=order_id, variety=variety):
            raise ValueError(f"Order not modifiable: {order_id}")

        if "price" in params and params["price"] is not None:
            order["price"] = float(params["price"])
        if "quantity" in params and params["quantity"] is not None:
            order["quantity"] = int(params["quantity"])
            order["pending_quantity"] = max(0, int(params["quantity"]) - int(order.get("filled_quantity", 0)))

        ts = datetime.now()
        order["exchange_timestamp"] = ts
        order.setdefault("history", []).append(
            {
                "status": order.get("status", "OPEN"),
                "timestamp": ts,
                "price": order.get("price"),
            }
        )
        logger.info(
            "PAPER MODIFY ORDER | order_id=%s | variety=%s | params=%s",
            order_id,
            variety,
            params,
        )
        return str(order_id)

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        order = self._orders.get(order_id)
        if order is None:
            return None
        return dict(order)

    def get_order_history(self, order_id: str) -> list[dict[str, Any]]:
        order = self._orders.get(order_id)
        if order is None:
            return []
        return list(order.get("history", []))

    def is_order_modifiable(self, order_id: str, variety: str) -> bool:
        order = self._orders.get(order_id)
        if order is None:
            return False
        status = str(order.get("status", "")).upper()
        if status not in self.MODIFIABLE_STATUSES:
            return False

        pending_quantity = int(order.get("pending_quantity") or 0)
        filled_quantity = int(order.get("filled_quantity") or 0)
        quantity = int(order.get("quantity") or 0)
        return pending_quantity > 0 and filled_quantity < quantity

    def cancel_order(self, variety: str, order_id: str) -> str:
        order = self._orders.get(order_id)
        if order is None:
            return order_id

        ts = datetime.now()
        order["status"] = "CANCELLED"
        order["pending_quantity"] = 0
        order["exchange_timestamp"] = ts
        order.setdefault("history", []).append(
            {
                "status": "CANCELLED",
                "timestamp": ts,
            }
        )
        logger.info("PAPER CANCEL ORDER | order_id=%s | variety=%s", order_id, variety)
        return order_id

    def exit_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        ts, exit_price = self.fetch_option_ltp(symbol)
        order_id = self._new_order_id("EXIT")
        self._record_order(
            {
                "order_id": order_id,
                "variety": "regular",
                "status": "COMPLETE",
                "tradingsymbol": symbol,
                "transaction_type": "SELL",
                "order_type": "MARKET",
                "price": 0.0,
                "average_price": float(exit_price),
                "filled_quantity": int(quantity),
                "pending_quantity": 0,
                "quantity": int(quantity),
                "order_timestamp": ts,
                "exchange_timestamp": ts,
                "history": [
                    {
                        "status": "COMPLETE",
                        "timestamp": ts,
                        "average_price": float(exit_price),
                    }
                ],
            }
        )
        logger.info(
            "PAPER EXIT MARKET | %s | product=%s | qty=%s | price=%.2f | order_id=%s",
            symbol,
            product,
            quantity,
            exit_price,
            order_id,
        )
        return order_id, exit_price, ts

    def get_available_funds(self) -> float:
        return self.capital_budget
