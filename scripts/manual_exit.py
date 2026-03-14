from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    control_path = repo_root / "runtime" / "control.json"
    control_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"action": "EXIT_NOW"}
    control_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print("Manual market exit request written. Engine will close current open trade.")


if __name__ == "__main__":
    main()

