from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Iterable


@dataclass
class MicroburstFeatures:
    ind_velocity_aligned: float
    ind_accel_aligned: float
    opt_velocity_aligned: float
    opt_depth_imb_mean: float
    opt_spread_mean: float | None
    score: int
    score_components: dict[str, int]


@dataclass
class PromotionDiagnostics:
    velocity_0_1s: float | None
    velocity_2_3s: float | None
    velocity_decay_ratio: float | None
    runup_3s: float
    pnl_3s: float
    mae_3s: float


def _setting(settings: Any, name: str, default: float | int | bool) -> Any:
    return getattr(settings, name, default)


def _side_name(side: Any) -> str:
    raw = getattr(side, "value", side)
    return str(raw).upper()


def _aligned_underlying_sign(side: Any) -> float:
    return -1.0 if _side_name(side) == "PUT" else 1.0


def _extract_attr(record: Any, name: str) -> Any:
    if isinstance(record, dict):
        return record.get(name)
    return getattr(record, name, None)


def _extract_timestamp_price(record: Any) -> tuple[datetime | None, float | None]:
    ts = _extract_attr(record, "timestamp")
    if not isinstance(ts, datetime):
        ts = _extract_attr(record, "timestamp_exchange")
    if not isinstance(ts, datetime):
        return None, None

    raw_price = _extract_attr(record, "ltp")
    try:
        price = float(raw_price) if raw_price is not None else None
    except (TypeError, ValueError):
        price = None
    return ts, price


def _window_change(records: list[Any]) -> float:
    if len(records) < 2:
        return 0.0
    _, first_price = _extract_timestamp_price(records[0])
    _, last_price = _extract_timestamp_price(records[-1])
    if first_price is None or last_price is None:
        return 0.0
    return float(last_price - first_price)


