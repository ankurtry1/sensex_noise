from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from .config import PipelineConfig
from .io_utils import iter_jsonl, parse_date_from_timestamp
from .schema_utils import has_depth_fields, has_subsecond_timestamp


def _collect_dates_from_jsonl(path: Path, ts_keys: tuple[str, ...] = ("timestamp",)) -> set[str]:
    dates: set[str] = set()
    if not path.exists():
        return dates
    for row in iter_jsonl(path):
        date_val = None
        for key in ts_keys:
            if key in row:
                date_val = parse_date_from_timestamp(row.get(key))
                if date_val:
                    break
        if date_val:
            dates.add(date_val)
    return dates


def _date_from_stem(stem: str, suffix: str) -> str | None:
    if not stem.endswith(suffix):
        return None
    candidate = stem[: -len(suffix)]
    if len(candidate) == 10 and candidate[4] == "-" and candidate[7] == "-":
        return candidate
    return None


def _infer_date_from_trade_id(trade_id: str) -> str | None:
    # Trade IDs often begin with YYYYMMDDT...
    if len(trade_id) >= 8 and trade_id[:8].isdigit():
        y, m, d = trade_id[:4], trade_id[4:6], trade_id[6:8]
        return f"{y}-{m}-{d}"
    return None


def _scan_zip_dates(zip_path: Path) -> set[str]:
    dates: set[str] = set()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                for token in Path(name).parts:
                    if len(token) == 10 and token[4] == "-" and token[7] == "-":
                        dates.add(token)
    except zipfile.BadZipFile:
        return dates
    return dates


def _score_row(row: dict[str, Any]) -> tuple[float, str, str]:
    score = 0.0
    notes: list[str] = []

    if row["has_trades_log"] or row["has_trades_enriched"]:
        score += 25
    else:
        notes.append("missing trade logs")

    if row["has_events_log"]:
        score += 15
    else:
        notes.append("missing events log")

    if row["has_trade_scoped_ticks"]:
        score += 25
    else:
        notes.append("missing trade scoped ticks")

    if row["has_sensex_ticks"]:
        score += 15
    else:
        notes.append("missing sensex ticks")

    if row["has_futures_ticks"]:
        score += 10
    else:
        notes.append("missing futures ticks")

    if row["has_options_ticks"]:
        score += 5

    if row["has_depth_fields"]:
        score += 3

    if row["subsecond_timestamp_supported"]:
        score += 2

    if row.get("trade_ids_reconcilable", 0) == 0:
        score -= 10
        notes.append("no reconcilable trade ids")

    if score >= 75:
        bucket = "HIGH"
    elif score >= 50:
        bucket = "MEDIUM"
    elif score >= 30:
        bucket = "LOW"
    else:
        bucket = "UNUSABLE"

    return max(0.0, min(100.0, score)), bucket, "; ".join(notes)


