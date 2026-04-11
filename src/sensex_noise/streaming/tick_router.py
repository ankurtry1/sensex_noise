from __future__ import annotations

import queue
from datetime import datetime
from typing import Any, Callable

from sensex_noise.runtime.telemetry import RuntimeTelemetry
from sensex_noise.streaming.tick_store import TickStore


class TickRouter:
    """Hot-path router: store tick then route to critical/background queues."""

    def __init__(
        self,
        tick_store: TickStore,
        critical_queue: queue.Queue[dict[str, Any]],
        background_queue: queue.Queue[dict[str, Any]],
        is_critical_tick: Callable[[dict[str, Any]], bool],
        telemetry: RuntimeTelemetry,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
        critical_put_timeout_seconds: float = 0.05,
    ) -> None:
        self.tick_store = tick_store
        self.critical_queue = critical_queue
        self.background_queue = background_queue
        self.is_critical_tick = is_critical_tick
        self.telemetry = telemetry
        self.on_event = on_event
        self.critical_put_timeout_seconds = float(critical_put_timeout_seconds)

    def route(self, tick: dict[str, Any]) -> bool:
        self.telemetry.mark_tick_received(tick)
        self.tick_store.put(tick)

        critical = self.is_critical_tick(tick)
        target_queue = self.critical_queue if critical else self.background_queue

        enqueued = False
        if critical:
            enqueued = self._enqueue_critical_tick(target_queue, tick)
        else:
            enqueued = self._enqueue_background_tick(target_queue, tick)

        self.telemetry.mark_queue_sizes(
            critical_size=self.critical_queue.qsize(),
            background_size=self.background_queue.qsize(),
        )
        return enqueued

    def _enqueue_critical_tick(
        self,
        target_queue: queue.Queue[dict[str, Any]],
        tick: dict[str, Any],
    ) -> bool:
        try:
            target_queue.put_nowait(tick)
            return True
        except queue.Full:
            pass

        # Brief blocking attempt for critical path before declaring drop.
        try:
            target_queue.put(tick, timeout=self.critical_put_timeout_seconds)
            return True
        except queue.Full:
            self.telemetry.mark_tick_dropped(critical=True)
            self._emit(
                "CRITICAL_TICK_DROP",
                {
                    "timestamp": datetime.now().isoformat(),
                    "source": tick.get("source"),
                    "instrument_token": tick.get("instrument_token"),
                    "symbol": tick.get("symbol"),
                    "critical_queue_size": target_queue.qsize(),
                },
            )
            return False

    def _enqueue_background_tick(
        self,
        target_queue: queue.Queue[dict[str, Any]],
        tick: dict[str, Any],
    ) -> bool:
        try:
            target_queue.put_nowait(tick)
            return True
        except queue.Full:
            self.telemetry.mark_tick_dropped(critical=False)
            self._emit(
                "BACKGROUND_TICK_DROP",
                {
                    "timestamp": datetime.now().isoformat(),
                    "source": tick.get("source"),
                    "instrument_token": tick.get("instrument_token"),
                    "symbol": tick.get("symbol"),
                    "background_queue_size": target_queue.qsize(),
                },
            )
            return False

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.on_event is None:
            return
        self.on_event(event_type, payload)
