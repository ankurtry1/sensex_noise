from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from kiteconnect import KiteConnect

logger = logging.getLogger(__name__)


class InstrumentService:
    def __init__(self, kite: KiteConnect, cache_path: Path) -> None:
        self.kite = kite
        self.cache_path = cache_path

    def load(self, force_refresh: bool = False) -> pd.DataFrame:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_path.exists() and not force_refresh:
            logger.info("Reading instrument dump from cache: %s", self.cache_path)
            return pd.read_csv(self.cache_path)

        logger.info("Downloading fresh instrument dump from Kite")
        instruments = self.kite.instruments()
        df = pd.DataFrame(instruments)
        df.to_csv(self.cache_path, index=False)
        logger.info("Instrument dump cached at: %s", self.cache_path)
        return df
