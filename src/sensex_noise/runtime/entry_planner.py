from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from sensex_noise.models import InstrumentChoice
from sensex_noise.services.microburst import classify_target, compute_pre_entry_features
from sensex_noise.strategy import Signal


@dataclass
class EntryPlan:
    signal: Signal
    choice: InstrumentChoice
    option_token: int
    option_quote: dict
    quantity: int
    target_points: float
    trade_id: str
    burst_score: int = 0
    burst_features: dict[str, Any] = field(default_factory=dict)
    is_promoted_candidate: bool = False
    base_target_points: float = 0.0
    promoted_target_points: float = 0.0


class EntryPlanner:
    """Builds an executable entry plan using in-memory option ticks."""

    def __init__(self, engine: object) -> None:
        self.engine = engine
        self.last_failure_reason: str | None = None

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        append_event = getattr(self.engine, "_append_event", None)
        if callable(append_event):
            append_event(event_type, payload)
            return
        self.engine.journal.append_event(event_type, payload)

    def build(self, signal: Signal, tick_time: datetime, spot_ltp: float) -> EntryPlan | None:
        self.last_failure_reason = None
        choice = self.engine.selector.pick_sensex_option(
            spot=spot_ltp,
            side=signal.side,
            now=tick_time,
        )

        option_quote = self.engine.market_data.option_quote(choice.full_symbol)
        trade_id = self.engine._build_trade_id(
            signal=signal,
            option_symbol=choice.full_symbol,
            signal_seen_time=tick_time,
        )

        entry_window_buffer = getattr(self.engine, "entry_window_buffer", None)
        if entry_window_buffer is not None:
            entry_window_buffer.add_option_tick(choice.full_symbol, option_quote)

        burst_score = 0
        burst_features: dict[str, Any] = {}
        is_promoted_candidate = False
        base_target_points = 0.0
        promoted_target_points = 0.0

        if bool(getattr(self.engine.settings, "enable_microburst_gate", False)):
            lookback_seconds = float(
                getattr(self.engine.settings, "entry_feature_lookback_seconds", 5.0)
            )
            underlying_window = (
                entry_window_buffer.get_underlying_window(lookback_seconds)
                if entry_window_buffer is not None
                else []
            )
            option_window = (
                entry_window_buffer.get_option_window(choice.full_symbol, lookback_seconds)
                if entry_window_buffer is not None
                else []
            )
            features = compute_pre_entry_features(
                recent_underlying_window=underlying_window,
                recent_option_window=option_window,
                side=signal.side,
                settings=self.engine.settings,
            )
            burst_score = int(features.score)
            burst_features = asdict(features)
            base_target_points = float(getattr(self.engine.settings, "normal_target_points", 3.0))
            self._append_event(
                "MICROBURST_FEATURES_COMPUTED",
                {
                    "trade_id": trade_id,
                    "symbol": choice.full_symbol,
                    "signal_kind": getattr(signal, "signal_kind", "UNKNOWN"),
                    "side": signal.side.value,
                    "lookback_seconds": lookback_seconds,
                    "underlying_window_points": len(underlying_window),
                    "option_window_points": len(option_window),
                    **burst_features,
                },
            )
            min_score = int(getattr(self.engine.settings, "microburst_min_score", 3))
            if burst_score < min_score:
                self.last_failure_reason = "MICROBURST_GATE_BLOCKED"
                self._append_event(
                    "ENTRY_BLOCKED_MICROBURST_GATE",
                    {
                        "trade_id": trade_id,
                        "symbol": choice.full_symbol,
                        "score": burst_score,
                        "minimum_score": min_score,
                        "score_components": burst_features.get("score_components", {}),
                        "signal_kind": getattr(signal, "signal_kind", "UNKNOWN"),
                    },
                )
                return None

            target_class, target_points = classify_target(burst_score, self.engine.settings)
            is_promoted_candidate = target_class == "promoted"
            if is_promoted_candidate:
                promoted_target_points = float(
                    getattr(self.engine.settings, "promoted_target_points", 7.0)
                )
            self._append_event(
                "ENTRY_ALLOWED_MICROBURST_GATE",
                {
                    "trade_id": trade_id,
                    "symbol": choice.full_symbol,
                    "score": burst_score,
                    "target_class": target_class,
                    "target_points": target_points,
                    "signal_kind": getattr(signal, "signal_kind", "UNKNOWN"),
                    "score_components": burst_features.get("score_components", {}),
                },
            )
        else:
            target_points = self.engine._get_target_points(entry_time=tick_time, fragile=False)
            base_target_points = float(target_points)

        option_token = self.engine.tick_store.token_for_symbol(choice.full_symbol)
        if option_token is None:
            option_token = self.engine.registry.token_for_symbol(choice.full_symbol)
        if option_token is None:
            self.last_failure_reason = "OPTION_TOKEN_UNAVAILABLE"
            return None

        option_ltp = float(option_quote["ltp"])
        quantity = self.engine._resolve_trade_quantity(option_ltp=option_ltp, lot_size=choice.lot_size)
        if quantity is None:
            self.last_failure_reason = "QUANTITY_UNAVAILABLE"
            return None

        return EntryPlan(
            signal=signal,
            choice=choice,
            option_token=int(option_token),
            option_quote=option_quote,
            quantity=quantity,
            target_points=target_points,
            trade_id=trade_id,
            burst_score=burst_score,
            burst_features=burst_features,
            is_promoted_candidate=is_promoted_candidate,
            base_target_points=base_target_points,
            promoted_target_points=promoted_target_points,
        )
