from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Iterable

from kiteconnect import KiteTicker

from sensex_noise.streaming.tick_normalizer import TickNormalizer
from sensex_noise.streaming.tick_router import TickRouter
from sensex_noise.streaming.token_registry import TokenRegistry

logger = logging.getLogger(__name__)


class StreamState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED_PENDING_FIRST_TICK = "CONNECTED_PENDING_FIRST_TICK"
    LIVE = "LIVE"
    STALE = "STALE"
    RECONNECTING = "RECONNECTING"


@dataclass
class _GenerationInfo:
    generation_id: int
    ticker: KiteTicker
    started_at: datetime
    connected_at: datetime | None = None
    first_tick_at: datetime | None = None
    subscriptions_ready: bool = False
    subscriptions_applied_at: datetime | None = None


class KiteStream:
    """WebSocket runtime for KiteTicker with generation-safe lifecycle state machine."""

    def __init__(
        self,
        api_key: str,
        access_token: str,
        registry: TokenRegistry,
        normalizer: TickNormalizer,
        router: TickRouter,
        on_disconnect: Callable[[int | None, str | None], None] | None = None,
        on_reconnect: Callable[[int], None] | None = None,
        on_connect_state: Callable[[], None] | None = None,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
        reconnect_cooldown_seconds: float = 10.0,
        rebase_persist_ticks: int = 3,
        rebase_cooldown_seconds: float = 3.0,
        rebase_min_move_points: int = 100,
        enable_sensex_option_tape_recorder: bool = False,
        sensex_tape_strike_range_points: int = 1500,
        sensex_tape_strike_step_points: int = 100,
        sensex_tape_expiry_mode: str = "nearest",
        sensex_tape_include_ce: bool = True,
        sensex_tape_include_pe: bool = True,
        sensex_tape_rebase_on_atm_move_points: int = 100,
    ) -> None:
        self.api_key = api_key
        self.access_token = access_token
        self.registry = registry
        self.normalizer = normalizer
        self.router = router
        self.on_disconnect_cb = on_disconnect
        self.on_reconnect_cb = on_reconnect
        self.on_connect_state_cb = on_connect_state
        self.on_event = on_event

        self.reconnect_cooldown_seconds = max(1.0, float(reconnect_cooldown_seconds))
        self.rebase_persist_ticks = max(1, int(rebase_persist_ticks))
        self.rebase_cooldown_seconds = max(0.0, float(rebase_cooldown_seconds))
        self.rebase_min_move_points = max(1, int(rebase_min_move_points))
        self.enable_sensex_option_tape_recorder = bool(enable_sensex_option_tape_recorder)
        self.sensex_tape_strike_range_points = max(0, int(sensex_tape_strike_range_points))
        self.sensex_tape_strike_step_points = max(1, int(sensex_tape_strike_step_points))
        self.sensex_tape_expiry_mode = str(sensex_tape_expiry_mode).strip().lower()
        self.sensex_tape_include_ce = bool(sensex_tape_include_ce)
        self.sensex_tape_include_pe = bool(sensex_tape_include_pe)
        self.sensex_tape_rebase_on_atm_move_points = max(
            1, int(sensex_tape_rebase_on_atm_move_points)
        )

        self._lock = threading.Lock()

        self._state = StreamState.DISCONNECTED
        self._state_entered_at = datetime.now()

        self._generation_seq = 0
        self._active_generation_id: int | None = None
        self._generations: dict[int, _GenerationInfo] = {}
        self._retiring_generation_ids: set[int] = set()
        self._retired_generation_ids: set[int] = set()

        self._last_reconnect_start_ts: datetime | None = None
        self._last_reconnect_success_ts: datetime | None = None
        self._last_reconnect_attempt: int | None = None

        self._forced_reconnect_reason: str | None = None
        self._forced_reconnect_details: dict[str, Any] = {}

        self._last_tick_at_any: datetime | None = None
        self._last_tick_at_index: datetime | None = None
        self._last_tick_at_future: datetime | None = None
        self._last_tick_at_option: datetime | None = None

        self._stale_since: datetime | None = None
        self._last_close_code: int | None = None
        self._last_close_reason: str | None = None
        self._last_error_code: int | None = None
        self._last_error_reason: str | None = None

        self._current_atm: int | None = None
        self._current_tape_atm: int | None = None
        self._desired_option_tokens: set[int] = set()
        self._desired_strategy_option_tokens: set[int] = set()
        self._desired_tape_option_tokens: set[int] = set()
        self._applied_option_tokens: set[int] = set()
        self._applied_strategy_option_tokens: set[int] = set()
        self._applied_tape_option_tokens: set[int] = set()
        self._subscriptions_applied_generation: int | None = None
        self._last_tape_rebase_ts: datetime | None = None

        self._rebase_candidate_atm: int | None = None
        self._rebase_candidate_count = 0
        self._last_rebase_ts: datetime | None = None

    @property
    def state(self) -> StreamState:
        with self._lock:
            return self._state

    @property
    def connected(self) -> bool:
        return bool(self.health_snapshot().get("connected"))

    @property
    def degraded(self) -> bool:
        return bool(self.health_snapshot().get("degraded"))

    @property
    def reconnect_in_progress(self) -> bool:
        return bool(self.health_snapshot().get("reconnecting"))

    @property
    def current_atm(self) -> int | None:
        with self._lock:
            return self._current_atm

    @property
    def option_lattice_size(self) -> int:
        with self._lock:
            return len(self._desired_option_tokens)

    @property
    def subscribed_token_count(self) -> int:
        with self._lock:
            return 2 + len(self._desired_option_tokens)

    def _strategy_option_tokens(self) -> set[int]:
        return set(getattr(self, "_desired_strategy_option_tokens", set()))

    def _tape_option_tokens(self) -> set[int]:
        return set(getattr(self, "_desired_tape_option_tokens", set()))

    def _combined_desired_option_tokens(self) -> set[int]:
        return self._strategy_option_tokens() | self._tape_option_tokens()

    def _build_tape_option_tokens_for_atm(self, atm: int, now: datetime) -> set[int]:
        if not bool(getattr(self, "enable_sensex_option_tape_recorder", False)):
            return set()
        metas = self.registry.option_tape_universe_for_atm(
            atm=atm,
            now=now,
            range_points=int(getattr(self, "sensex_tape_strike_range_points", 1500)),
            step_points=int(getattr(self, "sensex_tape_strike_step_points", 100)),
            expiry_mode=str(getattr(self, "sensex_tape_expiry_mode", "nearest")),
            include_ce=bool(getattr(self, "sensex_tape_include_ce", True)),
            include_pe=bool(getattr(self, "sensex_tape_include_pe", True)),
        )
        return {int(meta.instrument_token) for meta in metas}

    def start(self) -> None:
        self._start_new_generation(reason="start", reconnecting=False)

    def stop(self) -> None:
        logger.info("Stopping KiteTicker stream")
        with self._lock:
            infos = list(self._generations.values())
            self._generations.clear()
            self._retiring_generation_ids.clear()
            self._retired_generation_ids.clear()
            self._active_generation_id = None
        for info in infos:
            try:
                info.ticker.close()
            except Exception:
                logger.debug("Ticker close raised for generation=%s", info.generation_id, exc_info=True)
        self._transition_state(StreamState.DISCONNECTED, reason="stop", generation_id=None)

    def force_reconnect(self, reason: str, details: dict[str, Any] | None = None) -> bool:
        now = datetime.now()
        with self._lock:
            if self._state == StreamState.RECONNECTING:
                return False
            if self._last_reconnect_start_ts is not None:
                since = (now - self._last_reconnect_start_ts).total_seconds()
                if since < self.reconnect_cooldown_seconds:
                    return False
            self._last_reconnect_start_ts = now
            self._forced_reconnect_reason = reason
            self._forced_reconnect_details = dict(details or {})

        payload = {"timestamp": now.isoformat(), "reason": reason}
        payload.update(details or {})
        self._emit_event("FORCED_STREAM_RECONNECT_START", payload)
        logger.warning("Forced stream reconnect starting | reason=%s", reason)
        return self._start_new_generation(reason=f"forced_reconnect:{reason}", reconnecting=True)

    def mark_stale(self, reason: str, idle_seconds: float | None = None) -> None:
        with self._lock:
            active_gen = self._active_generation_id
            state = self._state
        if active_gen is None:
            return
        if state in {StreamState.LIVE, StreamState.CONNECTED_PENDING_FIRST_TICK}:
            extra = {"idle_seconds": idle_seconds} if idle_seconds is not None else None
            self._transition_state(StreamState.STALE, reason=f"watchdog:{reason}", generation_id=active_gen, extra=extra)

    def mark_recovered_from_stale(self, reason: str) -> None:
        with self._lock:
            active_gen = self._active_generation_id
            info = self._generations.get(active_gen) if active_gen is not None else None
            state = self._state
            subscriptions_ready = (
                info is not None
                and info.subscriptions_ready
                and self._subscriptions_applied_generation == active_gen
            )
            has_first_tick = info is not None and info.first_tick_at is not None
        if state == StreamState.STALE and active_gen is not None and subscriptions_ready and has_first_tick:
            self._transition_state(StreamState.LIVE, reason=f"recovered:{reason}", generation_id=active_gen)

    def health_snapshot(self, now: datetime | None = None) -> dict[str, Any]:
        current = now or datetime.now()
        with self._lock:
            state = self._state
            active_gen = self._active_generation_id
            info = self._generations.get(active_gen) if active_gen is not None else None
            state_entered_at = self._state_entered_at
            subscriptions_ready = (
                info is not None
                and info.subscriptions_ready
                and self._subscriptions_applied_generation == active_gen
            )
            first_tick_ready = info is not None and info.first_tick_at is not None
            connected = state in {
                StreamState.CONNECTED_PENDING_FIRST_TICK,
                StreamState.LIVE,
                StreamState.STALE,
            } and info is not None
            reconnecting = state == StreamState.RECONNECTING
            degraded = state != StreamState.LIVE

            last_any = self._last_tick_at_any
            last_index = self._last_tick_at_index

            return {
                "generation_id": active_gen,
                "stream_state": state.value,
                "connected": connected,
                "degraded": degraded,
                "reconnecting": reconnecting,
                "stale": state == StreamState.STALE,
                "active_generation_has_first_tick": first_tick_ready,
                "active_generation_subscriptions_ready": subscriptions_ready,
                "seconds_since_last_any_tick": (
                    (current - last_any).total_seconds() if last_any is not None else None
                ),
                "seconds_since_last_index_tick": (
                    (current - last_index).total_seconds() if last_index is not None else None
                ),
                "current_subscribed_token_count": 2 + len(self._desired_option_tokens),
                "desired_subscribed_count": 2 + len(self._desired_option_tokens),
                "active_applied_subscribed_count": 2 + len(self._applied_option_tokens),
                "current_option_lattice_size": len(self._desired_option_tokens),
                "current_atm_reference": self._current_atm,
                "strategy_option_lattice_size": len(getattr(self, "_desired_strategy_option_tokens", set())),
                "tape_option_lattice_size": len(getattr(self, "_desired_tape_option_tokens", set())),
                "current_tape_atm_reference": getattr(self, "_current_tape_atm", None),
                "tape_recorder_enabled": bool(getattr(self, "enable_sensex_option_tape_recorder", False)),
                "retiring_generations": sorted(self._retiring_generation_ids),
                "retiring_generations_count": len(self._retiring_generation_ids),
                "state_entered_at": state_entered_at.isoformat() if state_entered_at else None,
                "seconds_in_state": (
                    (current - state_entered_at).total_seconds() if state_entered_at is not None else None
                ),
            }

    def rebase_if_needed(self, spot_ltp: float, keep_tokens: Iterable[int] | None = None) -> bool:
        keep = {int(token) for token in (keep_tokens or set())}
        target_atm = self.registry.round_to_100(spot_ltp)
        now = datetime.now()

        with self._lock:
            old_atm = self._current_atm
            old_tape_atm = getattr(self, "_current_tape_atm", None)
            last_rebase_ts = self._last_rebase_ts
            candidate_atm = self._rebase_candidate_atm
            candidate_count = self._rebase_candidate_count
            state = self._state
            active_gen = self._active_generation_id
            info = self._generations.get(active_gen) if active_gen is not None else None
            active_ticker = info.ticker if info is not None else None
            existing_tape_tokens = set(getattr(self, "_desired_tape_option_tokens", set()))

        if old_atm is not None and abs(target_atm - old_atm) < self.rebase_min_move_points:
            with self._lock:
                self._rebase_candidate_atm = None
                self._rebase_candidate_count = 0
            return False

        if old_atm is not None and last_rebase_ts is not None and self.rebase_cooldown_seconds > 0:
            since = (now - last_rebase_ts).total_seconds()
            if since < self.rebase_cooldown_seconds:
                self._emit_event(
                    "LATTICE_REBASE_SKIPPED_COOLDOWN",
                    {
                        "timestamp": now.isoformat(),
                        "old_atm": old_atm,
                        "candidate_atm": target_atm,
                        "seconds_since_last_rebase": since,
                        "cooldown_seconds": self.rebase_cooldown_seconds,
                    },
                )
                return False

        if candidate_atm == target_atm:
            candidate_count += 1
        else:
            candidate_count = 1

        with self._lock:
            self._rebase_candidate_atm = target_atm
            self._rebase_candidate_count = candidate_count

        if candidate_count < self.rebase_persist_ticks:
            self._emit_event(
                "LATTICE_REBASE_SKIPPED_PERSISTENCE",
                {
                    "timestamp": now.isoformat(),
                    "old_atm": old_atm,
                    "candidate_atm": target_atm,
                    "persistence_count": candidate_count,
                    "required_persistence_ticks": self.rebase_persist_ticks,
                },
            )
            return False

        strategy_metas = self.registry.option_lattice_for_atm(atm=target_atm, now=now)
        new_strategy_tokens = {int(meta.instrument_token) for meta in strategy_metas}
        if not new_strategy_tokens and old_atm is not None:
            logger.warning("Option lattice empty for ATM=%s; keeping previous subscriptions", target_atm)
            return False

        tape_rebuilt = False
        new_tape_tokens = set(existing_tape_tokens)
        if bool(getattr(self, "enable_sensex_option_tape_recorder", False)):
            if old_tape_atm is None or abs(target_atm - old_tape_atm) >= int(
                getattr(self, "sensex_tape_rebase_on_atm_move_points", 100)
            ):
                new_tape_tokens = self._build_tape_option_tokens_for_atm(atm=target_atm, now=now)
                tape_rebuilt = True
        else:
            new_tape_tokens = set()

        new_option_tokens = new_strategy_tokens | new_tape_tokens

        with self._lock:
            old_tokens = set(self._desired_option_tokens)

        retained_old = old_tokens & keep
        unsubscribe_tokens = list(old_tokens - new_option_tokens - retained_old)
        subscribe_tokens = list(new_option_tokens - old_tokens)
        final_tokens = new_option_tokens | retained_old

        with self._lock:
            self._desired_strategy_option_tokens = set(new_strategy_tokens)
            self._desired_tape_option_tokens = set(new_tape_tokens)
            self._desired_option_tokens = set(final_tokens)
            self._current_atm = target_atm
            if bool(getattr(self, "enable_sensex_option_tape_recorder", False)):
                if tape_rebuilt:
                    self._current_tape_atm = target_atm
                    self._last_tape_rebase_ts = now
            else:
                self._current_tape_atm = None
                self._last_tape_rebase_ts = None
            self._rebase_candidate_atm = None
            self._rebase_candidate_count = 0
            self._last_rebase_ts = datetime.now()

        apply_now = state in {
            StreamState.CONNECTED_PENDING_FIRST_TICK,
            StreamState.LIVE,
            StreamState.STALE,
        } and active_ticker is not None

        if apply_now:
            try:
                if unsubscribe_tokens:
                    active_ticker.unsubscribe(unsubscribe_tokens)
                if subscribe_tokens:
                    active_ticker.subscribe(subscribe_tokens)
                    active_ticker.set_mode(active_ticker.MODE_FULL, subscribe_tokens)
                elif final_tokens:
                    active_ticker.set_mode(active_ticker.MODE_FULL, list(final_tokens))

                with self._lock:
                    self._applied_option_tokens = set(final_tokens)
                    self._applied_strategy_option_tokens = set(new_strategy_tokens)
                    self._applied_tape_option_tokens = set(new_tape_tokens)
                    if active_gen is not None:
                        self._subscriptions_applied_generation = active_gen
            except Exception as exc:
                self._emit_event(
                    "LATTICE_REBASE_ERROR",
                    {
                        "timestamp": datetime.now().isoformat(),
                        "old_atm": old_atm,
                        "candidate_atm": target_atm,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                logger.exception("Lattice rebase error")
                return False

        if bool(getattr(self, "enable_sensex_option_tape_recorder", False)) and tape_rebuilt:
            self._emit_event(
                "SENSEX_TAPE_REBASE",
                {
                    "timestamp": now.isoformat(),
                    "old_tape_atm": old_tape_atm,
                    "new_tape_atm": target_atm,
                    "tape_token_count": len(new_tape_tokens),
                    "strategy_token_count": len(new_strategy_tokens),
                    "combined_option_token_count": len(final_tokens),
                },
            )

        logger.info(
            "Lattice rebased | old_atm=%s | new_atm=%s | subscribed=%d | unsubscribed=%d | kept=%d",
            old_atm,
            target_atm,
            len(subscribe_tokens),
            len(unsubscribe_tokens),
            len(keep),
        )
        return True

    def _new_ticker(self) -> KiteTicker:
        return KiteTicker(api_key=self.api_key, access_token=self.access_token, reconnect=True)

    def _start_new_generation(self, reason: str, reconnecting: bool) -> bool:
        now = datetime.now()
        old_info: _GenerationInfo | None = None
        with self._lock:
            old_gen = self._active_generation_id
            if old_gen is not None:
                old_info = self._generations.get(old_gen)
                self._retiring_generation_ids.add(old_gen)

            self._generation_seq += 1
            new_gen = self._generation_seq
            ticker = self._new_ticker()
            self._bind_callbacks(ticker, new_gen)

            self._generations[new_gen] = _GenerationInfo(
                generation_id=new_gen,
                ticker=ticker,
                started_at=now,
            )
            self._active_generation_id = new_gen

        self._transition_state(
            StreamState.RECONNECTING if reconnecting else StreamState.CONNECTING,
            reason=reason,
            generation_id=new_gen,
        )

        if old_info is not None:
            try:
                old_info.ticker.close()
            except Exception:
                logger.debug("Failed to close retiring generation=%s", old_info.generation_id, exc_info=True)

        try:
            ticker.connect(threaded=True)
            return True
        except Exception as exc:
            logger.exception("Failed to connect generation=%s", new_gen)
            self._emit_event(
                "FORCED_STREAM_RECONNECT_FAILED" if reconnecting else "STREAM_CONNECT_FAILED",
                {
                    "timestamp": datetime.now().isoformat(),
                    "generation_id": new_gen,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "reason": reason,
                },
            )
            self._transition_state(StreamState.DISCONNECTED, reason="connect_failed", generation_id=new_gen)
            return False

    def _bind_callbacks(self, ticker: KiteTicker, generation_id: int) -> None:
        def _on_connect(ws: KiteTicker, response: dict, *, _g: int = generation_id) -> None:
            self._handle_on_connect(ws=ws, response=response, generation_id=_g)

        def _on_ticks(ws: KiteTicker, ticks: list[dict], *, _g: int = generation_id) -> None:
            self._handle_on_ticks(ws=ws, ticks=ticks, generation_id=_g)

        def _on_close(
            ws: KiteTicker,
            code: int | None,
            reason: str | None,
            *,
            _g: int = generation_id,
        ) -> None:
            self._handle_on_close(ws=ws, code=code, reason=reason, generation_id=_g)

        def _on_reconnect(ws: KiteTicker, attempts_count: int, *, _g: int = generation_id) -> None:
            self._handle_on_reconnect(ws=ws, attempts_count=attempts_count, generation_id=_g)

        def _on_error(
            ws: KiteTicker,
            code: int | None,
            reason: str | None,
            *,
            _g: int = generation_id,
        ) -> None:
            self._handle_on_error(ws=ws, code=code, reason=reason, generation_id=_g)

        def _on_noreconnect(ws: KiteTicker, *, _g: int = generation_id) -> None:
            self._handle_on_noreconnect(ws=ws, generation_id=_g)

        ticker.on_connect = _on_connect
        ticker.on_ticks = _on_ticks
        ticker.on_close = _on_close
        ticker.on_reconnect = _on_reconnect
        ticker.on_error = _on_error
        ticker.on_noreconnect = _on_noreconnect

    def _handle_on_connect(self, ws: KiteTicker, response: dict, generation_id: int) -> None:
        _ = response
        if self._ignore_stale_callback("on_connect", generation_id):
            return

        with self._lock:
            info = self._generations.get(generation_id)
            if info is None:
                return
            info.connected_at = datetime.now()

        self._transition_state(
            StreamState.CONNECTED_PENDING_FIRST_TICK,
            reason="on_connect",
            generation_id=generation_id,
        )

        try:
            self._apply_subscriptions_for_generation(ws=ws, generation_id=generation_id)
        except Exception as exc:
            self._emit_event(
                "STREAM_SUBSCRIPTIONS_ERROR",
                {
                    "timestamp": datetime.now().isoformat(),
                    "generation_id": generation_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            logger.exception("Subscription application failed for generation=%s", generation_id)
            self._transition_state(
                StreamState.STALE,
                reason="subscription_error",
                generation_id=generation_id,
            )

        logger.info("Kite stream connected | generation=%s", generation_id)

        if self.on_connect_state_cb is not None:
            self.on_connect_state_cb()

    def _apply_subscriptions_for_generation(self, ws: KiteTicker, generation_id: int) -> None:
        base_tokens = self.registry.initial_tokens()
        ws.subscribe(base_tokens)

        index_token = self.registry.index_meta.instrument_token
        future_token = self.registry.future_meta.instrument_token
        ws.set_mode(ws.MODE_QUOTE, [index_token])
        ws.set_mode(ws.MODE_FULL, [future_token])

        with self._lock:
            desired_tokens = sorted(self._desired_option_tokens)
            current_atm = self._current_atm
            strategy_tokens = sorted(getattr(self, "_desired_strategy_option_tokens", set()))
            tape_tokens = sorted(getattr(self, "_desired_tape_option_tokens", set()))

        if not desired_tokens:
            atm_hint = current_atm if current_atm is not None else self.registry.initial_atm_hint()
            if atm_hint is not None:
                strategy_metas = self.registry.option_lattice_for_atm(atm=atm_hint, now=datetime.now())
                strategy_tokens = [int(meta.instrument_token) for meta in strategy_metas]
                tape_tokens = sorted(self._build_tape_option_tokens_for_atm(atm=atm_hint, now=datetime.now()))
                desired_tokens = sorted(set(strategy_tokens) | set(tape_tokens))
                with self._lock:
                    self._desired_strategy_option_tokens = set(strategy_tokens)
                    self._desired_tape_option_tokens = set(tape_tokens)
                    self._desired_option_tokens = set(desired_tokens)
                    self._current_atm = atm_hint
                    if bool(getattr(self, "enable_sensex_option_tape_recorder", False)):
                        self._current_tape_atm = atm_hint
                        self._last_tape_rebase_ts = datetime.now()

        if desired_tokens:
            ws.subscribe(desired_tokens)
            ws.set_mode(ws.MODE_FULL, desired_tokens)

        with self._lock:
            info = self._generations.get(generation_id)
            if info is None:
                return
            info.subscriptions_ready = True
            info.subscriptions_applied_at = datetime.now()
            self._applied_option_tokens = set(desired_tokens)
            self._applied_strategy_option_tokens = set(strategy_tokens)
            self._applied_tape_option_tokens = set(tape_tokens)
            self._subscriptions_applied_generation = generation_id

        self._emit_event(
            "STREAM_SUBSCRIPTIONS_APPLIED",
            {
                "timestamp": datetime.now().isoformat(),
                "generation_id": generation_id,
                "base_count": len(base_tokens),
                "option_count": len(desired_tokens),
                "strategy_option_count": len(strategy_tokens),
                "tape_option_count": len(tape_tokens),
                "total_count": len(base_tokens) + len(desired_tokens),
            },
        )
        logger.info(
            "Stream subscriptions applied | gen=%s | base=%s | options=%s | total=%s",
            generation_id,
            len(base_tokens),
            len(desired_tokens),
            len(base_tokens) + len(desired_tokens),
        )

    def _handle_on_ticks(self, ws: KiteTicker, ticks: list[dict], generation_id: int) -> None:
        _ = ws
        if self._ignore_stale_callback("on_ticks", generation_id):
            return

        received_at = datetime.now()
        first_tick_accepted = False

        for raw in ticks:
            normalized = self.normalizer.normalize(raw_tick=raw, timestamp_receive=received_at)
            if normalized is None:
                continue

            with self._lock:
                self._last_tick_at_any = received_at
                source = str(normalized.get("source", "")).lower()
                if source == "index":
                    self._last_tick_at_index = received_at
                elif source == "future":
                    self._last_tick_at_future = received_at
                elif source == "option":
                    self._last_tick_at_option = received_at

                info = self._generations.get(generation_id)
                if info is not None and info.first_tick_at is None:
                    info.first_tick_at = received_at
                    first_tick_accepted = True

            self.router.route(normalized)

        if not first_tick_accepted:
            return

        with self._lock:
            info = self._generations.get(generation_id)
            subscriptions_ready = (
                info is not None
                and info.subscriptions_ready
                and self._subscriptions_applied_generation == generation_id
            )
            current_state = self._state

        self._emit_event(
            "STREAM_FIRST_TICK",
            {
                "timestamp": received_at.isoformat(),
                "generation_id": generation_id,
                "subscriptions_ready": subscriptions_ready,
            },
        )
        logger.info(
            "Stream first tick received | gen=%s | subscriptions_ready=%s",
            generation_id,
            subscriptions_ready,
        )

        if subscriptions_ready and current_state in {
            StreamState.CONNECTED_PENDING_FIRST_TICK,
            StreamState.STALE,
        }:
            self._transition_state(
                StreamState.LIVE,
                reason="first_tick_after_subscriptions",
                generation_id=generation_id,
            )
            self._retire_non_active_generations()
            self._mark_forced_reconnect_success_if_needed(generation_id)

    def _handle_on_close(
        self,
        ws: KiteTicker,
        code: int | None,
        reason: str | None,
        generation_id: int,
    ) -> None:
        _ = ws
        if self._ignore_stale_callback("on_close", generation_id, code=code, reason=reason):
            return

        with self._lock:
            self._last_close_code = code
            self._last_close_reason = reason
            state = self._state

        logger.warning("Kite stream closed | gen=%s | code=%s | reason=%s", generation_id, code, reason)
        self._emit_event(
            "STREAM_CLOSED",
            {
                "timestamp": datetime.now().isoformat(),
                "generation_id": generation_id,
                "code": code,
                "reason": reason,
            },
        )

        next_state = StreamState.RECONNECTING if state == StreamState.RECONNECTING else StreamState.DISCONNECTED
        self._transition_state(next_state, reason="on_close", generation_id=generation_id)

        if self.on_disconnect_cb is not None:
            self.on_disconnect_cb(code, reason)

    def _handle_on_reconnect(self, ws: KiteTicker, attempts_count: int, generation_id: int) -> None:
        _ = ws
        if self._ignore_stale_callback("on_reconnect", generation_id):
            return

        with self._lock:
            self._last_reconnect_attempt = int(attempts_count)

        logger.warning("Kite stream reconnect attempt=%s | gen=%s", attempts_count, generation_id)
        if self.on_reconnect_cb is not None:
            self.on_reconnect_cb(attempts_count)

    def _handle_on_error(
        self,
        ws: KiteTicker,
        code: int | None,
        reason: str | None,
        generation_id: int,
    ) -> None:
        _ = ws
        if self._ignore_stale_callback("on_error", generation_id, code=code, reason=reason):
            return

        with self._lock:
            self._last_error_code = code
            self._last_error_reason = reason
            state = self._state

        logger.error("Kite stream error | gen=%s | code=%s | reason=%s", generation_id, code, reason)
        self._emit_event(
            "STREAM_ERROR",
            {
                "timestamp": datetime.now().isoformat(),
                "generation_id": generation_id,
                "code": code,
                "reason": reason,
                "reconnect_attempt": self._last_reconnect_attempt,
            },
        )

        next_state = StreamState.RECONNECTING if state == StreamState.RECONNECTING else StreamState.STALE
        self._transition_state(next_state, reason="on_error", generation_id=generation_id)

    def _handle_on_noreconnect(self, ws: KiteTicker, generation_id: int) -> None:
        _ = ws
        if self._ignore_stale_callback("on_noreconnect", generation_id):
            return

        logger.error("Kite stream gave up reconnecting | gen=%s", generation_id)
        self._emit_event(
            "STREAM_NORECONNECT",
            {
                "timestamp": datetime.now().isoformat(),
                "generation_id": generation_id,
                "reconnect_attempt": self._last_reconnect_attempt,
                "last_error": self._last_error_reason,
            },
        )

        self._transition_state(StreamState.DISCONNECTED, reason="on_noreconnect", generation_id=generation_id)
        if self._forced_reconnect_reason is not None:
            payload = {
                "timestamp": datetime.now().isoformat(),
                "reason": self._forced_reconnect_reason,
                "generation_id": generation_id,
            }
            payload.update(self._forced_reconnect_details)
            self._emit_event("FORCED_STREAM_RECONNECT_FAILED", payload)
            self._forced_reconnect_reason = None
            self._forced_reconnect_details = {}

    def _ignore_stale_callback(
        self,
        callback_name: str,
        generation_id: int,
        code: int | None = None,
        reason: str | None = None,
    ) -> bool:
        with self._lock:
            active_gen = self._active_generation_id
        if generation_id == active_gen:
            return False

        logger.info(
            "Ignoring stale websocket callback | callback=%s | callback_gen=%s | active_gen=%s | code=%s | reason=%s",
            callback_name,
            generation_id,
            active_gen,
            code,
            reason,
        )
        return True

    def _transition_state(
        self,
        new_state: StreamState,
        *,
        reason: str,
        generation_id: int | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now()
        with self._lock:
            old_state = self._state
            if old_state == new_state:
                return
            self._state = new_state
            self._state_entered_at = now
            if new_state == StreamState.STALE and self._stale_since is None:
                self._stale_since = now
            elif new_state != StreamState.STALE:
                self._stale_since = None

        logger.info(
            "Stream state transition | gen=%s | %s -> %s | reason=%s",
            generation_id,
            old_state.value,
            new_state.value,
            reason,
        )

        payload = {
            "timestamp": now.isoformat(),
            "generation_id": generation_id,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "reason": reason,
        }
        if extra:
            payload.update(extra)
        self._emit_event("STREAM_STATE_TRANSITION", payload)

    def _retire_non_active_generations(self) -> None:
        with self._lock:
            active_gen = self._active_generation_id
            retiring = [gid for gid in self._generations if gid != active_gen]
            infos = [self._generations.pop(gid) for gid in retiring]
            self._retiring_generation_ids.difference_update(retiring)
            self._retired_generation_ids.update(retiring)

        for info in infos:
            try:
                info.ticker.close()
            except Exception:
                logger.debug("Failed to close retired generation=%s", info.generation_id, exc_info=True)

    def _mark_forced_reconnect_success_if_needed(self, generation_id: int) -> None:
        with self._lock:
            reason = self._forced_reconnect_reason
            details = dict(self._forced_reconnect_details)
            if reason is None:
                return
            self._last_reconnect_success_ts = datetime.now()
            self._forced_reconnect_reason = None
            self._forced_reconnect_details = {}

        payload = {
            "timestamp": datetime.now().isoformat(),
            "generation_id": generation_id,
            "reason": reason,
            "current_atm": self.current_atm,
            "option_lattice_size": self.option_lattice_size,
            "subscribed_token_count": self.subscribed_token_count,
        }
        payload.update(details)
        self._emit_event("FORCED_STREAM_RECONNECT_SUCCESS", payload)
        logger.info("Reconnect generation promoted to live | new_gen=%s", generation_id)

    def _emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(event_type, payload)
        except Exception:
            logger.debug("Failed to emit stream event %s", event_type, exc_info=True)
