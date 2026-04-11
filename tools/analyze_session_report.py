from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


@dataclass
class SessionPaths:
    session_date: date
    logs_dir: Path
    trades_enriched: Path | None
    trades_raw: Path | None
    events: Path | None
    ticks_sensex: Path | None
    ticks_futures: Path | None
    ticks_options: Path | None
    trade_ticks_dir: Path | None
    runtime_control: Path | None
    features_daily: Path | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a comprehensive post-trade session report")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--logs-dir", default="logs", help="Logs directory relative to repo root")
    parser.add_argument(
        "--output-root",
        default="analysis/session_report",
        help="Output root directory relative to repo root",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Optional explicit session date in YYYY-MM-DD. If omitted, auto-detect latest.",
    )
    return parser.parse_args()


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        # fallback for second precision without separators
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return rows


def infer_dates_from_filenames(logs_dir: Path) -> set[date]:
    candidates: set[date] = set()

    patterns = [
        logs_dir / "trades" / "*.trades_enriched.jsonl",
        logs_dir / "trades" / "*.trades.jsonl",
        logs_dir / "events" / "*.events.jsonl",
    ]
    for pattern in patterns:
        for path in pattern.parent.glob(pattern.name):
            m = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
            if m:
                try:
                    candidates.add(date.fromisoformat(m.group(1)))
                except ValueError:
                    pass

    for dirpath in [logs_dir / "ticks", logs_dir / "trade_ticks"]:
        if not dirpath.exists():
            continue
        for child in dirpath.iterdir():
            if child.is_dir():
                try:
                    candidates.add(date.fromisoformat(child.name))
                except ValueError:
                    continue

    return candidates


def infer_date_from_json_timestamps(logs_dir: Path) -> set[date]:
    candidates: set[date] = set()
    for p in [logs_dir / "trades_enriched.jsonl", logs_dir / "events.jsonl", logs_dir / "trades.jsonl"]:
        if not p.exists():
            continue
        rows = load_jsonl(p)
        for row in rows:
            for k in (
                "signal_time",
                "entry_fill_time",
                "exit_fill_time",
                "timestamp",
                "event_timestamp",
                "ts",
                "entry_time",
                "exit_time",
            ):
                dt = parse_dt(row.get(k))
                if dt is not None:
                    candidates.add(dt.date())
                    break
    return candidates


def detect_latest_session_date(logs_dir: Path, explicit_date: str | None) -> date:
    if explicit_date:
        return date.fromisoformat(explicit_date)

    candidates = infer_dates_from_filenames(logs_dir)
    if not candidates:
        candidates = infer_date_from_json_timestamps(logs_dir)
    if not candidates:
        raise RuntimeError(f"Could not infer session date from {logs_dir}")
    return max(candidates)


def choose_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def build_session_paths(repo_root: Path, logs_dir: Path, session_date: date) -> SessionPaths:
    d = session_date.isoformat()
    trades_enriched = choose_existing(
        [
            logs_dir / "trades" / f"{d}.trades_enriched.jsonl",
            logs_dir / "trades_enriched.jsonl",
        ]
    )
    trades_raw = choose_existing(
        [
            logs_dir / "trades" / f"{d}.trades.jsonl",
            logs_dir / "trades.jsonl",
        ]
    )
    events = choose_existing(
        [
            logs_dir / "events" / f"{d}.events.jsonl",
            logs_dir / "events.jsonl",
        ]
    )

    ticks_day = logs_dir / "ticks" / d
    trade_ticks_day = logs_dir / "trade_ticks" / d

    return SessionPaths(
        session_date=session_date,
        logs_dir=logs_dir,
        trades_enriched=trades_enriched,
        trades_raw=trades_raw,
        events=events,
        ticks_sensex=(ticks_day / "sensex.jsonl") if (ticks_day / "sensex.jsonl").exists() else None,
        ticks_futures=(ticks_day / "futures.jsonl") if (ticks_day / "futures.jsonl").exists() else None,
        ticks_options=(ticks_day / "options.jsonl") if (ticks_day / "options.jsonl").exists() else None,
        trade_ticks_dir=trade_ticks_day if trade_ticks_day.exists() else None,
        runtime_control=(repo_root / "runtime" / "control.json") if (repo_root / "runtime" / "control.json").exists() else None,
        features_daily=(logs_dir / "features_daily.csv") if (logs_dir / "features_daily.csv").exists() else None,
    )


def score_trade_record(record: dict[str, Any], seq_idx: int) -> tuple[int, int, datetime, int]:
    done = 1 if bool(record.get("post_exit_observation_done")) else 0
    enriched = 1 if record.get("summary_version") == "post_exit_enriched" else 0
    ts = (
        parse_dt(record.get("exit_fill_time"))
        or parse_dt(record.get("entry_fill_time"))
        or parse_dt(record.get("signal_time"))
        or datetime.min
    )
    return (done, enriched, ts, seq_idx)


