#!/usr/bin/env python3
"""Inspect which SENSEX expiry would be selected for a given spot/side."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from kiteconnect import KiteConnect

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sensex_noise.config import load_settings
from sensex_noise.models import SignalSide
from sensex_noise.selector import InstrumentSelector
from sensex_noise.services.instruments import InstrumentService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check SENSEX weekly/monthly expiry selection.")
    parser.add_argument("--spot", type=float, required=True, help="Current SENSEX spot price.")
    parser.add_argument(
        "--side",
        choices=[side.value for side in SignalSide],
        required=True,
        help="Signal side to inspect.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore today's cache and refresh the instrument dump once.",
    )
    parser.add_argument(
        "--now",
        default=None,
        help="Optional ISO timestamp override, for example 2026-05-04T10:00:00.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = load_settings()
    side = SignalSide(args.side)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now()

    kite = KiteConnect(api_key=settings.kite_api_key)
    kite.set_access_token(settings.kite_access_token)
    service = InstrumentService(kite=kite, cache_path=settings.instruments_cache_path)
    instruments = service.load(force_refresh=args.force_refresh)
    selector = InstrumentSelector(instruments)

    cache_path = settings.instruments_cache_path
    cache_mtime = None
    if cache_path.exists():
        cache_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime).isoformat()

    choice = selector.pick_sensex_option(spot=args.spot, side=side, now=now)
    eligible = selector.eligible_expiries_for(spot=args.spot, side=side, now=now)
    payload = {
        "cache_path": str(cache_path),
        "cache_mtime": cache_mtime,
        "force_refresh": bool(args.force_refresh),
        "now": now.isoformat(),
        "spot": float(args.spot),
        "side": side.value,
        "computed_strike": selector.computed_strike_for(spot=args.spot, side=side),
        "selected": {
            "exchange": choice.exchange,
            "tradingsymbol": choice.tradingsymbol,
            "strike": choice.strike,
            "expiry": choice.expiry.isoformat(),
            "option_type": choice.option_type,
            "lot_size": choice.lot_size,
        },
        "eligible_expiries": eligible,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
