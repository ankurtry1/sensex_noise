from __future__ import annotations

from datetime import datetime

from sensex_noise.broker.base import TradingBroker


class MarketDataService:
    def __init__(self, broker: TradingBroker) -> None:
        self.broker = broker

    def underlying_tick(self, full_symbol: str) -> tuple[datetime, float]:
        return self.broker.fetch_underlying_ltp(full_symbol)

    def option_tick(self, full_symbol: str) -> tuple[datetime, float]:
        return self.broker.fetch_option_ltp(full_symbol)
