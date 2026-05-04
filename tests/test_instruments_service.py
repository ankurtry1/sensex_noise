from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from sensex_noise.services.instruments import InstrumentService


class FakeKite:
    def __init__(self, instruments_result=None, error: Exception | None = None) -> None:
        self.instruments_result = instruments_result if instruments_result is not None else []
        self.error = error
        self.calls = 0

    def instruments(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.instruments_result


def _write_cache(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def _set_cache_mtime(path: Path, value: datetime) -> None:
    ts = value.timestamp()
    os.utime(path, (ts, ts))


def test_load_uses_todays_cache_without_downloading(tmp_path: Path) -> None:
    cache_path = tmp_path / "instruments.csv"
    cached_rows = [{"exchange": "BFO", "tradingsymbol": "SENSEX26MAY80700CE"}]
    _write_cache(cache_path, cached_rows)
    _set_cache_mtime(cache_path, datetime.now())

    kite = FakeKite(error=AssertionError("instruments() should not be called"))
    service = InstrumentService(kite=kite, cache_path=cache_path)

    df = service.load(force_refresh=False)

    assert kite.calls == 0
    assert df.to_dict(orient="records") == cached_rows


def test_load_refreshes_stale_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "instruments.csv"
    stale_rows = [{"exchange": "BFO", "tradingsymbol": "STALE"}]
    fresh_rows = [{"exchange": "BFO", "tradingsymbol": "FRESH"}]
    _write_cache(cache_path, stale_rows)
    _set_cache_mtime(cache_path, datetime.now() - timedelta(days=1))
    stale_mtime = cache_path.stat().st_mtime

    kite = FakeKite(instruments_result=fresh_rows)
    service = InstrumentService(kite=kite, cache_path=cache_path)

    df = service.load(force_refresh=False)

    assert kite.calls == 1
    assert df.to_dict(orient="records") == fresh_rows
    assert pd.read_csv(cache_path).to_dict(orient="records") == fresh_rows
    assert cache_path.stat().st_mtime >= stale_mtime


def test_load_force_refresh_ignores_todays_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "instruments.csv"
    cached_rows = [{"exchange": "BFO", "tradingsymbol": "TODAY"}]
    fresh_rows = [{"exchange": "BFO", "tradingsymbol": "FORCED"}]
    _write_cache(cache_path, cached_rows)
    _set_cache_mtime(cache_path, datetime.now())

    kite = FakeKite(instruments_result=fresh_rows)
    service = InstrumentService(kite=kite, cache_path=cache_path)

    df = service.load(force_refresh=True)

    assert kite.calls == 1
    assert df.to_dict(orient="records") == fresh_rows
    assert pd.read_csv(cache_path).to_dict(orient="records") == fresh_rows


def test_load_falls_back_to_stale_cache_if_download_fails(tmp_path: Path) -> None:
    cache_path = tmp_path / "instruments.csv"
    stale_rows = [{"exchange": "BFO", "tradingsymbol": "STALE_FALLBACK"}]
    _write_cache(cache_path, stale_rows)
    _set_cache_mtime(cache_path, datetime.now() - timedelta(days=1))

    kite = FakeKite(error=RuntimeError("download failed"))
    service = InstrumentService(kite=kite, cache_path=cache_path)

    df = service.load(force_refresh=False)

    assert kite.calls == 1
    assert df.to_dict(orient="records") == stale_rows
