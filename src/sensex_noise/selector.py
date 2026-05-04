from __future__ import annotations

from typing import Any
from datetime import datetime

import pandas as pd

from sensex_noise.models import InstrumentChoice, SignalSide


class InstrumentSelector:
    def __init__(self, instruments: pd.DataFrame) -> None:
        self.instruments = instruments.copy()
        if "expiry" in self.instruments.columns:
            self.instruments["expiry"] = pd.to_datetime(self.instruments["expiry"], errors="coerce")

    @staticmethod
    def round_to_100(value: float) -> int:
        return int(round(value / 100.0) * 100)

    def computed_strike_for(self, *, spot: float, side: SignalSide) -> int:
        return self.round_to_100(spot - 200) if side == SignalSide.CALL else self.round_to_100(spot + 200)

    def _eligible_sensex_options(self, *, spot: float, side: SignalSide, now: datetime) -> pd.DataFrame:
        strike = self.computed_strike_for(spot=spot, side=side)
        option_type = "CE" if side == SignalSide.CALL else "PE"

        df = self.instruments.copy()
        if "name" in df.columns:
            df = df[df["name"].fillna("").str.upper().eq("SENSEX")]
        else:
            df = df[df["tradingsymbol"].str.contains("SENSEX", na=False)]

        df = df[
            (df["segment"].astype(str).str.contains("BFO|BSE", na=False))
            & (df["instrument_type"].astype(str).str.upper() == option_type)
            & (df["strike"].astype(float) == float(strike))
            & (df["expiry"].notna())
            & (df["expiry"] >= pd.Timestamp(now.date()))
        ].sort_values(["expiry", "tradingsymbol"])
        return df

    def eligible_expiries_for(self, *, spot: float, side: SignalSide, now: datetime) -> list[dict[str, Any]]:
        eligible = self._eligible_sensex_options(spot=spot, side=side, now=now)
        rows: list[dict[str, Any]] = []
        for _, row in eligible.iterrows():
            expiry = pd.Timestamp(row["expiry"]).date().isoformat() if pd.notna(row["expiry"]) else None
            rows.append(
                {
                    "expiry": expiry,
                    "tradingsymbol": str(row["tradingsymbol"]),
                    "strike": int(float(row["strike"])),
                    "instrument_type": str(row["instrument_type"]),
                    "exchange": str(row["exchange"]),
                    "segment": str(row["segment"]),
                }
            )
        return rows

    def pick_sensex_option(self, *, spot: float, side: SignalSide, now: datetime) -> InstrumentChoice:
        strike = self.computed_strike_for(spot=spot, side=side)
        option_type = "CE" if side == SignalSide.CALL else "PE"
        df = self._eligible_sensex_options(spot=spot, side=side, now=now)

        if df.empty:
            raise ValueError(
                f"No eligible option found for side={side}, strike={strike}. Check your instrument dump and exchange segment."
            )

        row = df.iloc[0]
        return InstrumentChoice(
            exchange=str(row["exchange"]),
            tradingsymbol=str(row["tradingsymbol"]),
            strike=int(float(row["strike"])),
            expiry=pd.Timestamp(row["expiry"]).to_pydatetime(),
            option_type=option_type,
            lot_size=int(row.get("lot_size", 20) or 20),
        )
