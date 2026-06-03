from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sensex_noise.models import Candle


def floor_to_5_minute_bucket(ts: datetime) -> datetime:
    minute = ts.minute - (ts.minute % 5)
    return ts.replace(minute=minute, second=0, microsecond=0)


@dataclass
class CandleEngine:
    """5-minute candle builder from SENSEX index ticks only."""

    previous_candle: Candle | None = None
    current_candle: Candle | None = None

    def update_from_tick(self, tick_time: datetime, ltp: float) -> None:
        bucket_start = floor_to_5_minute_bucket(tick_time)
        bucket_end = bucket_start + timedelta(minutes=5)

        if self.current_candle is None:
            self.current_candle = Candle(
                start=bucket_start,
                end=bucket_end,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
            )
            return

        if bucket_start > self.current_candle.start:
            self.previous_candle = self.current_candle
            self.current_candle = Candle(
                start=bucket_start,
                end=bucket_end,
                open=ltp,
                high=ltp,
                low=ltp,
                close=ltp,
            )
            return

        self.current_candle.high = max(self.current_candle.high, ltp)
        self.current_candle.low = min(self.current_candle.low, ltp)
        self.current_candle.close = ltp

    # Compatibility alias so existing engine helper methods keep working.
    def update(self, now: datetime, ltp: float) -> None:
        self.update_from_tick(tick_time=now, ltp=ltp)
