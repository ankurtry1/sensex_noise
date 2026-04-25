from __future__ import annotations

import json
from pathlib import Path

from analysis_pipeline.config import PipelineConfig
from analysis_pipeline.reconciliation import reconcile_trades


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row) + "\n")


def test_reconciliation_matches_enriched_events_ticks(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    trade_id = "20260410T092001|BFO:OPT|CONTINUATION_CALL|CALL"

    _write_jsonl(
        logs / "trades" / "2026-04-10.trades_enriched.jsonl",
        [
            {
                "trade_id": trade_id,
                "symbol": "BFO:OPT",
                "signal_kind": "CONTINUATION_CALL",
                "side": "CALL",
                "entry_fill_time": "2026-04-10T09:20:01",
                "exit_fill_time": "2026-04-10T09:20:05",
                "entry_price": 100,
                "exit_price": 103,
                "gross_pnl": 3,
                "net_pnl": 3,
                "holding_seconds": 4,
                "closing_reason": "TARGET_HIT",
            }
        ],
    )

    _write_jsonl(
        logs / "events" / "2026-04-10.events.jsonl",
        [
            {"timestamp": "2026-04-10T09:20:01", "event_type": "TRADE_ENTERED", "payload": {"trade_id": trade_id}},
            {"timestamp": "2026-04-10T09:20:05", "event_type": "TRADE_EXITED", "payload": {"trade_id": trade_id}},
        ],
    )

    _write_jsonl(
        logs / "trade_ticks" / "2026-04-10" / "trade_1.jsonl",
        [
            {
                "trade_id": trade_id,
                "timestamp_exchange": "2026-04-10T09:20:02",
                "source": "option",
                "symbol": "BFO:OPT",
                "instrument_token": 1,
                "ltp": 101,
            }
        ],
    )

    _write_jsonl(
        logs / "ticks" / "2026-04-10" / "sensex.jsonl",
        [{"timestamp_exchange": "2026-04-10T09:20:02", "ltp": 77000}],
    )
    _write_jsonl(
        logs / "ticks" / "2026-04-10" / "futures.jsonl",
        [{"timestamp_exchange": "2026-04-10T09:20:02", "ltp": 77010}],
    )

    cfg = PipelineConfig(repo_root=tmp_path, output_dir=tmp_path / "analysis")
    result = reconcile_trades(cfg)

    assert not result.reconciled_df.empty
    row = result.reconciled_df.iloc[0]
    assert row["trade_id"] == trade_id
    assert bool(row["matched_enriched"])
    assert bool(row["matched_events"])
    assert bool(row["matched_trade_ticks"])
    assert row["match_status"] == "reconciled"
