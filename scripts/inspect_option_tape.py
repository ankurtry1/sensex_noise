from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect recorded SENSEX broad option tape.")
    parser.add_argument("--date", required=True, help="Trading date in YYYY-MM-DD format")
    parser.add_argument(
        "--root",
        default="data/tape/sensex_options",
        help="Root directory for the tape recorder output",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(args.root)
    day_dir = root / args.date
    options_path = day_dir / "options.jsonl"
    manifest_path = day_dir / "manifest.json"

    if not options_path.exists():
        print(f"warning: tape file missing: {options_path}")
        if manifest_path.exists():
            print(f"manifest: {manifest_path}")
        return 1

    row_count = 0
    unique_symbols: set[str] = set()
    unique_tokens: set[int] = set()
    ce_pe_counter: Counter[str] = Counter()
    min_ts: datetime | None = None
    max_ts: datetime | None = None
    strikes: list[int] = []

    with options_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            row_count += 1
            symbol = row.get("symbol")
            if isinstance(symbol, str) and symbol:
                unique_symbols.add(symbol)
            token = row.get("instrument_token")
            try:
                if token is not None:
                    unique_tokens.add(int(token))
            except (TypeError, ValueError):
                pass

            option_type = str(row.get("option_type", "")).upper()
            if option_type:
                ce_pe_counter[option_type] += 1

            strike = row.get("strike")
            try:
                if strike is not None:
                    strikes.append(int(strike))
            except (TypeError, ValueError):
                pass

            ts_raw = row.get("timestamp_exchange")
            if isinstance(ts_raw, str):
                try:
                    ts = datetime.fromisoformat(ts_raw)
                except ValueError:
                    ts = None
                if ts is not None:
                    min_ts = ts if min_ts is None or ts < min_ts else min_ts
                    max_ts = ts if max_ts is None or ts > max_ts else max_ts

    print(f"date: {args.date}")
    print(f"options_path: {options_path}")
    print(f"rows: {row_count}")
    print(f"unique_symbols: {len(unique_symbols)}")
    print(f"unique_tokens: {len(unique_tokens)}")
    print(f"timestamp_exchange_min: {min_ts.isoformat() if min_ts else 'n/a'}")
    print(f"timestamp_exchange_max: {max_ts.isoformat() if max_ts else 'n/a'}")
    if strikes:
        print(f"strike_min: {min(strikes)}")
        print(f"strike_max: {max(strikes)}")
    else:
        print("strike_min: n/a")
        print("strike_max: n/a")
    print(f"CE_count: {ce_pe_counter.get('CE', 0)}")
    print(f"PE_count: {ce_pe_counter.get('PE', 0)}")
    print(f"manifest: {manifest_path if manifest_path.exists() else 'missing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
