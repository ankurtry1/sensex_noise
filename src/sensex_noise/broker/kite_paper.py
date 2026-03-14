from __future__ import annotations

import logging
from datetime import datetime

from kiteconnect import KiteConnect

from sensex_noise.broker.base import TradingBroker

logger = logging.getLogger(__name__)


class KitePaperBroker(TradingBroker):
    def __init__(self, api_key: str, access_token: str, capital_budget: float) -> None:
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        self.capital_budget = float(capital_budget)
        self._next_order_id = 1

    def _new_order_id(self, prefix: str) -> str:
        order_id = f"PAPER-{prefix}-{self._next_order_id}"
        self._next_order_id += 1
        return order_id

    def _fetch_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        data = self.kite.ltp([full_symbol])
        if full_symbol not in data:
            raise ValueError(f"LTP missing for symbol: {full_symbol}")
        return datetime.now(), float(data[full_symbol]["last_price"])

    def fetch_underlying_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        return self._fetch_ltp(full_symbol)

    def fetch_option_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        return self._fetch_ltp(full_symbol)

    def verify_auth(self) -> dict:
        """Validate that auth is usable for authenticated Kite endpoints."""
        return self.kite.profile()

    def place_entry_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        ts, entry_price = self.fetch_option_ltp(symbol)
        order_id = self._new_order_id("ENTRY")
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
        logger.info(
            "PAPER EXIT LIMIT | %s | product=%s | qty=%s | price=%.2f | order_id=%s",
            symbol,
            product,
            quantity,
            price,
            order_id,
        )
        return order_id

    def cancel_order(self, order_id: str) -> None:
        logger.info("PAPER CANCEL ORDER | order_id=%s", order_id)

    def exit_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        ts, exit_price = self.fetch_option_ltp(symbol)
        order_id = self._new_order_id("EXIT")
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
