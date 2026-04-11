from __future__ import annotations


class QuoteUnavailableError(RuntimeError):
    """Raised when latest in-memory quote is unavailable in websocket runtime."""

    def __init__(self, symbol: str, source: str = "tick_store") -> None:
        self.symbol = symbol
        self.source = source
        super().__init__(f"Quote unavailable for {symbol} from {source}")
