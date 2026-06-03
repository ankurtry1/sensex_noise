from __future__ import annotations

import stat
from datetime import date, datetime

from sensex_noise.auth.token_store import TokenStore


def test_token_store_saves_and_reads_today_token(tmp_path) -> None:
    path = tmp_path / "kite_access_token.json"
    store = TokenStore(path)

    record = store.save(
        access_token="secret-token",
        api_key="api-key",
        user_id="AB1234",
        generated_at=datetime(2026, 5, 31, 8, 0, 0),
        trading_date=date(2026, 5, 31),
    )

    loaded = store.read_today(today=date(2026, 5, 31))
    assert loaded == record
    assert loaded is not None
    assert loaded.access_token == "secret-token"
    assert loaded.safe_metadata() == {
        "generated_at": "2026-05-31T08:00:00",
        "trading_date": "2026-05-31",
        "api_key_present": True,
        "user_id": "AB1234",
        "has_access_token": True,
    }
    assert "secret-token" not in str(loaded.safe_metadata())
    assert "api-key" not in str(loaded.safe_metadata())


def test_token_store_rejects_stale_token(tmp_path) -> None:
    store = TokenStore(tmp_path / "kite_access_token.json")
    store.save(
        access_token="secret-token",
        generated_at=datetime(2026, 5, 30, 8, 0, 0),
        trading_date=date(2026, 5, 30),
    )

    assert store.read_today(today=date(2026, 5, 31)) is None


def test_token_store_file_is_owner_only_when_supported(tmp_path) -> None:
    path = tmp_path / "kite_access_token.json"
    TokenStore(path).save(access_token="secret-token")

    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode & stat.S_IRWXG == 0
    assert mode & stat.S_IRWXO == 0