def build_inventory(config: PipelineConfig) -> tuple[pd.DataFrame, dict[str, Any], list[str]]:
    logs_dir = config.logs_dir
    warnings: list[str] = []

    date_rows: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "date": None,
            "has_trades_log": False,
            "has_events_log": False,
            "has_trades_enriched": False,
            "has_sensex_ticks": False,
            "has_futures_ticks": False,
            "has_options_ticks": False,
            "has_trade_scoped_ticks": False,
            "trade_tick_file_count": 0,
            "has_depth_fields": False,
            "subsecond_timestamp_supported": False,
            "trade_ids_reconcilable": 0,
            "entry_exit_matchable_to_ticks": 0.0,
            "data_trust_score": 0.0,
            "confidence_bucket": "UNUSABLE",
            "notes": "",
        }
    )

    def ensure_date(d: str) -> dict[str, Any]:
        row = date_rows[d]
        row["date"] = d
        return row

    # Day-wise split logs.
    trades_dir = logs_dir / "trades"
    if trades_dir.exists():
        for path in sorted(trades_dir.glob("*.trades.jsonl")):
            d = _date_from_stem(path.name, ".trades.jsonl")
            if not d:
                continue
            ensure_date(d)["has_trades_log"] = True

        for path in sorted(trades_dir.glob("*.trades_enriched.jsonl")):
            d = _date_from_stem(path.name, ".trades_enriched.jsonl")
            if not d:
                continue
            row = ensure_date(d)
            row["has_trades_enriched"] = True
            tids: set[str] = set()
            for obj in iter_jsonl(path, warnings=warnings):
                tid = obj.get("trade_id")
                if isinstance(tid, str) and tid.strip():
                    tids.add(tid)
            row["trade_ids_reconcilable"] = max(row["trade_ids_reconcilable"], len(tids))

    events_dir = logs_dir / "events"
    if events_dir.exists():
        for path in sorted(events_dir.glob("*.events.jsonl")):
            d = _date_from_stem(path.name, ".events.jsonl")
            if not d:
                continue
            ensure_date(d)["has_events_log"] = True

    ticks_dir = logs_dir / "ticks"
    if ticks_dir.exists():
        for day_dir in sorted([p for p in ticks_dir.iterdir() if p.is_dir()]):
            d = day_dir.name
            if len(d) != 10 or d[4] != "-" or d[7] != "-":
                continue
            row = ensure_date(d)
            sensex = day_dir / "sensex.jsonl"
            futures = day_dir / "futures.jsonl"
            options = day_dir / "options.jsonl"
            row["has_sensex_ticks"] = sensex.exists()
            row["has_futures_ticks"] = futures.exists()
            row["has_options_ticks"] = options.exists()

            for p in (sensex, futures, options):
                if not p.exists():
                    continue
                for obj in iter_jsonl(p, warnings=warnings):
                    row["has_depth_fields"] = row["has_depth_fields"] or has_depth_fields(obj)
                    row["subsecond_timestamp_supported"] = row[
                        "subsecond_timestamp_supported"
                    ] or has_subsecond_timestamp(obj)
                    break

    trade_ticks_dir = logs_dir / "trade_ticks"
    if trade_ticks_dir.exists():
        for day_dir in sorted([p for p in trade_ticks_dir.iterdir() if p.is_dir()]):
            d = day_dir.name
            if len(d) != 10 or d[4] != "-" or d[7] != "-":
                continue
            row = ensure_date(d)
            files = sorted(day_dir.glob("*.jsonl"))
            row["has_trade_scoped_ticks"] = len(files) > 0
            row["trade_tick_file_count"] = len(files)
            if files:
                for obj in iter_jsonl(files[0], warnings=warnings):
                    row["has_depth_fields"] = row["has_depth_fields"] or has_depth_fields(obj)
                    row["subsecond_timestamp_supported"] = row[
                        "subsecond_timestamp_supported"
                    ] or has_subsecond_timestamp(obj)
                    break

    # Root-level aggregate logs: infer dates from timestamps.
    root_trades = logs_dir / "trades.jsonl"
    root_events = logs_dir / "events.jsonl"
    root_enriched = logs_dir / "trades_enriched.jsonl"

    for d in _collect_dates_from_jsonl(root_trades, ts_keys=("timestamp",)):
        ensure_date(d)["has_trades_log"] = True
    for d in _collect_dates_from_jsonl(root_events, ts_keys=("timestamp",)):
        ensure_date(d)["has_events_log"] = True
    if root_enriched.exists():
        for obj in iter_jsonl(root_enriched, warnings=warnings):
            d = parse_date_from_timestamp(
                obj.get("entry_fill_time")
                or obj.get("signal_time")
                or obj.get("exit_fill_time")
            )
            if not d:
                tid = obj.get("trade_id")
                if isinstance(tid, str):
                    d = _infer_date_from_trade_id(tid)
            if not d:
                continue
            row = ensure_date(d)
            row["has_trades_enriched"] = True
            row["trade_ids_reconcilable"] += 1

    # Archive zip optional dates.
    archived_dates: set[str] = set()
    if config.include_archived:
        for zip_path in logs_dir.rglob("*.zip"):
            archived_dates.update(_scan_zip_dates(zip_path))
    for d in sorted(archived_dates):
        row = ensure_date(d)
        if row["notes"]:
            row["notes"] += "; "
        row["notes"] += "archived data present"

    rows = []
    for d in sorted(date_rows):
        if config.start_date and d < config.start_date:
            continue
        if config.end_date and d > config.end_date:
            continue
        row = date_rows[d]
        # crude ratio: available trade tick files / reconcilable trade ids
        recon = int(row.get("trade_ids_reconcilable", 0) or 0)
        files = int(row.get("trade_tick_file_count", 0) or 0)
        if recon > 0:
            row["entry_exit_matchable_to_ticks"] = min(1.0, files / recon)
        else:
            row["entry_exit_matchable_to_ticks"] = 0.0

        score, bucket, notes = _score_row(row)
        row["data_trust_score"] = score
        row["confidence_bucket"] = bucket
        if notes:
            if row["notes"]:
                row["notes"] += "; "
            row["notes"] += notes

        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("date").reset_index(drop=True)

    summary = {
        "dates_total": int(df.shape[0]),
        "dates_high_confidence": int((df["confidence_bucket"] == "HIGH").sum()) if not df.empty else 0,
        "dates_medium_confidence": int((df["confidence_bucket"] == "MEDIUM").sum()) if not df.empty else 0,
        "dates_low_confidence": int((df["confidence_bucket"] == "LOW").sum()) if not df.empty else 0,
        "dates_unusable": int((df["confidence_bucket"] == "UNUSABLE").sum()) if not df.empty else 0,
        "include_archived": config.include_archived,
    }

    return df, summary, warnings


