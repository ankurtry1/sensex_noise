from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WatchdogStatus:
    degraded: bool
    event_type: str | None = None
    payload: dict | None = None
    stale_reason: str | None = None
    idle_seconds: float | None = None
    should_alert: bool = False
    should_reconnect: bool = False


class StreamWatchdog:
    """Detects connected-but-stalled index stream and emits degrade/recovery states."""

    def __init__(self, max_idle_seconds: int, hard_reconnect_seconds: int) -> None:
        self.max_idle_seconds = int(max_idle_seconds)
        self.hard_reconnect_seconds = int(hard_reconnect_seconds)
        self._degraded = False

    @property
    def degraded(self) -> bool:
        return self._degraded

    def evaluate(
        self,
        *,
        now: datetime,
        stream_connected: bool,
        market_session_active: bool,
        last_index_receive_ts: datetime | None,
    ) -> WatchdogStatus:
        if not market_session_active or not stream_connected:
            return WatchdogStatus(degraded=self._degraded)

        if last_index_receive_ts is None:
            if not self._degraded:
                self._degraded = True
                return WatchdogStatus(
                    degraded=True,
                    event_type="WATCHDOG_ALERT",
                    payload={
                        "reason": "NO_INDEX_TICK_SEEN",
                        "max_idle_seconds": self.max_idle_seconds,
                        "hard_reconnect_seconds": self.hard_reconnect_seconds,
                    },
                    stale_reason="NO_INDEX_TICK_SEEN",
                    should_alert=True,
                )
            return WatchdogStatus(
                degraded=True,
                stale_reason="NO_INDEX_TICK_SEEN",
            )

        idle_seconds = max(0.0, (now - last_index_receive_ts).total_seconds())
        should_reconnect = idle_seconds > float(self.hard_reconnect_seconds)
        if idle_seconds > float(self.max_idle_seconds):
            if not self._degraded:
                self._degraded = True
                return WatchdogStatus(
                    degraded=True,
                    event_type="WATCHDOG_ALERT",
                    payload={
                        "reason": "INDEX_TICK_IDLE",
                        "idle_seconds": idle_seconds,
                        "max_idle_seconds": self.max_idle_seconds,
                        "hard_reconnect_seconds": self.hard_reconnect_seconds,
                    },
                    stale_reason="INDEX_TICK_IDLE",
                    idle_seconds=idle_seconds,
                    should_alert=True,
                    should_reconnect=should_reconnect,
                )
            return WatchdogStatus(
                degraded=True,
                stale_reason="INDEX_TICK_IDLE",
                idle_seconds=idle_seconds,
                should_reconnect=should_reconnect,
            )

        if self._degraded:
            self._degraded = False
            return WatchdogStatus(
                degraded=False,
                event_type="WATCHDOG_RECOVERED",
                payload={
                    "idle_seconds": idle_seconds,
                    "max_idle_seconds": self.max_idle_seconds,
                    "hard_reconnect_seconds": self.hard_reconnect_seconds,
                },
                idle_seconds=idle_seconds,
            )
        return WatchdogStatus(degraded=False, idle_seconds=idle_seconds)
