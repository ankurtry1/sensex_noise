from __future__ import annotations

from dataclasses import dataclass

from sensex_noise.models import Position


@dataclass(frozen=True)
class ChargeBreakup:
    total: float
    brokerage: float = 0.0
    stt: float = 0.0
    exchange_txn: float = 0.0
    gst: float = 0.0
    sebi: float = 0.0
    stamp_duty: float = 0.0


class ChargesModel:
    """Pluggable charges model.

    Right now this returns zero. Replace `calculate_round_trip` with your exact
    brokerage and statutory charges logic once you finalize it.
    """

    def calculate_round_trip(self, position: Position) -> ChargeBreakup:
        return ChargeBreakup(total=0.0)