def apply_reconciliation_coverage(
    inventory_df: pd.DataFrame,
    reconciliation_df: pd.DataFrame,
) -> pd.DataFrame:
    if inventory_df.empty:
        return inventory_df

    if reconciliation_df.empty:
        inventory_df = inventory_df.copy()
        inventory_df["trade_ids_reconcilable"] = 0
        inventory_df["entry_exit_matchable_to_ticks"] = 0.0
        return inventory_df

    grouped = reconciliation_df.groupby("date", dropna=False).agg(
        trade_ids_reconcilable=("trade_id", "nunique"),
        entry_exit_matchable_to_ticks=("matched_trade_ticks", "mean"),
    )
    grouped = grouped.reset_index()

    merged = inventory_df.merge(grouped, on="date", how="left", suffixes=("", "_recon"))
    for col in ("trade_ids_reconcilable", "entry_exit_matchable_to_ticks"):
        alt = f"{col}_recon"
        if alt in merged:
            merged[col] = merged[alt].fillna(merged[col])
            merged = merged.drop(columns=[alt])

    # Re-score based on improved reconciliation columns.
    rescored_rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        rec = row.to_dict()
        score, bucket, notes = _score_row(rec)
        rec["data_trust_score"] = score
        rec["confidence_bucket"] = bucket
        if notes and notes not in str(rec.get("notes", "")):
            if rec.get("notes"):
                rec["notes"] = f"{rec['notes']}; {notes}"
            else:
                rec["notes"] = notes
        rescored_rows.append(rec)

    return pd.DataFrame(rescored_rows).sort_values("date").reset_index(drop=True)


def build_research_summary(
    inventory_df: pd.DataFrame,
    inventory_summary: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = dict(inventory_summary)
    out["coverage_by_date"] = (
        inventory_df[["date", "confidence_bucket", "data_trust_score"]].to_dict("records")
        if not inventory_df.empty
        else []
    )
    if extra:
        out.update(extra)
    return out
