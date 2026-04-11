from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sensex_noise.models import Position


class TradeJournal:
    def __init__(
        self,
        path: Path,
        event_path: Path | None = None,
        enriched_trade_path: Path | None = None,
    ) -> None:
        self.path = path
        self.event_path = event_path or path
        self.enriched_trade_path = enriched_trade_path

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        if self.enriched_trade_path is not None:
            self.enriched_trade_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _jsonable(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(k): TradeJournal._jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [TradeJournal._jsonable(v) for v in value]
        if hasattr(value, "value") and isinstance(getattr(value, "value", None), str):
            return value.value
        return value

    def _append_jsonl(self, out_path: Path, record: dict[str, Any]) -> None:
        with out_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(self._jsonable(record), ensure_ascii=True) + "\n")

    def append(self, event_type: str, payload: dict[str, Any]) -> None:
        self.append_event(event_type=event_type, payload=payload)

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        # Backward compatibility: legacy path still receives the event stream.
        self._append_jsonl(self.path, record)
        if self.event_path != self.path:
            self._append_jsonl(self.event_path, record)

    def append_trade_summary(self, position: Position, extra_payload: dict[str, Any] | None = None) -> None:
        holding_seconds = None
        if position.exit_time is not None:
            holding_seconds = (position.exit_time - position.entry_time).total_seconds()

        summary: dict[str, Any] = {
            "trade_id": position.trade_id,
            "symbol": position.option_symbol,
            "strike": position.strike,
            "expiry": position.expiry,
            "side": position.side,
            "signal_kind": position.signal_kind,
            "signal_time": position.signal_time,
            "signal_seen_time": position.signal_seen_time,
            "trigger_price": position.trigger_price,
            "source_candle_start": position.source_candle_start,
            "entry_order_id": position.entry_order_id,
            "entry_order_sent_time": position.entry_order_sent_time,
            "entry_order_ack_time": position.entry_order_ack_time,
            "entry_decision_time": position.entry_decision_time,
            "entry_reference_price": position.entry_reference_price,
            "entry_fill_time": position.entry_fill_time,
            "entry_price": position.entry_price,
            "entry_slippage_points": position.entry_slippage_points,
            "entry_lag_seconds": position.entry_lag_seconds,
            "entry_bid": position.entry_bid,
            "entry_ask": position.entry_ask,
            "entry_spread": position.entry_spread,
            "underlying_spot_at_entry": position.underlying_spot,
            "exit_reason": position.exit_reason,
            "closing_reason": position.closing_reason,
            "exit_decision_time": position.exit_decision_time,
            "exit_trigger_reference_price": position.exit_trigger_reference_price,
            "exit_trigger_reason_candidates": position.exit_trigger_reason_candidates,
            "exit_order_id": position.exit_order_id,
            "exit_order_sent_time": position.exit_order_sent_time,
            "exit_order_ack_time": position.exit_order_ack_time,
            "exit_fill_time": position.exit_fill_time,
            "exit_price": position.exit_price,
            "exit_slippage_points": position.exit_slippage_points,
            "exit_lag_seconds": position.exit_lag_seconds,
            "exit_bid": position.exit_bid,
            "exit_ask": position.exit_ask,
            "exit_spread": position.exit_spread,
            "holding_seconds": holding_seconds,
            "target_points_used": position.target_points,
            "hard_stop_points_used": position.hard_stop_points_used,
            "fragile": position.fragile,
            "early_risk_exit_triggered": position.early_risk_exit_triggered,
            "path_risk_exit_triggered": position.path_risk_exit_triggered,
            "hard_stop_triggered": position.hard_stop_triggered,
            "early_failure_logged": position.early_failure_logged,
            "gross_pnl": position.gross_pnl,
            "net_pnl": position.net_pnl,
            "charges": position.charges,
            "mfe": position.max_favorable_excursion,
            "mae": position.max_adverse_excursion,
            "first_move_direction": position.first_move_direction,
            "first_positive_seconds": position.first_positive_seconds,
            "first_negative_seconds": position.first_negative_seconds,
            "time_to_minus_1": position.time_to_minus_1,
            "time_to_minus_3": position.time_to_minus_3,
            "time_to_minus_5": position.time_to_minus_5,
            "time_to_plus_1": position.time_to_plus_1,
            "time_to_plus_2": position.time_to_plus_2,
            "worst_step_slope": position.worst_step_slope,
            "avg_slope_5s": position.avg_slope_5s,
            "avg_slope_10s": position.avg_slope_10s,
            "pre_or_post_1pm": position.pre_or_post_1pm,
            "average_observed_spread": (
                (position.spread_sum / position.spread_count) if position.spread_count > 0 else None
            ),
            "post_exit_observation_done": position.post_exit_observation_done,
            "post_exit_path": position.post_exit_path,
            "post_exit_observation_seconds": position.post_exit_observation_seconds,
            "post_exit_points_best_recovery": position.post_exit_points_best_recovery,
            "post_exit_points_worst_further_loss": position.post_exit_points_worst_further_loss,
            "post_exit_recovered_above_exit": position.post_exit_recovered_above_exit,
            "post_exit_max_recovery_second": position.post_exit_max_recovery_second,
            "post_exit_max_further_loss_second": position.post_exit_max_further_loss_second,
            "post_exit_final_delta": position.post_exit_final_delta,
            "post_exit_final_delta_15s": (
                position.post_exit_final_delta
                if position.post_exit_observation_seconds == 15
                else None
            ),
            "target_reprice_count": position.target_reprice_count,
            "target_order_last_modify_time": position.target_order_last_modify_time,
        }

        # Include all snapshot-derived runups/drawdowns/current_pnls and other engineered features.
        summary.update(position.snapshot_features)

        if extra_payload:
            summary.update(extra_payload)

        self.append_event("TRADE_CLOSED_SUMMARY", summary)
        if self.enriched_trade_path is not None:
            self._append_jsonl(self.enriched_trade_path, summary)
