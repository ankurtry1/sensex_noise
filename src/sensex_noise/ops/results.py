from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo


class ResultsSettings(Protocol):
    data_dir: Path
    logs_dir: Path
    trade_log_path: Path
    event_log_path: Path
    enriched_trade_log_path: Path
    features_output_path: Path
    sensex_tape_log_dir: Path


def _today_ist() -> str:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()


def _line_count(path: Path) -> int:
    try:
        with path.open("rb") as fp:
            return sum(chunk.count(b"\n") for chunk in iter(lambda: fp.read(1024 * 1024), b""))
    except OSError:
        return 0


def _file_summary(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError:
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": 0,
            "line_count": 0,
            "modified_at": None,
        }
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "line_count": _line_count(path),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def _summarize_tree(root: Path, *, limit: int = 50) -> dict[str, Any]:
    files: list[Path] = []
    if root.exists():
        files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p))
    selected = files[:limit]
    summaries = [_file_summary(path) for path in selected]
    return {
        "root": str(root),
        "exists": root.exists(),
        "file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in summaries),
        "total_line_count": sum(item["line_count"] for item in summaries),
        "truncated": len(files) > limit,
        "files": summaries,
    }


def build_results_summary(settings: ResultsSettings, trading_date: str | None = None) -> dict[str, Any]:
    day = trading_date or _today_ist()
    tick_root = settings.logs_dir / "ticks" / day
    trade_tick_root = settings.logs_dir / "trade_ticks" / day
    tape_root = settings.sensex_tape_log_dir / day

    return {
        "trading_date": day,
        "logs_dir": str(settings.logs_dir),
        "market_ticks": _summarize_tree(tick_root),
        "trade_ticks": _summarize_tree(trade_tick_root),
        "option_tape": _summarize_tree(tape_root),
        "journals": {
            "trades": _file_summary(settings.trade_log_path),
            "events": _file_summary(settings.event_log_path),
            "trades_enriched": _file_summary(settings.enriched_trade_log_path),
            "features_daily": _file_summary(settings.features_output_path),
        },
    }
