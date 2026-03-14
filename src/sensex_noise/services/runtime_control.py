from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ControlCommand:
    action: str
    price: Optional[float] = None


def ensure_control_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _write(path, {"action": None})


def read_control(path: Path) -> dict[str, Any]:
    ensure_control_file(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read control file %s: %s", path, exc)
        return {"action": None}

    try:
        data = json.loads(raw) if raw.strip() else {"action": None}
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in control file %s: %s", path, exc)
        return {"action": None}

    if not isinstance(data, dict):
        return {"action": None}
    return data


def parse_command(data: dict[str, Any]) -> Optional[ControlCommand]:
    action = data.get("action")
    if action is None:
        return None
    if action == "EXIT_NOW":
        return ControlCommand(action="EXIT_NOW")
    if action == "EXIT_LIMIT":
        price = data.get("price")
        try:
            price_f = float(price)
        except (TypeError, ValueError):
            logger.warning("EXIT_LIMIT missing/invalid price in control file: %r", price)
            return None
        return ControlCommand(action="EXIT_LIMIT", price=price_f)
    logger.warning("Unsupported control action: %r", action)
    return None


def reset_control(path: Path) -> None:
    ensure_control_file(path)
    _write(path, {"action": None})


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

