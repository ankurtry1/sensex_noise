from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config import PipelineConfig
from .io_utils import iter_jsonl, parse_date_from_timestamp, parse_timestamp, slug_trade_id


@dataclass
class ReconciliationResult:
    reconciled_df: pd.DataFrame
    summary_df: pd.DataFrame
    warnings: list[str]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _iter_enriched_files(logs_dir: Path) -> list[Path]:
    files: list[Path] = []
    trades_dir = logs_dir / "trades"
    if trades_dir.exists():
        files.extend(sorted(trades_dir.glob("*.trades_enriched.jsonl")))
    root = logs_dir / "trades_enriched.jsonl"
    if root.exists():
        files.append(root)
    return files


def _iter_event_files(logs_dir: Path) -> list[Path]:
    files: list[Path] = []
    events_dir = logs_dir / "events"
    if events_dir.exists():
        files.extend(sorted(events_dir.glob("*.events.jsonl")))
    root = logs_dir / "events.jsonl"
    if root.exists():
        files.append(root)
    return files


def _row_date(row: dict[str, Any]) -> str | None:
    for key in (
        "entry_fill_time",
        "entry_time",
        "signal_time",
        "exit_fill_time",
        "exit_time",
    ):
        d = parse_date_from_timestamp(row.get(key))
        if d:
            return d
    tid = row.get("trade_id")
    if isinstance(tid, str) and len(tid) >= 8 and tid[:8].isdigit():
        return f"{tid[:4]}-{tid[4:6]}-{tid[6:8]}"
    return None


def _in_date_range(date_str: str | None, start: str | None, end: str | None) -> bool:
    if date_str is None:
        return False
    if start and date_str < start:
        return False
    if end and date_str > end:
        return False
    return True


def _load_enriched_latest(config: PipelineConfig, warnings: list[str]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for path in _iter_enriched_files(config.logs_dir):
        for row in iter_jsonl(path, warnings=warnings):
            tid = _safe_str(row.get("trade_id"))
            if not tid:
                continue
            date_str = _row_date(row)
            if not _in_date_range(date_str, config.start_date, config.end_date):
                continue
            existing = latest.get(tid)
            # Keep row with richer close fields when duplicates exist.
            score = sum(
                1
                for k in (
                    "exit_fill_time",
                    "exit_price",
                    "net_pnl",
                    "gross_pnl",
                    "post_exit_observation_done",
                )
                if row.get(k) is not None
            )
            if existing is None:
                latest[tid] = dict(row)
                latest[tid]["_quality_score"] = score
            else:
                prev_score = int(existing.get("_quality_score", 0))
                if score >= prev_score:
                    latest[tid] = dict(row)
                    latest[tid]["_quality_score"] = score
    return latest


def _load_event_index(config: PipelineConfig, warnings: list[str]) -> dict[str, dict[str, Any]]:
    event_index: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "event_count": 0,
            "has_trade_entered": False,
            "has_trade_exited": False,
            "has_trade_closed_summary": False,
            "exit_reasons_seen": set(),
            "first_event_time": None,
            "last_event_time": None,
        }
    )

    for path in _iter_event_files(config.logs_dir):
        for row in iter_jsonl(path, warnings=warnings):
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            tid = _safe_str(payload.get("trade_id"))
            if not tid:
                continue
            date_hint = parse_date_from_timestamp(row.get("timestamp"))
            if date_hint and not _in_date_range(date_hint, config.start_date, config.end_date):
                continue

            et = _safe_str(row.get("event_type")) or "UNKNOWN"
            state = event_index[tid]
            state["event_count"] += 1
            ts = parse_timestamp(row.get("timestamp"))
            if ts is not None:
                if state["first_event_time"] is None or ts < state["first_event_time"]:
                    state["first_event_time"] = ts
                if state["last_event_time"] is None or ts > state["last_event_time"]:
                    state["last_event_time"] = ts

            if et == "TRADE_ENTERED":
                state["has_trade_entered"] = True
            elif et == "TRADE_EXITED":
                state["has_trade_exited"] = True
            elif et == "TRADE_CLOSED_SUMMARY":
                state["has_trade_closed_summary"] = True

            if et.endswith("_EXIT") or et in {"TARGET_HIT", "TIME_STOP_AFTER_1PM", "TRADE_EXITED"}:
                state["exit_reasons_seen"].add(et)

    for tid, state in event_index.items():
        state["exit_reasons_seen"] = sorted(state["exit_reasons_seen"])

    return event_index


