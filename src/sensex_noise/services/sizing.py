from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


def calculate_position_quantity(
    option_ltp: float,
    lot_size: int,
    capital_budget: float,
    available_funds: float,
) -> int | None:
    if option_ltp <= 0 or lot_size <= 0:
        return None

    usable_capital = min(float(capital_budget), float(available_funds))
    logger.info(
        "Sizing debug | available_funds=%.2f | capital_budget=%.2f | usable_capital=%.2f",
        float(available_funds),
        float(capital_budget),
        usable_capital,
    )
    logger.info(
        "Sizing debug | option_ltp=%.2f | lot_size=%d",
        float(option_ltp),
        int(lot_size),
    )

    cost_per_lot = float(option_ltp) * int(lot_size)
    if cost_per_lot <= 0:
        return None

    lots = math.floor(usable_capital / cost_per_lot)
    quantity = lots * int(lot_size)
    logger.info(
        "Sizing debug | cost_per_lot=%.2f | lots=%d | quantity=%d",
        cost_per_lot,
        lots,
        quantity,
    )

    if lots <= 0:
        return None
    return quantity
