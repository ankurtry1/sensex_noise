from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalSide(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class CandleColor(str, Enum):
    GREEN = "GREEN"
    RED = "RED"
    NEUTRAL = "NEUTRAL"


@dataclass
class Candle:
    start: datetime
    end: datetime
    open: float
    high: float
    low: float
    close: float

    @property
    def color(self) -> CandleColor:
        if self.close > self.open:
            return CandleColor.GREEN
        if self.close < self.open:
            return CandleColor.RED
        return CandleColor.NEUTRAL


@dataclass
class InstrumentChoice:
    exchange: str
    tradingsymbol: str
    strike: int
    expiry: datetime
    option_type: str
    lot_size: int

    @property
    def full_symbol(self) -> str:
        return f"{self.exchange}:{self.tradingsymbol}"


@dataclass
class Position:
    side: SignalSide
    option_symbol: str
    product: str
    underlying_spot: float
    entry_price: float
    target_price: float
    quantity: int
    strike: int
    expiry: datetime
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    charges: float = 0.0
    status: str = "OPEN"


@dataclass
class TradeEvent:
    timestamp: datetime
    message: str
    data: dict = field(default_factory=dict)