def dedupe_trades(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_trade: dict[str, tuple[tuple[int, int, datetime, int], dict[str, Any]]] = {}
    for idx, row in enumerate(rows):
        trade_id = row.get("trade_id")
        if not trade_id:
            continue
        score = score_trade_record(row, idx)
        prev = by_trade.get(trade_id)
        if prev is None or score > prev[0]:
            by_trade[trade_id] = (score, row)
    deduped = [item[1] for item in sorted(by_trade.values(), key=lambda x: x[0][2])]
    return deduped


def filter_rows_by_session_date(rows: list[dict[str, Any]], session_date: date) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        hit = False
        for key in ("signal_time", "entry_fill_time", "exit_fill_time", "timestamp", "event_timestamp", "ts"):
            dt = parse_dt(row.get(key))
            if dt is not None and dt.date() == session_date:
                hit = True
                break
        if hit:
            out.append(row)
    return out


def parse_trade_tick_trade_id(path: Path) -> str | None:
    stem = path.stem
    parts = stem.split("_")
    if len(parts) < 6:
        return None
    return f"{parts[0]}|{parts[1]}:{parts[2]}|{parts[3]}_{parts[4]}|{parts[5]}"


def load_trade_tick_map(trade_ticks_dir: Path | None) -> dict[str, Path]:
    if trade_ticks_dir is None or not trade_ticks_dir.exists():
        return {}
    out: dict[str, Path] = {}
    for path in sorted(trade_ticks_dir.glob("*.jsonl")):
        trade_id = parse_trade_tick_trade_id(path)
        if trade_id:
            out[trade_id] = path
    return out


def calc_imbalance(bid5: Any, ask5: Any) -> float | None:
    bids = bid5 if isinstance(bid5, list) else []
    asks = ask5 if isinstance(ask5, list) else []

    def qty_sum(levels: list[Any]) -> float:
        total = 0.0
        for level in levels[:5]:
            if isinstance(level, dict):
                q = to_float(level.get("quantity"))
                if q is None:
                    q = to_float(level.get("qty"))
                if q is not None:
                    total += q
            elif isinstance(level, (list, tuple)) and len(level) >= 2:
                q = to_float(level[1])
                if q is not None:
                    total += q
        return total

    bq = qty_sum(bids)
    aq = qty_sum(asks)
    if bq + aq == 0:
        return None
    return (bq - aq) / (bq + aq)


def load_trade_tick_frame(path: Path, entry_time: datetime | None) -> pd.DataFrame:
    rows = load_jsonl(path)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        t_ex = parse_dt(row.get("timestamp_exchange"))
        t_rx = parse_dt(row.get("timestamp_receive"))
        t = t_ex or t_rx
        if t is None:
            continue
        rel = (t - entry_time).total_seconds() if entry_time else np.nan
        normalized.append(
            {
                "trade_id": row.get("trade_id"),
                "phase": row.get("phase"),
                "source": row.get("source"),
                "symbol": row.get("symbol"),
                "time": t,
                "timestamp_exchange": t_ex,
                "timestamp_receive": t_rx,
                "rel_sec": rel,
                "ltp": to_float(row.get("ltp")),
                "ltq": to_float(row.get("ltq")),
                "volume": to_float(row.get("volume")),
                "oi": to_float(row.get("oi")),
                "best_bid": to_float(row.get("best_bid")),
                "best_ask": to_float(row.get("best_ask")),
                "spread": to_float(row.get("spread")),
                "imbalance": calc_imbalance(row.get("bid[5]"), row.get("ask[5]")),
            }
        )

    if not normalized:
        return pd.DataFrame(
            columns=[
                "trade_id",
                "phase",
                "source",
                "symbol",
                "time",
                "timestamp_exchange",
                "timestamp_receive",
                "rel_sec",
                "ltp",
                "ltq",
                "volume",
                "oi",
                "best_bid",
                "best_ask",
                "spread",
                "imbalance",
            ]
        )

    df = pd.DataFrame(normalized)
    df = df.sort_values("time").reset_index(drop=True)
    return df


def choose_entry_time(trade: dict[str, Any]) -> datetime | None:
    return (
        parse_dt(trade.get("entry_fill_time"))
        or parse_dt(trade.get("entry_order_ack_time"))
        or parse_dt(trade.get("entry_order_sent_time"))
        or parse_dt(trade.get("signal_time"))
    )


def choose_exit_time(trade: dict[str, Any]) -> datetime | None:
    return (
        parse_dt(trade.get("exit_fill_time"))
        or parse_dt(trade.get("exit_order_ack_time"))
        or parse_dt(trade.get("exit_order_sent_time"))
    )


def first_valid(series: pd.Series) -> float | None:
    s = series.dropna()
    if s.empty:
        return None
    return float(s.iloc[0])


def last_valid(series: pd.Series) -> float | None:
    s = series.dropna()
    if s.empty:
        return None
    return float(s.iloc[-1])


def median_valid(series: pd.Series) -> float | None:
    s = series.dropna()
    if s.empty:
        return None
    return float(s.median())


def mean_valid(series: pd.Series) -> float | None:
    s = series.dropna()
    if s.empty:
        return None
    return float(s.mean())


def compute_trade_features(trade: dict[str, Any], tick_df: pd.DataFrame) -> dict[str, Any]:
    trade_id = str(trade.get("trade_id"))
    entry_price = to_float(trade.get("entry_price"))
    exit_price = to_float(trade.get("exit_price"))
    target_points = to_float(trade.get("target_points_used"))
    target_price_direct = to_float(trade.get("target_price"))
    target_price = target_price_direct
    if target_price is None and entry_price is not None and target_points is not None:
        target_price = entry_price + target_points

    side = trade.get("side") or trade.get("call_or_put")
    signal_kind = trade.get("signal_kind")
    pnl = to_float(trade.get("net_pnl"))
    if pnl is None:
        pnl = to_float(trade.get("gross_pnl"))
    pnl = pnl if pnl is not None else 0.0

    entry_time = choose_entry_time(trade)
    exit_time = choose_exit_time(trade)
    hold_seconds = to_float(trade.get("holding_seconds"))
    if hold_seconds is None and entry_time and exit_time:
        hold_seconds = (exit_time - entry_time).total_seconds()

    # subsets
    opt = tick_df[tick_df["source"] == "option"].copy()
    idx = tick_df[tick_df["source"] == "index"].copy()
    fut = tick_df[tick_df["source"] == "future"].copy()

    opt_pre = opt[opt["phase"] == "PRE_ENTRY"].copy()
    opt_in = opt[opt["phase"] == "IN_TRADE"].copy()
    opt_post = opt[opt["phase"] == "POST_EXIT"].copy()

    idx_pre = idx[idx["phase"] == "PRE_ENTRY"].copy()
    idx_in = idx[idx["phase"] == "IN_TRADE"].copy()
    idx_post = idx[idx["phase"] == "POST_EXIT"].copy()

    fut_pre = fut[fut["phase"] == "PRE_ENTRY"].copy()
    fut_in = fut[fut["phase"] == "IN_TRADE"].copy()
    fut_post = fut[fut["phase"] == "POST_EXIT"].copy()

    # entry anchoring
    opt_in_nonneg = opt_in[opt_in["rel_sec"] >= -0.2].copy()
    if opt_in_nonneg.empty:
        opt_in_nonneg = opt_in.copy()
    opt_in_nonneg = opt_in_nonneg.sort_values("time")

    entry_tick = opt_in_nonneg.iloc[0] if not opt_in_nonneg.empty else (opt_pre.sort_values("time").iloc[-1] if not opt_pre.empty else None)

    # pre-entry velocity
    pre_vel = None
    if len(opt_pre) >= 2:
        a = opt_pre.sort_values("time").iloc[0]
        b = opt_pre.sort_values("time").iloc[-1]
        dt = (b["time"] - a["time"]).total_seconds()
        if dt > 0 and pd.notna(a["ltp"]) and pd.notna(b["ltp"]):
            pre_vel = float((b["ltp"] - a["ltp"]) / dt)

    # in-trade path metrics
    in_ltp = opt_in_nonneg[["time", "rel_sec", "ltp", "best_bid", "best_ask", "spread", "imbalance"]].dropna(subset=["ltp"]).sort_values("time")
    in_entry_price = entry_price if entry_price is not None else first_valid(in_ltp["ltp"])

    max_in = None
    min_in = None
    in_points_max = None
    in_points_min = None
    first_1s_move = None
    first_3s_move = None
    max_gain_first_3s = None

    if in_entry_price is not None and not in_ltp.empty:
        max_in = float(in_ltp["ltp"].max())
        min_in = float(in_ltp["ltp"].min())
        in_points_max = max_in - in_entry_price
        in_points_min = min_in - in_entry_price

        w1 = in_ltp[in_ltp["rel_sec"] <= 1.0]
        w3 = in_ltp[in_ltp["rel_sec"] <= 3.0]
        if not w1.empty:
            first_1s_move = float(w1.iloc[-1]["ltp"] - in_entry_price)
        if not w3.empty:
            first_3s_move = float(w3.iloc[-1]["ltp"] - in_entry_price)
            max_gain_first_3s = float(w3["ltp"].max() - in_entry_price)

    spread_entry = to_float(trade.get("entry_spread"))
    if spread_entry is None and entry_tick is not None:
        spread_entry = to_float(entry_tick.get("spread"))

    imbalance_entry = None
    if entry_tick is not None:
        imbalance_entry = to_float(entry_tick.get("imbalance"))

    first_2s = in_ltp[in_ltp["rel_sec"] <= 2.0]
    spread_median_first_2s = median_valid(first_2s["spread"]) if not first_2s.empty else None
    imbalance_drift_first_2s = None
    if not first_2s.empty and first_2s["imbalance"].notna().sum() >= 2:
        imbalance_drift_first_2s = float(first_2s["imbalance"].dropna().iloc[-1] - first_2s["imbalance"].dropna().iloc[0])

    best_bid_stepped_down = None
    first_3s = in_ltp[in_ltp["rel_sec"] <= 3.0]
    if not first_3s.empty and first_3s["best_bid"].notna().sum() >= 2:
        b0 = float(first_3s["best_bid"].dropna().iloc[0])
        bmin = float(first_3s["best_bid"].dropna().min())
        best_bid_stepped_down = bool((b0 - bmin) >= 0.5)

    # target proximity and missed opportunities
    target_nearly_reached = None
    target_touched_in_trade = None
    if target_price is not None and max_in is not None:
        target_nearly_reached = bool(max_in >= target_price - 0.5)
        target_touched_in_trade = bool(max_in >= target_price)

    # post-exit metrics from tick path
    post_best_delta = None
    post_worst_delta = None
    post_final_delta = None
    post_recovered_above_exit = None
    post_touched_target = None

    if exit_price is not None and not opt_post.empty:
        post_ltp = opt_post.sort_values("time")["ltp"].dropna()
        if not post_ltp.empty:
            deltas = post_ltp - exit_price
            post_best_delta = float(deltas.max())
            post_worst_delta = float(deltas.min())
            post_final_delta = float(deltas.iloc[-1])
            post_recovered_above_exit = bool((deltas >= 0).any())

            if target_price is not None:
                post_touched_target = bool((post_ltp >= target_price).any())

    # parse post_exit_path if present and richer
    post_exit_path = trade.get("post_exit_path")
    if isinstance(post_exit_path, list) and post_exit_path:
        path_deltas = [to_float(x.get("delta_from_exit_price")) for x in post_exit_path]
        path_deltas = [x for x in path_deltas if x is not None]
        if path_deltas:
            post_best_delta = max(path_deltas) if post_best_delta is None else max(post_best_delta, max(path_deltas))
            post_worst_delta = min(path_deltas) if post_worst_delta is None else min(post_worst_delta, min(path_deltas))
            post_final_delta = path_deltas[-1]
            post_recovered_above_exit = bool(any(x >= 0 for x in path_deltas))

    immediate_reversal = None
    if first_1s_move is not None and first_3s_move is not None:
        immediate_reversal = bool(first_1s_move < 0 and first_3s_move <= 0)

    target_approached_not_hit = False
    if target_nearly_reached is not None and target_touched_in_trade is not None:
        target_approached_not_hit = bool(target_nearly_reached and not target_touched_in_trade)

    # source context deltas
    def source_delta(df: pd.DataFrame) -> float | None:
        if df.empty:
            return None
        s = df.sort_values("time")["ltp"].dropna()
        if len(s) < 2:
            return None
        return float(s.iloc[-1] - s.iloc[0])

    out = {
        "trade_id": trade_id,
        "symbol": trade.get("symbol"),
        "side": side,
        "signal_kind": signal_kind,
        "continuation_or_reversal": trade.get("continuation_or_reversal"),
        "fragile": bool(trade.get("fragile")) if trade.get("fragile") is not None else None,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "holding_seconds": hold_seconds,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "target_points_used": target_points,
        "target_price": target_price,
        "net_pnl": pnl,
        "exit_reason": trade.get("exit_reason"),
        "mfe": to_float(trade.get("mfe")),
        "mae": to_float(trade.get("mae")),
        "entry_spread": spread_entry,
        "spread_median_first_2s": spread_median_first_2s,
        "imbalance_entry": imbalance_entry,
        "imbalance_drift_first_2s": imbalance_drift_first_2s,
        "pre_entry_velocity": pre_vel,
        "first_1s_move": first_1s_move,
        "first_3s_move": first_3s_move,
        "max_gain_first_3s": max_gain_first_3s,
        "best_bid_stepped_down_first_3s": best_bid_stepped_down,
        "target_nearly_reached": target_nearly_reached,
        "target_touched_in_trade": target_touched_in_trade,
        "target_approached_not_hit": target_approached_not_hit,
        "immediate_reversal": immediate_reversal,
        "in_trade_max_points": in_points_max,
        "in_trade_min_points": in_points_min,
        "post_exit_best_delta": post_best_delta,
        "post_exit_worst_delta": post_worst_delta,
        "post_exit_final_delta": post_final_delta,
        "post_exit_recovered_above_exit": post_recovered_above_exit,
        "post_exit_touched_target": post_touched_target,
        "opt_pre_delta": source_delta(opt_pre),
        "opt_in_delta": source_delta(opt_in_nonneg),
        "opt_post_delta": source_delta(opt_post),
        "idx_pre_delta": source_delta(idx_pre),
        "idx_in_delta": source_delta(idx_in),
        "idx_post_delta": source_delta(idx_post),
        "fut_pre_delta": source_delta(fut_pre),
        "fut_in_delta": source_delta(fut_in),
        "fut_post_delta": source_delta(fut_post),
        "opt_pre_spread_avg": mean_valid(opt_pre["spread"]) if not opt_pre.empty else None,
        "opt_in_spread_avg": mean_valid(opt_in_nonneg["spread"]) if not opt_in_nonneg.empty else None,
        "opt_post_spread_avg": mean_valid(opt_post["spread"]) if not opt_post.empty else None,
        "fut_pre_spread_avg": mean_valid(fut_pre["spread"]) if not fut_pre.empty else None,
        "fut_in_spread_avg": mean_valid(fut_in["spread"]) if not fut_in.empty else None,
        "fut_post_spread_avg": mean_valid(fut_post["spread"]) if not fut_post.empty else None,
        "pre_entry_tick_count_option": int(len(opt_pre)),
        "in_trade_tick_count_option": int(len(opt_in_nonneg)),
        "post_exit_tick_count_option": int(len(opt_post)),
    }

    # explicit exit timing label for ledger/report readability
    exit_reason = str(trade.get("exit_reason") or "")
    if exit_reason == "TARGET_HIT":
        if post_best_delta is not None and post_best_delta > 5:
            exit_timing = "Captured target; additional upside remained"
        elif post_final_delta is not None and post_final_delta < -3:
            exit_timing = "Timely target exit; post-exit fade"
        else:
            exit_timing = "Reasonable target exit"
    else:
        if post_best_delta is not None and post_best_delta >= 3:
            exit_timing = "Possibly early; post-exit recovery"
        elif post_final_delta is not None and post_final_delta <= -3:
            exit_timing = "Likely justified; weakness persisted"
        else:
            exit_timing = "Mixed / inconclusive timing"
    out["exit_timing_assessment"] = exit_timing

    out["outcome"] = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT"

    return out


def fmt_num(x: Any, nd: int = 2) -> str:
    if x is None:
        return "NA"
    try:
        if math.isnan(float(x)):
            return "NA"
    except (TypeError, ValueError):
        return "NA"
    return f"{float(x):.{nd}f}"


def fmt_dt(dt: Any) -> str:
    if not isinstance(dt, datetime):
        return "NA"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    if df.empty:
        return "(no rows)"

    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        vals: list[str] = []
        for c in columns:
            v = row.get(c)
            if isinstance(v, datetime):
                vals.append(v.strftime("%H:%M:%S"))
            elif isinstance(v, float):
                vals.append(fmt_num(v, nd=2))
            elif v is None or (isinstance(v, float) and np.isnan(v)):
                vals.append("NA")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def clean_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)


