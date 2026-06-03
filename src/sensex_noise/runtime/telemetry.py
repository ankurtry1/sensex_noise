from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any


@dataclass
class _ReceiveTimestamps:
    index: datetime | None = None
    future: datetime | None = None
    option: datetime | None = None
    any_tick: datetime | None = None


class RuntimeTelemetry:
    """Thread-safe runtime telemetry counters/state for health visibility."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.runtime_ticks_received_total = 0
        self.runtime_ticks_processed_total = 0
        self.runtime_ticks_dropped_total = 0
        self.critical_ticks_dropped_total = 0
        self.background_ticks_dropped_total = 0

        self.journal_records_enqueued_total = 0
        self.journal_records_written_total = 0
        self.journal_records_dropped_total = 0

        self.critical_queue_max_size_seen = 0
        self.background_queue_max_size_seen = 0
        self.journal_queue_max_size_seen = 0

        self.current_subscribed_token_count = 0
        self.current_option_lattice_size = 0
        self.current_atm_reference: int | None = None

        self._last_receive = _ReceiveTimestamps()

        self.stream_connected = False
        self.stream_degraded = True
        self.stream_reconnect_in_progress = False
        self.stream_state: str | None = None
        self.stream_generation_id: int | None = None
        self.active_trade_id: str | None = None

    def mark_tick_received(self, tick: dict[str, Any]) -> None:
        source = str(tick.get("source", "")).lower()
        ts = tick.get("timestamp_receive")
        with self._lock:
            self.runtime_ticks_received_total += 1
            if isinstance(ts, datetime):
                self._last_receive.any_tick = ts
                if source == "index":
                    self._last_receive.index = ts
                elif source == "future":
                    self._last_receive.future = ts
                elif source == "option":
                    self._last_receive.option = ts

    def mark_tick_processed(self) -> None:
        with self._lock:
            self.runtime_ticks_processed_total += 1

    def mark_tick_dropped(self, critical: bool) -> None:
        with self._lock:
            self.runtime_ticks_dropped_total += 1
            if critical:
                self.critical_ticks_dropped_total += 1
            else:
                self.background_ticks_dropped_total += 1

    def mark_queue_sizes(self, critical_size: int, background_size: int, journal_size: int | None = None) -> None:
        with self._lock:
            self.critical_queue_max_size_seen = max(self.critical_queue_max_size_seen, int(critical_size))
            self.background_queue_max_size_seen = max(
                self.background_queue_max_size_seen,
                int(background_size),
            )
            if journal_size is not None:
                self.journal_queue_max_size_seen = max(
                    self.journal_queue_max_size_seen,
                    int(journal_size),
                )

    def sync_journal_stats(self, stats: dict[str, Any]) -> None:
        with self._lock:
            self.journal_records_enqueued_total = int(stats.get("records_enqueued_total", 0))
            self.journal_records_written_total = int(stats.get("records_written_total", 0))
            self.journal_records_dropped_total = int(stats.get("records_dropped_total", 0))
            qmax = stats.get("queue_max_size_seen")
            if qmax is not None:
                self.journal_queue_max_size_seen = max(self.journal_queue_max_size_seen, int(qmax))

    def set_subscription_state(
        self,
        subscribed_token_count: int,
        option_lattice_size: int,
        current_atm_reference: int | None,
    ) -> None:
        with self._lock:
            self.current_subscribed_token_count = int(subscribed_token_count)
            self.current_option_lattice_size = int(option_lattice_size)
            self.current_atm_reference = current_atm_reference

    def set_stream_state(
        self,
        connected: bool,
        degraded: bool,
        reconnect_in_progress: bool = False,
        state: str | None = None,
        generation_id: int | None = None,
    ) -> None:
        with self._lock:
            self.stream_connected = bool(connected)
            self.stream_degraded = bool(degraded)
            self.stream_reconnect_in_progress = bool(reconnect_in_progress)
            if state is not None:
                self.stream_state = str(state)
            self.stream_generation_id = generation_id

    def set_active_trade_id(self, trade_id: str | None) -> None:
        with self._lock:
            self.active_trade_id = trade_id

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "runtime_ticks_received_total": self.runtime_ticks_received_total,
                "runtime_ticks_processed_total": self.runtime_ticks_processed_total,
                "runtime_ticks_dropped_total": self.runtime_ticks_dropped_total,
                "critical_ticks_dropped_total": self.critical_ticks_dropped_total,
                "background_ticks_dropped_total": self.background_ticks_dropped_total,
                "journal_records_enqueued_total": self.journal_records_enqueued_total,
                "journal_records_written_total": self.journal_records_written_total,
                "journal_records_dropped_total": self.journal_records_dropped_total,
                "critical_queue_max_size_seen": self.critical_queue_max_size_seen,
                "background_queue_max_size_seen": self.background_queue_max_size_seen,
                "journal_queue_max_size_seen": self.journal_queue_max_size_seen,
                "current_subscribed_token_count": self.current_subscribed_token_count,
                "current_option_lattice_size": self.current_option_lattice_size,
                "current_atm_reference": self.current_atm_reference,
                "last_index_tick_receive_ts": (
                    self._last_receive.index.isoformat() if self._last_receive.index is not None else None
                ),
                "last_future_tick_receive_ts": (
                    self._last_receive.future.isoformat() if self._last_receive.future is not None else None
                ),
                "last_option_tick_receive_ts": (
                    self._last_receive.option.isoformat() if self._last_receive.option is not None else None
                ),
                "last_any_tick_receive_ts": (
                    self._last_receive.any_tick.isoformat() if self._last_receive.any_tick is not None else None
                ),
                "stream_connected": self.stream_connected,
                "stream_degraded": self.stream_degraded,
                "stream_reconnect_in_progress": self.stream_reconnect_in_progress,
                "stream_state": self.stream_state,
                "stream_generation_id": self.stream_generation_id,
                "active_trade_id": self.active_trade_id,
            }

    def last_index_receive_ts(self) -> datetime | None:
        with self._lock:
            return self._last_receive.index

    def last_any_receive_ts(self) -> datetime | None:
        with self._lock:
            return self._last_receive.any_tick
