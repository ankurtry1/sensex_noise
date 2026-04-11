from __future__ import annotations

import json
import queue
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


@dataclass
class _WriteJob:
    path: Path
    record: dict[str, Any]


class TickJournal:
    """Async JSONL writer with persistent file handles and explicit backpressure telemetry."""

    def __init__(
        self,
        logs_root: Path = Path("logs"),
        max_queue_size: int = 50000,
        flush_interval_seconds: float = 1.0,
        enable_full_option_tape_logging: bool = False,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.logs_root = logs_root
        self.ticks_root = logs_root / "ticks"
        self.trade_ticks_root = logs_root / "trade_ticks"

        self.flush_interval_seconds = max(0.1, float(flush_interval_seconds))
        self.enable_full_option_tape_logging = bool(enable_full_option_tape_logging)
        self.on_event = on_event

        self._queue: queue.Queue[_WriteJob | None] = queue.Queue(maxsize=int(max_queue_size))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._stats_lock = threading.Lock()

        self._records_enqueued_total = 0
        self._records_written_total = 0
        self._records_dropped_total = 0
        self._trade_path_records_dropped_total = 0
        self._queue_max_size_seen = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._writer_loop, name="tick-journal-writer", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            self._emit(
                "JOURNAL_BACKPRESSURE",
                {
                    "timestamp": datetime.now().isoformat(),
                    "reason": "STOP_SIGNAL_QUEUE_FULL",
                    "queue_size": self._queue.qsize(),
                },
            )
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def append_market_tick(self, tick: dict[str, Any]) -> bool:
        source = str(tick.get("source", "")).lower()
        if source == "index":
            name = "sensex.jsonl"
        elif source == "future":
            name = "futures.jsonl"
        elif source == "option":
            if not self.enable_full_option_tape_logging:
                return True
            name = "options.jsonl"
        else:
            return True

        day = self._day_for_tick(tick)
        path = self.ticks_root / day / name
        return self._enqueue(path=path, record=tick, critical=False, category="market")

    def append_trade_tick(
        self,
        trade_id: str,
        tick: dict[str, Any],
        phase: str,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        day = self._day_for_tick(tick)
        path = self.trade_ticks_root / day / f"{self._safe_trade_id(trade_id)}.jsonl"
        payload = {
            "trade_id": trade_id,
            "phase": phase,
            **tick,
        }
        if extra:
            payload.update(extra)
        return self._enqueue(path=path, record=payload, critical=True, category="trade_path")

    def append_trade_ticks(
        self,
        trade_id: str,
        ticks: list[dict[str, Any]],
        phase: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        for tick in ticks:
            self.append_trade_tick(trade_id=trade_id, tick=tick, phase=phase, extra=extra)

    def stats_snapshot(self) -> dict[str, int]:
        with self._stats_lock:
            return {
                "records_enqueued_total": self._records_enqueued_total,
                "records_written_total": self._records_written_total,
                "records_dropped_total": self._records_dropped_total,
                "trade_path_records_dropped_total": self._trade_path_records_dropped_total,
                "queue_max_size_seen": self._queue_max_size_seen,
                "queue_size": self._queue.qsize(),
            }

    def _enqueue(
        self,
        path: Path,
        record: dict[str, Any],
        critical: bool,
        category: str,
    ) -> bool:
        job = _WriteJob(path=path, record=record)

        if critical:
            try:
                self._queue.put_nowait(job)
                self._mark_enqueued()
                return True
            except queue.Full:
                self._emit(
                    "JOURNAL_BACKPRESSURE",
                    {
                        "timestamp": datetime.now().isoformat(),
                        "critical": True,
                        "category": category,
                        "queue_size": self._queue.qsize(),
                    },
                )
                try:
                    # Trade-path records are critical: prefer brief blocking before dropping.
                    self._queue.put(job, timeout=0.1)
                    self._mark_enqueued()
                    return True
                except queue.Full:
                    self._mark_dropped(category=category)
                    self._emit(
                        "JOURNAL_CRITICAL_DROP",
                        {
                            "timestamp": datetime.now().isoformat(),
                            "category": category,
                            "queue_size": self._queue.qsize(),
                            "path": str(path),
                        },
                    )
                    return False

        try:
            self._queue.put_nowait(job)
            self._mark_enqueued()
            return True
        except queue.Full:
            self._mark_dropped(category=category)
            self._emit(
                "JOURNAL_DROP",
                {
                    "timestamp": datetime.now().isoformat(),
                    "critical": False,
                    "category": category,
                    "queue_size": self._queue.qsize(),
                    "path": str(path),
                },
            )
            return False

    def _mark_enqueued(self) -> None:
        with self._stats_lock:
            self._records_enqueued_total += 1
            self._queue_max_size_seen = max(self._queue_max_size_seen, self._queue.qsize())

    def _mark_written(self) -> None:
        with self._stats_lock:
            self._records_written_total += 1

    def _mark_dropped(self, category: str) -> None:
        with self._stats_lock:
            self._records_dropped_total += 1
            if category == "trade_path":
                self._trade_path_records_dropped_total += 1

    def _writer_loop(self) -> None:
        handles: dict[Path, Any] = {}
        last_flush = time.monotonic()

        while not self._stop.is_set() or not self._queue.empty():
            try:
                job = self._queue.get(timeout=0.2)
            except queue.Empty:
                job = None

            if isinstance(job, _WriteJob):
                fp = self._get_handle(handles, job.path)
                fp.write(json.dumps(self._jsonable(job.record), ensure_ascii=True) + "\n")
                self._mark_written()

            now = time.monotonic()
            if (now - last_flush) >= self.flush_interval_seconds:
                self._flush_handles(handles)
                last_flush = now

            if job is None and self._stop.is_set() and self._queue.empty():
                break

        self._flush_handles(handles)
        self._close_handles(handles)

    def _get_handle(self, handles: dict[Path, Any], path: Path) -> Any:
        fp = handles.get(path)
        if fp is not None and not fp.closed:
            return fp

        path.parent.mkdir(parents=True, exist_ok=True)
        fp = path.open("a", encoding="utf-8")
        handles[path] = fp
        return fp

    @staticmethod
    def _flush_handles(handles: dict[Path, Any]) -> None:
        for fp in handles.values():
            if fp.closed:
                continue
            fp.flush()

    @staticmethod
    def _close_handles(handles: dict[Path, Any]) -> None:
        for fp in handles.values():
            if fp.closed:
                continue
            fp.flush()
            fp.close()

    @staticmethod
    def _safe_trade_id(trade_id: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", trade_id.strip())
        return safe or "trade"

    @staticmethod
    def _day_for_tick(tick: dict[str, Any]) -> str:
        ts = tick.get("timestamp_exchange")
        if isinstance(ts, datetime):
            return ts.date().isoformat()
        return datetime.now().date().isoformat()

    @staticmethod
    def _jsonable(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(k): TickJournal._jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [TickJournal._jsonable(v) for v in value]
        return value

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.on_event is None:
            return
        self.on_event(event_type, payload)
