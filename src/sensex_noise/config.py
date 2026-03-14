from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    kite_api_key: str
    kite_api_secret: str
    kite_access_token: str
    kite_request_token: str
    poll_interval_seconds: int
    starting_capital: float
    trade_qty: int
    order_product: str
    trading_mode: str
    position_sizing_mode: str
    capital_budget: float
    use_kite_funds: bool
    target_points: float
    entry_buffer_points: float
    call_offset_points: int
    put_offset_points: int
    underlying_symbol: str
    instruments_cache_path: Path
    trade_log_path: Path
    control_path: Path
    entry_cutoff_time: str
    log_level: str


def _required(name: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        raise ValueError(f"Missing required environment variable: {name}. Add it to .env.")

    value = raw.strip()
    if not value:
        raise ValueError(f"Environment variable {name} is empty/whitespace. Set a valid value in .env.")
    return value


def _bool(name: str, default: str = "false") -> bool:
    raw = os.getenv(name, default).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=repo_root / ".env")
    settings = Settings(
        kite_api_key=_required("KITE_API_KEY"),
        kite_api_secret=os.getenv("KITE_API_SECRET", "").strip(),
        kite_access_token=_required("KITE_ACCESS_TOKEN"),
        kite_request_token=os.getenv("KITE_REQUEST_TOKEN", "").strip(),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "2")),
        starting_capital=float(os.getenv("STARTING_CAPITAL", "1000000")),
        trade_qty=int(os.getenv("TRADE_QTY", "500")),
        order_product=os.getenv("ORDER_PRODUCT", "MIS").strip().upper(),
        trading_mode=os.getenv("TRADING_MODE", "paper").strip().lower(),
        position_sizing_mode=os.getenv("POSITION_SIZING_MODE", "fixed").strip().lower(),
        capital_budget=float(os.getenv("CAPITAL_BUDGET", "300000")),
        use_kite_funds=_bool("USE_KITE_FUNDS", "false"),
        target_points=float(os.getenv("TARGET_POINTS", "3")),
        entry_buffer_points=float(os.getenv("ENTRY_BUFFER_POINTS", "5")),
        call_offset_points=int(os.getenv("CALL_OFFSET_POINTS", "-200")),
        put_offset_points=int(os.getenv("PUT_OFFSET_POINTS", "200")),
        underlying_symbol=os.getenv("UNDERLYING_SYMBOL", "BSE:SENSEX"),
        instruments_cache_path=Path(os.getenv("INSTRUMENTS_CACHE_PATH", "data/instruments.csv")),
        trade_log_path=Path(os.getenv("TRADE_LOG_PATH", "logs/trades.jsonl")),
        control_path=Path(os.getenv("CONTROL_PATH", "runtime/control.json")),
        entry_cutoff_time=os.getenv("ENTRY_CUTOFF_TIME", "14:55"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
    if settings.trading_mode not in {"paper", "live"}:
        raise ValueError("TRADING_MODE must be one of: paper, live")
    if settings.order_product not in {"MIS", "NRML"}:
        raise ValueError("ORDER_PRODUCT must be one of: MIS, NRML")
    if settings.position_sizing_mode not in {"fixed", "capital_based"}:
        raise ValueError("POSITION_SIZING_MODE must be one of: fixed, capital_based")
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return settings
