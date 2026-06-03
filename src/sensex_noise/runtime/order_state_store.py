from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExitOrderState:
    order_type: str | None = None
    price: float | None = None
    order_id: str | None = None
    variety: str = "regular"
    sent_time: datetime | None = None
    ack_time: datetime | None = None


class OrderStateStore:
    """Small adapter around exit-order state tracked on StrategyEngine."""

    @staticmethod
    def snapshot(engine: object) -> ExitOrderState:
        return ExitOrderState(
            order_type=getattr(engine, "active_exit_order_type", None),
            price=getattr(engine, "active_exit_price", None),
            order_id=getattr(engine, "active_exit_order_id", None),
            variety=getattr(engine, "active_exit_order_variety", "regular"),
            sent_time=getattr(engine, "active_exit_order_sent_time", None),
            ack_time=getattr(engine, "active_exit_order_ack_time", None),
        )
