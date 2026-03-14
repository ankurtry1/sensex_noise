from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from sensex_noise.models import Position


@dataclass
class Wallet:
    starting_capital: float
    cash: float = field(init=False)
    realized_pnl: float = 0.0
    trades: List[Position] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.starting_capital

    def apply_closed_trade(self, position: Position) -> None:
        self.realized_pnl += position.net_pnl
        self.cash = self.starting_capital + self.realized_pnl
        self.trades.append(position)

    @property
    def trade_count(self) -> int:
        return len(self.trades)
