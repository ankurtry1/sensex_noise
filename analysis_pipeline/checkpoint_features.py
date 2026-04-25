from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from .constants import CHECKPOINT_SECONDS
from .io_utils import nearest_value_at_or_after, parse_timestamp
from .trade_path import TradePathLoader


def _cp_tag(seconds: float) -> str:
    s = f"{seconds:g}"
    return s.replace(".", "p") + "s"


def _nearest_leq(df: pd.DataFrame, target: datetime, ts_col: str = "timestamp_exchange") -> pd.Series | None:
    if df.empty:
        return None
    sub = df[df[ts_col] <= target]
    if sub.empty:
        return None
    return sub.sort_values(ts_col).iloc[-1]


def _extract_depth_qty(depth: Any) -> float | None:
    if not isinstance(depth, list) or not depth:
        return None
    row = depth[0]
    if not isinstance(row, dict):
        return None
    qty = row.get("quantity")
    try:
        return float(qty)
    except (TypeError, ValueError):
        return None


def _microprice(bid: float | None, ask: float | None, bid_qty: float | None, ask_qty: float | None) -> float | None:
    if bid is None or ask is None or bid_qty is None or ask_qty is None:
        return None
    denom = bid_qty + ask_qty
    if denom <= 0:
        return None
    return (ask * bid_qty + bid * ask_qty) / denom


def _first_sign_times(option_after_entry: pd.DataFrame, entry_price: float) -> tuple[float | None, float | None]:
    if option_after_entry.empty:
        return None, None
    t_pos = None
    t_neg = None
    start = option_after_entry["timestamp_exchange"].iloc[0]
    for _, r in option_after_entry.iterrows():
        ts = r["timestamp_exchange"]
        pnl = float(r["ltp"]) - entry_price
        dt = (ts - start).total_seconds()
        if pnl > 0 and t_pos is None:
            t_pos = dt
        if pnl < 0 and t_neg is None:
            t_neg = dt
        if t_pos is not None and t_neg is not None:
            break
    return t_pos, t_neg


def _value_at_entry(df: pd.DataFrame, entry_time: datetime, value_col: str = "ltp") -> float | None:
    if df.empty:
        return None
    row = _nearest_leq(df, entry_time)
    if row is None:
        row = df.sort_values("timestamp_exchange").iloc[0]
    try:
        return float(row.get(value_col))
    except (TypeError, ValueError):
        return None


