from __future__ import annotations

import json
from pathlib import Path

from analysis_pipeline.config import PipelineConfig
from analysis_pipeline.inventory import build_inventory
from analysis_pipeline.io_utils import parse_timestamp


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row) + "\n")


def test_parse_timestamp_supports_iso_and_epoch() -> None:
    assert parse_timestamp("2026-04-10T09:20:01.123456") is not None
    assert parse_timestamp(1712728201) is not None
    assert parse_timestamp("1712728201000") is not None


def test_inventory_detects_daywise_coverage(tmp_path: Path) -> None:
    logs = tmp_path / "logs"

    _write_jsonl(
        logs / "trades" / "2026-04-10.trades_enriched.jsonl",
        [
            {
                "trade_id": "20260410T092001|OPT|CONTINUATION_CALL|CALL",
                "entry_fill_time": "2026-04-10T09:20:01.100000",
                "exit_fill_time": "2026-04-10T09:20:05.200000",
                "entry_price": 100,
                "exit_price": 103,
                "net_pnl": 3,
            }
        ],
    )
    _write_jsonl(
        logs / "events" / "2026-04-10.events.jsonl",
        [{"timestamp": "2026-04-10T09:20:00", "event_type": "TRADE_ENTERED", "payload": {"trade_id": "x"}}],
    )
    _write_jsonl(
        logs / "ticks" / "2026-04-10" / "sensex.jsonl",
        [
            {
                "timestamp_exchange": "2026-04-10T09:20:00.100000",
                "symbol": "BSE:SENSEX",
                "instrument_token": 265,
                "ltp": 77000,
                "best_bid": None,
                "best_ask": None,
                "bid[5]": [],
                "ask[5]": [],
            }
        ],
    )
    _write_jsonl(
        logs / "ticks" / "2026-04-10" / "futures.jsonl",
        [
            {
                "timestamp_exchange": "2026-04-10T09:20:00",
                "symbol": "BFO:SENSEXFUT",
                "instrument_token": 123,
                "ltp": 77010,
                "best_bid": 77009,
                "best_ask": 77011,
                "bid[5]": [{"price": 77009, "quantity": 10}],
                "ask[5]": [{"price": 77011, "quantity": 10}],
            }
        ],
    )
    _write_jsonl(
        logs / "trade_ticks" / "2026-04-10" / "trade_a.jsonl",
        [
            {
                "trade_id": "20260410T092001|OPT|CONTINUATION_CALL|CALL",
                "phase": "IN_TRADE",
                "timestamp_exchange": "2026-04-10T09:20:02.000000",
                "source": "option",
                "instrument_token": 1,
                "ltp": 101,
            }
        ],
    )

    cfg = PipelineConfig(repo_root=tmp_path, output_dir=tmp_path / "analysis")
    inv_df, summary, _ = build_inventory(cfg)

    assert not inv_df.empty
    row = inv_df[inv_df["date"] == "2026-04-10"].iloc[0]
    assert bool(row["has_trades_enriched"])
    assert bool(row["has_events_log"])
    assert bool(row["has_sensex_ticks"])
    assert bool(row["has_trade_scoped_ticks"])
    assert row["trade_tick_file_count"] == 1
    assert summary["dates_total"] >= 1
