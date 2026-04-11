from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_FILES = [
    REPO_ROOT / "logs" / "11Mar_trades.jsonl",
    REPO_ROOT / "logs" / "12Mar_trades.jsonl",
    REPO_ROOT / "logs" / "trades.jsonl",
]
INSTRUMENTS_PATH = REPO_ROOT / "data" / "instruments.csv"
OUTPUT_DIR = REPO_ROOT / "analysis" / "output"
REPORT_PATH = REPO_ROOT / "analysis" / "HYPOTHESIS_TEST_REPORT.md"
LARGE_LOSS_THRESHOLD = -10000.0


@dataclass(frozen=True)
class EarlyExitRule:
    rule_id: str
    description: str
    evaluator: Callable[[pd.Series, pd.DataFrame], tuple[pd.Timestamp, float] | None]


@dataclass(frozen=True)
class EntryFilterRule:
    rule_id: str
    description: str
    keep_mask_builder: Callable[[pd.DataFrame], pd.Series]


def _safe_float(value: object) -> float | np.nan:
    if value is None:
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def _safe_int(value: object) -> int | np.nan:
    if value is None:
        return np.nan
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return np.nan


def _to_ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _require_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = np.nan
    return out


def load_events(log_files: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in log_files:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as fp:
            for line_no, line in enumerate(fp, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                payload = record.get("payload", {}) or {}
                flat = dict(payload)
                flat["event_type"] = record.get("event_type")
                flat["event_timestamp"] = record.get("timestamp")
                flat["source_file"] = path.name
                flat["source_line"] = line_no
                rows.append(flat)
    events = pd.DataFrame(rows)
    if events.empty:
        raise RuntimeError("No trade journal events found.")
    events["event_timestamp"] = _to_ts(events["event_timestamp"])
    events["event_date"] = events["event_timestamp"].dt.date
    return events


def _summarize_marks(group: pd.DataFrame) -> pd.Series:
    g = group.sort_values("mark_time").copy()
    sec = g["seconds_since_entry"]
    pnl = g["pnl_delta"]

    out: dict[str, object] = {
        "mark_count": int(len(g)),
        "first_mark_time": g["mark_time"].iloc[0],
        "last_mark_time": g["mark_time"].iloc[-1],
        "first_mark_delay_seconds": float(sec.iloc[0]),
        "first_ltp": float(g["ltp"].iloc[0]),
        "last_ltp": float(g["ltp"].iloc[-1]),
        "min_ltp": float(g["ltp"].min()),
        "max_ltp": float(g["ltp"].max()),
        "max_mfe_from_marks": float(g["cum_mfe"].max()),
        "max_mae_from_marks": float(g["cum_mae"].min()),
        "first_move_points": float(pnl.iloc[0]),
    }

    first_move = float(pnl.iloc[0])
    if first_move > 0:
        out["first_move_direction"] = "FAVOR"
    elif first_move < 0:
        out["first_move_direction"] = "AGAINST"
    else:
        out["first_move_direction"] = "FLAT"

    horizons = [5, 10, 15, 20, 30, 60]
    for h in horizons:
        sub = g[sec <= h]
        out[f"runup_{h}s"] = float(sub["pnl_delta"].max()) if not sub.empty else np.nan
        out[f"drawdown_{h}s"] = float(sub["pnl_delta"].min()) if not sub.empty else np.nan
        out[f"last_pnl_{h}s"] = float(sub["pnl_delta"].iloc[-1]) if not sub.empty else np.nan
        out[f"price_range_{h}s"] = (
            float(sub["ltp"].max() - sub["ltp"].min()) if not sub.empty else np.nan
        )

    plus_thresholds = [0.5, 1.0, 1.5, 2.0, 3.0]
    minus_thresholds = [1.0, 2.0, 3.0, 5.0]
    for th in plus_thresholds:
        key = str(th).replace(".", "_")
        hit = sec[pnl >= th]
        out[f"time_to_plus_{key}s"] = float(hit.iloc[0]) if not hit.empty else np.nan
    for th in minus_thresholds:
        key = str(th).replace(".", "_")
        hit = sec[pnl <= -th]
        out[f"time_to_minus_{key}s"] = float(hit.iloc[0]) if not hit.empty else np.nan

    return pd.Series(out)


def build_trade_dataset(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    entries = events[events["event_type"] == "TRADE_ENTERED"].copy()
    exits = events[events["event_type"] == "TRADE_EXITED"].copy()
    targets = events[events["event_type"] == "TARGET_PLACED"].copy()
    early = events[events["event_type"] == "EARLY_FAILURE_SIGNAL"].copy()
    marks = events[events["event_type"] == "OPEN_POSITION_MARK"].copy()

    entries = _require_columns(
        entries,
        [
            "trade_id",
            "symbol",
            "side",
            "product",
            "entry_time",
            "entry_price",
            "target_price",
            "quantity",
            "strike",
            "expiry",
            "underlying_spot",
            "source_candle_start",
            "trigger_price",
            "signal_kind",
        ],
    )
    exits = _require_columns(
        exits,
        [
            "trade_id",
            "exit_time",
            "exit_reason",
            "exit_price",
            "gross_pnl",
            "net_pnl",
            "charges",
            "realized_pnl_after_trade",
        ],
    )
    targets = _require_columns(targets, ["trade_id", "order_id", "target_price"])
    early = _require_columns(
        early,
        [
            "trade_id",
            "mark_time",
            "duration_seconds",
            "current_price",
            "mfe",
            "mae",
            "signal_kind",
        ],
    )
    marks = _require_columns(
        marks,
        ["trade_id", "mark_time", "entry_price", "target_price", "ltp", "signal_kind", "mfe", "mae"],
    )

    entries["entry_time"] = _to_ts(entries["entry_time"])
    entries["source_candle_start"] = _to_ts(entries["source_candle_start"])
    entries["expiry"] = _to_ts(entries["expiry"])
    entries["event_timestamp"] = _to_ts(entries["event_timestamp"])
    entries = entries.sort_values(["entry_time", "event_timestamp"]).drop_duplicates(
        subset=["trade_id"], keep="first"
    )

    exits["exit_time"] = _to_ts(exits["exit_time"])
    exits["event_timestamp"] = _to_ts(exits["event_timestamp"])
    exits = exits.sort_values(["exit_time", "event_timestamp"]).drop_duplicates(
        subset=["trade_id"], keep="last"
    )

    targets = targets.sort_values("event_timestamp").drop_duplicates(subset=["trade_id"], keep="first")

    early["mark_time"] = _to_ts(early["mark_time"])
    early["event_timestamp"] = _to_ts(early["event_timestamp"])
    early = early.sort_values(["mark_time", "event_timestamp"]).drop_duplicates(
        subset=["trade_id"], keep="first"
    )

    marks["mark_time"] = _to_ts(marks["mark_time"])
    marks["event_timestamp"] = _to_ts(marks["event_timestamp"])
    marks["mark_time"] = marks["mark_time"].fillna(marks["event_timestamp"])
    marks["entry_price"] = marks["entry_price"].map(_safe_float)
    marks["target_price"] = marks["target_price"].map(_safe_float)
    marks["ltp"] = marks["ltp"].map(_safe_float)
    marks = marks.dropna(subset=["trade_id", "mark_time", "ltp"]).copy()

    numeric_cols = ["entry_price", "target_price", "quantity", "strike", "underlying_spot", "trigger_price"]
    for col in numeric_cols:
        entries[col] = entries[col].map(_safe_float)
    entries["quantity"] = entries["quantity"].map(_safe_int)

    trades = entries[
        [
            "trade_id",
            "source_file",
            "entry_time",
            "symbol",
            "side",
            "product",
            "entry_price",
            "target_price",
            "quantity",
            "strike",
            "expiry",
            "underlying_spot",
            "source_candle_start",
            "trigger_price",
            "signal_kind",
        ]
    ].copy()
    trades = trades.merge(
        exits[
            [
                "trade_id",
                "exit_time",
                "exit_reason",
                "exit_price",
                "gross_pnl",
                "net_pnl",
                "charges",
                "realized_pnl_after_trade",
            ]
        ],
        on="trade_id",
        how="left",
    )
    trades = trades.merge(
        targets[["trade_id", "order_id"]].rename(columns={"order_id": "target_order_id"}),
        on="trade_id",
        how="left",
    )
    trades = trades.merge(
        early[
            [
                "trade_id",
                "mark_time",
                "duration_seconds",
                "current_price",
                "mfe",
                "mae",
                "signal_kind",
            ]
        ].rename(
            columns={
                "mark_time": "early_failure_mark_time",
                "duration_seconds": "early_failure_duration_seconds",
                "current_price": "early_failure_price",
                "mfe": "early_failure_mfe",
                "mae": "early_failure_mae",
                "signal_kind": "early_failure_signal_kind",
            }
        ),
        on="trade_id",
        how="left",
    )

    marks_enriched = marks.merge(
        trades[["trade_id", "entry_time", "entry_price", "target_price"]],
        on="trade_id",
        how="left",
        suffixes=("", "_trade"),
    )
    marks_enriched["entry_time"] = marks_enriched["entry_time"].fillna(marks_enriched["entry_time_trade"])
    marks_enriched["entry_price"] = marks_enriched["entry_price"].fillna(marks_enriched["entry_price_trade"])
    marks_enriched["target_price"] = marks_enriched["target_price"].fillna(marks_enriched["target_price_trade"])
    marks_enriched = marks_enriched.drop(columns=["entry_time_trade", "entry_price_trade", "target_price_trade"])
    marks_enriched["entry_time"] = _to_ts(marks_enriched["entry_time"])
    marks_enriched["mark_time"] = _to_ts(marks_enriched["mark_time"])
    marks_enriched["entry_price"] = marks_enriched["entry_price"].map(_safe_float)
    marks_enriched["target_price"] = marks_enriched["target_price"].map(_safe_float)
    marks_enriched["ltp"] = marks_enriched["ltp"].map(_safe_float)
    marks_enriched = marks_enriched.dropna(subset=["entry_time", "mark_time", "entry_price", "ltp"]).copy()
    marks_enriched["seconds_since_entry"] = (
        marks_enriched["mark_time"] - marks_enriched["entry_time"]
    ).dt.total_seconds()
    marks_enriched = marks_enriched[marks_enriched["seconds_since_entry"] >= 0].copy()
    marks_enriched["pnl_delta"] = marks_enriched["ltp"] - marks_enriched["entry_price"]
    marks_enriched = marks_enriched.sort_values(["trade_id", "mark_time"])
    marks_enriched["cum_mfe"] = marks_enriched.groupby("trade_id")["pnl_delta"].cummax()
    marks_enriched["cum_mae"] = marks_enriched.groupby("trade_id")["pnl_delta"].cummin()

    mark_rows: list[dict[str, object]] = []
    for trade_id, grp in marks_enriched.groupby("trade_id"):
        summary = _summarize_marks(grp).to_dict()
        summary["trade_id"] = trade_id
        mark_rows.append(summary)
    mark_summary = pd.DataFrame(mark_rows)
    trades = trades.merge(mark_summary, on="trade_id", how="left")
    trades["max_dd"] = np.maximum(0.0, -trades["max_mae_from_marks"])
    trades["max_runup"] = np.maximum(0.0, trades["max_mfe_from_marks"])

    trades["effective_exit_time"] = trades["exit_time"].fillna(trades["last_mark_time"])
    trades["effective_exit_price"] = trades["exit_price"].fillna(trades["last_ltp"])
    trades["holding_seconds"] = (
        trades["effective_exit_time"] - trades["entry_time"]
    ).dt.total_seconds()
    trades["realized_points"] = trades["effective_exit_price"] - trades["entry_price"]
    trades["computed_gross_pnl"] = trades["realized_points"] * trades["quantity"]
    trades["net_pnl"] = trades["net_pnl"].map(_safe_float)
    trades["gross_pnl"] = trades["gross_pnl"].map(_safe_float)
    trades["net_pnl_effective"] = trades["net_pnl"].fillna(trades["computed_gross_pnl"])
    trades["status"] = np.where(trades["exit_time"].isna(), "OPEN", "CLOSED")
    trades["target_hit"] = trades["exit_reason"].eq("TARGET_HIT")
    trades["early_failure_logged"] = trades["early_failure_mark_time"].notna()

    trades["signal_kind"] = trades["signal_kind"].fillna("").astype(str)
    trades["signal_family"] = np.where(
        trades["signal_kind"].str.startswith("CONTINUATION"),
        "CONTINUATION",
        np.where(trades["signal_kind"].str.startswith("REVERSAL"), "REVERSAL", "UNKNOWN"),
    )
    trades["entry_date"] = trades["entry_time"].dt.date
    trades["entry_hour"] = trades["entry_time"].dt.hour
    trades["entry_minute"] = trades["entry_time"].dt.minute
    trades["entry_delay_seconds"] = (
        trades["entry_time"] - trades["source_candle_start"]
    ).dt.total_seconds()
    trades["trigger_gap_directional"] = np.where(
        trades["side"].eq("CALL"),
        trades["underlying_spot"] - trades["trigger_price"],
        np.where(trades["side"].eq("PUT"), trades["trigger_price"] - trades["underlying_spot"], np.nan),
    )

    atm_strike = np.round(trades["underlying_spot"] / 100.0) * 100.0
    trades["atm_strike"] = atm_strike
    trades["strike_minus_spot"] = trades["strike"] - trades["underlying_spot"]
    trades["atm_distance_points"] = (trades["strike"] - trades["atm_strike"]).abs()

    def _classify_moneyness(row: pd.Series) -> str:
        side = str(row.get("side", ""))
        strike = row.get("strike")
        spot = row.get("underlying_spot")
        if pd.isna(strike) or pd.isna(spot):
            return "UNKNOWN"
        if abs(strike - spot) <= 50:
            return "ATM"
        if side == "CALL":
            return "ITM" if strike < spot else "OTM"
        if side == "PUT":
            return "ITM" if strike > spot else "OTM"
        return "UNKNOWN"

    trades["moneyness_class"] = trades.apply(_classify_moneyness, axis=1)
    trades["atm_distance_bucket"] = pd.cut(
        trades["atm_distance_points"],
        bins=[-1, 50, 150, 250, 500, 1000, np.inf],
        labels=["ATM", "100", "200", "300-500", "600-1000", "1000+"],
    )
    trades["premium_confirm_5s"] = trades["runup_5s"] >= 0.5
    trades["premium_confirm_10s"] = trades["runup_10s"] >= 1.0
    trades["premium_stall_10s"] = trades["runup_10s"] < 0.5
    trades["adverse_5s_ge_2"] = trades["drawdown_5s"] <= -2.0
    trades["adverse_10s_ge_3"] = trades["drawdown_10s"] <= -3.0
    trades["large_loss"] = trades["net_pnl_effective"] <= LARGE_LOSS_THRESHOLD

    return trades, marks_enriched


def _summary_stats(df: pd.DataFrame) -> dict[str, float]:
    if df.empty:
        return {
            "trades": 0,
            "win_rate": np.nan,
            "avg_pnl": np.nan,
            "median_pnl": np.nan,
            "max_loss": np.nan,
            "avg_holding_seconds": np.nan,
            "expectancy": np.nan,
            "net_pnl": 0.0,
        }
    pnl = df["net_pnl_effective"]
    return {
        "trades": int(len(df)),
        "win_rate": float((pnl > 0).mean()),
        "avg_pnl": float(pnl.mean()),
        "median_pnl": float(pnl.median()),
        "max_loss": float(pnl.min()),
        "avg_holding_seconds": float(df["holding_seconds"].mean()),
        "expectancy": float(pnl.mean()),
        "net_pnl": float(pnl.sum()),
    }


def hypothesis_tests(trades: pd.DataFrame) -> pd.DataFrame:
    closed = trades[trades["status"] == "CLOSED"].copy()
    rows: list[dict[str, object]] = []

    if closed.empty:
        return pd.DataFrame()

    # H1
    target_rate = closed["target_hit"].mean()
    rows.append(
        {
            "hypothesis_id": "H1",
            "statement": "5-point trigger often yields +3 premium follow-through.",
            "test_definition": "Target-hit rate across all closed trades.",
            "sample_size": int(len(closed)),
            "metric_1": float(target_rate),
            "metric_2": float(closed["net_pnl_effective"].mean()),
            "support_level": "suggestive" if target_rate >= 0.7 else "weak",
            "notes": "High hit-rate can coexist with negative expectancy if loser tails are large.",
        }
    )

    # H2
    delay_bins = pd.cut(
        closed["entry_delay_seconds"],
        bins=[-np.inf, 10, 20, 40, np.inf],
        labels=["<=10s", "10-20s", "20-40s", ">40s"],
    )
    h2 = (
        closed.assign(delay_bin=delay_bins)
        .groupby("delay_bin", dropna=False)
        .agg(trades=("trade_id", "count"), win_rate=("net_pnl_effective", lambda s: (s > 0).mean()), avg_pnl=("net_pnl_effective", "mean"))
        .reset_index()
    )
    corr_delay = (
        closed["entry_delay_seconds"].rank(method="average").corr(
            closed["net_pnl_effective"].rank(method="average")
        )
    )
    rows.append(
        {
            "hypothesis_id": "H2",
            "statement": "Fast trigger moves perform better than slow trigger moves.",
            "test_definition": "Entry delay from source candle start vs outcomes.",
            "sample_size": int(len(closed)),
            "metric_1": float(corr_delay) if pd.notna(corr_delay) else np.nan,
            "metric_2": float(h2[h2["delay_bin"] == ">40s"]["avg_pnl"].iloc[0]) if (h2["delay_bin"] == ">40s").any() else np.nan,
            "support_level": "suggestive" if pd.notna(corr_delay) and corr_delay < -0.15 else "inconclusive",
            "notes": "Negative Spearman correlation suggests slower setups underperform.",
        }
    )

    # H3
    conf = closed.groupby("premium_confirm_10s").agg(
        trades=("trade_id", "count"),
        win_rate=("net_pnl_effective", lambda s: (s > 0).mean()),
        avg_pnl=("net_pnl_effective", "mean"),
    )
    if True in conf.index and False in conf.index:
        delta = conf.loc[True, "avg_pnl"] - conf.loc[False, "avg_pnl"]
    else:
        delta = np.nan
    rows.append(
        {
            "hypothesis_id": "H3",
            "statement": "Premium confirmation soon after entry improves outcomes.",
            "test_definition": "runup_10s >= 1.0 vs < 1.0.",
            "sample_size": int(len(closed)),
            "metric_1": float(delta) if pd.notna(delta) else np.nan,
            "metric_2": float(conf.loc[True, "win_rate"]) if True in conf.index else np.nan,
            "support_level": "suggestive" if pd.notna(delta) and delta > 0 else "weak",
            "notes": "Confirmation uses post-entry premium behavior as proxy.",
        }
    )

    # H4
    late = closed["entry_hour"] >= 13
    late_avg = closed.loc[late, "net_pnl_effective"].mean() if late.any() else np.nan
    early_avg = closed.loc[~late, "net_pnl_effective"].mean() if (~late).any() else np.nan
    rows.append(
        {
            "hypothesis_id": "H4",
            "statement": "Later-day trades underperform.",
            "test_definition": "Compare before 13:00 vs >=13:00 PnL.",
            "sample_size": int(len(closed)),
            "metric_1": float(early_avg) if pd.notna(early_avg) else np.nan,
            "metric_2": float(late_avg) if pd.notna(late_avg) else np.nan,
            "support_level": "suggestive" if pd.notna(early_avg) and pd.notna(late_avg) and late_avg < early_avg else "inconclusive",
            "notes": "Post-1PM time-stop losses can materially impact late session expectancy.",
        }
    )

    # H5
    stall = closed["premium_stall_10s"]
    stall_avg = closed.loc[stall, "net_pnl_effective"].mean() if stall.any() else np.nan
    flow_avg = closed.loc[~stall, "net_pnl_effective"].mean() if (~stall).any() else np.nan
    rows.append(
        {
            "hypothesis_id": "H5",
            "statement": "If premium does not move quickly, trade quality is poor.",
            "test_definition": "runup_10s < 0.5 vs >= 0.5.",
            "sample_size": int(len(closed)),
            "metric_1": float(stall_avg) if pd.notna(stall_avg) else np.nan,
            "metric_2": float(flow_avg) if pd.notna(flow_avg) else np.nan,
            "support_level": "suggestive" if pd.notna(stall_avg) and pd.notna(flow_avg) and stall_avg < flow_avg else "inconclusive",
            "notes": "Useful kill-switch signal if this gap is stable over more days.",
        }
    )

    # H6 (spot fallback unavailable directly)
    rows.append(
        {
            "hypothesis_id": "H6",
            "statement": "Spot fallback toward trigger invalidates continuation.",
            "test_definition": "Spot post-entry path not logged; proxy with option drawdown_10s <= -2.",
            "sample_size": int(closed["drawdown_10s"].notna().sum()),
            "metric_1": float(closed.loc[closed["drawdown_10s"] <= -2, "net_pnl_effective"].mean())
            if (closed["drawdown_10s"] <= -2).any()
            else np.nan,
            "metric_2": float(closed.loc[closed["drawdown_10s"] > -2, "net_pnl_effective"].mean())
            if (closed["drawdown_10s"] > -2).any()
            else np.nan,
            "support_level": "proxy_only",
            "notes": "Requires spot tick logging around trigger/entry to test directly.",
        }
    )

    # H7
    m_grp = (
        closed.groupby("moneyness_class")
        .agg(trades=("trade_id", "count"), avg_pnl=("net_pnl_effective", "mean"), win_rate=("net_pnl_effective", lambda s: (s > 0).mean()))
        .reset_index()
    )
    rows.append(
        {
            "hypothesis_id": "H7",
            "statement": "Moneyness influences premium response quality.",
            "test_definition": "Compare ITM/ATM/OTM groups at entry.",
            "sample_size": int(len(closed)),
            "metric_1": float(m_grp["avg_pnl"].max()) if not m_grp.empty else np.nan,
            "metric_2": float(m_grp["avg_pnl"].min()) if not m_grp.empty else np.nan,
            "support_level": "suggestive" if len(m_grp) >= 2 else "inconclusive",
            "notes": "Interpret cautiously if one class dominates sample.",
        }
    )

    # H8
    vol_proxy = closed["price_range_30s"]
    median_vol = vol_proxy.median()
    hi = closed[vol_proxy >= median_vol]
    lo = closed[vol_proxy < median_vol]
    rows.append(
        {
            "hypothesis_id": "H8",
            "statement": "Regime/candle context affects outcomes.",
            "test_definition": "Proxy regime by first-30s premium range (high vs low).",
            "sample_size": int(vol_proxy.notna().sum()),
            "metric_1": float(hi["net_pnl_effective"].mean()) if not hi.empty else np.nan,
            "metric_2": float(lo["net_pnl_effective"].mean()) if not lo.empty else np.nan,
            "support_level": "inconclusive",
            "notes": "True candle/volatility context requires underlying tick/candle logs.",
        }
    )

    # H9
    adv = closed["adverse_5s_ge_2"]
    rows.append(
        {
            "hypothesis_id": "H9",
            "statement": "Immediate adverse move predicts weak expectancy.",
            "test_definition": "drawdown_5s <= -2 vs better first-5s profile.",
            "sample_size": int(len(closed)),
            "metric_1": float(closed.loc[adv, "net_pnl_effective"].mean()) if adv.any() else np.nan,
            "metric_2": float(closed.loc[~adv, "net_pnl_effective"].mean()) if (~adv).any() else np.nan,
            "support_level": "suggestive" if adv.any() and (~adv).any() else "inconclusive",
            "notes": "Strong candidate for quick invalidation if stable over more sessions.",
        }
    )

    # H10
    known = closed[closed["signal_family"].isin(["CONTINUATION", "REVERSAL"])]
    if not known.empty:
        fam = known.groupby("signal_family").agg(
            trades=("trade_id", "count"),
            avg_pnl=("net_pnl_effective", "mean"),
            win_rate=("net_pnl_effective", lambda s: (s > 0).mean()),
            avg_dd=("max_dd", "mean"),
        )
        rows.append(
            {
                "hypothesis_id": "H10",
                "statement": "Continuation and reversal setups behave differently.",
                "test_definition": "Compare known signal families.",
                "sample_size": int(len(known)),
                "metric_1": float(fam.loc["CONTINUATION", "avg_pnl"]) if "CONTINUATION" in fam.index else np.nan,
                "metric_2": float(fam.loc["REVERSAL", "avg_pnl"]) if "REVERSAL" in fam.index else np.nan,
                "support_level": "suggestive" if len(fam.index) >= 2 else "inconclusive",
                "notes": "Only evaluated where signal_kind exists.",
            }
        )
    else:
        rows.append(
            {
                "hypothesis_id": "H10",
                "statement": "Continuation and reversal setups behave differently.",
                "test_definition": "signal_kind missing for this sample.",
                "sample_size": 0,
                "metric_1": np.nan,
                "metric_2": np.nan,
                "support_level": "unavailable",
                "notes": "Requires signal_kind logging.",
            }
        )

    return pd.DataFrame(rows)


def _mark_at_or_after(g: pd.DataFrame, second: float) -> pd.Series | None:
    hit = g[g["seconds_since_entry"] >= second]
    if hit.empty:
        return None
    return hit.iloc[0]


def _rule_early_failure_event(row: pd.Series, _: pd.DataFrame) -> tuple[pd.Timestamp, float] | None:
    t = row.get("early_failure_mark_time")
    p = row.get("early_failure_price")
    if pd.isna(t) or pd.isna(p):
        return None
    return pd.Timestamp(t), float(p)


def _rule_no_progress(second: float, min_mfe: float) -> Callable[[pd.Series, pd.DataFrame], tuple[pd.Timestamp, float] | None]:
    def _inner(_: pd.Series, marks: pd.DataFrame) -> tuple[pd.Timestamp, float] | None:
        mark = _mark_at_or_after(marks, second)
        if mark is None:
            return None
        if float(mark["cum_mfe"]) < min_mfe:
            return pd.Timestamp(mark["mark_time"]), float(mark["ltp"])
        return None

    return _inner


def _rule_no_progress_and_below_entry(second: float, min_mfe: float) -> Callable[[pd.Series, pd.DataFrame], tuple[pd.Timestamp, float] | None]:
    def _inner(row: pd.Series, marks: pd.DataFrame) -> tuple[pd.Timestamp, float] | None:
        mark = _mark_at_or_after(marks, second)
        if mark is None:
            return None
        if float(mark["cum_mfe"]) < min_mfe and float(mark["ltp"]) <= float(row["entry_price"]):
            return pd.Timestamp(mark["mark_time"]), float(mark["ltp"])
        return None

    return _inner


def _rule_adverse_breach(within_seconds: float, adverse_points: float) -> Callable[[pd.Series, pd.DataFrame], tuple[pd.Timestamp, float] | None]:
    def _inner(_: pd.Series, marks: pd.DataFrame) -> tuple[pd.Timestamp, float] | None:
        hit = marks[(marks["seconds_since_entry"] <= within_seconds) & (marks["pnl_delta"] <= -adverse_points)]
        if hit.empty:
            return None
        first = hit.iloc[0]
        return pd.Timestamp(first["mark_time"]), float(first["ltp"])

    return _inner


def _rule_global_time_stop(seconds: float) -> Callable[[pd.Series, pd.DataFrame], tuple[pd.Timestamp, float] | None]:
    def _inner(_: pd.Series, marks: pd.DataFrame) -> tuple[pd.Timestamp, float] | None:
        mark = _mark_at_or_after(marks, seconds)
        if mark is None:
            return None
        return pd.Timestamp(mark["mark_time"]), float(mark["ltp"])

    return _inner


def build_early_exit_rules() -> list[EarlyExitRule]:
    return [
        EarlyExitRule("EXIT_ON_EARLY_FAILURE_EVENT", "Exit when EARLY_FAILURE_SIGNAL is logged.", _rule_early_failure_event),
        EarlyExitRule("EXIT_IF_NO_PROGRESS_10S_MFE_LT_0_5", "At 10s, if MFE < 0.5 then exit.", _rule_no_progress(10, 0.5)),
        EarlyExitRule("EXIT_IF_NO_PROGRESS_15S_MFE_LT_1_0", "At 15s, if MFE < 1.0 then exit.", _rule_no_progress(15, 1.0)),
        EarlyExitRule("EXIT_IF_NO_PROGRESS_20S_MFE_LT_1_5", "At 20s, if MFE < 1.5 then exit.", _rule_no_progress(20, 1.5)),
        EarlyExitRule(
            "EXIT_IF_STAGNANT_AND_BELOW_ENTRY_10S",
            "At 10s, if MFE < 0.5 and still below entry, exit.",
            _rule_no_progress_and_below_entry(10, 0.5),
        ),
        EarlyExitRule("EXIT_IF_ADVERSE_2PTS_WITHIN_5S", "Exit on -2 points adverse move within 5s.", _rule_adverse_breach(5, 2.0)),
        EarlyExitRule("EXIT_IF_ADVERSE_3PTS_WITHIN_10S", "Exit on -3 points adverse move within 10s.", _rule_adverse_breach(10, 3.0)),
        EarlyExitRule("EXIT_IF_ADVERSE_5PTS_WITHIN_15S", "Exit on -5 points adverse move within 15s.", _rule_adverse_breach(15, 5.0)),
        EarlyExitRule("EXIT_WITH_GLOBAL_90S_TIME_STOP", "Exit at first mark after 90s if still open.", _rule_global_time_stop(90)),
        EarlyExitRule("EXIT_WITH_GLOBAL_180S_TIME_STOP", "Exit at first mark after 180s if still open.", _rule_global_time_stop(180)),
    ]


def simulate_early_exit_rules(
    trades: pd.DataFrame, marks: pd.DataFrame, rules: list[EarlyExitRule]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    closed = trades[trades["status"] == "CLOSED"].copy()
    mark_map = {tid: grp.sort_values("mark_time") for tid, grp in marks.groupby("trade_id")}
    baseline_total = float(closed["net_pnl_effective"].sum())
    per_trade_records: list[dict[str, object]] = []
    summary_records: list[dict[str, object]] = []

    for rule in rules:
        sims: list[dict[str, object]] = []
        for _, row in closed.iterrows():
            tid = row["trade_id"]
            g = mark_map.get(tid)
            if g is None or g.empty:
                trigger = None
            else:
                trigger = rule.evaluator(row, g)

            baseline_exit_time = pd.Timestamp(row["effective_exit_time"])
            baseline_exit_price = float(row["effective_exit_price"])
            simulated_exit_time = baseline_exit_time
            simulated_exit_price = baseline_exit_price
            modified = False
            simulated_reason = row["exit_reason"]

            if trigger is not None:
                trigger_time, trigger_price = trigger
                if pd.notna(trigger_time) and trigger_time < baseline_exit_time:
                    simulated_exit_time = trigger_time
                    simulated_exit_price = float(trigger_price)
                    modified = True
                    simulated_reason = rule.rule_id

            simulated_points = simulated_exit_price - float(row["entry_price"])
            simulated_pnl = simulated_points * float(row["quantity"])
            baseline_pnl = float(row["net_pnl_effective"])
            pnl_delta = simulated_pnl - baseline_pnl
            improved_large_loser = (
                (baseline_pnl <= LARGE_LOSS_THRESHOLD) and (simulated_pnl > baseline_pnl)
            )
            winner_killed = (baseline_pnl > 0) and modified and (simulated_pnl < baseline_pnl)
            winner_flipped = (baseline_pnl > 0) and modified and (simulated_pnl <= 0)

            sims.append(
                {
                    "rule_id": rule.rule_id,
                    "trade_id": tid,
                    "entry_time": row["entry_time"],
                    "signal_kind": row["signal_kind"],
                    "baseline_exit_reason": row["exit_reason"],
                    "simulated_exit_reason": simulated_reason,
                    "baseline_exit_time": baseline_exit_time,
                    "simulated_exit_time": simulated_exit_time,
                    "baseline_pnl": baseline_pnl,
                    "simulated_pnl": simulated_pnl,
                    "pnl_delta": pnl_delta,
                    "modified": modified,
                    "baseline_holding_seconds": float(row["holding_seconds"]),
                    "simulated_holding_seconds": (
                        simulated_exit_time - pd.Timestamp(row["entry_time"])
                    ).total_seconds(),
                    "improved_large_loser": improved_large_loser,
                    "winner_prematurely_killed": winner_killed,
                    "winner_flipped_to_loss": winner_flipped,
                }
            )

        sim_df = pd.DataFrame(sims)
        per_trade_records.extend(sim_df.to_dict("records"))
        stats = _summary_stats(
            sim_df.rename(
                columns={
                    "simulated_pnl": "net_pnl_effective",
                    "simulated_holding_seconds": "holding_seconds",
                }
            )
        )
        summary_records.append(
            {
                "rule_id": rule.rule_id,
                "rule_type": "early_exit",
                "description": rule.description,
                "trades_total": int(len(sim_df)),
                "trades_modified": int(sim_df["modified"].sum()),
                "trades_filtered_out": 0,
                "win_rate": stats["win_rate"],
                "avg_pnl": stats["avg_pnl"],
                "median_pnl": stats["median_pnl"],
                "max_loss": stats["max_loss"],
                "avg_holding_seconds": stats["avg_holding_seconds"],
                "expectancy": stats["expectancy"],
                "net_pnl": stats["net_pnl"],
                "net_pnl_change_vs_baseline": stats["net_pnl"] - baseline_total,
                "large_losers_avoided": int(sim_df["improved_large_loser"].sum()),
                "winners_prematurely_killed": int(sim_df["winner_prematurely_killed"].sum()),
                "winners_flipped_to_loss": int(sim_df["winner_flipped_to_loss"].sum()),
            }
        )

    return pd.DataFrame(summary_records), pd.DataFrame(per_trade_records)


def build_entry_filter_rules() -> list[EntryFilterRule]:
    return [
        EntryFilterRule(
            "FILTER_KEEP_BEFORE_1300",
            "Only take entries before 13:00.",
            lambda df: df["entry_time"].dt.hour < 13,
        ),
        EntryFilterRule(
            "FILTER_KEEP_BEFORE_1330",
            "Only take entries before 13:30.",
            lambda df: (df["entry_time"].dt.hour < 13)
            | ((df["entry_time"].dt.hour == 13) & (df["entry_time"].dt.minute < 30)),
        ),
        EntryFilterRule(
            "FILTER_KEEP_BEFORE_1400",
            "Only take entries before 14:00.",
            lambda df: df["entry_time"].dt.hour < 14,
        ),
        EntryFilterRule(
            "FILTER_ENTRY_DELAY_LE_30S",
            "Skip entries triggered later than 30s into the source candle.",
            lambda df: df["entry_delay_seconds"] <= 30,
        ),
        EntryFilterRule(
            "FILTER_ENTRY_DELAY_LE_40S",
            "Skip entries triggered later than 40s into the source candle.",
            lambda df: df["entry_delay_seconds"] <= 40,
        ),
        EntryFilterRule(
            "FILTER_REQUIRE_SIGNAL_KIND_KNOWN",
            "Require signal_kind to be logged.",
            lambda df: df["signal_family"] != "UNKNOWN",
        ),
        EntryFilterRule(
            "FILTER_CONTINUATION_ONLY_WHEN_KNOWN",
            "When signal_kind is known, take only continuation setups.",
            lambda df: (df["signal_family"] == "UNKNOWN") | (df["signal_family"] == "CONTINUATION"),
        ),
        EntryFilterRule(
            "FILTER_REVERSAL_ONLY_WHEN_KNOWN",
            "When signal_kind is known, take only reversal setups.",
            lambda df: (df["signal_family"] == "UNKNOWN") | (df["signal_family"] == "REVERSAL"),
        ),
    ]


def evaluate_entry_filters(trades: pd.DataFrame, rules: list[EntryFilterRule]) -> tuple[pd.DataFrame, pd.DataFrame]:
    closed = trades[trades["status"] == "CLOSED"].copy()
    baseline_total = float(closed["net_pnl_effective"].sum())
    summary_records: list[dict[str, object]] = []
    per_trade_records: list[dict[str, object]] = []

    for rule in rules:
        keep = rule.keep_mask_builder(closed).fillna(False)
        kept = closed[keep].copy()
        filtered = closed[~keep].copy()
        stats = _summary_stats(kept)
        summary_records.append(
            {
                "rule_id": rule.rule_id,
                "rule_type": "entry_filter",
                "description": rule.description,
                "trades_total": int(len(closed)),
                "trades_modified": int((~keep).sum()),
                "trades_filtered_out": int((~keep).sum()),
                "win_rate": stats["win_rate"],
                "avg_pnl": stats["avg_pnl"],
                "median_pnl": stats["median_pnl"],
                "max_loss": stats["max_loss"],
                "avg_holding_seconds": stats["avg_holding_seconds"],
                "expectancy": stats["expectancy"],
                "net_pnl": stats["net_pnl"],
                "net_pnl_change_vs_baseline": stats["net_pnl"] - baseline_total,
                "large_losers_avoided": int((filtered["net_pnl_effective"] <= LARGE_LOSS_THRESHOLD).sum()),
                "winners_prematurely_killed": int((filtered["net_pnl_effective"] > 0).sum()),
                "winners_flipped_to_loss": np.nan,
            }
        )
        for _, row in closed.iterrows():
            per_trade_records.append(
                {
                    "rule_id": rule.rule_id,
                    "trade_id": row["trade_id"],
                    "entry_time": row["entry_time"],
                    "signal_kind": row["signal_kind"],
                    "baseline_pnl": row["net_pnl_effective"],
                    "kept": bool(keep.loc[row.name]),
                }
            )

    return pd.DataFrame(summary_records), pd.DataFrame(per_trade_records)


def inventory_summary(events: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    inv = []
    for source_file, sdf in events.groupby("source_file"):
        days = sorted(sdf["event_date"].dropna().astype(str).unique().tolist())
        inv.append(
            {
                "source_file": source_file,
                "records": int(len(sdf)),
                "date_start": days[0] if days else "",
                "date_end": days[-1] if days else "",
                "dates": ",".join(days),
                "trade_entries": int((sdf["event_type"] == "TRADE_ENTERED").sum()),
                "open_marks": int((sdf["event_type"] == "OPEN_POSITION_MARK").sum()),
                "trade_exits": int((sdf["event_type"] == "TRADE_EXITED").sum()),
                "early_failure_events": int((sdf["event_type"] == "EARLY_FAILURE_SIGNAL").sum()),
            }
        )
    inv_df = pd.DataFrame(inv).sort_values("source_file")
    inv_df["usable_for_trade_lifecycle"] = "yes"
    inv_df["usable_for_spot_tick_replay"] = "no"
    inv_df["usable_for_option_tick_replay"] = "partial_from_marks_only"
    return inv_df


def _df_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if isinstance(v, float):
                if np.isnan(v):
                    vals.append("")
                else:
                    vals.append(f"{v:.6g}")
            else:
                vals.append(str(v))
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + body)


def write_report(
    report_path: Path,
    inventory_df: pd.DataFrame,
    trades: pd.DataFrame,
    hypothesis_df: pd.DataFrame,
    rule_df: pd.DataFrame,
) -> None:
    closed = trades[trades["status"] == "CLOSED"].copy()
    overall = _summary_stats(closed)
    top_rules = rule_df.sort_values("net_pnl_change_vs_baseline", ascending=False).head(8)
    top_loss_reduction = rule_df.sort_values(
        ["large_losers_avoided", "net_pnl_change_vs_baseline"], ascending=[False, False]
    ).head(8)
    by_hour = (
        closed.groupby("entry_hour")
        .agg(
            trades=("trade_id", "count"),
            win_rate=("net_pnl_effective", lambda s: (s > 0).mean()),
            avg_pnl=("net_pnl_effective", "mean"),
            net_pnl=("net_pnl_effective", "sum"),
            avg_dd=("max_dd", "mean"),
            early_rate=("early_failure_logged", "mean"),
        )
        .reset_index()
        .sort_values("entry_hour")
    )

    lines: list[str] = []
    lines.append("# Hypothesis Test Report")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Objective: empirically validate the strategy hypothesis and test candidate invalidation/kill-switch rules using repository journal data.")
    lines.append("- Data period detected from logs: "
                 f"{trades['entry_date'].min()} to {trades['entry_date'].max()}.")
    lines.append(f"- Closed trades analyzed: {len(closed)}")
    lines.append("")
    lines.append("## Data Sources Used")
    lines.append(_df_to_markdown(inventory_df))
    lines.append("")
    lines.append("## Reconstructed Trade Fields")
    lines.append("- Core lifecycle: signal trigger context, entry, target placement, open marks, exit.")
    lines.append("- Derived fields: holding time, realized points/PnL, max drawdown (MAE), max run-up (MFE), first move direction, early-window response, entry delay from source candle start, moneyness class.")
    lines.append("- Missing for direct hypothesis tests: underlying spot tick path after entry, previous-candle OHLC snapshots at signal time, IV/spread/greeks, option LTP at signal trigger (pre-entry).")
    lines.append("")
    lines.append("## Baseline Strategy Snapshot")
    lines.append(
        f"- Win rate: {overall['win_rate']:.2%}, avg PnL/trade: {overall['avg_pnl']:.2f}, "
        f"median PnL/trade: {overall['median_pnl']:.2f}, max loss: {overall['max_loss']:.2f}, "
        f"net PnL: {overall['net_pnl']:.2f}"
    )
    lines.append(
        f"- Avg holding time: {overall['avg_holding_seconds']:.2f}s, "
        f"early-failure logged trades: {int(closed['early_failure_logged'].sum())}/{len(closed)}"
    )
    lines.append("")
    lines.append("## Per-Hypothesis Findings (H1-H10)")
    if hypothesis_df.empty:
        lines.append("_No hypothesis rows generated._")
    else:
        lines.append(_df_to_markdown(hypothesis_df))
    lines.append("")
    lines.append("## Candidate Kill-Switch / Filter Rules")
    lines.append("Top rules by net PnL change vs baseline:")
    lines.append(_df_to_markdown(top_rules))
    lines.append("")
    lines.append("Top rules by large-loser avoidance:")
    lines.append(_df_to_markdown(top_loss_reduction))
    lines.append("")
    lines.append("## Time-of-Day Behavior")
    lines.append(_df_to_markdown(by_hour))
    lines.append("")
    lines.append("## What The Data Supports vs Suggests")
    lines.append("- Supported descriptively: large adverse early moves and weak early premium response are associated with poorer expectancy.")
    lines.append("- Suggestive (not definitive): slower trigger timing and later-session entries tend to underperform in this sample.")
    lines.append("- Not directly testable with current logs: spot fallback-to-trigger and pre-entry spot velocity quality.")
    lines.append("- Reliability caveat: sample is only a few sessions; thresholds should be treated as candidate ranges, not fixed truths.")
    lines.append("")
    lines.append("## Candidate Operational Guardrails (Empirical, Not Final)")
    lines.append("- Early invalidation candidate: adverse premium breach within first 5-15s (e.g., -2 to -5 points) shows strong loser-avoidance potential.")
    lines.append("- Follow-through absence candidate: no meaningful MFE in first 10-20s is a useful kill-switch family to test.")
    lines.append("- Session control candidate: stricter entry windows in late day can reduce tail risk.")
    lines.append("")
    lines.append("## Lightweight Instrumentation Plan (Forward-Compatible)")
    lines.append("Add these journal events/fields to improve hypothesis fidelity:")
    lines.append("1. `SIGNAL_GENERATED` event in engine right after strategy signal: `signal_time`, `signal_kind`, `side`, `source_candle_start`, `previous_candle_open`, `previous_candle_close`, `trigger_price`, `spot_ltp_at_signal`.")
    lines.append("2. `ENTRY_CONTEXT` event just before broker entry: `option_ltp_pre_entry`, `spot_ltp_pre_entry`, `entry_delay_seconds`, `selector_offset_points`, `atm_strike`, `moneyness_class`.")
    lines.append("3. `EARLY_SNAPSHOT` events at +5s/+10s/+15s/+20s: `spot_ltp`, `option_ltp`, `pnl_delta`, `cum_mfe`, `cum_mae`, `spread_if_available`.")
    lines.append("4. `RULE_TRIGGERED` event for any future kill-switch: `rule_id`, `trigger_time`, `trigger_price`, `reason_metrics`.")
    lines.append("5. Optional per-trade summary event at close: `max_mfe`, `max_mae`, `time_to_mfe_1`, `time_to_target`, `max_spot_fallback_from_trigger`.")
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("- Script: `analysis/hypothesis_killswitch_analysis.py`")
    lines.append("- Run command from repo root: `.venv/bin/python analysis/hypothesis_killswitch_analysis.py`")
    lines.append("- Outputs directory: `analysis/output/`")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events(LOG_FILES)
    trades, marks = build_trade_dataset(events)

    inventory_df = inventory_summary(events, trades)
    hypothesis_df = hypothesis_tests(trades)

    early_exit_rules = build_early_exit_rules()
    early_summary_df, early_per_trade_df = simulate_early_exit_rules(trades, marks, early_exit_rules)

    entry_filter_rules = build_entry_filter_rules()
    filter_summary_df, filter_per_trade_df = evaluate_entry_filters(trades, entry_filter_rules)

    rule_comparison_df = (
        pd.concat([early_summary_df, filter_summary_df], ignore_index=True)
        .sort_values("net_pnl_change_vs_baseline", ascending=False)
        .reset_index(drop=True)
    )

    by_hour = (
        trades[trades["status"] == "CLOSED"]
        .groupby("entry_hour")
        .agg(
            trades=("trade_id", "count"),
            win_rate=("net_pnl_effective", lambda s: (s > 0).mean()),
            avg_pnl=("net_pnl_effective", "mean"),
            median_pnl=("net_pnl_effective", "median"),
            net_pnl=("net_pnl_effective", "sum"),
            avg_holding_seconds=("holding_seconds", "mean"),
            avg_max_drawdown=("max_dd", "mean"),
            avg_max_runup=("max_runup", "mean"),
            early_failure_rate=("early_failure_logged", "mean"),
        )
        .reset_index()
    )

    signal_summary = (
        trades[trades["status"] == "CLOSED"]
        .groupby(["signal_family", "signal_kind"], dropna=False)
        .agg(
            trades=("trade_id", "count"),
            win_rate=("net_pnl_effective", lambda s: (s > 0).mean()),
            avg_pnl=("net_pnl_effective", "mean"),
            median_pnl=("net_pnl_effective", "median"),
            net_pnl=("net_pnl_effective", "sum"),
            avg_holding_seconds=("holding_seconds", "mean"),
            avg_max_drawdown=("max_dd", "mean"),
            avg_max_runup=("max_runup", "mean"),
            early_failure_rate=("early_failure_logged", "mean"),
        )
        .reset_index()
    )

    day_summary = (
        trades[trades["status"] == "CLOSED"]
        .groupby("entry_date")
        .agg(
            trades=("trade_id", "count"),
            win_rate=("net_pnl_effective", lambda s: (s > 0).mean()),
            avg_pnl=("net_pnl_effective", "mean"),
            net_pnl=("net_pnl_effective", "sum"),
            median_holding_seconds=("holding_seconds", "median"),
            avg_max_drawdown=("max_dd", "mean"),
            early_failure_rate=("early_failure_logged", "mean"),
        )
        .reset_index()
    )

    inventory_df.to_csv(OUTPUT_DIR / "data_inventory.csv", index=False)
    events.to_csv(OUTPUT_DIR / "events_normalized.csv", index=False)
    trades.sort_values("entry_time").to_csv(OUTPUT_DIR / "enriched_trades.csv", index=False)
    marks.sort_values(["trade_id", "mark_time"]).to_csv(OUTPUT_DIR / "enriched_marks.csv", index=False)
    hypothesis_df.to_csv(OUTPUT_DIR / "hypothesis_tests.csv", index=False)
    rule_comparison_df.to_csv(OUTPUT_DIR / "killswitch_rule_comparison.csv", index=False)
    early_per_trade_df.to_csv(OUTPUT_DIR / "killswitch_rule_trade_outcomes.csv", index=False)
    filter_per_trade_df.to_csv(OUTPUT_DIR / "entry_filter_trade_outcomes.csv", index=False)
    by_hour.to_csv(OUTPUT_DIR / "time_of_day_summary.csv", index=False)
    signal_summary.to_csv(OUTPUT_DIR / "signal_summary.csv", index=False)
    day_summary.to_csv(OUTPUT_DIR / "day_summary.csv", index=False)

    write_report(REPORT_PATH, inventory_df, trades, hypothesis_df, rule_comparison_df)

    print("Analysis complete.")
    print(f"Report: {REPORT_PATH}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
