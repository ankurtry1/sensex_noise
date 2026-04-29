from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from sensex_noise.persistence.tick_journal import TickJournal
from sensex_noise.replay.option_tape_loader import iter_sensex_option_ticks
from sensex_noise.streaming.tick_normalizer import TickNormalizer
from sensex_noise.streaming.token_registry import TokenRegistry


def _build_instruments() -> pd.DataFrame:
    expiry = datetime(2026, 4, 30)
    rows: list[dict[str, object]] = [
        {
            "exchange": "BSE",
            "tradingsymbol": "SENSEX",
            "name": "SENSEX",
            "instrument_type": "INDEX",
            "expiry": None,
            "segment": "BSE-INDEX",
            "instrument_token": 1,
            "strike": None,
            "lot_size": None,
            "last_price": 80000.0,
        },
        {
            "exchange": "BFO",
            "tradingsymbol": "SENSEX26APR-FUT",
            "name": "SENSEX",
            "instrument_type": "FUT",
            "expiry": expiry,
            "segment": "BFO-FUT",
            "instrument_token": 2,
            "strike": None,
            "lot_size": 20,
            "last_price": 80010.0,
        },
    ]

    token = 1000
    for strike in range(78500, 81501, 100):
        for option_type in ("CE", "PE"):
            token += 1
            rows.append(
                {
                    "exchange": "BFO",
                    "tradingsymbol": f"SENSEX26APR{strike}{option_type}",
                    "name": "SENSEX",
                    "instrument_type": option_type,
                    "expiry": expiry,
                    "segment": "BFO-OPT",
                    "instrument_token": token,
                    "strike": strike,
                    "lot_size": 20,
                    "last_price": 100.0,
                }
            )
    return pd.DataFrame(rows)


def test_option_tape_universe_for_atm_supports_wide_lattice() -> None:
    registry = TokenRegistry(instruments=_build_instruments())
    now = datetime(2026, 4, 24, 10, 0, 0)

    narrow = registry.option_tape_universe_for_atm(atm=80000, now=now, range_points=300, step_points=100)
    wide = registry.option_tape_universe_for_atm(atm=80000, now=now, range_points=1500, step_points=100)
    ce_only = registry.option_tape_universe_for_atm(
        atm=80000,
        now=now,
        range_points=300,
        step_points=100,
        include_ce=True,
        include_pe=False,
    )
    pe_only = registry.option_tape_universe_for_atm(
        atm=80000,
        now=now,
        range_points=300,
        step_points=100,
        include_ce=False,
        include_pe=True,
    )

    assert len(narrow) == 14
    assert len(wide) == 62
    assert len(ce_only) == 7
    assert len(pe_only) == 7
    assert {meta.option_type for meta in ce_only} == {"CE"}
    assert {meta.option_type for meta in pe_only} == {"PE"}


def test_option_tape_universe_rejects_unsupported_expiry_mode() -> None:
    registry = TokenRegistry(instruments=_build_instruments())

    try:
        registry.option_tape_universe_for_atm(
            atm=80000,
            now=datetime(2026, 4, 24, 10, 0, 0),
            expiry_mode="all",
        )
    except ValueError as exc:
        assert "expiry_mode" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported expiry_mode")


def test_tick_normalizer_includes_option_metadata() -> None:
    registry = TokenRegistry(instruments=_build_instruments())
    normalizer = TickNormalizer(registry=registry)
    meta = registry.option_tape_universe_for_atm(
        atm=80000,
        now=datetime(2026, 4, 24, 10, 0, 0),
        range_points=0,
    )[0]

    tick = normalizer.normalize(
        raw_tick={
            "instrument_token": meta.instrument_token,
            "last_price": 123.45,
            "last_traded_quantity": 5,
            "volume_traded": 100,
            "oi": 50,
            "timestamp": datetime(2026, 4, 24, 10, 0, 1),
            "depth": {
                "buy": [{"price": 123.0, "quantity": 10, "orders": 1}],
                "sell": [{"price": 124.0, "quantity": 12, "orders": 1}],
            },
        },
        timestamp_receive=datetime(2026, 4, 24, 10, 0, 1, 500000),
    )

    assert tick is not None
    assert tick["tradingsymbol"] == meta.tradingsymbol
    assert tick["exchange"] == meta.exchange
    assert tick["strike"] == meta.strike
    assert tick["expiry"] == meta.expiry.date().isoformat()
    assert tick["option_type"] == meta.option_type
    assert tick["lot_size"] == meta.lot_size


def test_tick_journal_writes_dedicated_tape_without_legacy_option_log(tmp_path: Path) -> None:
    ts = datetime(2026, 4, 24, 10, 0, 0)
    day = ts.date().isoformat()
    tape_root = tmp_path / "sensex_options"
    journal = TickJournal(
        logs_root=tmp_path,
        max_queue_size=100,
        flush_interval_seconds=0.1,
        enable_full_option_tape_logging=False,
        enable_sensex_option_tape_recorder=True,
        sensex_tape_log_dir=tape_root,
        sensex_tape_write_legacy_options_log=False,
    )
    journal.start()
    journal.append_market_tick(
        {
            "timestamp_exchange": ts,
            "source": "option",
            "symbol": "BFO:SENSEX26APR80000CE",
            "instrument_token": 123,
            "strike": 80000,
            "option_type": "CE",
            "ltp": 100.0,
        }
    )
    journal.stop()

    legacy_path = tmp_path / "ticks" / day / "options.jsonl"
    tape_path = tape_root / day / "options.jsonl"

    assert not legacy_path.exists()
    assert tape_path.exists()
    rows = [json.loads(line) for line in tape_path.read_text().splitlines() if line.strip()]
    assert rows[0]["tape_source"] == "sensex_option_tape"


def test_loader_filters_by_strike_and_option_type(tmp_path: Path) -> None:
    root = tmp_path / "sensex_options"
    day = root / "2026-04-24"
    day.mkdir(parents=True)
    path = day / "options.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"symbol": "A", "strike": 80000, "option_type": "CE"}),
                json.dumps({"symbol": "B", "strike": 80100, "option_type": "PE"}),
                json.dumps({"symbol": "C", "strike": 80000, "option_type": "PE"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = list(
        iter_sensex_option_ticks(
            date="2026-04-24",
            root=root,
            strikes=[80000],
            option_types=["PE"],
        )
    )

    assert [row["symbol"] for row in rows] == ["C"]