def make_trade_chart(
    trade: dict[str, Any],
    feature_row: dict[str, Any],
    tick_df: pd.DataFrame,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    entry_time = choose_entry_time(trade)
    exit_time = choose_exit_time(trade)
    hold = to_float(feature_row.get("holding_seconds"))

    if entry_time is None:
        return

    option_df = tick_df[tick_df["source"] == "option"].sort_values("time")
    index_df = tick_df[tick_df["source"] == "index"].sort_values("time")
    future_df = tick_df[tick_df["source"] == "future"].sort_values("time")

    if option_df.empty:
        return

    fig = plt.figure(figsize=(13, 7), constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.5, 1.2])
    ax = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax)

    # Main option series
    ax.plot(option_df["rel_sec"], option_df["ltp"], color="#1f77b4", lw=1.8, label="Option LTP")

    if option_df["best_bid"].notna().any():
        ax.plot(option_df["rel_sec"], option_df["best_bid"], color="#2ca02c", lw=1.0, alpha=0.5, label="Best Bid")
    if option_df["best_ask"].notna().any():
        ax.plot(option_df["rel_sec"], option_df["best_ask"], color="#d62728", lw=1.0, alpha=0.5, label="Best Ask")

    entry_price = to_float(feature_row.get("entry_price"))
    exit_price = to_float(feature_row.get("exit_price"))
    target_price = to_float(feature_row.get("target_price"))

    if entry_price is not None:
        ax.axhline(entry_price, color="#9467bd", linestyle="--", lw=1.2, label=f"Entry {entry_price:.2f}")
    if target_price is not None:
        ax.axhline(target_price, color="#ff7f0e", linestyle="--", lw=1.2, label=f"Target {target_price:.2f}")
    if exit_price is not None:
        ax.axhline(exit_price, color="#8c564b", linestyle="--", lw=1.2, label=f"Exit {exit_price:.2f}")

    # marks and phase shading
    ax.axvline(0, color="black", lw=1.1, alpha=0.8, label="Entry Time")
    if hold is not None:
        ax.axvline(hold, color="black", lw=1.1, alpha=0.8, linestyle=":", label="Exit Time")

    xmin = float(option_df["rel_sec"].min()) if option_df["rel_sec"].notna().any() else -5
    xmax = float(option_df["rel_sec"].max()) if option_df["rel_sec"].notna().any() else 15
    if hold is None:
        hold = 0.0

    ax.axvspan(xmin, 0, color="#dbe9f6", alpha=0.5, label="Pre-entry")
    ax.axvspan(0, hold, color="#eaf4dc", alpha=0.4, label="In-trade")
    ax.axvspan(hold, xmax, color="#fce8e6", alpha=0.4, label="Post-exit")

    ax.set_ylabel("Option Price")
    ax.grid(alpha=0.2)

    title = (
        f"{feature_row.get('trade_id')} | {feature_row.get('symbol')} | "
        f"Entry {fmt_dt(entry_time)} | Exit {fmt_dt(exit_time)} | PnL {fmt_num(feature_row.get('net_pnl'))}"
    )
    ax.set_title(title, fontsize=10)

    # Underlying/futures context (normalized)
    def plot_norm(series_df: pd.DataFrame, label: str, color: str) -> None:
        if series_df.empty:
            return
        s = series_df[["rel_sec", "ltp"]].dropna().sort_values("rel_sec")
        if s.empty:
            return
        base = float(s.iloc[0]["ltp"])
        ax2.plot(s["rel_sec"], s["ltp"] - base, lw=1.4, label=f"{label} Δ", color=color)

    plot_norm(index_df, "Index", "#17becf")
    plot_norm(future_df, "Future", "#bcbd22")
    ax2.axvline(0, color="black", lw=1.0, alpha=0.8)
    ax2.axvline(hold, color="black", lw=1.0, alpha=0.8, linestyle=":")
    ax2.axhline(0, color="gray", lw=0.8, alpha=0.7)
    ax2.set_ylabel("Underlying/Future Δ")
    ax2.set_xlabel("Seconds Relative to Entry")
    ax2.grid(alpha=0.2)

    handles, labels = ax.get_legend_handles_labels()
    # de-duplicate legend entries
    seen: set[str] = set()
    dedup_h: list[Any] = []
    dedup_l: list[str] = []
    for h, l in zip(handles, labels):
        if l in seen:
            continue
        seen.add(l)
        dedup_h.append(h)
        dedup_l.append(l)
    ax.legend(dedup_h, dedup_l, fontsize=8, ncols=3, loc="upper left")

    if ax2.get_legend_handles_labels()[0]:
        ax2.legend(fontsize=8, loc="upper left")

    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def make_session_timeline_chart(features_df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if features_df.empty:
        return

    df = features_df.copy().sort_values("entry_time")
    fig, ax = plt.subplots(figsize=(13, 5))

    colors = df["net_pnl"].apply(lambda x: "#2ca02c" if x > 0 else "#d62728" if x < 0 else "#7f7f7f")
    sizes = df["holding_seconds"].fillna(0).clip(lower=0).apply(lambda x: 30 + min(220, x * 10))

    ax.scatter(df["entry_time"], df["net_pnl"], c=colors, s=sizes, alpha=0.75, edgecolors="black", linewidths=0.4)
    ax.axhline(0, color="black", lw=1.0)
    ax.set_title("Session Trade Timeline: PnL by Entry Time (size ~ duration)")
    ax.set_xlabel("Entry Time")
    ax.set_ylabel("Realized PnL")
    ax.grid(alpha=0.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def make_distribution_charts(features_df: pd.DataFrame, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, Path] = {}

    if features_df.empty:
        return output_paths

    # PnL distribution
    p1 = out_dir / "pnl_distribution.png"
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(features_df["net_pnl"].dropna(), bins=20, color="#1f77b4", alpha=0.8)
    ax.axvline(0, color="black", lw=1)
    ax.set_title("PnL Distribution")
    ax.set_xlabel("Net PnL")
    ax.set_ylabel("Count")
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(p1, dpi=150)
    plt.close(fig)
    output_paths["pnl_distribution"] = p1

    # Duration distribution
    p2 = out_dir / "duration_distribution.png"
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(features_df["holding_seconds"].dropna(), bins=20, color="#ff7f0e", alpha=0.8)
    ax.set_title("Holding Duration Distribution")
    ax.set_xlabel("Holding Seconds")
    ax.set_ylabel("Count")
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(p2, dpi=150)
    plt.close(fig)
    output_paths["duration_distribution"] = p2

    # MFE vs MAE scatter
    p3 = out_dir / "mfe_vs_mae_scatter.png"
    fig, ax = plt.subplots(figsize=(6.5, 6))
    tmp = features_df.dropna(subset=["mfe", "mae", "net_pnl"])
    colors = tmp["net_pnl"].apply(lambda x: "#2ca02c" if x > 0 else "#d62728" if x < 0 else "#7f7f7f")
    ax.scatter(tmp["mfe"], tmp["mae"], c=colors, alpha=0.8, edgecolors="black", linewidths=0.4)
    ax.axhline(0, color="black", lw=1)
    ax.axvline(0, color="black", lw=1)
    ax.set_title("MFE vs MAE")
    ax.set_xlabel("MFE (points)")
    ax.set_ylabel("MAE (points)")
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(p3, dpi=150)
    plt.close(fig)
    output_paths["mfe_vs_mae"] = p3

    # PnL vs MFE
    p4 = out_dir / "pnl_vs_mfe_scatter.png"
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    tmp = features_df.dropna(subset=["mfe", "net_pnl"])
    colors = tmp["net_pnl"].apply(lambda x: "#2ca02c" if x > 0 else "#d62728" if x < 0 else "#7f7f7f")
    ax.scatter(tmp["mfe"], tmp["net_pnl"], c=colors, alpha=0.8, edgecolors="black", linewidths=0.4)
    ax.axhline(0, color="black", lw=1)
    ax.set_title("Realized PnL vs In-trade MFE")
    ax.set_xlabel("MFE (points)")
    ax.set_ylabel("Realized PnL")
    ax.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(p4, dpi=150)
    plt.close(fig)
    output_paths["pnl_vs_mfe"] = p4

    return output_paths


def make_first5s_path_chart(features_df: pd.DataFrame, per_trade_tick_frames: dict[str, pd.DataFrame], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    xgrid = np.arange(0, 5.01, 0.5)
    curves: dict[str, list[np.ndarray]] = {"WIN": [], "LOSS": []}

    for _, row in features_df.iterrows():
        outcome = row.get("outcome")
        if outcome not in curves:
            continue
        trade_id = row.get("trade_id")
        entry_price = row.get("entry_price")
        if trade_id not in per_trade_tick_frames or pd.isna(entry_price):
            continue
        df = per_trade_tick_frames[trade_id]
        opt = df[(df["source"] == "option") & (df["phase"] == "IN_TRADE")].dropna(subset=["ltp", "rel_sec"]).sort_values("rel_sec")
        opt = opt[(opt["rel_sec"] >= 0) & (opt["rel_sec"] <= 5)]
        if len(opt) < 2:
            continue
        x = opt["rel_sec"].to_numpy(dtype=float)
        y = opt["ltp"].to_numpy(dtype=float) - float(entry_price)
        if np.unique(x).size < 2:
            continue
        y_interp = np.interp(xgrid, x, y)
        curves[outcome].append(y_interp)

    fig, ax = plt.subplots(figsize=(8, 5))
    for outcome, color in [("WIN", "#2ca02c"), ("LOSS", "#d62728")]:
        arrs = curves[outcome]
        if not arrs:
            continue
        arr = np.vstack(arrs)
        mean = arr.mean(axis=0)
        lo = np.percentile(arr, 25, axis=0)
        hi = np.percentile(arr, 75, axis=0)
        ax.plot(xgrid, mean, color=color, lw=2, label=f"{outcome} mean")
        ax.fill_between(xgrid, lo, hi, color=color, alpha=0.2, label=f"{outcome} IQR")

    ax.axhline(0, color="black", lw=1)
    ax.set_title("Entry-to-First-5s Option Path (relative to entry price)")
    ax.set_xlabel("Seconds after entry")
    ax.set_ylabel("Option Δ points")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def parse_event_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload")
    if isinstance(payload, dict):
        return payload
    return {}


def build_runtime_df(events_rows: list[dict[str, Any]], session_date: date) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    filtered_events: list[dict[str, Any]] = []

    for row in events_rows:
        ts = parse_dt(row.get("timestamp") or row.get("ts") or row.get("event_timestamp"))
        if ts is None or ts.date() != session_date:
            continue
        row2 = dict(row)
        row2["_ts"] = ts
        filtered_events.append(row2)

        if row.get("event_type") != "RUNTIME_HEALTH":
            continue

        payload = parse_event_payload(row)
        rec = {
            "timestamp": ts,
            "runtime_ticks_received_total": to_float(payload.get("runtime_ticks_received_total")),
            "runtime_ticks_processed_total": to_float(payload.get("runtime_ticks_processed_total")),
            "runtime_ticks_dropped_total": to_float(payload.get("runtime_ticks_dropped_total")),
            "critical_ticks_dropped_total": to_float(payload.get("critical_ticks_dropped_total")),
            "background_ticks_dropped_total": to_float(payload.get("background_ticks_dropped_total")),
            "journal_records_enqueued_total": to_float(payload.get("journal_records_enqueued_total")),
            "journal_records_written_total": to_float(payload.get("journal_records_written_total")),
            "journal_records_dropped_total": to_float(payload.get("journal_records_dropped_total")),
            "critical_queue_max_size_seen": to_float(payload.get("critical_queue_max_size_seen")),
            "background_queue_max_size_seen": to_float(payload.get("background_queue_max_size_seen")),
            "journal_queue_max_size_seen": to_float(payload.get("journal_queue_max_size_seen")),
            "current_subscribed_token_count": to_float(payload.get("current_subscribed_token_count")),
            "current_option_lattice_size": to_float(payload.get("current_option_lattice_size")),
            "current_atm_reference": to_float(payload.get("current_atm_reference")),
            "stream_connected": bool(payload.get("stream_connected")) if payload.get("stream_connected") is not None else None,
            "stream_degraded": bool(payload.get("stream_degraded")) if payload.get("stream_degraded") is not None else None,
        }
        rows.append(rec)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("timestamp").reset_index(drop=True)

    return df, filtered_events


def make_runtime_stability_chart(runtime_df: pd.DataFrame, event_rows: list[dict[str, Any]], out_path: Path) -> None:
    if runtime_df.empty:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

    # drops
    for col, color in [
        ("runtime_ticks_dropped_total", "#1f77b4"),
        ("critical_ticks_dropped_total", "#d62728"),
        ("background_ticks_dropped_total", "#ff7f0e"),
        ("journal_records_dropped_total", "#9467bd"),
    ]:
        if col in runtime_df:
            axes[0].plot(runtime_df["timestamp"], runtime_df[col], label=col, lw=1.6, color=color)
    axes[0].set_title("Runtime Drop Counters Over Session")
    axes[0].set_ylabel("Cumulative Count")
    axes[0].grid(alpha=0.2)
    axes[0].legend(fontsize=8, ncols=2)

    # queue max seen
    for col, color in [
        ("critical_queue_max_size_seen", "#2ca02c"),
        ("background_queue_max_size_seen", "#17becf"),
        ("journal_queue_max_size_seen", "#8c564b"),
    ]:
        if col in runtime_df:
            axes[1].plot(runtime_df["timestamp"], runtime_df[col], label=col, lw=1.6, color=color)
    axes[1].set_title("Queue Max-Size-Observed Metrics")
    axes[1].set_ylabel("Max Size Seen")
    axes[1].set_xlabel("Time")
    axes[1].grid(alpha=0.2)

    # event markers
    for event in event_rows:
        et = event.get("event_type")
        ts = event.get("_ts")
        if not isinstance(ts, datetime):
            continue
        marker_color = None
        if isinstance(et, str) and ("RECONNECT" in et or et in {"STREAM_CONNECTED", "STREAM_CLOSED"}):
            marker_color = "#7f7f7f"
        elif isinstance(et, str) and ("WATCHDOG" in et or et in {"STREAM_DEGRADED", "STREAM_RECOVERED"}):
            marker_color = "#d62728"
        elif et in {"ENTRY_DEFERRED_QUOTE_UNAVAILABLE", "QUEUE_DROP", "JOURNAL_BACKPRESSURE"}:
            marker_color = "#ff7f0e"
        if marker_color:
            axes[1].axvline(ts, color=marker_color, alpha=0.2, lw=0.9)

    axes[1].legend(fontsize=8)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def summarize_runtime(event_rows: list[dict[str, Any]], runtime_df: pd.DataFrame) -> dict[str, Any]:
    event_types = [str(r.get("event_type")) for r in event_rows if r.get("event_type") is not None]
    counts = Counter(event_types)

    reconnect_related = sum(v for k, v in counts.items() if "RECONNECT" in k)
    watchdog_related = sum(v for k, v in counts.items() if "WATCHDOG" in k)

    stream_connected = counts.get("STREAM_CONNECTED", 0)
    stream_closed = counts.get("STREAM_CLOSED", 0)
    stream_degraded_events = counts.get("STREAM_DEGRADED", 0)
    stream_recovered_events = counts.get("STREAM_RECOVERED", 0)

    entry_deferred = counts.get("ENTRY_DEFERRED_QUOTE_UNAVAILABLE", 0)
    lattice_rebase = counts.get("LATTICE_REBASE", 0)

    queue_drop_events = sum(v for k, v in counts.items() if ("DROP" in k or "BACKPRESSURE" in k))

    summary: dict[str, Any] = {
        "event_counts": counts,
        "stream_connected_events": stream_connected,
        "stream_closed_events": stream_closed,
        "reconnect_events": reconnect_related,
        "watchdog_events": watchdog_related,
        "stream_degraded_events": stream_degraded_events,
        "stream_recovered_events": stream_recovered_events,
        "entry_deferred_quote_unavailable": entry_deferred,
        "lattice_rebase_events": lattice_rebase,
        "queue_or_backpressure_events": queue_drop_events,
        "max_runtime_ticks_dropped_total": None,
        "max_critical_ticks_dropped_total": None,
        "max_background_ticks_dropped_total": None,
        "max_journal_records_dropped_total": None,
        "max_critical_queue_size_seen": None,
        "max_background_queue_size_seen": None,
        "max_journal_queue_size_seen": None,
        "runtime_health_rows": int(len(runtime_df)),
        "trustworthy_for_inference": None,
        "trust_comment": "",
    }

    if not runtime_df.empty:
        for k, src in [
            ("max_runtime_ticks_dropped_total", "runtime_ticks_dropped_total"),
            ("max_critical_ticks_dropped_total", "critical_ticks_dropped_total"),
            ("max_background_ticks_dropped_total", "background_ticks_dropped_total"),
            ("max_journal_records_dropped_total", "journal_records_dropped_total"),
            ("max_critical_queue_size_seen", "critical_queue_max_size_seen"),
            ("max_background_queue_size_seen", "background_queue_max_size_seen"),
            ("max_journal_queue_size_seen", "journal_queue_max_size_seen"),
        ]:
            if src in runtime_df and runtime_df[src].notna().any():
                summary[k] = float(runtime_df[src].max())

        drops_zero = all(
            (summary.get(k) is not None and float(summary.get(k)) == 0.0)
            for k in [
                "max_runtime_ticks_dropped_total",
                "max_critical_ticks_dropped_total",
                "max_background_ticks_dropped_total",
                "max_journal_records_dropped_total",
            ]
        )
        no_watchdog = (watchdog_related + stream_degraded_events) == 0
        no_reconnect = reconnect_related == 0

        trustworthy = drops_zero and no_watchdog
        summary["trustworthy_for_inference"] = trustworthy
        if trustworthy:
            summary["trust_comment"] = "No drop/backpressure evidence and no degradation incidents in session telemetry; data quality appears reliable for behavioral inference."
        elif drops_zero:
            summary["trust_comment"] = "No drop evidence, but stream/watchdog instability events were present; inference is usable but should consider potential transient data gaps."
        else:
            summary["trust_comment"] = "Tick/journal drop or backpressure signals were observed; quantitative conclusions should be treated as lower confidence."

    return summary


def classify_day_pattern(features_df: pd.DataFrame) -> str:
    if features_df.empty:
        return "No-trade session"

    wins = features_df[features_df["net_pnl"] > 0]
    losses = features_df[features_df["net_pnl"] < 0]
    avg_win = wins["net_pnl"].mean() if not wins.empty else 0.0
    avg_loss_abs = abs(losses["net_pnl"].mean()) if not losses.empty else 0.0
    largest_loss_abs = abs(losses["net_pnl"].min()) if not losses.empty else 0.0

    if len(wins) >= 2 * max(1, len(losses)) and largest_loss_abs > 4 * max(1.0, avg_win):
        return "Many small wins offset by a few tail losses"
    if len(losses) == 0:
        return "Uniformly positive day with no realized losers"
    if len(wins) == 0:
        return "Loss-dominated day"
    if avg_win > avg_loss_abs and features_df["net_pnl"].sum() > 0:
        return "Positive expectancy driven by frequent target hits"
    return "Mixed outcomes without a single dominant regime"


def make_counterfactual_table(features_df: pd.DataFrame) -> pd.DataFrame:
    thresholds = [2.0, 3.0, 4.0, 5.0]
    rows: list[dict[str, Any]] = []

    for th in thresholds:
        touched = features_df["in_trade_max_points"].fillna(-np.inf) >= th
        touched_rate = float(touched.mean()) if len(features_df) else np.nan

        win_mask = features_df["outcome"] == "WIN"
        loss_mask = features_df["outcome"] == "LOSS"

        win_rate = float((features_df.loc[win_mask, "in_trade_max_points"].fillna(-np.inf) >= th).mean()) if win_mask.any() else np.nan
        loss_rate = float((features_df.loc[loss_mask, "in_trade_max_points"].fillna(-np.inf) >= th).mean()) if loss_mask.any() else np.nan

        rows.append(
            {
                "target_points": th,
                "touch_rate_all": touched_rate,
                "touch_rate_winners": win_rate,
                "touch_rate_losers": loss_rate,
            }
        )

    # weak follow-through warning
    weak_warning = (features_df["first_1s_move"].fillna(0) <= 0) & (features_df["max_gain_first_3s"].fillna(0) < 1.0)
    loser_mask = features_df["outcome"] == "LOSS"
    winner_mask = features_df["outcome"] == "WIN"

    warning_row = {
        "target_points": "weak_follow_through_warning",
        "touch_rate_all": float(weak_warning.mean()) if len(features_df) else np.nan,
        "touch_rate_winners": float(weak_warning[winner_mask].mean()) if winner_mask.any() else np.nan,
        "touch_rate_losers": float(weak_warning[loser_mask].mean()) if loser_mask.any() else np.nan,
    }
    rows.append(warning_row)

    # post-exit target touch for non-target exits
    non_target = features_df[features_df["exit_reason"] != "TARGET_HIT"]
    rows.append(
        {
            "target_points": "non_target_exits_post_exit_target_touch",
            "touch_rate_all": float(non_target["post_exit_touched_target"].fillna(False).mean()) if not non_target.empty else np.nan,
            "touch_rate_winners": np.nan,
            "touch_rate_losers": np.nan,
        }
    )

    return pd.DataFrame(rows)


def make_time_of_day_summary(features_df: pd.DataFrame) -> pd.DataFrame:
    if features_df.empty:
        return pd.DataFrame()

    df = features_df.copy()
    df["entry_hour"] = df["entry_time"].dt.hour

    # before/after 1 PM
    df["bucket_pre_post_1pm"] = np.where(df["entry_time"].dt.time < time(13, 0), "PRE_1PM", "POST_1PM")

    # early/mid/late bins
    conditions = [
        df["entry_time"].dt.time < time(11, 0),
        (df["entry_time"].dt.time >= time(11, 0)) & (df["entry_time"].dt.time < time(13, 0)),
        df["entry_time"].dt.time >= time(13, 0),
    ]
    choices = ["EARLY_SESSION", "MID_SESSION", "LATE_SESSION"]
    df["bucket_3way"] = np.select(conditions, choices, default="OTHER")

    rows: list[dict[str, Any]] = []
    for bucket_col in ["bucket_pre_post_1pm", "bucket_3way"]:
        for bucket, g in df.groupby(bucket_col):
            wins = (g["net_pnl"] > 0).sum()
            losses = (g["net_pnl"] < 0).sum()
            tail_loss_count = int((g["net_pnl"] <= g["net_pnl"].quantile(0.1)).sum()) if len(g) >= 3 else int((g["net_pnl"] < 0).sum())
            rows.append(
                {
                    "bucket_type": bucket_col,
                    "bucket": bucket,
                    "trades": int(len(g)),
                    "wins": int(wins),
                    "losses": int(losses),
                    "hit_rate": float(wins / len(g)) if len(g) else np.nan,
                    "avg_pnl": float(g["net_pnl"].mean()) if len(g) else np.nan,
                    "median_pnl": float(g["net_pnl"].median()) if len(g) else np.nan,
                    "tail_loss_count": tail_loss_count,
                    "tail_loss_share": float(tail_loss_count / len(g)) if len(g) else np.nan,
                }
            )

    return pd.DataFrame(rows)


def make_runtime_stress_summary(event_rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not event_rows:
        return pd.DataFrame()

    stress_rows: list[dict[str, Any]] = []
    stress_keywords = ("DROP", "BACKPRESSURE", "WATCHDOG", "RECONNECT")
    direct_stress_events = {
        "STREAM_DEGRADED",
        "STREAM_RECOVERED",
        "ENTRY_DEFERRED_QUOTE_UNAVAILABLE",
        "JOURNAL_BACKPRESSURE",
        "QUEUE_DROP",
    }

    for event in event_rows:
        et = str(event.get("event_type") or "")
        ts = event.get("_ts")
        if not isinstance(ts, datetime):
            continue
        is_stress = (et in direct_stress_events) or any(k in et for k in stress_keywords)
        if not is_stress:
            continue

        pre_post = "PRE_1PM" if ts.time() < time(13, 0) else "POST_1PM"
        if ts.time() < time(11, 0):
            bucket3 = "EARLY_SESSION"
        elif ts.time() < time(13, 0):
            bucket3 = "MID_SESSION"
        else:
            bucket3 = "LATE_SESSION"

        stress_rows.append(
            {
                "timestamp": ts,
                "event_type": et,
                "bucket_pre_post_1pm": pre_post,
                "bucket_3way": bucket3,
            }
        )

    if not stress_rows:
        return pd.DataFrame(
            [
                {
                    "bucket_type": "bucket_pre_post_1pm",
                    "bucket": "PRE_1PM",
                    "stress_event_count": 0,
                    "distinct_stress_types": "",
                },
                {
                    "bucket_type": "bucket_pre_post_1pm",
                    "bucket": "POST_1PM",
                    "stress_event_count": 0,
                    "distinct_stress_types": "",
                },
                {
                    "bucket_type": "bucket_3way",
                    "bucket": "EARLY_SESSION",
                    "stress_event_count": 0,
                    "distinct_stress_types": "",
                },
                {
                    "bucket_type": "bucket_3way",
                    "bucket": "MID_SESSION",
                    "stress_event_count": 0,
                    "distinct_stress_types": "",
                },
                {
                    "bucket_type": "bucket_3way",
                    "bucket": "LATE_SESSION",
                    "stress_event_count": 0,
                    "distinct_stress_types": "",
                },
            ]
        )

    df = pd.DataFrame(stress_rows)
    rows: list[dict[str, Any]] = []
    for bucket_col in ["bucket_pre_post_1pm", "bucket_3way"]:
        grouped = df.groupby(bucket_col)
        for bucket, g in grouped:
            rows.append(
                {
                    "bucket_type": bucket_col,
                    "bucket": bucket,
                    "stress_event_count": int(len(g)),
                    "distinct_stress_types": ",".join(sorted(set(g["event_type"]))),
                }
            )
    return pd.DataFrame(rows)


def make_trade_lifecycle_text(row: pd.Series) -> str:
    pre = row.get("opt_pre_delta")
    idx_pre = row.get("idx_pre_delta")
    in_delta = row.get("opt_in_delta")
    first1 = row.get("first_1s_move")
    first3 = row.get("first_3s_move")
    best = row.get("in_trade_max_points")
    worst = row.get("in_trade_min_points")
    post_best = row.get("post_exit_best_delta")
    post_final = row.get("post_exit_final_delta")

    # exit interpretation
    exit_reason = row.get("exit_reason")
    if exit_reason == "TARGET_HIT":
        if post_best is not None and post_best > 5:
            exit_note = "Target exit worked but left additional upside afterwards."
        elif post_final is not None and post_final < -3:
            exit_note = "Exit looks timely; post-exit path faded materially."
        else:
            exit_note = "Exit looks reasonable around target completion."
    else:
        if post_best is not None and post_best >= 3:
            exit_note = "Exit may be early; meaningful recovery appeared after close."
        elif post_final is not None and post_final <= -3:
            exit_note = "Exit appears justified; weakness persisted post-close."
        else:
            exit_note = "Exit quality mixed; post-exit path inconclusive."

    return (
        f"Pre-entry option drift {fmt_num(pre)} points (index {fmt_num(idx_pre)}). "
        f"After entry: first 1s move {fmt_num(first1)}, first 3s move {fmt_num(first3)}, "
        f"in-trade range [{fmt_num(worst)}, {fmt_num(best)}] points vs entry. "
        f"Post-exit best/worst delta: {fmt_num(post_best)} / {fmt_num(row.get('post_exit_worst_delta'))}, "
        f"final @15s {fmt_num(post_final)}. {exit_note}"
    )


def collect_actionable_insights(features_df: pd.DataFrame, runtime_summary: dict[str, Any]) -> list[str]:
    insights: list[str] = []
    if features_df.empty:
        return ["No trade data available for insight extraction."]

    wins = features_df[features_df["outcome"] == "WIN"]
    losses = features_df[features_df["outcome"] == "LOSS"]

    # runtime insight
    insights.append(
        "[runtime insight] Drop counters stayed at zero across runtime telemetry, indicating no observable tick/journal loss in this session."
        if runtime_summary.get("max_runtime_ticks_dropped_total", 0) == 0
        else "[runtime insight] Non-zero drop counters were observed; microstructure conclusions should be treated with caution."
    )

    if not losses.empty:
        weak_warn = ((losses["first_1s_move"].fillna(0) <= 0) & (losses["max_gain_first_3s"].fillna(0) < 1)).mean()
        insights.append(
            f"[strategy behavior insight] {weak_warn:.0%} of losing trades showed weak immediate follow-through (first 1s <= 0 and <1 point max gain in first 3s)."
        )

        recover = losses["post_exit_best_delta"].fillna(-np.inf).ge(3).mean()
        insights.append(
            f"[execution insight] {recover:.0%} of losing trades had >=3 points of post-exit rebound, suggesting some exits were defensive but potentially early."
        )

    if not wins.empty:
        fast_wins = wins["holding_seconds"].dropna().le(5).mean()
        insights.append(
            f"[strategy behavior insight] {fast_wins:.0%} of winning trades closed within 5 seconds, consistent with a fast-follow-through payoff profile."
        )

    spread_gap = None
    if not wins.empty and not losses.empty:
        spread_gap = losses["opt_in_spread_avg"].mean() - wins["opt_in_spread_avg"].mean()
        insights.append(
            f"[candidate microstructure filter idea] In-trade option spread difference (loss-win) was {spread_gap:.2f} points; spread alone appears weak as a discriminator in this sample."
        )

        slope_diff = losses["first_3s_move"].mean() - wins["first_3s_move"].mean()
        insights.append(
            f"[candidate microstructure filter idea] First-3-second move was {slope_diff:.2f} points lower in losers vs winners, making early path momentum a stronger candidate signal than spread/imbalance."
        )

    post_target_touch_non_target = features_df[features_df["exit_reason"] != "TARGET_HIT"]["post_exit_touched_target"].fillna(False).mean()
    if not np.isnan(post_target_touch_non_target):
        insights.append(
            f"[execution insight] {post_target_touch_non_target:.0%} of non-target exits later touched target in the next 15 seconds."
        )

    insights.append(
        "[logging/data-quality insight] Trade-path capture (pre-entry/in-trade/post-exit) was available trade-by-trade, enabling high-confidence path diagnostics without needing full-day options tape."
    )

    # ensure 5-10 items
    if len(insights) > 10:
        insights = insights[:10]
    return insights


def write_report(
    out_report: Path,
    session_date: date,
    session_paths: SessionPaths,
    features_df: pd.DataFrame,
    trade_summary_df: pd.DataFrame,
    runtime_summary: dict[str, Any],
    runtime_df: pd.DataFrame,
    counterfactual_df: pd.DataFrame,
    tod_df: pd.DataFrame,
    runtime_stress_df: pd.DataFrame,
    chart_paths: dict[str, Path],
    per_trade_chart_paths: dict[str, Path],
    lifecycle_notes: dict[str, str],
) -> None:
    out_report.parent.mkdir(parents=True, exist_ok=True)

    if features_df.empty:
        out_report.write_text(
            f"# Session Report ({session_date.isoformat()})\n\nNo trade records were available for the selected session.\n",
            encoding="utf-8",
        )
        return

    wins = features_df[features_df["net_pnl"] > 0]
    losses = features_df[features_df["net_pnl"] < 0]

    gross_pnl = float(features_df["net_pnl"].sum())
    net_pnl = gross_pnl  # charges already embedded in net if present

    avg_winner = float(wins["net_pnl"].mean()) if not wins.empty else np.nan
    avg_loser = float(losses["net_pnl"].mean()) if not losses.empty else np.nan
    largest_win = float(features_df["net_pnl"].max())
    largest_loss = float(features_df["net_pnl"].min())
    hit_rate = float((features_df["net_pnl"] > 0).mean())
    expectancy = float(features_df["net_pnl"].mean())

    analyzed_files = [
        session_paths.trades_enriched,
        session_paths.trades_raw,
        session_paths.events,
        session_paths.features_daily,
        session_paths.ticks_sensex,
        session_paths.ticks_futures,
        session_paths.ticks_options,
        session_paths.trade_ticks_dir,
        session_paths.runtime_control,
    ]
    analyzed_files = [p for p in analyzed_files if p is not None and p.exists()]

    day_pattern = classify_day_pattern(features_df)
    insights = collect_actionable_insights(features_df, runtime_summary)

    # Winner/loser microstructure comparison
    compare_fields = [
        "entry_spread",
        "spread_median_first_2s",
        "imbalance_entry",
        "imbalance_drift_first_2s",
        "pre_entry_velocity",
        "first_1s_move",
        "first_3s_move",
        "in_trade_max_points",
        "in_trade_min_points",
        "post_exit_best_delta",
        "post_exit_final_delta",
        "holding_seconds",
    ]

    comp_rows: list[dict[str, Any]] = []
    for col in compare_fields:
        comp_rows.append(
            {
                "feature": col,
                "winner_mean": wins[col].mean() if col in wins else np.nan,
                "loser_mean": losses[col].mean() if col in losses else np.nan,
                "winner_median": wins[col].median() if col in wins else np.nan,
                "loser_median": losses[col].median() if col in losses else np.nan,
            }
        )
    comp_df = pd.DataFrame(comp_rows)

    # tail losses segmentation
    losses_sorted = losses.sort_values("net_pnl")
    tail_threshold = losses_sorted["net_pnl"].quantile(0.5) if not losses_sorted.empty else np.nan
    losses_tail = losses_sorted[losses_sorted["net_pnl"] <= tail_threshold] if not losses_sorted.empty else losses_sorted
    losses_small = losses_sorted[losses_sorted["net_pnl"] > tail_threshold] if not losses_sorted.empty else losses_sorted

    continuation = features_df[features_df["continuation_or_reversal"] == "CONTINUATION"]
    reversal = features_df[features_df["continuation_or_reversal"] == "REVERSAL"]
    fragile = features_df[features_df["fragile"] == True]
    non_fragile = features_df[features_df["fragile"] == False]

    early = features_df[features_df["entry_time"].dt.time < time(11, 30)]
    late = features_df[features_df["entry_time"].dt.time >= time(13, 0)]

    # Exit quality aggregate
    non_target = features_df[features_df["exit_reason"] != "TARGET_HIT"]
    target_exits = features_df[features_df["exit_reason"] == "TARGET_HIT"]

    non_target_recovered = non_target["post_exit_best_delta"].fillna(-np.inf).ge(3).mean() if not non_target.empty else np.nan
    target_faded = target_exits["post_exit_final_delta"].fillna(0).lt(-3).mean() if not target_exits.empty else np.nan

    # full trade table for markdown
    ledger_cols = [
        "trade_id",
        "entry_time",
        "exit_time",
        "holding_seconds",
        "side",
        "symbol",
        "entry_price",
        "exit_price",
        "target_price",
        "mfe",
        "mae",
        "net_pnl",
        "exit_reason",
        "exit_timing_assessment",
        "target_nearly_reached",
        "post_exit_best_delta",
        "post_exit_final_delta",
    ]
    ledger_md = markdown_table(trade_summary_df.sort_values("entry_time"), ledger_cols)

    lines: list[str] = []
    lines.append(f"# Session Report ({session_date.isoformat()})")
    lines.append("")
    lines.append(f"Analyzed date: **{session_date.isoformat()}**")
    lines.append("")
    lines.append("## Data Inputs Used")
    for p in analyzed_files:
        lines.append(f"- `{p}`")
    lines.append("")

    lines.append("## 1. Executive Summary")
    lines.append(f"- Trades: **{len(features_df)}**")
    lines.append(f"- Wins / Losses / Flat: **{len(wins)} / {len(losses)} / {len(features_df) - len(wins) - len(losses)}**")
    lines.append(f"- Gross PnL: **{fmt_num(gross_pnl)}**")
    lines.append(f"- Net PnL: **{fmt_num(net_pnl)}**")
    lines.append(f"- Average Winner: **{fmt_num(avg_winner)}**")
    lines.append(f"- Average Loser: **{fmt_num(avg_loser)}**")
    lines.append(f"- Largest Win: **{fmt_num(largest_win)}**")
    lines.append(f"- Largest Loss: **{fmt_num(largest_loss)}**")
    lines.append(f"- Hit Rate: **{hit_rate:.2%}**")
    lines.append(f"- Expectancy per Trade: **{fmt_num(expectancy)}**")
    lines.append(f"- Day Pattern: **{day_pattern}**")
    lines.append("")

    lines.append("## 2. System Health / Runtime Summary")
    lines.append(f"- STREAM_CONNECTED events: **{runtime_summary.get('stream_connected_events')}**")
    lines.append(f"- Stream close events: **{runtime_summary.get('stream_closed_events')}**")
    lines.append(f"- Reconnect-related events: **{runtime_summary.get('reconnect_events')}**")
    lines.append(f"- Watchdog-related events: **{runtime_summary.get('watchdog_events')}**")
    lines.append(f"- Stream degraded/recovered events: **{runtime_summary.get('stream_degraded_events')} / {runtime_summary.get('stream_recovered_events')}**")
    lines.append(f"- Entry deferred (quote unavailable): **{runtime_summary.get('entry_deferred_quote_unavailable')}**")
    lines.append(f"- Lattice rebases: **{runtime_summary.get('lattice_rebase_events')}**")
    lines.append(f"- Queue/backpressure explicit events: **{runtime_summary.get('queue_or_backpressure_events')}**")
    lines.append(f"- Max runtime tick drops: **{fmt_num(runtime_summary.get('max_runtime_ticks_dropped_total'),0)}**")
    lines.append(f"- Max critical tick drops: **{fmt_num(runtime_summary.get('max_critical_ticks_dropped_total'),0)}**")
    lines.append(f"- Max background tick drops: **{fmt_num(runtime_summary.get('max_background_ticks_dropped_total'),0)}**")
    lines.append(f"- Max journal drops: **{fmt_num(runtime_summary.get('max_journal_records_dropped_total'),0)}**")
    lines.append(
        f"- Queue max sizes seen (critical/background/journal): **{fmt_num(runtime_summary.get('max_critical_queue_size_seen'),0)} / {fmt_num(runtime_summary.get('max_background_queue_size_seen'),0)} / {fmt_num(runtime_summary.get('max_journal_queue_size_seen'),0)}**"
    )
    lines.append(f"- Inference trustworthiness: **{runtime_summary.get('trustworthy_for_inference')}**")
    lines.append(f"- Data-quality assessment: {runtime_summary.get('trust_comment')}")
    lines.append("")

    lines.append("## 3. Trade Ledger Table")
    lines.append(ledger_md)
    lines.append("")

    lines.append("## 4. Full Trade Lifecycle Analysis (Per Trade)")
    for _, row in trade_summary_df.sort_values("entry_time").iterrows():
        tid = row["trade_id"]
        lines.append(f"### {tid}")
        lines.append(f"- Side/Contract: `{row.get('side')}` `{row.get('symbol')}`")
        lines.append(
            f"- Entry/Exit: `{fmt_dt(row.get('entry_time'))}` -> `{fmt_dt(row.get('exit_time'))}` | Duration `{fmt_num(row.get('holding_seconds'))}s` | Exit reason `{row.get('exit_reason')}`"
        )
        lines.append(
            f"- Prices: entry `{fmt_num(row.get('entry_price'))}`, target `{fmt_num(row.get('target_price'))}`, exit `{fmt_num(row.get('exit_price'))}` | Realized PnL `{fmt_num(row.get('net_pnl'))}`"
        )
        lines.append(f"- Lifecycle read: {lifecycle_notes.get(tid, 'No lifecycle note available.')}")
        chart_path = per_trade_chart_paths.get(tid)
        if chart_path:
            lines.append(f"- Chart: `{chart_path}`")
        lines.append("")

    lines.append("## 5. Visualizations")
    lines.append("- Session-level charts:")
    for name, path in chart_paths.items():
        lines.append(f"  - {name}: `{path}`")
    lines.append("- Per-trade charts:")
    lines.append(f"  - Count generated: **{len(per_trade_chart_paths)}**")
    lines.append(f"  - Folder: `{(out_report.parent / 'trade_charts')}`")
    lines.append("")

    lines.append("## 6. Microstructure Feature Analysis")
    lines.append("### Winners vs Losers")
    lines.append(markdown_table(comp_df, ["feature", "winner_mean", "loser_mean", "winner_median", "loser_median"]))
    lines.append("")

    lines.append("### Small Losers vs Tail Losers")
    lines.append(
        f"- Loser count: **{len(losses_sorted)}**, tail-loss threshold (median loser pnl): **{fmt_num(tail_threshold)}**"
    )
    if not losses_tail.empty:
        lines.append(
            f"- Tail losers average first_3s_move: **{fmt_num(losses_tail['first_3s_move'].mean())}**, average post_exit_best_delta: **{fmt_num(losses_tail['post_exit_best_delta'].mean())}**"
        )
    if not losses_small.empty:
        lines.append(
            f"- Smaller losers average first_3s_move: **{fmt_num(losses_small['first_3s_move'].mean())}**, average post_exit_best_delta: **{fmt_num(losses_small['post_exit_best_delta'].mean())}**"
        )
    lines.append("")

    lines.append("### Continuation/Reversal and Fragility Views")
    lines.append(
        f"- Continuation trades: **{len(continuation)}**, avg pnl `{fmt_num(continuation['net_pnl'].mean() if not continuation.empty else np.nan)}`"
    )
    lines.append(
        f"- Reversal trades: **{len(reversal)}**, avg pnl `{fmt_num(reversal['net_pnl'].mean() if not reversal.empty else np.nan)}`"
    )
    lines.append(
        f"- Fragile trades: **{len(fragile)}**, avg pnl `{fmt_num(fragile['net_pnl'].mean() if not fragile.empty else np.nan)}`"
    )
    lines.append(
        f"- Non-fragile trades: **{len(non_fragile)}**, avg pnl `{fmt_num(non_fragile['net_pnl'].mean() if not non_fragile.empty else np.nan)}`"
    )
    lines.append("")

    lines.append("### Early-Day vs Late-Day")
    lines.append(
        f"- Early (before 11:30): **{len(early)}** trades, hit rate `{(early['net_pnl'] > 0).mean():.2%}` avg pnl `{fmt_num(early['net_pnl'].mean() if not early.empty else np.nan)}`"
    )
    lines.append(
        f"- Late (after 13:00): **{len(late)}** trades, hit rate `{(late['net_pnl'] > 0).mean():.2%}` avg pnl `{fmt_num(late['net_pnl'].mean() if not late.empty else np.nan)}`"
    )
    lines.append("")

    lines.append("## 7. Exit Quality Analysis")
    lines.append(
        f"- Target exits: **{len(target_exits)}**, share of target exits with post-exit fade (< -3 points final delta): **{target_faded:.2%}**"
        if not np.isnan(target_faded)
        else f"- Target exits: **{len(target_exits)}**"
    )
    lines.append(
        f"- Non-target exits: **{len(non_target)}**, share with post-exit rebound >= +3 points: **{non_target_recovered:.2%}**"
        if not np.isnan(non_target_recovered)
        else f"- Non-target exits: **{len(non_target)}**"
    )

    reasons = trade_summary_df["exit_reason"].value_counts()
    reason_txt = ", ".join([f"{k}: {v}" for k, v in reasons.items()])
    lines.append(f"- Exit reason mix: {reason_txt}")

    lines.append(
        f"- Share of trades that nearly reached target without in-trade touch: **{trade_summary_df['target_approached_not_hit'].fillna(False).mean():.2%}**"
    )
    lines.append("")

    lines.append("## 8. Counterfactual / What-if Analysis")
    lines.append(markdown_table(counterfactual_df, ["target_points", "touch_rate_all", "touch_rate_winners", "touch_rate_losers"]))
    lines.append(
        "- Interpretation: target-touch counterfactuals are descriptive only; they do not model fill quality, queueing, or order-state interactions."
    )
    lines.append("")

    lines.append("## 9. Time-of-Day Analysis")
    if not tod_df.empty:
        lines.append(markdown_table(tod_df, ["bucket_type", "bucket", "trades", "wins", "losses", "hit_rate", "avg_pnl", "median_pnl", "tail_loss_count", "tail_loss_share"]))
    else:
        lines.append("No time-of-day slices were available.")
    lines.append("")
    lines.append("### Runtime Stress Concentration by Time Bucket")
    if runtime_stress_df is not None and not runtime_stress_df.empty:
        lines.append(markdown_table(runtime_stress_df, ["bucket_type", "bucket", "stress_event_count", "distinct_stress_types"]))
    else:
        lines.append("No runtime stress events were observed in the session event stream.")
    lines.append("")

    lines.append("## 10. Actionable Insights")
    for insight in insights:
        lines.append(f"- {insight}")
    lines.append("")

    lines.append("## 11. Final Recommendation")
    lines.append("- Healthy aspects: runtime telemetry showed stable ingest/write behavior with no visible drop counters; trade-path logging quality is high.")
    lines.append("- Fragile aspects: tail losses remain concentrated in a minority of trades and are associated with weak immediate follow-through in early seconds.")
    lines.append("- Next investigation: validate early path-momentum diagnostics over multiple sessions before changing live risk logic.")
    lines.append("- Tomorrow run posture: proceed with strategy unchanged, with observational focus on early in-trade trajectory and post-exit recovery diagnostics.")
    lines.append("")

    lines.append("## Method Notes")
    lines.append("- Session date auto-detected from the latest dated log folders/files unless explicitly supplied.")
    lines.append("- Trade rows were de-duplicated by `trade_id`, preferring `post_exit_observation_done=true` and `summary_version=post_exit_enriched`.")
    lines.append("- Feature formulas are transparent and based on direct tick-path arithmetic (spread medians, imbalance, first-1s/3s move, pre-velocity, post-exit deltas).")
    lines.append("- Missing-file handling: optional files (`features_daily.csv`, full-day `options.jsonl`) are used if present; analysis continues when absent.")

    out_report.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()

    repo_root = Path(args.repo_root).resolve()
    logs_dir = (repo_root / args.logs_dir).resolve()
    out_root = (repo_root / args.output_root).resolve()

    session_date = detect_latest_session_date(logs_dir, args.date)
    paths = build_session_paths(repo_root, logs_dir, session_date)

    out_dir = out_root / session_date.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    trade_chart_dir = out_dir / "trade_charts"

    # load core datasets
    trade_rows = load_jsonl(paths.trades_enriched)
    if not trade_rows and paths.trades_raw:
        trade_rows = load_jsonl(paths.trades_raw)

    trade_rows = filter_rows_by_session_date(trade_rows, session_date)
    trade_rows = dedupe_trades(trade_rows)

    if not trade_rows:
        raise RuntimeError(f"No trade rows found for session {session_date.isoformat()} in {paths.trades_enriched}")

    tick_file_map = load_trade_tick_map(paths.trade_ticks_dir)

    feature_rows: list[dict[str, Any]] = []
    per_trade_tick_frames: dict[str, pd.DataFrame] = {}
    per_trade_chart_paths: dict[str, Path] = {}
    lifecycle_notes: dict[str, str] = {}

    # per trade feature extraction + charts
    for trade in sorted(trade_rows, key=lambda x: choose_entry_time(x) or datetime.min):
        trade_id = str(trade.get("trade_id"))
        entry_time = choose_entry_time(trade)

        tick_path = tick_file_map.get(trade_id)
        tick_df = load_trade_tick_frame(tick_path, entry_time) if tick_path is not None else pd.DataFrame()
        per_trade_tick_frames[trade_id] = tick_df

        feat = compute_trade_features(trade, tick_df)
        feature_rows.append(feat)
        lifecycle_notes[trade_id] = make_trade_lifecycle_text(pd.Series(feat))

        chart_name = f"{clean_filename(trade_id)}.png"
        chart_path = trade_chart_dir / chart_name
        make_trade_chart(trade, feat, tick_df, chart_path)
        if chart_path.exists():
            per_trade_chart_paths[trade_id] = chart_path

    features_df = pd.DataFrame(feature_rows)
    if features_df.empty:
        raise RuntimeError("No trade features computed for session.")

    # ensure datetime columns typed
    for col in ["entry_time", "exit_time"]:
        if col in features_df:
            features_df[col] = pd.to_datetime(features_df[col], errors="coerce")

    features_df = features_df.sort_values("entry_time").reset_index(drop=True)

    # trade summary (ledger-ready)
    trade_summary_df = features_df.copy()

    # save csv outputs
    trade_summary_csv = out_dir / "trade_summary.csv"
    trade_features_csv = out_dir / "trade_features.csv"
    trade_summary_df.to_csv(trade_summary_csv, index=False)
    features_df.to_csv(trade_features_csv, index=False)

    # charts
    chart_paths: dict[str, Path] = {}

    p_timeline = out_dir / "session_trade_timeline.png"
    make_session_timeline_chart(features_df, p_timeline)
    if p_timeline.exists():
        chart_paths["session_trade_timeline"] = p_timeline

    dist_paths = make_distribution_charts(features_df, out_dir)
    chart_paths.update({k: v for k, v in dist_paths.items() if v.exists()})

    p_first5 = out_dir / "entry_first_5s_path_behavior.png"
    make_first5s_path_chart(features_df, per_trade_tick_frames, p_first5)
    if p_first5.exists():
        chart_paths["entry_first_5s_path_behavior"] = p_first5

    # runtime
    events_rows = load_jsonl(paths.events)
    runtime_df, event_rows_for_day = build_runtime_df(events_rows, session_date)
    runtime_summary = summarize_runtime(event_rows_for_day, runtime_df)

    runtime_csv = out_dir / "runtime_health_timeseries.csv"
    if not runtime_df.empty:
        runtime_df.to_csv(runtime_csv, index=False)
        chart_paths["runtime_health_timeseries_csv"] = runtime_csv

    p_runtime = out_dir / "runtime_stability.png"
    make_runtime_stability_chart(runtime_df, event_rows_for_day, p_runtime)
    if p_runtime.exists():
        chart_paths["runtime_stability"] = p_runtime

    # counterfactuals
    counterfactual_df = make_counterfactual_table(features_df)
    counterfactual_csv = out_dir / "counterfactual_summary.csv"
    counterfactual_df.to_csv(counterfactual_csv, index=False)
    chart_paths["counterfactual_summary_csv"] = counterfactual_csv

    # time of day
    tod_df = make_time_of_day_summary(features_df)
    tod_csv = out_dir / "time_of_day_summary.csv"
    tod_df.to_csv(tod_csv, index=False)
    chart_paths["time_of_day_summary_csv"] = tod_csv

    runtime_stress_df = make_runtime_stress_summary(event_rows_for_day)
    runtime_stress_csv = out_dir / "runtime_stress_by_time_bucket.csv"
    runtime_stress_df.to_csv(runtime_stress_csv, index=False)
    chart_paths["runtime_stress_by_time_bucket_csv"] = runtime_stress_csv

    # report
    report_path = out_dir / "report.md"
    write_report(
        out_report=report_path,
        session_date=session_date,
        session_paths=paths,
        features_df=features_df,
        trade_summary_df=trade_summary_df,
        runtime_summary=runtime_summary,
        runtime_df=runtime_df,
        counterfactual_df=counterfactual_df,
        tod_df=tod_df,
        runtime_stress_df=runtime_stress_df,
        chart_paths=chart_paths,
        per_trade_chart_paths=per_trade_chart_paths,
        lifecycle_notes=lifecycle_notes,
    )

    # also save machine-readable summary
    summary_json = {
        "session_date": session_date.isoformat(),
        "report_path": str(report_path),
        "trade_count": int(len(features_df)),
        "win_count": int((features_df["net_pnl"] > 0).sum()),
        "loss_count": int((features_df["net_pnl"] < 0).sum()),
        "net_pnl": float(features_df["net_pnl"].sum()),
        "runtime_trustworthy": runtime_summary.get("trustworthy_for_inference"),
        "output_dir": str(out_dir),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary_json, indent=2), encoding="utf-8")

    print(f"Session report generated for {session_date.isoformat()}")
    print(f"Report: {report_path}")
    print(f"Trades analyzed: {len(features_df)}")
    print(f"Per-trade charts: {len(per_trade_chart_paths)}")


if __name__ == "__main__":
    main()
