from __future__ import annotations

from datetime import datetime
from typing import Any

from sensex_noise.streaming.token_registry import TokenRegistry


def _best_price(depth_side: list[dict[str, Any]] | None) -> float | None:
    if not depth_side:
        return None
    first = depth_side[0]
    try:
        raw = first.get("price")
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _normalize_depth(depth_side: list[dict[str, Any]] | None) -> list[dict[str, float | int | None]]:
    rows: list[dict[str, float | int | None]] = []
    for row in (depth_side or [])[:5]:
        price = row.get("price")
        quantity = row.get("quantity")
        orders = row.get("orders")
        try:
            price_out = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_out = None
        try:
            qty_out = int(quantity) if quantity is not None else None
        except (TypeError, ValueError):
            qty_out = None
        try:
            orders_out = int(orders) if orders is not None else None
        except (TypeError, ValueError):
            orders_out = None
        rows.append({"price": price_out, "quantity": qty_out, "orders": orders_out})
    return rows


class TickNormalizer:
    """Normalizes Kite tick packets into a strict, strategy-friendly schema."""

    def __init__(self, registry: TokenRegistry) -> None:
        self.registry = registry

    def normalize(self, raw_tick: dict[str, Any], timestamp_receive: datetime) -> dict[str, Any] | None:
        token_raw = raw_tick.get("instrument_token")
        if token_raw is None:
            return None

        try:
            token = int(token_raw)
        except (TypeError, ValueError):
            return None

        meta = self.registry.meta_by_token(token)
        if meta is None:
            return None

        exchange_ts = (
            raw_tick.get("timestamp")
            or raw_tick.get("last_trade_time")
            or timestamp_receive
        )
        if not isinstance(exchange_ts, datetime):
            exchange_ts = timestamp_receive

        depth = raw_tick.get("depth") if isinstance(raw_tick.get("depth"), dict) else {}
        buy_depth = depth.get("buy") if isinstance(depth, dict) else []
        sell_depth = depth.get("sell") if isinstance(depth, dict) else []

        best_bid = _best_price(buy_depth)
        best_ask = _best_price(sell_depth)
        spread = (best_ask - best_bid) if best_bid is not None and best_ask is not None else None

        ltp_raw = raw_tick.get("last_price")
        if ltp_raw is None:
            return None

        try:
            ltp = float(ltp_raw)
        except (TypeError, ValueError):
            return None

        ltq_raw = raw_tick.get("last_traded_quantity")
        vol_raw = raw_tick.get("volume_traded")
        oi_raw = raw_tick.get("oi")

        try:
            ltq = int(ltq_raw) if ltq_raw is not None else 0
        except (TypeError, ValueError):
            ltq = 0
        try:
            volume = int(vol_raw) if vol_raw is not None else 0
        except (TypeError, ValueError):
            volume = 0
        try:
            oi = int(oi_raw) if oi_raw is not None else 0
        except (TypeError, ValueError):
            oi = 0

        return {
            "timestamp_exchange": exchange_ts,
            "timestamp_receive": timestamp_receive,
            "symbol": meta.full_symbol,
            "instrument_token": token,
            "tradingsymbol": meta.tradingsymbol,
            "exchange": meta.exchange,
            "strike": meta.strike,
            "expiry": meta.expiry.date().isoformat() if meta.expiry is not None else None,
            "option_type": meta.option_type,
            "lot_size": meta.lot_size,
            "ltp": ltp,
            "ltq": ltq,
            "volume": volume,
            "oi": oi,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "bid[5]": _normalize_depth(buy_depth),
            "ask[5]": _normalize_depth(sell_depth),
            "source": meta.source,
        }
