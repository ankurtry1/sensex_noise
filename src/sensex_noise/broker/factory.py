from __future__ import annotations

from sensex_noise.broker.base import TradingBroker
from sensex_noise.broker.kite_live import KiteLiveBroker
from sensex_noise.broker.kite_paper import KitePaperBroker
from sensex_noise.config import Settings


def create_broker(settings: Settings) -> TradingBroker:
    if settings.trading_mode == "live":
        return KiteLiveBroker(
            api_key=settings.kite_api_key,
            access_token=settings.kite_access_token,
        )
    return KitePaperBroker(
        api_key=settings.kite_api_key,
        access_token=settings.kite_access_token,
        capital_budget=settings.capital_budget,
    )
