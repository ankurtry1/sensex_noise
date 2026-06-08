from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any
from urllib import request
from urllib.error import URLError


logger = logging.getLogger(__name__)


def _bool_env(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _event_enabled(event: str) -> bool:
    normalized = event.lower()
    if "start" in normalized:
        return _bool_env("NOTIFY_ON_START", "true")
    if "stop" in normalized:
        return _bool_env("NOTIFY_ON_STOP", "true")
    if "fail" in normalized or "error" in normalized:
        return _bool_env("NOTIFY_ON_FAILURE", "true")
    return True


def notify(event: str, status: str, message: str, *, webhook_url: str | None = None) -> bool:
    url = (webhook_url if webhook_url is not None else os.getenv("NOTIFY_WEBHOOK_URL", "")).strip()
    if not url or not _event_enabled(event):
        return False

    payload: dict[str, Any] = {
        "event": event,
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "message": message,
    }
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            return 200 <= int(response.status) < 300
    except (OSError, URLError) as exc:
        logger.warning("Notification webhook failed for event=%s: %s", event, type(exc).__name__)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send an optional operational notification.")
    parser.add_argument("--event", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--message", required=True)
    args = parser.parse_args(argv)
    notify(args.event, args.status, args.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
