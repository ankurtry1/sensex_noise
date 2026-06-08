from __future__ import annotations

import json

from sensex_noise.ops.worker_status import read_worker_status, write_worker_status


def test_missing_worker_status_returns_unknown(tmp_path) -> None:
    status = read_worker_status(tmp_path / "worker_status.json")

    assert status["worker_state"] == "unknown"
    assert status["token_present"] is None


def test_write_worker_status_is_secret_free_and_atomic(tmp_path) -> None:
    path = tmp_path / "runtime" / "worker_status.json"

    written = write_worker_status(
        path,
        {
            "worker_state": "running",
            "pid": 123,
            "token_present": True,
            "trading_date": "2026-06-08",
            "last_error": None,
        },
    )

    assert written["worker_state"] == "running"
    assert written["pid"] == 123
    assert written["updated_at"]

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["worker_state"] == "running"
    assert "access_token" not in data
    assert "api_secret" not in data