def _split_by_midpoint(records: list[Any]) -> tuple[list[Any], list[Any]]:
    if len(records) < 2:
        return records, records
    first_ts, _ = _extract_timestamp_price(records[0])
    last_ts, _ = _extract_timestamp_price(records[-1])
    if first_ts is None or last_ts is None or last_ts <= first_ts:
        midpoint_index = max(1, len(records) // 2)
        return records[:midpoint_index], records[midpoint_index:]

    midpoint = first_ts + (last_ts - first_ts) / 2
    earlier = [record for record in records if (_extract_timestamp_price(record)[0] or first_ts) <= midpoint]
    later = [record for record in records if (_extract_timestamp_price(record)[0] or last_ts) >= midpoint]
    if not earlier:
        earlier = records[:1]
    if not later:
        later = records[-1:]
    return earlier, later


def _mean_depth_imbalance(records: Iterable[Any]) -> float:
    values: list[float] = []
    for record in records:
        bid_qty = _extract_attr(record, "bid_qty")
        ask_qty = _extract_attr(record, "ask_qty")
        try:
            bid = float(bid_qty) if bid_qty is not None else None
            ask = float(ask_qty) if ask_qty is not None else None
        except (TypeError, ValueError):
            bid = None
            ask = None
        if bid is None or ask is None or (bid + ask) <= 0:
            continue
        values.append((bid - ask) / (bid + ask))
    return float(mean(values)) if values else 0.0


def _mean_spread(records: Iterable[Any]) -> float | None:
    values: list[float] = []
    for record in records:
        raw = _extract_attr(record, "spread")
        try:
            spread = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            spread = None
        if spread is not None:
            values.append(spread)
    return float(mean(values)) if values else None


def score_microburst(features: MicroburstFeatures, settings: Any) -> tuple[int, dict[str, int]]:
    score_components = {
        "ind_accel_threshold_1": 0,
        "ind_accel_threshold_2": 0,
        "opt_velocity": 0,
        "opt_depth_imbalance": 0,
        "ind_velocity_band": 0,
    }

    accel_1 = float(_setting(settings, "microburst_ind_accel_threshold_1", 1.688))
    accel_2 = float(_setting(settings, "microburst_ind_accel_threshold_2", 3.945))
    opt_velocity = float(_setting(settings, "microburst_opt_velocity_threshold", 1.583))
    opt_imb = float(_setting(settings, "microburst_opt_depth_imb_threshold", 0.0857))
    ind_vel_min = float(_setting(settings, "microburst_ind_velocity_min", 1.646))
    ind_vel_max = float(_setting(settings, "microburst_ind_velocity_max", 2.356))

    if features.ind_accel_aligned > accel_1:
        score_components["ind_accel_threshold_1"] = 2
    if features.ind_accel_aligned > accel_2:
        score_components["ind_accel_threshold_2"] = 1
    if features.opt_velocity_aligned > opt_velocity:
        score_components["opt_velocity"] = 1
    if features.opt_depth_imb_mean > opt_imb:
        score_components["opt_depth_imbalance"] = 1
    if ind_vel_min < features.ind_velocity_aligned <= ind_vel_max:
        score_components["ind_velocity_band"] = 1

    return sum(score_components.values()), score_components


def compute_pre_entry_features(
    recent_underlying_window: Iterable[Any],
    recent_option_window: Iterable[Any],
    side: Any,
    settings: Any,
) -> MicroburstFeatures:
    underlying = list(recent_underlying_window)
    option = list(recent_option_window)
    sign = _aligned_underlying_sign(side)

    ind_velocity_aligned = sign * _window_change(underlying)
    early_underlying, late_underlying = _split_by_midpoint(underlying)
    ind_accel_aligned = sign * (_window_change(late_underlying) - _window_change(early_underlying))
    opt_velocity_aligned = _window_change(option)
    opt_depth_imb_mean = _mean_depth_imbalance(option)
    opt_spread_mean = _mean_spread(option)

    provisional = MicroburstFeatures(
        ind_velocity_aligned=ind_velocity_aligned,
        ind_accel_aligned=ind_accel_aligned,
        opt_velocity_aligned=opt_velocity_aligned,
        opt_depth_imb_mean=opt_depth_imb_mean,
        opt_spread_mean=opt_spread_mean,
        score=0,
        score_components={},
    )
    score, score_components = score_microburst(provisional, settings)
    provisional.score = score
    provisional.score_components = score_components
    return provisional


def classify_target(score: int, settings: Any) -> tuple[str, float]:
    promoted_min_score = int(_setting(settings, "promoted_min_score", 5))
    if int(score) >= promoted_min_score:
        return "promoted", float(_setting(settings, "promoted_target_points", 7.0))
    return "normal", float(_setting(settings, "normal_target_points", 3.0))


def _normalize_price_history(
    price_history: Iterable[tuple[datetime, float] | dict[str, Any]],
    *,
    current_time: datetime | None = None,
    current_price: float | None = None,
) -> list[tuple[datetime, float]]:
    out: list[tuple[datetime, float]] = []
    for row in price_history:
        if isinstance(row, tuple) and len(row) == 2 and isinstance(row[0], datetime):
            try:
                out.append((row[0], float(row[1])))
            except (TypeError, ValueError):
                continue
            continue

        if isinstance(row, dict):
            ts = row.get("timestamp") or row.get("timestamp_exchange")
            raw = row.get("ltp")
            if isinstance(ts, datetime):
                try:
                    out.append((ts, float(raw)))
                except (TypeError, ValueError):
                    continue

    if current_time is not None and current_price is not None:
        if not out or out[-1][0] != current_time:
            out.append((current_time, float(current_price)))
    out.sort(key=lambda item: item[0])
    return out


def _nearest_price(points: list[tuple[datetime, float]], target: datetime) -> float | None:
    if not points:
        return None
    nearest = min(
        points,
        key=lambda row: (abs((row[0] - target).total_seconds()), 0 if row[0] >= target else 1),
    )
    return nearest[1]


def compute_promoted_3s_diagnostics(
    price_history: Iterable[tuple[datetime, float] | dict[str, Any]],
    *,
    entry_time: datetime,
    entry_price: float,
    current_time: datetime | None = None,
    current_price: float | None = None,
) -> PromotionDiagnostics:
    points = _normalize_price_history(
        price_history,
        current_time=current_time,
        current_price=current_price,
    )
    cp_1 = entry_time + timedelta(seconds=1)
    cp_2 = entry_time + timedelta(seconds=2)
    cp_3 = current_time if current_time is not None else entry_time + timedelta(seconds=3)

    price_1 = _nearest_price(points, cp_1)
    price_2 = _nearest_price(points, cp_2)
    price_3 = _nearest_price(points, cp_3)

    velocity_0_1s = None if price_1 is None else float(price_1 - entry_price)
    velocity_2_3s = None if price_2 is None or price_3 is None else float(price_3 - price_2)

    velocity_decay_ratio: float | None = None
    if velocity_0_1s is not None and velocity_2_3s is not None and abs(velocity_0_1s) > 1e-9:
        velocity_decay_ratio = float(velocity_2_3s / velocity_0_1s)

    upto_3 = [(ts, price) for ts, price in points if ts <= cp_3]
    if not upto_3 and points:
        upto_3 = [min(points, key=lambda row: abs((row[0] - cp_3).total_seconds()))]

    if upto_3:
        pnl_values = [price - entry_price for _, price in upto_3]
        runup_3s = float(max(pnl_values))
        mae_3s = float(min(pnl_values))
    else:
        runup_3s = 0.0
        mae_3s = 0.0

    if price_3 is not None:
        pnl_3s = float(price_3 - entry_price)
    elif upto_3:
        pnl_3s = float(upto_3[-1][1] - entry_price)
    else:
        pnl_3s = 0.0

    return PromotionDiagnostics(
        velocity_0_1s=velocity_0_1s,
        velocity_2_3s=velocity_2_3s,
        velocity_decay_ratio=velocity_decay_ratio,
        runup_3s=runup_3s,
        pnl_3s=pnl_3s,
        mae_3s=mae_3s,
    )


def promoted_trade_survives_3s(diag: PromotionDiagnostics, settings: Any) -> tuple[bool, str]:
    min_runup = float(_setting(settings, "promoted_3s_min_runup_points", 4.0))
    min_pnl = float(_setting(settings, "promoted_3s_min_pnl_points", 1.5))
    max_mae = float(_setting(settings, "promoted_3s_max_mae_points", 3.5))
    min_ratio = float(_setting(settings, "promoted_3s_min_velocity_decay_ratio", 0.5))

    if diag.runup_3s < min_runup:
        return False, "RUNUP_BELOW_MIN"
    if diag.pnl_3s <= min_pnl:
        return False, "PNL_BELOW_MIN"
    if diag.mae_3s <= -max_mae:
        return False, "MAE_TOO_NEGATIVE"
    if diag.velocity_decay_ratio is None:
        return False, "VELOCITY_RATIO_UNAVAILABLE"
    if diag.velocity_decay_ratio < min_ratio:
        return False, "VELOCITY_DECAY_TOO_HIGH"
    return True, "PASS"


def layer4_persistence_result(
    *,
    now: datetime,
    first_hit_time: datetime | None,
    deadline_time: datetime | None,
    current_pnl: float,
    settings: Any,
    persistence_passed: bool = False,
) -> tuple[str, str]:
    if first_hit_time is None or deadline_time is None:
        return "inactive", "NOT_ARMED"
    if persistence_passed:
        return "pass", "ALREADY_PASSED"

    required_followthrough = float(_setting(settings, "layer4_required_followthrough_points", 4.5))
    if current_pnl >= required_followthrough and now <= deadline_time:
        return "pass", "FOLLOWTHROUGH_REACHED"
    if now >= deadline_time:
        return "fail", "WINDOW_EXPIRED"
    return "pending", "WINDOW_OPEN"
