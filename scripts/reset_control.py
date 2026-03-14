from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    control_path = repo_root / "runtime" / "control.json"
    control_path.parent.mkdir(parents=True, exist_ok=True)
    control_path.write_text(json.dumps({"action": None}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print("Control file reset.")


if __name__ == "__main__":
    main()

