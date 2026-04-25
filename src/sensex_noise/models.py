from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


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
    signal_kind: str = ""

    # identity/signal lineage
    trade_id: str = ""
    signal_time: Optional[datetime] = None
    signal_seen_time: Optional[datetime] = None
    trigger_price: float = 0.0
    source_candle_start: Optional[datetime] = None

    # policy state
    target_points: float = 0.0
    base_target_points: float = 0.0
    promoted_target_points: float = 0.0
    hard_stop_points_used: float = 0.0
    burst_score: int = 0
    burst_features: dict[str, Any] = field(default_factory=dict)
    is_promoted_candidate: bool = False
    is_promoted_active: bool = False
    promoted_3s_passed: Optional[bool] = None
    promoted_3s_reason: Optional[str] = None
    velocity_0_1s: Optional[float] = None
    velocity_2_3s: Optional[float] = None
    velocity_decay_ratio_3s: Optional[float] = None
    promotion_first_hit_trigger_time: Optional[datetime] = None
    promotion_deadline_time: Optional[datetime] = None
    promotion_persistence_exit_triggered: bool = False
    promotion_persistence_passed: Optional[bool] = None
    fragile: bool = False
    early_risk_suspicion_logged: bool = False
    early_risk_exit_triggered: bool = False
    path_risk_exit_triggered: bool = False
    hard_stop_triggered: bool = False

    # order lifecycle
    entry_order_id: str = ""
    entry_order_sent_time: Optional[datetime] = None
    entry_order_ack_time: Optional[datetime] = None
    entry_fill_time: Optional[datetime] = None
    entry_decision_time: Optional[datetime] = None
    entry_reference_price: Optional[float] = None
    entry_slippage_points: Optional[float] = None
    entry_lag_seconds: Optional[float] = None
    exit_order_id: str = ""
    exit_order_sent_time: Optional[datetime] = None
    exit_order_ack_time: Optional[datetime] = None
    exit_fill_time: Optional[datetime] = None
    exit_slippage_points: Optional[float] = None
    exit_lag_seconds: Optional[float] = None

    # quote context
    entry_bid: Optional[float] = None
    entry_ask: Optional[float] = None
    entry_spread: Optional[float] = None
    exit_bid: Optional[float] = None
    exit_ask: Optional[float] = None
    exit_spread: Optional[float] = None
    current_price: Optional[float] = None
    current_spot: Optional[float] = None
    edge_current_pnl_points: float = 0.0
    edge_max_favorable_excursion_points: float = 0.0
    edge_max_adverse_excursion_points: float = 0.0
    edge_first_update_time: Optional[datetime] = None
    edge_last_update_time: Optional[datetime] = None
    edge_elapsed_seconds: float = 0.0
    edge_has_checked_1s: bool = False
    edge_has_checked_3s: bool = False
    edge_stale_quote_flag: bool = False
    edge_exit_candidate_reasons: list[str] = field(default_factory=list)
    edge_last_spread: Optional[float] = None
    edge_bid_price: Optional[float] = None
    edge_ask_price: Optional[float] = None
    edge_has_subsecond_timestamps: bool = False
    edge_last_state_update_log_second: Optional[int] = None
    edge_exit_decision_reason: Optional[str] = None
    edge_exit_decision_elapsed_seconds: Optional[float] = None
    edge_exit_decision_pnl_points: Optional[float] = None
    edge_exit_decision_mfe_points: Optional[float] = None
    edge_exit_decision_mae_points: Optional[float] = None
    edge_legacy_logic_bypassed: bool = False

    # path metrics
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0
    snapshots_emitted: list[int] = field(default_factory=list)
    snapshot_features: dict[str, Any] = field(default_factory=dict)
    first_move_direction: str = "UNKNOWN"
    first_positive_seconds: Optional[float] = None
    first_negative_seconds: Optional[float] = None
    time_to_minus_1: Optional[float] = None
    time_to_minus_3: Optional[float] = None
    time_to_minus_5: Optional[float] = None
    time_to_plus_1: Optional[float] = None
    time_to_plus_2: Optional[float] = None
    worst_step_slope: Optional[float] = None
    avg_slope_5s: Optional[float] = None
    avg_slope_10s: Optional[float] = None

    # quote spread aggregation
    spread_sum: float = 0.0
    spread_count: int = 0

    # historical marks
    price_history: list[tuple[datetime, float]] = field(default_factory=list)

    # terminal state
    post_exit_observation_done: bool = False
    post_exit_path: list[dict[str, Any]] = field(default_factory=list)
    post_exit_observation_seconds: int = 0
    post_exit_points_best_recovery: Optional[float] = None
    post_exit_points_worst_further_loss: Optional[float] = None
    post_exit_recovered_above_exit: bool = False
    post_exit_max_recovery_second: Optional[int] = None
    post_exit_max_further_loss_second: Optional[int] = None
    post_exit_final_delta: Optional[float] = None
    pre_or_post_1pm: str = "PRE_1PM"
    closing: bool = False
    closing_reason: Optional[str] = None
    exit_decision_time: Optional[datetime] = None
    exit_trigger_reference_price: Optional[float] = None
    exit_trigger_reason_candidates: list[str] = field(default_factory=list)
    target_reprice_in_progress: bool = False
    target_reprice_count: int = 0
    target_order_last_modify_time: Optional[datetime] = None
    exit_reason: Optional[str] = None
    early_failure_logged: bool = False
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
