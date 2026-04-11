from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class TradingBroker(ABC):
    @abstractmethod
    def verify_auth(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def fetch_underlying_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        raise NotImplementedError

    @abstractmethod
    def fetch_option_ltp(self, full_symbol: str) -> tuple[datetime, float]:
        raise NotImplementedError

    @abstractmethod
    def fetch_underlying_quote(self, full_symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_option_quote(self, full_symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def place_entry_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        raise NotImplementedError

    @abstractmethod
    def place_exit_limit(self, symbol: str, quantity: int, price: float, product: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def modify_order(self, variety: str, order_id: str, params: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_order(self, order_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def get_order_history(self, order_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def is_order_modifiable(self, order_id: str, variety: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, variety: str, order_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def exit_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        raise NotImplementedError

    @abstractmethod
    def get_available_funds(self) -> float:
        raise NotImplementedError