def build_checkpoint_features(
    reconciled_df: pd.DataFrame,
    loader: TradePathLoader,
    checkpoints: tuple[float, ...] = CHECKPOINT_SECONDS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    long_rows: list[dict[str, Any]] = []
    availability_rows: list[dict[str, Any]] = []

    if reconciled_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    for _, trade in reconciled_df.iterrows():
        if trade.get("match_status") != "reconciled":
            continue

        entry_time = parse_timestamp(trade.get("entry_time"))
        exit_time = parse_timestamp(trade.get("exit_time"))
        entry_price = trade.get("entry_price")
        try:
            entry_price = float(entry_price)
        except (TypeError, ValueError):
            continue
        if entry_time is None or exit_time is None:
            continue

        ctx = loader.load_trade_context(trade.to_dict())
        if ctx is None:
            continue

        option = ctx.option_ticks.copy()
        if option.empty:
            base = {
                "trade_id": trade.get("trade_id"),
                "date": trade.get("date"),
                "label_final": "winner" if float(trade.get("net_pnl", 0) or 0) > 0 else "loser",
                "has_trade_ticks": False,
                "has_underlying_ticks": ctx.has_underlying_ticks,
                "has_futures_ticks": ctx.has_futures_ticks,
                "has_depth": ctx.has_depth,
                "has_subsecond_time": ctx.has_subsecond_time,
                "feature_extraction_status": "NO_OPTION_TICKS",
                "fill_method": ctx.fill_method,
            }
            rows.append(base)
            availability_rows.append(base)
            continue

        option = option.sort_values("timestamp_exchange").reset_index(drop=True)
        option_after = option[option["timestamp_exchange"] >= entry_time].copy().reset_index(drop=True)
        if option_after.empty:
            base = {
                "trade_id": trade.get("trade_id"),
                "date": trade.get("date"),
                "label_final": "winner" if float(trade.get("net_pnl", 0) or 0) > 0 else "loser",
                "has_trade_ticks": True,
                "has_underlying_ticks": ctx.has_underlying_ticks,
                "has_futures_ticks": ctx.has_futures_ticks,
                "has_depth": ctx.has_depth,
                "has_subsecond_time": ctx.has_subsecond_time,
                "feature_extraction_status": "NO_POST_ENTRY_OPTION_TICKS",
                "fill_method": ctx.fill_method,
            }
            rows.append(base)
            availability_rows.append(base)
            continue

        option_after["seconds_from_entry"] = (
            option_after["timestamp_exchange"] - entry_time
        ).dt.total_seconds()
        option_after["pnl"] = option_after["ltp"].astype(float) - entry_price

        first_pos, first_neg = _first_sign_times(option_after, entry_price)

        row_out: dict[str, Any] = {
            "trade_id": trade.get("trade_id"),
            "date": trade.get("date"),
            "symbol": trade.get("symbol"),
            "signal_kind": trade.get("signal_kind"),
            "side": trade.get("side"),
            "pre_or_post_1pm": trade.get("pre_or_post_1pm"),
            "net_pnl": float(trade.get("net_pnl") or 0.0),
            "exit_reason": trade.get("exit_reason"),
            "hold_seconds": float(trade.get("hold_seconds") or 0.0),
            "has_trade_ticks": ctx.has_trade_ticks,
            "has_underlying_ticks": ctx.has_underlying_ticks,
            "has_futures_ticks": ctx.has_futures_ticks,
            "has_depth": ctx.has_depth,
            "has_subsecond_time": ctx.has_subsecond_time,
            "fill_method": ctx.fill_method,
            "feature_extraction_status": "OK",
            "first_move_direction": (
                "POSITIVE" if (first_pos is not None and (first_neg is None or first_pos <= first_neg))
                else "NEGATIVE" if first_neg is not None
                else "UNKNOWN"
            ),
            "time_to_first_favorable": first_pos,
            "time_to_first_adverse": first_neg,
            "adverse_before_favorable": (
                int(first_neg is not None and (first_pos is None or first_neg < first_pos))
            ),
            "entry_spread": trade.get("entry_spread"),
        }

        index_entry = _value_at_entry(ctx.index_ticks, entry_time) if ctx.has_underlying_ticks else None
        fut_entry = _value_at_entry(ctx.futures_ticks, entry_time) if ctx.has_futures_ticks else None

        for cp in checkpoints:
            cp_ts = entry_time + timedelta(seconds=float(cp))
            cp_tag = _cp_tag(cp)

            seen = option_after[option_after["timestamp_exchange"] <= cp_ts]
            last = _nearest_leq(option_after, cp_ts)

            if last is None:
                row_out[f"missing_update_{cp_tag}"] = 1
                row_out[f"stale_quote_{cp_tag}"] = 1
                row_out[f"pnl_{cp_tag}"] = np.nan
                row_out[f"runup_{cp_tag}"] = np.nan
                row_out[f"drawdown_{cp_tag}"] = np.nan
                row_out[f"num_price_changes_{cp_tag}"] = 0
                long_rows.append(
                    {
                        "trade_id": trade.get("trade_id"),
                        "date": trade.get("date"),
                        "checkpoint_seconds": cp,
                        "available": 0,
                    }
                )
                continue

            last_ts = last["timestamp_exchange"]
            last_pnl = float(last["ltp"]) - entry_price
            stale = int((cp_ts - last_ts).total_seconds() > 1.0)
            missing = int(seen.empty)

            runup = float(seen["pnl"].max()) if not seen.empty else last_pnl
            drawdown = float(seen["pnl"].min()) if not seen.empty else last_pnl
            changes = int(seen["ltp"].diff().fillna(0).ne(0).sum()) if not seen.empty else 0
            elapsed = max(cp, 1e-6)
            vel = float(last_pnl / elapsed)

            bid_qty = _extract_depth_qty(last.get("bid5"))
            ask_qty = _extract_depth_qty(last.get("ask5"))
            imbalance = None
            if bid_qty is not None and ask_qty is not None and (bid_qty + ask_qty) > 0:
                imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty)

            bid = last.get("best_bid")
            ask = last.get("best_ask")
            spread = last.get("spread")
            micro = _microprice(bid, ask, bid_qty, ask_qty)

            # Underlying and futures context.
            index_last = _nearest_leq(ctx.index_ticks, cp_ts) if ctx.has_underlying_ticks else None
            fut_last = _nearest_leq(ctx.futures_ticks, cp_ts) if ctx.has_futures_ticks else None
            u_move = None
            f_move = None
            u_vel = None
            f_vel = None
            div = None
            if index_last is not None and index_entry is not None:
                try:
                    u_move = float(index_last.get("ltp")) - float(index_entry)
                    u_vel = u_move / elapsed
                except (TypeError, ValueError):
                    pass
            if fut_last is not None and fut_entry is not None:
                try:
                    f_move = float(fut_last.get("ltp")) - float(fut_entry)
                    f_vel = f_move / elapsed
                except (TypeError, ValueError):
                    pass
            if u_move is not None and f_move is not None:
                div = u_move - f_move

            cf_pnl = nearest_value_at_or_after(
                option_after,
                target_ts=cp_ts,
                value_col="ltp",
                ts_col="timestamp_exchange",
                tolerance_seconds=2.0,
            )
            if cf_pnl is not None:
                cf_pnl = float(cf_pnl) - entry_price

            row_out[f"missing_update_{cp_tag}"] = missing
            row_out[f"stale_quote_{cp_tag}"] = stale
            row_out[f"pnl_{cp_tag}"] = last_pnl
            row_out[f"runup_{cp_tag}"] = runup
            row_out[f"drawdown_{cp_tag}"] = drawdown
            row_out[f"net_excursion_{cp_tag}"] = runup + drawdown
            row_out[f"num_price_changes_{cp_tag}"] = changes
            row_out[f"tick_velocity_{cp_tag}"] = vel
            row_out[f"spread_{cp_tag}"] = spread
            row_out[f"spread_vs_entry_{cp_tag}"] = (
                (float(spread) - float(trade.get("entry_spread")))
                if spread is not None and trade.get("entry_spread") is not None
                else np.nan
            )
            row_out[f"bid_qty_{cp_tag}"] = bid_qty
            row_out[f"ask_qty_{cp_tag}"] = ask_qty
            row_out[f"depth_imbalance_{cp_tag}"] = imbalance
            row_out[f"microprice_{cp_tag}"] = micro
            row_out[f"underlying_move_{cp_tag}"] = u_move
            row_out[f"underlying_velocity_{cp_tag}"] = u_vel
            row_out[f"futures_move_{cp_tag}"] = f_move
            row_out[f"futures_velocity_{cp_tag}"] = f_vel
            row_out[f"spot_futures_divergence_{cp_tag}"] = div
            row_out[f"counterfactual_exit_pnl_{cp_tag}"] = cf_pnl

            long_rows.append(
                {
                    "trade_id": trade.get("trade_id"),
                    "date": trade.get("date"),
                    "checkpoint_seconds": cp,
                    "available": 1,
                    "pnl": last_pnl,
                    "runup": runup,
                    "drawdown": drawdown,
                    "spread": spread,
                    "underlying_move": u_move,
                    "futures_move": f_move,
                    "missing_update": missing,
                    "stale_quote": stale,
                    "counterfactual_exit_pnl": cf_pnl,
                }
            )

        # Summary flags derived from early checkpoints.
        cp1 = _cp_tag(1.0)
        cp3 = _cp_tag(3.0)
        row_out["immediate_confirmation_flag"] = int((row_out.get(f"runup_{cp1}") or -999) >= 1.0)
        row_out["immediate_rejection_flag"] = int((row_out.get(f"drawdown_{cp1}") or 999) <= -1.5)
        row_out["quote_quality_degradation_flag"] = int((row_out.get(f"spread_vs_entry_{cp3}") or 0) > 2.0)

        rows.append(row_out)
        availability_rows.append(
            {
                "trade_id": trade.get("trade_id"),
                "date": trade.get("date"),
                "has_trade_ticks": ctx.has_trade_ticks,
                "has_underlying_ticks": ctx.has_underlying_ticks,
                "has_futures_ticks": ctx.has_futures_ticks,
                "has_depth": ctx.has_depth,
                "has_subsecond_time": ctx.has_subsecond_time,
                "fill_method": ctx.fill_method,
                "feature_extraction_status": "OK",
            }
        )

    features_df = pd.DataFrame(rows)
    long_df = pd.DataFrame(long_rows)
    availability_df = pd.DataFrame(availability_rows)

    return features_df, long_df, availability_df
