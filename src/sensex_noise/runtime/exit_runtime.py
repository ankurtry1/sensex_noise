from __future__ import annotations

from datetime import datetime
from typing import Any


class ExitRuntime:
    """Runs exit selection/execution while preserving StrategyEngine rules."""

    def __init__(self, engine: object) -> None:
        self.engine = engine

    def evaluate_and_execute(
        self,
        option_quote: dict[str, Any],
        spot_quote: dict[str, Any],
        option_tick_time: datetime,
    ) -> str | None:
        if self.engine.open_position is None or self.engine.open_position.closing:
            return None

        option_ltp = float(option_quote["ltp"])
        spot_ltp = float(spot_quote["ltp"])
        duration_seconds = (option_tick_time - self.engine.open_position.entry_time).total_seconds()

        exit_candidates = self.engine._collect_exit_candidates(
            position=self.engine.open_position,
            option_quote=option_quote,
            mark_time=option_tick_time,
        )
        selected_reason = self.engine._select_exit_reason(exit_candidates)
        if selected_reason is None:
            return None

        decision_time = datetime.now()
        self.engine._mark_position_closing(
            position=self.engine.open_position,
            selected_reason=selected_reason,
            candidates=exit_candidates,
            decision_time=decision_time,
            trigger_reference_price=option_ltp,
        )
        self.engine._log_exit_decision_selected(
            position=self.engine.open_position,
            selected_reason=selected_reason,
            candidates=exit_candidates,
            option_ltp=option_ltp,
            spot_ltp=spot_ltp,
            holding_seconds=duration_seconds,
        )
        if selected_reason == "MANUAL_EXIT":
            self.engine.manual_exit_requested = False

        if selected_reason in {
            "MANUAL_EXIT",
            "EDGE_HARD_STOP",
            "STALE_QUOTE_FAILSAFE",
            "EARLY_FAIL_1S",
            "EARLY_FAIL_3S",
            "PROMOTED_FAIL_3S",
            "PROMOTION_PERSISTENCE_FAIL",
            "HARD_STOP_EXIT",
            "EARLY_RISK_EXIT",
            "PATH_RISK_EXIT",
            "TIME_STOP_AFTER_1PM",
        }:
            if selected_reason == "HARD_STOP_EXIT":
                self.engine._should_hard_stop(
                    self.engine.open_position,
                    mark_time=option_tick_time,
                    option_ltp=option_ltp,
                    record=True,
                )
            elif selected_reason == "EARLY_RISK_EXIT":
                self.engine._should_early_exit(
                    self.engine.open_position,
                    mark_time=option_tick_time,
                    option_ltp=option_ltp,
                    record=True,
                )
            elif selected_reason == "PATH_RISK_EXIT":
                self.engine._should_path_exit(
                    self.engine.open_position,
                    mark_time=option_tick_time,
                    option_ltp=option_ltp,
                    record=True,
                )
            if selected_reason == "TIME_STOP_AFTER_1PM":
                self.engine._append_event(
                    "TIME_STOP_AFTER_1PM",
                    {
                        "trade_id": self.engine.open_trade_id,
                        "symbol": self.engine.open_position.option_symbol,
                        "duration_seconds": duration_seconds,
                        "time_stop_seconds": self.engine.settings.post_1pm_time_stop_seconds,
                    },
                )
            self.engine._cancel_active_exit_order(reason=selected_reason)
            self.engine._execute_market_exit(
                exit_reason=selected_reason,
                option_quote=option_quote,
            )
            return selected_reason

        if selected_reason == "MANUAL_LIMIT_HIT":
            self.engine._append_event(
                "MANUAL_LIMIT_HIT",
                {
                    "trade_id": self.engine.open_trade_id,
                    "symbol": self.engine.open_position.option_symbol,
                    "price": self.engine.active_exit_price,
                    "closing": self.engine.open_position.closing,
                    "fragile": self.engine.open_position.fragile,
                },
            )
            self.engine._exit_open_position(
                exit_time=option_tick_time,
                exit_price=self.engine.active_exit_price,
                exit_reason="MANUAL_LIMIT_HIT",
                exit_quote=option_quote,
            )
            return selected_reason

        if selected_reason == "TARGET_HIT":
            self.engine._append_event(
                "TARGET_HIT",
                {
                    "trade_id": self.engine.open_trade_id,
                    "symbol": self.engine.open_position.option_symbol,
                    "target_price": self.engine.open_position.target_price,
                    "target_points": self.engine.open_position.target_points,
                    "closing": self.engine.open_position.closing,
                    "fragile": self.engine.open_position.fragile,
                },
            )
            self.engine._exit_open_position(
                exit_time=option_tick_time,
                exit_price=self.engine.open_position.target_price,
                exit_reason="TARGET_HIT",
                exit_quote=option_quote,
            )
            return selected_reason

        return None
