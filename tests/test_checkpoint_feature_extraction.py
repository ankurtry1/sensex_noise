from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from analysis_pipeline.trade_path import TradePathLoader
from analysis_pipeline.checkpoint_features import build_checkpoint_features


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row) + "\n")


def test_checkpoint_features_from_trade_scoped_tape(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    trade_id = "20260410T092001|BFO:OPT|CONTINUATION_CALL|CALL"
    trade_path = logs / "trade_ticks" / "2026-04-10" / "trade_1.jsonl"

    _write_jsonl(
        trade_path,
        [
            {"trade_id": trade_id, "phase": "PRE_ENTRY", "timestamp_exchange": "2026-04-10T09:20:00.500000", "source": "option", "symbol": "BFO:OPT", "ltp": 100, "best_bid": 99.5, "best_ask": 100.5, "spread": 1.0, "bid[5]": [{"price": 99.5, "quantity": 10}], "ask[5]": [{"price": 100.5, "quantity": 10}]},
            {"trade_id": trade_id, "phase": "IN_TRADE", "timestamp_exchange": "2026-04-10T09:20:01.000000", "source": "option", "symbol": "BFO:OPT", "ltp": 101, "best_bid": 100.5, "best_ask": 101.5, "spread": 1.0, "bid[5]": [{"price": 100.5, "quantity": 12}], "ask[5]": [{"price": 101.5, "quantity": 8}]},
            {"trade_id": trade_id, "phase": "IN_TRADE", "timestamp_exchange": "2026-04-10T09:20:02.000000", "source": "option", "symbol": "BFO:OPT", "ltp": 103, "best_bid": 102.5, "best_ask": 103.5, "spread": 1.0, "bid[5]": [{"price": 102.5, "quantity": 11}], "ask[5]": [{"price": 103.5, "quantity": 9}]},
            {"trade_id": trade_id, "phase": "IN_TRADE", "timestamp_exchange": "2026-04-10T09:20:01.000000", "source": "index", "symbol": "BSE:SENSEX", "ltp": 77000},
            {"trade_id": trade_id, "phase": "IN_TRADE", "timestamp_exchange": "2026-04-10T09:20:02.000000", "source": "future", "symbol": "BFO:SENSEXFUT", "ltp": 77010},
        ],
    )

    reconciled = pd.DataFrame(
        [
            {
                "trade_id": trade_id,
                "date": "2026-04-10",
                "symbol": "BFO:OPT",
                "signal_kind": "CONTINUATION_CALL",
                "side": "CALL",
                "entry_time": "2026-04-10T09:20:01.000000",
                "exit_time": "2026-04-10T09:20:05.000000",
                "entry_price": 100.0,
                "exit_price": 103.0,
                "net_pnl": 3.0,
                "hold_seconds": 4.0,
                "exit_reason": "TARGET_HIT",
                "match_status": "reconciled",
                "trade_tick_path": str(trade_path),
                "pre_or_post_1pm": "PRE_1PM",
            }
        ]
    )

    loader = TradePathLoader(logs_dir=logs)
    features, long_df, _ = build_checkpoint_features(reconciled, loader)

    assert not features.empty
    row = features.iloc[0]
    assert row["trade_id"] == trade_id
    assert row["feature_extraction_status"] == "OK"
    assert row["pnl_1s"] >= 0
    assert not long_df.empty
