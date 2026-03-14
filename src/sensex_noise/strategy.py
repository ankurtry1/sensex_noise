from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sensex_noise.models import Candle, CandleColor, SignalSide


@dataclass
class Signal:
    side: SignalSide
    trigger_price: float
    source_candle_start: datetime


class StrategyEvaluator:
    def __init__(self, entry_buffer_points: float) -> None:
        self.entry_buffer_points = entry_buffer_points
        self.last_exit_candle_start: Optional[datetime] = None

    def mark_exit(self, candle_start: datetime) -> None:
        self.last_exit_candle_start = candle_start

    def evaluate(self, previous_candle: Optional[Candle], current_candle: Optional[Candle], live_ltp: float) -> Optional[Signal]:
        if previous_candle is None or current_candle is None:
            return None

        if self.last_exit_candle_start is not None and current_candle.start == self.last_exit_candle_start:
            return None

        if previous_candle.color == CandleColor.NEUTRAL:
            return None

        if previous_candle.color == CandleColor.GREEN:
            trigger_price = previous_candle.close + self.entry_buffer_points
            if live_ltp >= trigger_price:
                return Signal(side=SignalSide.CALL, trigger_price=trigger_price, source_candle_start=current_candle.start)

        if previous_candle.color == CandleColor.RED:
            trigger_price = previous_candle.close - self.entry_buffer_points
            if live_ltp <= trigger_price:
                return Signal(side=SignalSide.PUT, trigger_price=trigger_price, source_candle_start=current_candle.start)

        return None
