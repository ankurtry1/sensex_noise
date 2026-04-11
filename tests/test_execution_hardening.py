from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sensex_noise.broker.kite_paper import KitePaperBroker
from sensex_noise.models import Position, SignalSide
from sensex_noise.services.engine import StrategyEngine
from sensex_noise.services.trade_journal import TradeJournal


class _DummyJournal:
    def append(self, event_type: str, payload: dict) -> None:
        _ = (event_type, payload)

    def append_event(self, event_type: str, payload: dict) -> None:
        _ = (event_type, payload)


class _FakeBroker:
    def __init__(self) -> None:
        self.cancel_calls = 0
        self.place_calls = 0

    def cancel_order(self, variety: str, order_id: str) -> str:
        self.cancel_calls += 1
        return order_id

    def place_exit_limit(self, symbol: str, quantity: int, price: float, product: str) -> str:
        self.place_calls += 1
        return "NEW-TARGET-ORDER"

    def is_order_modifiable(self, order_id: str, variety: str) -> bool:
        return False

    def modify_order(self, variety: str, order_id: str, params: dict) -> str:
        raise RuntimeError("modify unavailable")

    def get_order(self, order_id: str) -> dict | None:
        return {
            "order_id": order_id,
            "status": "OPEN",
            "pending_quantity": 20,
            "filled_quantity": 0,
            "quantity": 20,
            "price": 105.0,
        }



def _build_position() -> Position:
    now = datetime(2026, 3, 22, 10, 0, 0)
    return Position(
        side=SignalSide.CALL,
        option_symbol="BFO:SENSEX26MAR77900CE",
        product="MIS",
        underlying_spot=78000.0,
        entry_price=100.0,
        target_price=103.0,
        quantity=20,
        strike=77900,
        expiry=datetime(2026, 3, 26, 0, 0, 0),
        entry_time=now,
        signal_kind="CONTINUATION_CALL",
        trade_id="T1",
    )


def test_exit_precedence_single_selection() -> None:
    engine = StrategyEngine.__new__(StrategyEngine)
    candidates = ["TARGET_HIT", "HARD_STOP_EXIT", "MANUAL_LIMIT_HIT", "MANUAL_EXIT"]
    selected = engine._select_exit_reason(candidates)
    assert selected == "MANUAL_EXIT"


def test_position_closing_blocks_additional_exit_logic() -> None:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.manual_exit_requested = True
    position = _build_position()
    position.closing = True

    candidates = engine._collect_exit_candidates(
        position=position,
        option_quote={"ltp": 90.0},
        mark_time=position.entry_time,
    )
    assert candidates == []


def test_paper_broker_modify_order_updates_target_order() -> None:
    broker = KitePaperBroker(api_key="k", access_token="t", capital_budget=100000)
    order_id = broker.place_exit_limit(
        symbol="BFO:SENSEX26MAR77900CE",
        quantity=20,
        price=103.0,
        product="MIS",
    )

    assert broker.is_order_modifiable(order_id=order_id, variety="regular") is True
    broker.modify_order(variety="regular", order_id=order_id, params={"price": 101.5})
    order = broker.get_order(order_id)
    assert order is not None
    assert float(order["price"]) == 101.5


def test_target_reprice_falls_back_when_modify_unavailable() -> None:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = SimpleNamespace(
        enable_dynamic_risky_target=True,
        risky_target_points=2.0,
        strict_after_1pm_risky_target_points=2.0,
        enable_target_reprice_modify=True,
        enable_target_reprice_fallback_cancel_replace=True,
        target_reprice_debounce_seconds=0,
        order_product="MIS",
    )
    engine.journal = _DummyJournal()
    engine.broker = _FakeBroker()
    engine.open_trade_id = "T1"
    engine.active_exit_order_type = "TARGET"
    engine.active_exit_order_id = "OLD-TARGET-ORDER"
    engine.active_exit_order_variety = "regular"
    engine.active_exit_price = 103.0
    engine.active_exit_order_sent_time = None
    engine.active_exit_order_ack_time = None

    position = _build_position()
    position.fragile = True
    position.current_price = 99.0
    position.target_price = 103.0
    position.target_points = 3.0
    engine.open_position = position

    engine._maybe_reprice_target_for_fragile(position)

    assert engine.broker.cancel_calls == 1
    assert engine.broker.place_calls == 1
    assert engine.active_exit_order_id == "NEW-TARGET-ORDER"
    assert position.target_points == 2.0
    assert position.target_reprice_count >= 1


