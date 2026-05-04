from datetime import datetime

import pandas as pd

from sensex_noise.models import SignalSide
from sensex_noise.selector import InstrumentSelector


def test_round_to_100() -> None:
    assert InstrumentSelector.round_to_100(77943) == 77900
    assert InstrumentSelector.round_to_100(78343) == 78300
    assert InstrumentSelector.round_to_100(77850) == 77800 or InstrumentSelector.round_to_100(77850) == 77900


def test_pick_sensex_option() -> None:
    df = pd.DataFrame(
        [
            {
                "exchange": "BFO",
                "tradingsymbol": "SENSEX26MAR77900CE",
                "name": "SENSEX",
                "segment": "BFO-OPT",
                "instrument_type": "CE",
                "strike": 77900,
                "expiry": "2026-03-26",
                "lot_size": 20,
            },
            {
                "exchange": "BFO",
                "tradingsymbol": "SENSEX26MAR78300PE",
                "name": "SENSEX",
                "segment": "BFO-OPT",
                "instrument_type": "PE",
                "strike": 78300,
                "expiry": "2026-03-26",
                "lot_size": 20,
            },
        ]
    )
    selector = InstrumentSelector(df)
    call_choice = selector.pick_sensex_option(spot=78143, side=SignalSide.CALL, now=datetime(2026, 3, 10, 10, 0))
    put_choice = selector.pick_sensex_option(spot=78143, side=SignalSide.PUT, now=datetime(2026, 3, 10, 10, 0))
    assert call_choice.strike == 77900
    assert put_choice.strike == 78300


def test_pick_sensex_option_prefers_nearest_expiry_over_monthly() -> None:
    df = pd.DataFrame(
        [
            {
                "exchange": "BFO",
                "tradingsymbol": "SENSEX26MAY0780700CE",
                "name": "SENSEX",
                "segment": "BFO-OPT",
                "instrument_type": "CE",
                "strike": 80700,
                "expiry": "2026-05-07",
                "lot_size": 20,
            },
            {
                "exchange": "BFO",
                "tradingsymbol": "SENSEX26MAY2880700CE",
                "name": "SENSEX",
                "segment": "BFO-OPT",
                "instrument_type": "CE",
                "strike": 80700,
                "expiry": "2026-05-28",
                "lot_size": 20,
            },
        ]
    )
    selector = InstrumentSelector(df)

    choice = selector.pick_sensex_option(
        spot=80900,
        side=SignalSide.CALL,
        now=datetime(2026, 5, 4, 10, 0),
    )

    assert choice.strike == 80700
    assert choice.tradingsymbol == "SENSEX26MAY0780700CE"
    assert choice.expiry.date().isoformat() == "2026-05-07"
    assert selector.eligible_expiries_for(
        spot=80900,
        side=SignalSide.CALL,
        now=datetime(2026, 5, 4, 10, 0),
    ) == [
        {
            "expiry": "2026-05-07",
            "tradingsymbol": "SENSEX26MAY0780700CE",
            "strike": 80700,
            "instrument_type": "CE",
            "exchange": "BFO",
            "segment": "BFO-OPT",
        },
        {
            "expiry": "2026-05-28",
            "tradingsymbol": "SENSEX26MAY2880700CE",
            "strike": 80700,
            "instrument_type": "CE",
            "exchange": "BFO",
            "segment": "BFO-OPT",
        },
    ]


def test_pick_sensex_put_prefers_nearest_expiry_over_monthly() -> None:
    df = pd.DataFrame(
        [
            {
                "exchange": "BFO",
                "tradingsymbol": "SENSEX26MAY0781100PE",
                "name": "SENSEX",
                "segment": "BFO-OPT",
                "instrument_type": "PE",
                "strike": 81100,
                "expiry": "2026-05-07",
                "lot_size": 20,
            },
            {
                "exchange": "BFO",
                "tradingsymbol": "SENSEX26MAY2881100PE",
                "name": "SENSEX",
                "segment": "BFO-OPT",
                "instrument_type": "PE",
                "strike": 81100,
                "expiry": "2026-05-28",
                "lot_size": 20,
            },
        ]
    )
    selector = InstrumentSelector(df)

    choice = selector.pick_sensex_option(
        spot=80900,
        side=SignalSide.PUT,
        now=datetime(2026, 5, 4, 10, 0),
    )

    assert choice.strike == 81100
    assert choice.tradingsymbol == "SENSEX26MAY0781100PE"
    assert choice.expiry.date().isoformat() == "2026-05-07"
