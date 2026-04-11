from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class TokenMeta:
    instrument_token: int
    full_symbol: str
    exchange: str
    tradingsymbol: str
    source: str
    strike: int | None = None
    expiry: datetime | None = None
    option_type: str | None = None
    lot_size: int | None = None


class TokenRegistry:
    """Symbol/token registry for SENSEX index, nearest future, and dynamic option lattice."""

    def __init__(self, instruments: pd.DataFrame, underlying_symbol: str = "BSE:SENSEX") -> None:
        self.underlying_symbol = underlying_symbol
        self.instruments = instruments.copy()
        if "expiry" in self.instruments.columns:
            self.instruments["expiry"] = pd.to_datetime(self.instruments["expiry"], errors="coerce")

        self._meta_by_symbol: dict[str, TokenMeta] = {}
        self._meta_by_token: dict[int, TokenMeta] = {}
        self._index_meta: TokenMeta | None = None
        self._future_meta: TokenMeta | None = None
        self._active_option_symbols: set[str] = set()

        self._seed_registry()

    @staticmethod
    def round_to_100(value: float) -> int:
        return int(round(float(value) / 100.0) * 100)

    @property
    def index_meta(self) -> TokenMeta:
        if self._index_meta is None:
            raise ValueError(f"Underlying symbol not found in instruments: {self.underlying_symbol}")
        return self._index_meta

    @property
    def future_meta(self) -> TokenMeta:
        if self._future_meta is None:
            raise ValueError("Nearest SENSEX future not found in instruments")
        return self._future_meta

    @property
    def active_option_symbols(self) -> set[str]:
        return set(self._active_option_symbols)

    def meta_by_symbol(self, full_symbol: str) -> TokenMeta | None:
        return self._meta_by_symbol.get(full_symbol)

    def meta_by_token(self, token: int) -> TokenMeta | None:
        return self._meta_by_token.get(int(token))

    def token_for_symbol(self, full_symbol: str) -> int | None:
        meta = self.meta_by_symbol(full_symbol)
        return None if meta is None else meta.instrument_token

    def symbol_for_token(self, token: int) -> str | None:
        meta = self.meta_by_token(token)
        return None if meta is None else meta.full_symbol

    def initial_tokens(self) -> list[int]:
        return [self.index_meta.instrument_token, self.future_meta.instrument_token]

    def initial_atm_hint(self) -> int | None:
        """Best-effort startup ATM hint from instrument dump (if last_price is populated)."""
        for symbol in (self.future_meta.full_symbol, self.index_meta.full_symbol):
            exchange, tradingsymbol = symbol.split(":", 1)
            rows = self.instruments[
                (self.instruments["exchange"].astype(str).str.upper() == exchange)
                & (self.instruments["tradingsymbol"].astype(str) == tradingsymbol)
            ]
            if rows.empty:
                continue
            raw = rows.iloc[0].get("last_price")
            try:
                price = float(raw)
            except (TypeError, ValueError):
                price = 0.0
            if price > 0:
                return self.round_to_100(price)
        return None

    def option_lattice_for_atm(self, atm: int, now: datetime) -> list[TokenMeta]:
        strike_grid = list(range(int(atm) - 300, int(atm) + 301, 100))
        options = self._sensex_options_frame(now=now)
        if options.empty:
            return []

        # Keep one nearest expiry lattice at a time.
        nearest_expiry = options["expiry"].min()
        options = options[options["expiry"] == nearest_expiry]

        selected: list[TokenMeta] = []
        for strike in strike_grid:
            for opt_type in ("CE", "PE"):
                rows = options[
                    (options["instrument_type"].astype(str).str.upper() == opt_type)
                    & (options["strike"].astype(float) == float(strike))
                ]
                if rows.empty:
                    continue
                row = rows.iloc[0]
                meta = self._row_to_meta(row=row, source="option")
                self._register(meta)
                selected.append(meta)
        self._active_option_symbols = {meta.full_symbol for meta in selected}
        return selected

    def _seed_registry(self) -> None:
        for _, row in self.instruments.iterrows():
            exchange = str(row.get("exchange", "") or "").strip().upper()
            tradingsymbol = str(row.get("tradingsymbol", "") or "").strip()
            if not exchange or not tradingsymbol:
                continue
            full_symbol = f"{exchange}:{tradingsymbol}"
            name = str(row.get("name", "") or "").strip().upper()
            inst_type = str(row.get("instrument_type", "") or "").strip().upper()

            if full_symbol == self.underlying_symbol:
                meta = self._row_to_meta(row=row, source="index")
                self._register(meta)
                self._index_meta = meta
                continue

            # Keep SENSEX family in local registry to support option lookups and manual symbol mapping.
            if name != "SENSEX" and "SENSEX" not in tradingsymbol.upper():
                continue

            source = "option" if inst_type in {"CE", "PE"} else "future" if inst_type == "FUT" else "index"
            meta = self._row_to_meta(row=row, source=source)
            self._register(meta)

        self._future_meta = self._resolve_nearest_future()

    def _resolve_nearest_future(self) -> TokenMeta | None:
        today = pd.Timestamp(datetime.now().date())
        candidates = self.instruments.copy()
        if "name" in candidates.columns:
            candidates = candidates[candidates["name"].astype(str).str.upper() == "SENSEX"]
        else:
            candidates = candidates[candidates["tradingsymbol"].astype(str).str.contains("SENSEX", na=False)]

        candidates = candidates[
            (candidates["instrument_type"].astype(str).str.upper() == "FUT")
            & (candidates["expiry"].notna())
            & (candidates["expiry"] >= today)
        ].sort_values(["expiry", "tradingsymbol"])
        if candidates.empty:
            return None

        row = candidates.iloc[0]
        meta = self._row_to_meta(row=row, source="future")
        self._register(meta)
        return meta

    def _sensex_options_frame(self, now: datetime) -> pd.DataFrame:
        df = self.instruments.copy()
        if "name" in df.columns:
            df = df[df["name"].astype(str).str.upper() == "SENSEX"]
        else:
            df = df[df["tradingsymbol"].astype(str).str.contains("SENSEX", na=False)]

        return df[
            (df["instrument_type"].astype(str).str.upper().isin({"CE", "PE"}))
            & (df["expiry"].notna())
            & (df["expiry"] >= pd.Timestamp(now.date()))
            & (df["segment"].astype(str).str.contains("BFO|BSE", na=False))
        ].sort_values(["expiry", "strike", "tradingsymbol"])

    def _register(self, meta: TokenMeta) -> None:
        self._meta_by_symbol[meta.full_symbol] = meta
        self._meta_by_token[int(meta.instrument_token)] = meta

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _row_to_meta(row: Any, source: str) -> TokenMeta:
        exchange = str(row.get("exchange", "") or "").strip().upper()
        tradingsymbol = str(row.get("tradingsymbol", "") or "").strip()
        if not exchange or not tradingsymbol:
            raise ValueError("Instrument row missing exchange/tradingsymbol")

        token = int(row.get("instrument_token"))
        expiry_raw = row.get("expiry")
        expiry: datetime | None = None
        if pd.notna(expiry_raw):
            expiry = pd.Timestamp(expiry_raw).to_pydatetime()

        option_type = str(row.get("instrument_type", "") or "").strip().upper()
        if option_type not in {"CE", "PE"}:
            option_type = None

        return TokenMeta(
            instrument_token=token,
            full_symbol=f"{exchange}:{tradingsymbol}",
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            source=source,
            strike=TokenRegistry._safe_int(row.get("strike")),
            expiry=expiry,
            option_type=option_type,
            lot_size=TokenRegistry._safe_int(row.get("lot_size")),
        )
