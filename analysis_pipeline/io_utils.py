from __future__ import annotations

import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pandas as pd


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_timestamp(value: Any) -> datetime | None:
    """Best-effort timestamp parser for mixed schemas.

    Supports:
    - ISO strings (with/without timezone)
    - subsecond strings
    - epoch seconds / milliseconds
    - pandas/datetime objects
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime()

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            return None
        v = float(value)
        # Heuristic: ms epoch if too large.
        if v > 1e12:
            v /= 1000.0
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        # Numeric strings first.
        if raw.replace(".", "", 1).isdigit():
            try:
                return parse_timestamp(float(raw))
            except ValueError:
                pass

        # Normalize Z suffix.
        normalized = raw.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            pass

        # Fallback to pandas parser.
        try:
            ts = pd.to_datetime(raw, errors="coerce", utc=True)
            if pd.isna(ts):
                return None
            return ts.to_pydatetime().replace(tzinfo=None)
        except Exception:
            return None

    return None


def parse_date_from_timestamp(value: Any) -> str | None:
    dt = parse_timestamp(value)
    if dt is None:
        return None
    return dt.date().isoformat()


def read_jsonl(path: Path, warnings: list[str] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out

    with path.open("r", encoding="utf-8") as fp:
        for i, line in enumerate(fp, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                if warnings is not None:
                    warnings.append(f"JSON decode error {path}:{i}: {exc}")
                continue
            if isinstance(obj, dict):
                out.append(obj)
            elif warnings is not None:
                warnings.append(f"Non-object JSON row {path}:{i}")
    return out


def iter_jsonl(path: Path, warnings: list[str] | None = None) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fp:
        for i, line in enumerate(fp, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                if warnings is not None:
                    warnings.append(f"JSON decode error {path}:{i}: {exc}")
                continue
            if isinstance(obj, dict):
                yield obj


def scan_zip_jsonl_dates(zip_path: Path) -> set[str]:
    dates: set[str] = set()
    if not zip_path.exists():
        return dates
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                parts = Path(name).parts
                for token in parts:
                    if len(token) == 10 and token[4] == "-" and token[7] == "-":
                        dates.add(token)
    except zipfile.BadZipFile:
        return dates
    return dates


def write_df(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False)


def write_json(data: dict[str, Any], path: Path) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, sort_keys=True, default=str)


def slug_trade_id(trade_id: str) -> str:
    import re

    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", trade_id.strip())
    return safe or "trade"


def nearest_value_at_or_after(
    series_df: pd.DataFrame,
    target_ts: datetime,
    value_col: str = "ltp",
    ts_col: str = "timestamp_exchange",
    tolerance_seconds: float = 2.0,
) -> float | None:
    if series_df.empty:
        return None
    mask = series_df[ts_col] >= target_ts
    candidates = series_df.loc[mask].sort_values(ts_col)
    if candidates.empty:
        return None
    row = candidates.iloc[0]
    ts = row.get(ts_col)
    if not isinstance(ts, datetime):
        return None
    if (ts - target_ts).total_seconds() > tolerance_seconds:
        return None
    try:
        return float(row.get(value_col))
    except (TypeError, ValueError):
        return None
