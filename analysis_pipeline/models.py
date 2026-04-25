from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TradeRecord:
    trade_id: str
    date: str
    symbol: str | None = None
    signal_kind: str | None = None
    side: str | None = None
    entry_time: datetime | None = None
    exit_time: datetime | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    gross_pnl: float | None = None
    net_pnl: float | None = None
    exit_reason: str | None = None
    hold_seconds: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventRecord:
    timestamp: datetime | None
    event_type: str
    payload: dict[str, Any]


@dataclass
class TickRecord:
    timestamp_exchange: datetime | None
    timestamp_receive: datetime | None
    symbol: str | None
    instrument_token: int | None
    ltp: float | None
    source: str | None
    best_bid: float | None = None
    best_ask: float | None = None
    spread: float | None = None
    bid5: list[dict[str, Any]] = field(default_factory=list)
    ask5: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TradePathSnapshot:
    trade_id: str
    checkpoint_seconds: float
    option_price: float | None
    option_pnl: float | None
    runup: float | None
    drawdown: float | None
    spread: float | None
    underlying_move: float | None
    futures_move: float | None
    stale_quote: bool | None
    missing_update: bool | None


@dataclass
class CheckpointFeatureRow:
    trade_id: str
    date: str
    has_trade_ticks: bool
    has_underlying_ticks: bool
    has_futures_ticks: bool
    has_depth: bool
    has_subsecond_time: bool
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleEvaluationRow:
    rule_id: str
    checkpoint: float
    rule_definition: str
    sample_size: int
    trades_killed: int
    losers_captured: int
    tail_losers_captured: int
    winners_killed: int
    winner_preservation_rate: float
    tail_capture_rate: float
    post_rule_net_pnl: float
    post_rule_expectancy: float
    post_rule_profit_factor: float | None
    post_rule_max_loss: float | None
    implementation_complexity: str
    robustness_note: str


@dataclass
class PolicyScenarioRow:
    policy_id: str
    policy_name: str
    rule_text: str
    assumptions: str
    trade_count: int
    net_pnl: float
    avg_pnl: float
    median_pnl: float
    max_loss: float | None
    max_gain: float | None
    profit_factor: float | None
    expectancy: float
    winners_lost: int
    losers_prevented: int
    tail_losers_prevented: int
    killed_before_1s: int
    killed_before_2s: int
    killed_before_3s: int
    killed_before_5s: int
    evaluable_trade_count: int


@dataclass
class OperationalCaseRow:
    trade_id: str
    date: str
    exit_reason: str | None
    hold_seconds: float | None
    manual_flag: bool
    long_duration_flag: bool
    stale_quote_flag: bool
    missing_updates_flag: bool
    execution_anomaly_flag: bool
    policy_failure_flag: bool
    operational_failure_flag: bool
    notes: str
