from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol

from sensex_noise.auth.token_store import TokenStore


class WorkerStatusSettings(Protocol):
    runtime_dir: Path
    token_store_path: Path


VALID_WORKER_STATES = {
    "idle",
    "starting",
    "running",
    "stopping",
    "stopped",
    "failed",
    "unknown",
}

STATUS_KEYS = {
    "worker_state",
    "last_start_attempt_at",
    "last_started_at",
    "last_heartbeat_at",
    "last_stopped_at",
    "last_exit_code",
    "last_error",
    "pid",
    "container_name",
    "token_present",
    "trading_date",
    "updated_at",
}


def worker_status_path(settings: WorkerStatusSettings) -> Path:
    return settings.runtime_dir / "worker_status.json"


def empty_status() -> dict[str, Any]:
    return {
        "worker_state": "unknown",
        "last_start_attempt_at": None,
        "last_started_at": None,
        "last_heartbeat_at": None,
        "last_stopped_at": None,
        "last_exit_code": None,
        "last_error": None,
        "pid": None,
        "container_name": None,
        "token_present": None,
        "trading_date": None,
        "updated_at": None,
    }


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_worker_status(path: Path) -> dict[str, Any]:
    status = empty_status()
    if not path.exists():
        return status
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        status["worker_state"] = "unknown"
        status["last_error"] = "worker status file is unreadable"
        return status
    if not isinstance(raw, dict):
        status["worker_state"] = "unknown"
        status["last_error"] = "worker status file does not contain an object"
        return status

    for key in STATUS_KEYS:
        if key in raw:
            status[key] = raw[key]
    if status["worker_state"] not in VALID_WORKER_STATES:
        status["worker_state"] = "unknown"
    return status


def write_worker_status(path: Path, updates: dict[str, Any]) -> dict[str, Any]:
    unknown = set(updates) - STATUS_KEYS
    if unknown:
        raise ValueError(f"unsupported worker status keys: {', '.join(sorted(unknown))}")

    state = updates.get("worker_state")
    if state is not None and state not in VALID_WORKER_STATES:
        raise ValueError(f"unsupported worker_state: {state}")

    status = read_worker_status(path)
    status.update(updates)
    status["updated_at"] = utc_now_iso()

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(status, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass
    return status


def build_worker_summary(settings: WorkerStatusSettings) -> dict[str, Any]:
    status_path = worker_status_path(settings)
    status = read_worker_status(status_path)
    token_record = TokenStore(settings.token_store_path).read_today(today=date.today())
    status["token_present"] = token_record is not None
    status["trading_date"] = token_record.trading_date if token_record is not None else date.today().isoformat()
    status["status_path"] = str(status_path)
    return status


def _parse_value(raw: str) -> Any:
    value = raw.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() in {"none", "null"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def _parse_set(values: list[str]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for item in values:
        key, sep, raw_value = item.partition("=")
        if not sep:
            raise ValueError(f"--set value must be key=value, got: {item}")
        key = key.strip()
        if key not in STATUS_KEYS:
            raise ValueError(f"unsupported worker status key: {key}")
        updates[key] = _parse_value(raw_value)
    return updates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read or update the Sensex market-worker status file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--path", required=True)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--path", required=True)
    write_parser.add_argument("--state", choices=sorted(VALID_WORKER_STATES))
    write_parser.add_argument("--mark", action="append", default=[], choices=sorted(STATUS_KEYS))
    write_parser.add_argument("--set", action="append", default=[])

    args = parser.parse_args(argv)
    path = Path(args.path)

    if args.command == "read":
        print(json.dumps(read_worker_status(path), ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    updates = _parse_set(args.set)
    if args.state:
        updates["worker_state"] = args.state
    for key in args.mark:
        updates[key] = utc_now_iso()
    print(json.dumps(write_worker_status(path, updates), ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
