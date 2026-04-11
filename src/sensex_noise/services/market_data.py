from __future__ import annotations

from datetime import datetime
from typing import Any

from sensex_noise.broker.base import TradingBroker
from sensex_noise.errors import QuoteUnavailableError
from sensex_noise.streaming.tick_store import TickStore
from sensex_noise.streaming.token_registry import TokenRegistry


class MarketDataService:
    """Compatibility layer preserving legacy interface, now backed by TickStore."""

    def __init__(
        self,
        broker: TradingBroker,
        tick_store: TickStore | None = None,
        token_registry: TokenRegistry | None = None,
    ) -> None:
        self.broker = broker
        self.tick_store = tick_store
        self.token_registry = token_registry

    def underlying_quote(self, full_symbol: str) -> dict[str, Any]:
        return self._quote_from_store_or_broker(full_symbol=full_symbol, is_underlying=True)

    def option_quote(self, full_symbol: str) -> dict[str, Any]:
        return self._quote_from_store_or_broker(full_symbol=full_symbol, is_underlying=False)

    def underlying_tick(self, full_symbol: str) -> tuple[datetime, float]:
        quote = self.underlying_quote(full_symbol)
        return quote["timestamp"], float(quote["ltp"])

    def option_tick(self, full_symbol: str) -> tuple[datetime, float]:
        quote = self.option_quote(full_symbol)
        return quote["timestamp"], float(quote["ltp"])

    def _quote_from_store_or_broker(self, full_symbol: str, is_underlying: bool) -> dict[str, Any]:
        if self.tick_store is not None:
            tick = self.tick_store.latest_by_symbol(full_symbol)
            if tick is None and self.token_registry is not None:
                token = self.token_registry.token_for_symbol(full_symbol)
                if token is not None:
                    tick = self.tick_store.latest_by_token(token)
                    if tick is not None:
                        self.tick_store.register_symbol_token(full_symbol, int(token))

            if tick is not None:
                return {
                    "timestamp": tick["timestamp_exchange"],
                    "ltp": float(tick["ltp"]),
                    "bid": tick.get("best_bid"),
                    "ask": tick.get("best_ask"),
                    "spread": tick.get("spread"),
                    "last_trade_time": tick.get("timestamp_exchange"),
                }

            raise QuoteUnavailableError(symbol=full_symbol, source="tick_store")

        if is_underlying:
            return self.broker.fetch_underlying_quote(full_symbol)
        return self.broker.fetch_option_quote(full_symbol)
