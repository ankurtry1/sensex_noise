from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

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
    def place_entry_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        raise NotImplementedError

    @abstractmethod
    def place_exit_limit(self, symbol: str, quantity: int, price: float, product: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exit_market(self, symbol: str, quantity: int, product: str) -> tuple[str, float, datetime]:
        raise NotImplementedError

    @abstractmethod
    def get_available_funds(self) -> float:
        raise NotImplementedError
