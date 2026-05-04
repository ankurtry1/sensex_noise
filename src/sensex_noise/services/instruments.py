from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from kiteconnect import KiteConnect

logger = logging.getLogger(__name__)


class InstrumentService:
    def __init__(self, kite: KiteConnect, cache_path: Path) -> None:
        self.kite = kite
        self.cache_path = cache_path

    def _cache_date(self) -> date | None:
        if not self.cache_path.exists():
            return None
        try:
            return datetime.fromtimestamp(self.cache_path.stat().st_mtime).date()
        except OSError:
            return None

    def _cache_is_fresh_today(self) -> bool:
        return self._cache_date() == date.today()

    def load(self, force_refresh: bool = False) -> pd.DataFrame:
        """Load the Kite instrument dump.

        The dump is date-sensitive. SENSEX weekly option contracts can change from
        session to session, and using an old cached `data/instruments.csv` may make
        the selector choose the monthly expiry simply because the current weekly
        expiry is absent from the stale cache. Therefore, the live path refreshes
        automatically when the cache is not from today.

        This refresh happens once at process startup when the engine builds the
        in-memory instrument universe. The trading path then reuses that in-memory
        dataframe for selection and must not download instruments before each trade.
        """
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        should_use_cache = self.cache_path.exists() and not force_refresh and self._cache_is_fresh_today()
        if should_use_cache:
            logger.info("Reading today's instrument dump from cache: %s", self.cache_path)
            return pd.read_csv(self.cache_path)

        if self.cache_path.exists() and not force_refresh:
            logger.info(
                "Instrument cache is stale or undated; refreshing dump | path=%s | cache_date=%s",
                self.cache_path,
                self._cache_date(),
            )

        logger.info("Downloading fresh instrument dump from Kite")
        try:
            instruments = self.kite.instruments()
        except Exception:
            if self.cache_path.exists():
                logger.exception(
                    "Fresh instrument download failed; falling back to cached dump: %s",
                    self.cache_path,
                )
                return pd.read_csv(self.cache_path)
            raise

        df = pd.DataFrame(instruments)
        df.to_csv(self.cache_path, index=False)
        logger.info("Instrument dump cached at: %s", self.cache_path)
        return df
