from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit("Usage: python scripts/manual_limit_exit.py 545.25")

    try:
        price = float(argv[1])
    except ValueError:
        raise SystemExit(f"Invalid price: {argv[1]!r}")

    repo_root = Path(__file__).resolve().parents[1]
    control_path = repo_root / "runtime" / "control.json"
    control_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"action": "EXIT_LIMIT", "price": price}
    control_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"Manual limit exit request written at price {price}.")


if __name__ == "__main__":
    main(sys.argv)