def _load_trade_tick_file_index(config: PipelineConfig, warnings: list[str]) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    trade_ticks_dir = config.logs_dir / "trade_ticks"
    if not trade_ticks_dir.exists():
        return mapping

    for day_dir in sorted([p for p in trade_ticks_dir.iterdir() if p.is_dir()]):
        d = day_dir.name
        if not _in_date_range(d, config.start_date, config.end_date):
            continue
        for path in sorted(day_dir.glob("*.jsonl")):
            tid = None
            for row in iter_jsonl(path, warnings=warnings):
                candidate = _safe_str(row.get("trade_id"))
                if candidate:
                    tid = candidate
                break
            if tid:
                mapping[tid] = path

    return mapping


def _tick_time_bounds(path: Path, warnings: list[str]) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    first_ts = None
    last_ts = None
    for row in iter_jsonl(path, warnings=warnings):
        ts = parse_timestamp(row.get("timestamp_exchange") or row.get("timestamp"))
        if ts is None:
            continue
        if first_ts is None:
            first_ts = ts
        last_ts = ts
    return first_ts, last_ts


def _build_underlying_bounds_index(config: PipelineConfig, warnings: list[str]) -> dict[tuple[str, str], tuple[Any, Any]]:
    out: dict[tuple[str, str], tuple[Any, Any]] = {}
    ticks_root = config.logs_dir / "ticks"
    if not ticks_root.exists():
        return out
    for day_dir in sorted([p for p in ticks_root.iterdir() if p.is_dir()]):
        d = day_dir.name
        if not _in_date_range(d, config.start_date, config.end_date):
            continue
        for source, fname in (("sensex", "sensex.jsonl"), ("futures", "futures.jsonl")):
            path = day_dir / fname
            if not path.exists():
                continue
            out[(d, source)] = _tick_time_bounds(path, warnings=warnings)
    return out


