from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sensex_noise.runtime.exit_runtime import ExitRuntime

logger = logging.getLogger(__name__)


class PositionTracker:
    """Updates open-position state on every option tick and delegates exit execution."""

    def __init__(self, engine: object, exit_runtime: ExitRuntime) -> None:
        self.engine = engine
        self.exit_runtime = exit_runtime

    def on_option_tick(
        self,
        option_quote: dict[str, Any],
        spot_quote: dict[str, Any],
        future_quote: dict[str, Any] | None = None,
    ) -> str | None:
        if self.engine.open_position is None:
            return None

        option_tick_time = option_quote["timestamp"]
        option_ltp = float(option_quote["ltp"])

        resolved_thresholds = self.engine._update_path_features(
            position=self.engine.open_position,
            mark_time=option_tick_time,
            option_quote=option_quote,
            spot_quote=spot_quote,
        )
        self.engine._emit_due_snapshots(
            position=self.engine.open_position,
            mark_time=option_tick_time,
            option_quote=option_quote,
            spot_quote=spot_quote,
            resolved_thresholds=resolved_thresholds,
        )

        if self.engine.settings.enable_verbose_trade_logging:
            payload = {
                "trade_id": self.engine.open_trade_id,
                "symbol": self.engine.open_position.option_symbol,
                "product": self.engine.open_position.product,
                "mark_time": option_tick_time.isoformat(),
                "entry_price": self.engine.open_position.entry_price,
                "target_price": self.engine.open_position.target_price,
                "active_exit_order_type": self.engine.active_exit_order_type,
                "active_exit_price": self.engine.active_exit_price,
                "ltp": option_ltp,
                "spot_ltp": float(spot_quote["ltp"]),
                "signal_kind": self.engine.open_position.signal_kind,
                "burst_score": self.engine.open_position.burst_score,
                "is_promoted_candidate": self.engine.open_position.is_promoted_candidate,
                "is_promoted_active": self.engine.open_position.is_promoted_active,
                "mfe": self.engine.open_position.max_favorable_excursion,
                "mae": self.engine.open_position.max_adverse_excursion,
            }
            if future_quote is not None:
                payload["futures_ltp"] = float(future_quote.get("ltp", 0.0))
                ts = future_quote.get("timestamp")
                if isinstance(ts, datetime):
                    payload["futures_timestamp"] = ts.isoformat()
            logger.info(
                "OPEN POSITION | %s | entry=%.2f | target=%.2f | ltp=%.2f",
                self.engine.open_position.option_symbol,
                self.engine.open_position.entry_price,
                self.engine.open_position.target_price,
                option_ltp,
            )
            self.engine.journal.append("OPEN_POSITION_MARK", payload)

        duration_seconds = (option_tick_time - self.engine.open_position.entry_time).total_seconds()
        if (
            duration_seconds <= self.engine.settings.early_failure_window_seconds
            and not self.engine.open_position.early_failure_logged
            and self.engine.open_position.max_favorable_excursion < self.engine.settings.early_failure_mfe_min
            and option_ltp <= self.engine.open_position.entry_price
            and self.engine.open_position.max_adverse_excursion <= self.engine.settings.early_failure_mae_max
        ):
            logger.warning("Early failure signal detected")
            self.engine.journal.append(
                "EARLY_FAILURE_SIGNAL",
                {
                    "trade_id": self.engine.open_trade_id,
                    "symbol": self.engine.open_position.option_symbol,
                    "product": self.engine.open_position.product,
                    "signal_kind": self.engine.open_position.signal_kind,
                    "entry_time": self.engine.open_position.entry_time.isoformat(),
                    "mark_time": option_tick_time.isoformat(),
                    "duration_seconds": duration_seconds,
                    "entry_price": self.engine.open_position.entry_price,
                    "current_price": option_ltp,
                    "mfe": self.engine.open_position.max_favorable_excursion,
                    "mae": self.engine.open_position.max_adverse_excursion,
                    "target_price": self.engine.open_position.target_price,
                },
            )
            self.engine.open_position.early_failure_logged = True

        if not self.engine.open_position.closing:
            self.engine._maybe_mark_early_suspicion(
                position=self.engine.open_position,
                mark_time=option_tick_time,
                option_ltp=option_ltp,
            )

        return self.exit_runtime.evaluate_and_execute(
            option_quote=option_quote,
            spot_quote=spot_quote,
            option_tick_time=option_tick_time,
        )
