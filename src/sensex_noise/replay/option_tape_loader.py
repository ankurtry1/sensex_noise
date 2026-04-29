from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def iter_sensex_option_ticks(
    date: str,
    root: str | Path = "data/tape/sensex_options",
    symbols: list[str] | None = None,
    strikes: list[int] | None = None,
    option_types: list[str] | None = None,
) -> Iterable[dict[str, Any]]:
    path = Path(root) / date / "options.jsonl"
    if not path.exists():
        return

    symbol_set = set(symbols or [])
    strike_set = {int(x) for x in strikes} if strikes else None
    type_set = {str(x).upper() for x in option_types} if option_types else None

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if symbol_set and row.get("symbol") not in symbol_set:
                continue
            if strike_set is not None:
                try:
                    row_strike = int(row.get("strike"))
                except (TypeError, ValueError):
                    continue
                if row_strike not in strike_set:
                    continue
            if type_set is not None and str(row.get("option_type", "")).upper() not in type_set:
                continue
            yield row