def test_entry_exit_lag_and_slippage_fields_present(tmp_path: Path) -> None:
    event_path = tmp_path / "events.jsonl"
    enriched_path = tmp_path / "trades_enriched.jsonl"
    journal = TradeJournal(path=event_path, event_path=event_path, enriched_trade_path=enriched_path)

    position = _build_position()
    position.signal_time = datetime(2026, 3, 22, 9, 59, 55)
    position.signal_seen_time = datetime(2026, 3, 22, 10, 0, 0)
    position.entry_decision_time = datetime(2026, 3, 22, 10, 0, 1)
    position.entry_reference_price = 100.2
    position.entry_fill_time = datetime(2026, 3, 22, 10, 0, 2)
    position.entry_slippage_points = -0.2
    position.entry_lag_seconds = 2.0

    position.exit_reason = "TARGET_HIT"
    position.closing_reason = "TARGET_HIT"
    position.exit_decision_time = datetime(2026, 3, 22, 10, 0, 10)
    position.exit_trigger_reference_price = 102.8
    position.exit_fill_time = datetime(2026, 3, 22, 10, 0, 12)
    position.exit_time = position.exit_fill_time
    position.exit_price = 103.0
    position.exit_slippage_points = 0.2
    position.exit_lag_seconds = 2.0
    position.status = "CLOSED"

    journal.append_trade_summary(position=position)

    lines = enriched_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])

    assert "entry_reference_price" in row
    assert "entry_slippage_points" in row
    assert "entry_lag_seconds" in row
    assert "exit_trigger_reference_price" in row
    assert "exit_slippage_points" in row
    assert "exit_lag_seconds" in row


def test_hard_stop_does_not_trigger_before_arm_window() -> None:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = SimpleNamespace(enable_hard_stop=True, hard_stop_arm_after_seconds=30)
    position = _build_position()
    position.entry_price = 100.0
    position.hard_stop_points_used = 8.0

    triggered = engine._should_hard_stop(
        position=position,
        mark_time=position.entry_time + timedelta(seconds=20),
        option_ltp=88.0,
    )
    assert triggered is False


def test_hard_stop_triggers_after_arm_window() -> None:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = SimpleNamespace(enable_hard_stop=True, hard_stop_arm_after_seconds=30)
    position = _build_position()
    position.entry_price = 100.0
    position.hard_stop_points_used = 8.0

    triggered = engine._should_hard_stop(
        position=position,
        mark_time=position.entry_time + timedelta(seconds=35),
        option_ltp=88.0,
    )
    assert triggered is True


def test_hard_stop_active_exactly_at_arm_boundary() -> None:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = SimpleNamespace(enable_hard_stop=True, hard_stop_arm_after_seconds=30)
    position = _build_position()
    position.entry_price = 100.0
    position.hard_stop_points_used = 8.0

    triggered = engine._should_hard_stop(
        position=position,
        mark_time=position.entry_time + timedelta(seconds=30),
        option_ltp=88.0,
    )
    assert triggered is True


def test_hard_stop_arm_zero_preserves_immediate_behavior() -> None:
    engine = StrategyEngine.__new__(StrategyEngine)
    engine.settings = SimpleNamespace(enable_hard_stop=True, hard_stop_arm_after_seconds=0)
    position = _build_position()
    position.entry_price = 100.0
    position.hard_stop_points_used = 8.0

    triggered = engine._should_hard_stop(
        position=position,
        mark_time=position.entry_time + timedelta(seconds=5),
        option_ltp=88.0,
    )
    assert triggered is True