def reconcile_trades(config: PipelineConfig) -> ReconciliationResult:
    warnings: list[str] = []

    enriched = _load_enriched_latest(config, warnings)
    event_idx = _load_event_index(config, warnings)
    trade_tick_idx = _load_trade_tick_file_index(config, warnings)
    bounds_idx = _build_underlying_bounds_index(config, warnings)

    rows: list[dict[str, Any]] = []
    exclusion_counter: Counter[str] = Counter()

    for tid, row in enriched.items():
        date = _row_date(row)
        if not _in_date_range(date, config.start_date, config.end_date):
            continue

        entry_time = parse_timestamp(row.get("entry_fill_time") or row.get("entry_time") or row.get("signal_time"))
        exit_time = parse_timestamp(row.get("exit_fill_time") or row.get("exit_time"))
        entry_price = _safe_float(row.get("entry_price"))
        exit_price = _safe_float(row.get("exit_price"))
        net_pnl = _safe_float(row.get("net_pnl"))
        gross_pnl = _safe_float(row.get("gross_pnl"))
        hold_seconds = _safe_float(row.get("holding_seconds"))

        matched_events = tid in event_idx
        matched_trade_ticks = tid in trade_tick_idx

        matched_underlying = False
        if date and entry_time is not None and exit_time is not None:
            sensex_bounds = bounds_idx.get((date, "sensex"))
            futures_bounds = bounds_idx.get((date, "futures"))
            if sensex_bounds and futures_bounds:
                s0, s1 = sensex_bounds
                f0, f1 = futures_bounds
                if all(x is not None for x in (s0, s1, f0, f1)):
                    matched_underlying = bool(s0 <= entry_time <= s1 and f0 <= entry_time <= f1)

        exclusion_reason = None
        if exit_time is None:
            exclusion_reason = "missing_exit"
        elif entry_time is None:
            exclusion_reason = "missing_entry"
        elif entry_price is None or exit_price is None:
            exclusion_reason = "missing_prices"

        status = "reconciled"
        if exclusion_reason is not None:
            status = "excluded"
            exclusion_counter[exclusion_reason] += 1

        rows.append(
            {
                "trade_id": tid,
                "date": date,
                "symbol": _safe_str(row.get("symbol")),
                "signal_kind": _safe_str(row.get("signal_kind")),
                "side": _safe_str(row.get("side")),
                "entry_time": entry_time.isoformat() if entry_time else None,
                "exit_time": exit_time.isoformat() if exit_time else None,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "exit_reason": _safe_str(row.get("closing_reason") or row.get("exit_reason")),
                "hold_seconds": hold_seconds,
                "matched_enriched": True,
                "matched_events": bool(matched_events),
                "matched_trade_ticks": bool(matched_trade_ticks),
                "matched_underlying_ticks": bool(matched_underlying),
                "match_status": status,
                "exclusion_reason": exclusion_reason,
                "entry_order_id": _safe_str(row.get("entry_order_id")),
                "exit_order_id": _safe_str(row.get("exit_order_id")),
                "mfe": _safe_float(row.get("mfe")),
                "mae": _safe_float(row.get("mae")),
                "pre_or_post_1pm": _safe_str(row.get("pre_or_post_1pm")),
                "continuation_or_reversal": _safe_str(row.get("continuation_or_reversal")),
                "call_or_put": _safe_str(row.get("call_or_put")),
                "entry_slippage_points": _safe_float(row.get("entry_slippage_points")),
                "exit_slippage_points": _safe_float(row.get("exit_slippage_points")),
                "trade_tick_path": str(trade_tick_idx.get(tid)) if tid in trade_tick_idx else None,
                "trade_tick_safe_id": slug_trade_id(tid),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        summary = pd.DataFrame(
            [
                {
                    "metric": "reconciled_trade_count",
                    "value": 0,
                }
            ]
        )
        return ReconciliationResult(df, summary, warnings)

    df = df.sort_values(["date", "trade_id"]).reset_index(drop=True)

    summary_rows: list[dict[str, Any]] = []
    summary_rows.append({"metric": "total_trade_ids_seen", "value": int(df.trade_id.nunique())})
    summary_rows.append(
        {
            "metric": "reconciled_closed_trades",
            "value": int(df[df["match_status"] == "reconciled"].shape[0]),
        }
    )
    summary_rows.append(
        {
            "metric": "with_events_match",
            "value": int(df["matched_events"].sum()),
        }
    )
    summary_rows.append(
        {
            "metric": "with_trade_tick_match",
            "value": int(df["matched_trade_ticks"].sum()),
        }
    )
    summary_rows.append(
        {
            "metric": "with_underlying_match",
            "value": int(df["matched_underlying_ticks"].sum()),
        }
    )

    for reason, count in sorted(exclusion_counter.items()):
        summary_rows.append({"metric": f"excluded_{reason}", "value": int(count)})

    by_date = (
        df.groupby("date", dropna=False)
        .agg(
            trades=("trade_id", "nunique"),
            reconciled=("match_status", lambda s: int((s == "reconciled").sum())),
            matched_trade_ticks=("matched_trade_ticks", "mean"),
            matched_underlying_ticks=("matched_underlying_ticks", "mean"),
        )
        .reset_index()
    )
    for _, r in by_date.iterrows():
        summary_rows.append(
            {
                "metric": f"date_{r['date']}",
                "value": json.dumps(
                    {
                        "trades": int(r["trades"]),
                        "reconciled": int(r["reconciled"]),
                        "matched_trade_ticks_ratio": float(r["matched_trade_ticks"]),
                        "matched_underlying_ratio": float(r["matched_underlying_ticks"]),
                    }
                ),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    return ReconciliationResult(df, summary_df, warnings)
