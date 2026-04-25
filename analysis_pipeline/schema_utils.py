from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .io_utils import iter_jsonl, parse_timestamp


TIMESTAMP_CANDIDATES = (
    "timestamp_exchange",
    "timestamp_receive",
    "timestamp",
    "entry_time",
    "entry_fill_time",
    "exit_time",
    "exit_fill_time",
    "signal_time",
)


def detect_timestamp_key(record: dict[str, Any]) -> str | None:
    for key in TIMESTAMP_CANDIDATES:
        if key in record:
            return key
    return None


def has_subsecond_timestamp(record: dict[str, Any]) -> bool:
    for key in TIMESTAMP_CANDIDATES:
        if key not in record:
            continue
        value = record.get(key)
        if isinstance(value, str) and "." in value:
            return True
        dt = parse_timestamp(value)
        if dt is not None and dt.microsecond > 0:
            return True
    return False


def has_depth_fields(record: dict[str, Any]) -> bool:
    bid = record.get("bid[5]")
    ask = record.get("ask[5]")
    if isinstance(bid, list) and isinstance(ask, list) and (bid or ask):
        return True
    if record.get("best_bid") is not None or record.get("best_ask") is not None:
        return True
    return False


def summarize_schema(path: Path, sample_rows: int = 200) -> dict[str, Any]:
    key_counter: Counter[str] = Counter()
    has_depth = False
    has_subsecond = False
    rows = 0

    for row in iter_jsonl(path):
        rows += 1
        key_counter.update(row.keys())
        has_depth = has_depth or has_depth_fields(row)
        has_subsecond = has_subsecond or has_subsecond_timestamp(row)
        if rows >= sample_rows:
            break

    return {
        "rows_sampled": rows,
        "top_keys": [k for k, _ in key_counter.most_common(20)],
        "has_depth_fields": has_depth,
        "subsecond_timestamp_supported": has_subsecond,
    }
