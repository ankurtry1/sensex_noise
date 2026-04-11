from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            raw = line.strip()
            if not raw:
                continue
            rows.append(json.loads(raw))
    return rows


def build_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        keys.update(str(key) for key in row.keys())
    preferred = [
        "trade_id",
        "symbol",
        "signal_kind",
        "side",
        "entry_price",
        "exit_price",
        "exit_reason",
        "gross_pnl",
        "net_pnl",
        "mfe",
        "mae",
        "fragile",
    ]
    remaining = sorted(k for k in keys if k not in preferred)
    ordered = [k for k in preferred if k in keys]
    ordered.extend(remaining)
    return ordered


def write_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = build_fieldnames(rows)
    with out_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)



def main() -> None:
    parser = argparse.ArgumentParser(description="Build a flat CSV feature table from enriched trade JSONL")
    parser.add_argument(
        "--input",
        default="logs/trades_enriched.jsonl",
        help="Input enriched trade summary JSONL path",
    )
    parser.add_argument(
        "--output",
        default="logs/features_daily.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    rows = load_jsonl(in_path)
    if not rows:
        print(f"No rows found in {in_path}")
        return

    write_csv(rows, out_path)
    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
