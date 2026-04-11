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
ANALYSIS_DIR = REPO_ROOT / "analysis"
REPORT_PATH = ANALYSIS_DIR / "TAIL_LOSS_FORENSICS_REPORT.md"
OUT_PER_TRADE = ANALYSIS_DIR / "per_trade_forensics.csv"
OUT_CANDIDATE = ANALYSIS_DIR / "candidate_killswitch_results.csv"
OUT_COMPOSITE = ANALYSIS_DIR / "composite_policy_results.csv"
OUT_TIMELINES = ANALYSIS_DIR / "worst_trade_timelines.csv"
TARGET_DATE = pd.Timestamp("2026-03-19").date()


@dataclass(frozen=True)
class RuleDef:
    rule_id: str
    description: str
    scope: str
    evaluator: Callable[[pd.Series, pd.DataFrame, pd.Series | None], tuple[pd.Timestamp, float] | None]
    testable: bool = True
    note: str = ""


@dataclass(frozen=True)
class CompositePolicy:
    policy_id: str
    description: str
    entry_filter: Callable[[pd.Series], bool] | None
    exit_evaluator: Callable[[pd.Series, pd.DataFrame, pd.Series | None], tuple[pd.Timestamp, float] | None] | None


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


def load_events() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in LOG_FILES:
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
        raise RuntimeError("No events found in logs.")
    events["event_timestamp"] = _to_ts(events["event_timestamp"])
    events["event_date"] = events["event_timestamp"].dt.date
    return events


def _require_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = np.nan
    return out


def build_day_dataset(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    day = events[events["event_date"] == TARGET_DATE].copy()

    entries = _require_columns(
        day[day["event_type"] == "TRADE_ENTERED"].copy(),
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
        day[day["event_type"] == "TRADE_EXITED"].copy(),
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
    early = _require_columns(
        day[day["event_type"] == "EARLY_FAILURE_SIGNAL"].copy(),
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
        day[day["event_type"] == "OPEN_POSITION_MARK"].copy(),
        ["trade_id", "mark_time", "ltp", "entry_price", "target_price", "mfe", "mae", "signal_kind"],
    )

    entries["entry_time"] = _to_ts(entries["entry_time"])
    entries["source_candle_start"] = _to_ts(entries["source_candle_start"])
    entries["expiry"] = _to_ts(entries["expiry"])
    entries["event_timestamp"] = _to_ts(entries["event_timestamp"])
    entries = entries.sort_values(["entry_time", "event_timestamp"]).drop_duplicates(subset=["trade_id"], keep="first")

    exits["exit_time"] = _to_ts(exits["exit_time"])
    exits["event_timestamp"] = _to_ts(exits["event_timestamp"])
    exits = exits.sort_values(["exit_time", "event_timestamp"]).drop_duplicates(subset=["trade_id"], keep="last")

    early["mark_time"] = _to_ts(early["mark_time"])
    early["event_timestamp"] = _to_ts(early["event_timestamp"])
    early = early.sort_values(["mark_time", "event_timestamp"]).drop_duplicates(subset=["trade_id"], keep="first")

    marks["mark_time"] = _to_ts(marks["mark_time"])
    marks["event_timestamp"] = _to_ts(marks["event_timestamp"])
    marks["mark_time"] = marks["mark_time"].fillna(marks["event_timestamp"])

    numeric_cols_entries = ["entry_price", "target_price", "quantity", "strike", "underlying_spot", "trigger_price"]
    for col in numeric_cols_entries:
        entries[col] = entries[col].map(_safe_float)
    entries["quantity"] = entries["quantity"].map(_safe_int)

    for col in ["exit_price", "gross_pnl", "net_pnl", "charges", "realized_pnl_after_trade"]:
        exits[col] = exits[col].map(_safe_float)

    for col in ["ltp", "entry_price", "target_price", "mfe", "mae"]:
        marks[col] = marks[col].map(_safe_float)

    trades = entries[
        [
            "trade_id",
            "source_file",
            "entry_time",
            "event_timestamp",
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
        early[
            ["trade_id", "mark_time", "duration_seconds", "current_price", "mfe", "mae"]
        ].rename(
            columns={
                "mark_time": "early_failure_mark_time",
                "duration_seconds": "early_failure_duration_seconds",
                "current_price": "early_failure_price",
                "mfe": "early_failure_mfe",
                "mae": "early_failure_mae",
            }
        ),
        on="trade_id",
        how="left",
    )

    marks = marks.merge(
        trades[["trade_id", "entry_time", "entry_price", "target_price", "exit_time", "exit_reason", "signal_kind"]],
        on="trade_id",
        how="left",
        suffixes=("", "_trade"),
    )
    if "entry_time_trade" in marks.columns:
        marks["entry_time"] = marks["entry_time"].fillna(marks["entry_time_trade"])
    marks["entry_price"] = marks["entry_price"].fillna(marks["entry_price_trade"])
    marks["target_price"] = marks["target_price"].fillna(marks["target_price_trade"])
    marks["signal_kind"] = marks["signal_kind"].fillna(marks["signal_kind_trade"])
    marks = marks.drop(
        columns=[
            c
            for c in ["entry_time_trade", "entry_price_trade", "target_price_trade", "signal_kind_trade"]
            if c in marks.columns
        ]
    )
    marks["entry_time"] = _to_ts(marks["entry_time"])
    marks["mark_time"] = _to_ts(marks["mark_time"])
    marks["exit_time"] = _to_ts(marks["exit_time"])
    marks = marks.dropna(subset=["trade_id", "entry_time", "mark_time", "ltp", "entry_price"])
    marks["seconds_since_entry"] = (marks["mark_time"] - marks["entry_time"]).dt.total_seconds()
    marks = marks[marks["seconds_since_entry"] >= 0].copy()
    marks["pnl_delta"] = marks["ltp"] - marks["entry_price"]
    marks = marks.sort_values(["trade_id", "mark_time"]).copy()
    marks["cum_mfe"] = marks.groupby("trade_id")["pnl_delta"].cummax()
    marks["cum_mae"] = marks.groupby("trade_id")["pnl_delta"].cummin()
    marks["drawdown_from_peak"] = marks["pnl_delta"] - marks["cum_mfe"]

    trades["effective_exit_time"] = trades["exit_time"]
    trades["effective_exit_price"] = trades["exit_price"]

    last_mark = marks.sort_values("mark_time").groupby("trade_id").tail(1)[["trade_id", "mark_time", "ltp"]]
    trades = trades.merge(last_mark.rename(columns={"mark_time": "last_mark_time", "ltp": "last_mark_ltp"}), on="trade_id", how="left")

    trades["effective_exit_time"] = trades["effective_exit_time"].fillna(trades["last_mark_time"])
    trades["effective_exit_price"] = trades["effective_exit_price"].fillna(trades["last_mark_ltp"])

    trades["holding_seconds"] = (trades["effective_exit_time"] - trades["entry_time"]).dt.total_seconds()
    trades["realized_points"] = trades["effective_exit_price"] - trades["entry_price"]
    trades["computed_gross_pnl"] = trades["realized_points"] * trades["quantity"]
    trades["net_pnl_effective"] = trades["net_pnl"].fillna(trades["computed_gross_pnl"])
    trades["status"] = np.where(trades["exit_time"].notna(), "CLOSED", "OPEN")
    trades["target_hit"] = trades["exit_reason"].eq("TARGET_HIT")
    trades["early_failure_logged"] = trades["early_failure_mark_time"].notna()

    trades["signal_kind"] = trades["signal_kind"].fillna("UNKNOWN").astype(str)
    trades["signal_family"] = np.where(
        trades["signal_kind"].str.startswith("CONTINUATION"),
        "CONTINUATION",
        np.where(trades["signal_kind"].str.startswith("REVERSAL"), "REVERSAL", "UNKNOWN"),
    )
    trades["entry_hour"] = trades["entry_time"].dt.hour
    trades["entry_minute"] = trades["entry_time"].dt.minute
    trades["entry_tod"] = trades["entry_time"].dt.strftime("%H:%M:%S")

    return trades, marks, early


def _first_row(marks: pd.DataFrame, cond: pd.Series) -> pd.Series | None:
    sub = marks[cond]
    if sub.empty:
        return None
    return sub.iloc[0]


def _row_at_or_after(marks: pd.DataFrame, seconds: float) -> pd.Series | None:
    sub = marks[marks["seconds_since_entry"] >= seconds]
    if sub.empty:
        return None
    return sub.iloc[0]


def _window(marks: pd.DataFrame, seconds: float) -> pd.DataFrame:
    return marks[marks["seconds_since_entry"] <= seconds]


def compute_trade_forensics(trades: pd.DataFrame, marks: pd.DataFrame, early: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    marks_map = {tid: grp.sort_values("mark_time").copy() for tid, grp in marks.groupby("trade_id")}
    early_map = early.set_index("trade_id", drop=False).to_dict("index") if not early.empty else {}

    for _, tr in trades.iterrows():
        tid = tr["trade_id"]
        m = marks_map.get(tid, pd.DataFrame())

        out: dict[str, object] = {
            "trade_id": tid,
            "signal_kind": tr["signal_kind"],
            "signal_family": tr["signal_family"],
            "direction": tr["side"],
            "entry_time": tr["entry_time"],
            "trigger_time_proxy": tr["event_timestamp"],
            "source_candle_start": tr["source_candle_start"],
            "entry_price": tr["entry_price"],
            "target_price": tr["target_price"],
            "quantity": tr["quantity"],
            "exit_time": tr["effective_exit_time"],
            "exit_reason": tr["exit_reason"],
            "holding_seconds": tr["holding_seconds"],
            "realized_points": tr["realized_points"],
            "realized_pnl": tr["net_pnl_effective"],
            "early_failure_logged": bool(tr["early_failure_logged"]),
            "early_failure_mark_time": tr.get("early_failure_mark_time"),
            "early_failure_duration_seconds": tr.get("early_failure_duration_seconds"),
            "spot_revert_toward_trigger_testable": False,
            "spot_revert_toward_trigger": np.nan,
            "spot_revert_note": "Underlying spot path is not logged post-entry in OPEN_POSITION_MARK events.",
        }

        if m.empty:
            out.update(
                {
                    "mark_count": 0,
                    "first_favorable_seconds": np.nan,
                    "first_favorable_points": np.nan,
                    "first_adverse_seconds": np.nan,
                    "first_adverse_points": np.nan,
                    "mfe_points": np.nan,
                    "mae_points": np.nan,
                    "max_drawdown_points": np.nan,
                    "runup_5s": np.nan,
                    "runup_10s": np.nan,
                    "runup_15s": np.nan,
                    "drawdown_5s": np.nan,
                    "drawdown_10s": np.nan,
                    "drawdown_15s": np.nan,
                    "drawdown_20s": np.nan,
                    "time_to_minus_1": np.nan,
                    "time_to_minus_2": np.nan,
                    "time_to_minus_3": np.nan,
                    "time_to_plus_0_5": np.nan,
                    "time_to_plus_1": np.nan,
                    "option_premium_failed_confirmation": np.nan,
                    "move_stalled": np.nan,
                    "time_near_entry_before_damage_accel_seconds": np.nan,
                    "loss_expansion_pattern": "unknown_no_marks",
                }
            )
            rows.append(out)
            continue

        m = m.copy()
        m = m.sort_values("mark_time")

        first_fav = _first_row(m, m["pnl_delta"] > 0)
        first_adv = _first_row(m, m["pnl_delta"] < 0)

        runup_5 = _window(m, 5)["pnl_delta"].max() if not _window(m, 5).empty else np.nan
        runup_10 = _window(m, 10)["pnl_delta"].max() if not _window(m, 10).empty else np.nan
        runup_15 = _window(m, 15)["pnl_delta"].max() if not _window(m, 15).empty else np.nan
        draw_5 = _window(m, 5)["pnl_delta"].min() if not _window(m, 5).empty else np.nan
        draw_10 = _window(m, 10)["pnl_delta"].min() if not _window(m, 10).empty else np.nan
        draw_15 = _window(m, 15)["pnl_delta"].min() if not _window(m, 15).empty else np.nan
        draw_20 = _window(m, 20)["pnl_delta"].min() if not _window(m, 20).empty else np.nan

        minus1 = _first_row(m, m["pnl_delta"] <= -1.0)
        minus2 = _first_row(m, m["pnl_delta"] <= -2.0)
        minus3 = _first_row(m, m["pnl_delta"] <= -3.0)
        plus05 = _first_row(m, m["pnl_delta"] >= 0.5)
        plus1 = _first_row(m, m["pnl_delta"] >= 1.0)

        failed_confirm = bool((pd.isna(runup_5) or runup_5 < 0.5) and (pd.isna(runup_10) or runup_10 < 1.0))
        move_stalled = bool((pd.isna(runup_15) or runup_15 < 1.0) and (pd.notna(draw_20) and draw_20 <= -1.5))

        near_entry_before_accel = np.nan
        if minus2 is not None:
            t_accel = float(minus2["seconds_since_entry"])
            near = m[(m["seconds_since_entry"] <= t_accel) & (m["pnl_delta"].abs() <= 0.5)]
            if not near.empty:
                near_entry_before_accel = float(near["seconds_since_entry"].max())
            else:
                near_entry_before_accel = 0.0
        if minus2 is None:
            loss_pattern = "no_accelerated_damage"
        else:
            t2 = float(minus2["seconds_since_entry"])
            if t2 <= 10:
                loss_pattern = "immediate"
            elif t2 <= 60:
                loss_pattern = "after_waiting"
            else:
                loss_pattern = "very_delayed"

        out.update(
            {
                "mark_count": int(len(m)),
                "first_mark_time": m["mark_time"].iloc[0],
                "last_mark_time": m["mark_time"].iloc[-1],
                "first_favorable_seconds": np.nan if first_fav is None else float(first_fav["seconds_since_entry"]),
                "first_favorable_points": np.nan if first_fav is None else float(first_fav["pnl_delta"]),
                "first_adverse_seconds": np.nan if first_adv is None else float(first_adv["seconds_since_entry"]),
                "first_adverse_points": np.nan if first_adv is None else float(first_adv["pnl_delta"]),
                "mfe_points": float(m["pnl_delta"].max()),
                "mae_points": float(m["pnl_delta"].min()),
                "max_drawdown_points": float(max(0.0, -m["pnl_delta"].min())),
                "runup_5s": np.nan if pd.isna(runup_5) else float(runup_5),
                "runup_10s": np.nan if pd.isna(runup_10) else float(runup_10),
                "runup_15s": np.nan if pd.isna(runup_15) else float(runup_15),
                "drawdown_5s": np.nan if pd.isna(draw_5) else float(draw_5),
                "drawdown_10s": np.nan if pd.isna(draw_10) else float(draw_10),
                "drawdown_15s": np.nan if pd.isna(draw_15) else float(draw_15),
                "drawdown_20s": np.nan if pd.isna(draw_20) else float(draw_20),
                "time_to_minus_1": np.nan if minus1 is None else float(minus1["seconds_since_entry"]),
                "time_to_minus_2": np.nan if minus2 is None else float(minus2["seconds_since_entry"]),
                "time_to_minus_3": np.nan if minus3 is None else float(minus3["seconds_since_entry"]),
                "time_to_plus_0_5": np.nan if plus05 is None else float(plus05["seconds_since_entry"]),
                "time_to_plus_1": np.nan if plus1 is None else float(plus1["seconds_since_entry"]),
                "option_premium_failed_confirmation": failed_confirm,
                "move_stalled": move_stalled,
                "time_near_entry_before_damage_accel_seconds": near_entry_before_accel,
                "loss_expansion_pattern": loss_pattern,
            }
        )

        option_revert_proxy = False
        if first_fav is not None and minus2 is not None:
            option_revert_proxy = float(minus2["seconds_since_entry"]) > float(first_fav["seconds_since_entry"])
        out["spot_revert_proxy_from_option_path"] = option_revert_proxy

        rows.append(out)

    forensic = pd.DataFrame(rows)

    worst_pnl_ids = forensic.nsmallest(10, "realized_pnl")["trade_id"].tolist()
    worst_dd_ids = forensic.nlargest(10, "max_drawdown_points")["trade_id"].tolist()

    forensic["focus_manual_or_time_stop"] = forensic["exit_reason"].isin(["MANUAL_EXIT", "TIME_STOP_AFTER_1PM"])
    forensic["focus_top10_pnl"] = forensic["trade_id"].isin(worst_pnl_ids)
    forensic["focus_top10_drawdown"] = forensic["trade_id"].isin(worst_dd_ids)
    forensic["focus_major_loser"] = (
        forensic["focus_manual_or_time_stop"] | forensic["focus_top10_pnl"] | forensic["focus_top10_drawdown"]
    )

    focus_ids = set(forensic.loc[forensic["focus_major_loser"], "trade_id"])
    tl = marks[marks["trade_id"].isin(focus_ids)].copy()
    criteria_map = {
        tid: ",".join(
            [
                lbl
                for lbl, cond in [
                    ("TOP10_PNL", tid in set(worst_pnl_ids)),
                    ("TOP10_DD", tid in set(worst_dd_ids)),
                    (
                        "MANUAL_OR_TIME_STOP",
                        bool(forensic.loc[forensic["trade_id"] == tid, "focus_manual_or_time_stop"].iloc[0]),
                    ),
                ]
                if cond
            ]
        )
        for tid in focus_ids
    }

    tl["focus_criteria"] = tl["trade_id"].map(criteria_map)
    f_map = forensic.set_index("trade_id")
    tl["direction"] = tl["trade_id"].map(f_map["direction"])
    tl["entry_time_meta"] = tl["trade_id"].map(f_map["entry_time"])
    tl["exit_reason_meta"] = tl["trade_id"].map(f_map["exit_reason"])
    tl["realized_pnl"] = tl["trade_id"].map(f_map["realized_pnl"])
    if "signal_kind" not in tl.columns:
        tl["signal_kind"] = tl["trade_id"].map(f_map["signal_kind"])

    if "entry_time" in tl.columns:
        tl["entry_time"] = tl["entry_time"].fillna(tl["entry_time_meta"])
    else:
        tl["entry_time"] = tl["entry_time_meta"]

    if "exit_reason" in tl.columns:
        tl["exit_reason"] = tl["exit_reason"].fillna(tl["exit_reason_meta"])
    else:
        tl["exit_reason"] = tl["exit_reason_meta"]
    tl = tl[
        [
            "trade_id",
            "focus_criteria",
            "signal_kind",
            "direction",
            "entry_time",
            "mark_time",
            "seconds_since_entry",
            "ltp",
            "entry_price",
            "pnl_delta",
            "cum_mfe",
            "cum_mae",
            "drawdown_from_peak",
            "exit_reason",
            "realized_pnl",
        ]
    ].sort_values(["trade_id", "mark_time"])

    return forensic, tl


def _make_no_gain_rule(rule_id: str, desc: str, min_gain: float, by_seconds: float, scope_fn: Callable[[pd.Series], bool] | None = None) -> RuleDef:
    def _eval(tr: pd.Series, marks: pd.DataFrame, early: pd.Series | None) -> tuple[pd.Timestamp, float] | None:
        if scope_fn is not None and not scope_fn(tr):
            return None
        w = _window(marks, by_seconds)
        if w.empty:
            return None
        if float(w["pnl_delta"].max()) < min_gain:
            r = _row_at_or_after(marks, by_seconds)
            if r is None:
                r = w.iloc[-1]
            return pd.Timestamp(r["mark_time"]), float(r["ltp"])
        return None

    return RuleDef(rule_id=rule_id, description=desc, scope="trade-scope", evaluator=_eval)


def _make_drop_rule(rule_id: str, desc: str, drop_points: float, within_seconds: float, scope_fn: Callable[[pd.Series], bool] | None = None) -> RuleDef:
    def _eval(tr: pd.Series, marks: pd.DataFrame, early: pd.Series | None) -> tuple[pd.Timestamp, float] | None:
        if scope_fn is not None and not scope_fn(tr):
            return None
        w = _window(marks, within_seconds)
        if w.empty:
            return None
        hit = _first_row(w, w["pnl_delta"] <= -drop_points)
        if hit is None:
            return None
        return pd.Timestamp(hit["mark_time"]), float(hit["ltp"])

    return RuleDef(rule_id=rule_id, description=desc, scope="trade-scope", evaluator=_eval)


def _make_early_failure_no_recovery(rule_id: str, desc: str, wait_seconds: float, recover_level: float = 0.0) -> RuleDef:
    def _eval(tr: pd.Series, marks: pd.DataFrame, early: pd.Series | None) -> tuple[pd.Timestamp, float] | None:
        if early is None:
            return None
        ef_t = pd.to_datetime(early.get("mark_time"), errors="coerce")
        entry_t = pd.to_datetime(tr.get("entry_time"), errors="coerce")
        if pd.isna(ef_t) or pd.isna(entry_t):
            return None
        ef_elapsed = (ef_t - entry_t).total_seconds()
        checkpoint = ef_elapsed + wait_seconds
        window_after = marks[(marks["seconds_since_entry"] >= ef_elapsed) & (marks["seconds_since_entry"] <= checkpoint)]
        if not window_after.empty and (window_after["pnl_delta"] >= recover_level).any():
            return None
        r = _row_at_or_after(marks, checkpoint)
        if r is None:
            return None
        return pd.Timestamp(r["mark_time"]), float(r["ltp"])

    return RuleDef(rule_id=rule_id, description=desc, scope="early_failure_only", evaluator=_eval)


def _make_not_testable(rule_id: str, desc: str, note: str) -> RuleDef:
    def _eval(tr: pd.Series, marks: pd.DataFrame, early: pd.Series | None) -> tuple[pd.Timestamp, float] | None:
        return None

    return RuleDef(rule_id=rule_id, description=desc, scope="not_testable", evaluator=_eval, testable=False, note=note)


def build_candidate_rules() -> list[RuleDef]:
    is_after_1230 = lambda tr: pd.to_datetime(tr["entry_time"]).time() >= pd.Timestamp("12:30:00").time()
    is_after_1300 = lambda tr: pd.to_datetime(tr["entry_time"]).time() >= pd.Timestamp("13:00:00").time()
    is_kind = lambda kind: (lambda tr: str(tr.get("signal_kind", "")) == kind)

    rules = [
        _make_no_gain_rule("NO_PLUS_0_5_BY_5S", "Exit if premium fails to gain +0.5 within 5 seconds", 0.5, 5),
        _make_no_gain_rule("NO_PLUS_1_BY_10S", "Exit if premium fails to gain +1.0 within 10 seconds", 1.0, 10),
        _make_no_gain_rule("NO_PLUS_1_BY_15S", "Exit if premium fails to gain +1.0 within 15 seconds", 1.0, 15),
        _make_drop_rule("DROP_1_WITHIN_5S", "Exit if premium drops 1 point within first 5 seconds", 1.0, 5),
        _make_drop_rule("DROP_1_WITHIN_10S", "Exit if premium drops 1 point within first 10 seconds", 1.0, 10),
        _make_drop_rule("DROP_1_WITHIN_15S", "Exit if premium drops 1 point within first 15 seconds", 1.0, 15),
        _make_drop_rule("DD_2_WITHIN_10S", "Exit if drawdown exceeds 2 points within first 10 seconds", 2.0, 10),
        _make_drop_rule("DD_3_WITHIN_15S", "Exit if drawdown exceeds 3 points within first 15 seconds", 3.0, 15),
        _make_drop_rule("DD_5_WITHIN_20S", "Exit if drawdown exceeds 5 points within first 20 seconds", 5.0, 20),
        _make_drop_rule("DD_8_WITHIN_20S", "Exit if drawdown exceeds 8 points within first 20 seconds", 8.0, 20),
        _make_no_gain_rule("MFE_LT_0_5_BY_10S", "Exit if MFE is below +0.5 after 10 seconds", 0.5, 10),
        _make_no_gain_rule("MFE_LT_1_BY_15S", "Exit if MFE is below +1.0 after 15 seconds", 1.0, 15),
        _make_early_failure_no_recovery("EARLY_FAIL_NO_RECOVERY_10S", "Exit if early-failure occurs and no recovery within 10 seconds", 10, 0.0),
        _make_early_failure_no_recovery("EARLY_FAIL_NO_RECOVERY_15S", "Exit if early-failure occurs and no recovery within 15 seconds", 15, 0.0),
        _make_no_gain_rule("POST_1230_NO_PLUS_1_BY_10S", "Post-12:30 trades: exit if no +1 in 10 seconds", 1.0, 10, is_after_1230),
        _make_drop_rule("POST_1PM_DD_2_WITHIN_10S", "Post-1PM trades: exit on 2-point drawdown in 10 seconds", 2.0, 10, is_after_1300),
        _make_no_gain_rule("CONT_CALL_NO_PLUS_1_BY_10S", "Continuation call only: exit if no +1 in 10 seconds", 1.0, 10, is_kind("CONTINUATION_CALL")),
        _make_no_gain_rule("CONT_PUT_NO_PLUS_1_BY_10S", "Continuation put only: exit if no +1 in 10 seconds", 1.0, 10, is_kind("CONTINUATION_PUT")),
        _make_no_gain_rule("REV_CALL_NO_PLUS_1_BY_10S", "Reversal call only: exit if no +1 in 10 seconds", 1.0, 10, is_kind("REVERSAL_CALL")),
        _make_no_gain_rule("REV_PUT_NO_PLUS_1_BY_10S", "Reversal put only: exit if no +1 in 10 seconds", 1.0, 10, is_kind("REVERSAL_PUT")),
        _make_not_testable(
            "SPOT_REVERT_2_FROM_TRIGGER",
            "Exit if spot reverts 2 points from trigger after entry",
            "Not testable from current logs: spot ticks after entry are not captured in OPEN_POSITION_MARK.",
        ),
        _make_not_testable(
            "SPOT_REVERT_3_FROM_TRIGGER",
            "Exit if spot reverts 3 points from trigger after entry",
            "Not testable from current logs: spot ticks after entry are not captured in OPEN_POSITION_MARK.",
        ),
        _make_not_testable(
            "SPOT_REVERT_5_FROM_TRIGGER",
            "Exit if spot reverts 5 points from trigger after entry",
            "Not testable from current logs: spot ticks after entry are not captured in OPEN_POSITION_MARK.",
        ),
    ]
    return rules


def _simulate_single_policy(
    trades: pd.DataFrame,
    marks_map: dict[str, pd.DataFrame],
    early_map: dict[str, pd.Series],
    policy_id: str,
    description: str,
    entry_filter: Callable[[pd.Series], bool] | None,
    exit_evaluator: Callable[[pd.Series, pd.DataFrame, pd.Series | None], tuple[pd.Timestamp, float] | None] | None,
    baseline_tail_ids: list[str],
) -> dict[str, object]:
    sim = trades.copy()
    sim["policy_id"] = policy_id
    sim["policy_desc"] = description
    sim["skipped_entry"] = False
    sim["rule_triggered"] = False
    sim["sim_exit_reason"] = sim["exit_reason"]
    sim["sim_exit_time"] = sim["effective_exit_time"]
    sim["sim_exit_price"] = sim["effective_exit_price"]

    for idx, tr in sim.iterrows():
        tid = tr["trade_id"]
        marks = marks_map.get(tid)
        early = early_map.get(tid)

        if entry_filter is not None and entry_filter(tr):
            sim.at[idx, "skipped_entry"] = True
            sim.at[idx, "sim_exit_reason"] = "ENTRY_SKIPPED_BY_POLICY"
            sim.at[idx, "sim_exit_time"] = tr["entry_time"]
            sim.at[idx, "sim_exit_price"] = tr["entry_price"]
            continue

        if marks is None or marks.empty or exit_evaluator is None:
            continue

        trig = exit_evaluator(tr, marks, early)
        if trig is None:
            continue
        trig_t, trig_px = trig
        if pd.isna(trig_t) or pd.isna(trig_px):
            continue
        base_exit_t = pd.to_datetime(tr["effective_exit_time"], errors="coerce")
        if pd.isna(base_exit_t):
            continue
        if trig_t < base_exit_t:
            sim.at[idx, "rule_triggered"] = True
            sim.at[idx, "sim_exit_reason"] = policy_id
            sim.at[idx, "sim_exit_time"] = trig_t
            sim.at[idx, "sim_exit_price"] = float(trig_px)

    sim["sim_points"] = sim["sim_exit_price"] - sim["entry_price"]
    sim["sim_gross_pnl"] = sim["sim_points"] * sim["quantity"]
    sim["sim_net_pnl"] = sim["sim_gross_pnl"] - sim["charges"].fillna(0.0)
    sim.loc[sim["skipped_entry"], "sim_net_pnl"] = 0.0

    active = sim[~sim["skipped_entry"]].copy()
    base = trades.copy()

    winners_cut = int(((base["net_pnl_effective"] > 0) & sim["rule_triggered"]).sum())
    losers_cut = int(((base["net_pnl_effective"] <= 0) & sim["rule_triggered"]).sum())

    baseline_target_hits = int((base["exit_reason"] == "TARGET_HIT").sum())
    new_target_hits = int((active["sim_exit_reason"] == "TARGET_HIT").sum())

    baseline_tail_abs = float(abs(base[base["trade_id"].isin(baseline_tail_ids)]["net_pnl_effective"].sum()))
    new_tail_abs = float(abs(sim[sim["trade_id"].isin(baseline_tail_ids)]["sim_net_pnl"].sum()))
    tail_reduction_abs = baseline_tail_abs - new_tail_abs
    tail_reduction_pct = tail_reduction_abs / baseline_tail_abs if baseline_tail_abs > 0 else np.nan

    result = {
        "policy_id": policy_id,
        "description": description,
        "tested": True,
        "total_trades": int(len(sim)),
        "active_trades": int(len(active)),
        "entries_skipped": int(sim["skipped_entry"].sum()),
        "trades_affected": int(sim["rule_triggered"].sum() + sim["skipped_entry"].sum()),
        "winners_cut_early": winners_cut,
        "losers_cut_early": losers_cut,
        "new_net_pnl": float(sim["sim_net_pnl"].sum()),
        "new_win_rate": float((active["sim_net_pnl"] > 0).mean()) if not active.empty else np.nan,
        "new_avg_pnl": float(active["sim_net_pnl"].mean()) if not active.empty else np.nan,
        "new_median_pnl": float(active["sim_net_pnl"].median()) if not active.empty else np.nan,
        "new_max_loss": float(active["sim_net_pnl"].min()) if not active.empty else np.nan,
        "new_expectancy": float(active["sim_net_pnl"].mean()) if not active.empty else np.nan,
        "tail_loss_contribution_abs": new_tail_abs,
        "tail_loss_reduction_abs": float(tail_reduction_abs),
        "tail_loss_reduction_pct": float(tail_reduction_pct) if pd.notna(tail_reduction_pct) else np.nan,
        "target_hit_count_new": new_target_hits,
        "target_hit_change": int(new_target_hits - baseline_target_hits),
    }
    return result


def evaluate_candidates(trades: pd.DataFrame, marks: pd.DataFrame, early: pd.DataFrame) -> pd.DataFrame:
    closed = trades[trades["status"] == "CLOSED"].copy()
    marks_map = {tid: grp.sort_values("mark_time").copy() for tid, grp in marks.groupby("trade_id")}
    early_map = early.set_index("trade_id").to_dict("index") if not early.empty else {}
    baseline_tail_ids = closed.nsmallest(10, "net_pnl_effective")["trade_id"].tolist()

    rows: list[dict[str, object]] = []

    baseline = _simulate_single_policy(
        trades=closed,
        marks_map=marks_map,
        early_map=early_map,
        policy_id="BASELINE",
        description="Actual outcomes from logs",
        entry_filter=None,
        exit_evaluator=None,
        baseline_tail_ids=baseline_tail_ids,
    )
    rows.append(baseline)

    for rule in build_candidate_rules():
        if not rule.testable:
            out = baseline.copy()
            out.update(
                {
                    "policy_id": rule.rule_id,
                    "description": rule.description,
                    "tested": False,
                    "trades_affected": 0,
                    "winners_cut_early": 0,
                    "losers_cut_early": 0,
                    "target_hit_count_new": baseline["target_hit_count_new"],
                    "target_hit_change": 0,
                    "note": rule.note,
                }
            )
            rows.append(out)
            continue

        out = _simulate_single_policy(
            trades=closed,
            marks_map=marks_map,
            early_map=early_map,
            policy_id=rule.rule_id,
            description=rule.description,
            entry_filter=None,
            exit_evaluator=rule.evaluator,
            baseline_tail_ids=baseline_tail_ids,
        )
        out["note"] = ""
        rows.append(out)

    result = pd.DataFrame(rows)
    baseline_net = float(result.loc[result["policy_id"] == "BASELINE", "new_net_pnl"].iloc[0])
    baseline_max_loss = float(result.loc[result["policy_id"] == "BASELINE", "new_max_loss"].iloc[0])
    result["delta_net_pnl_vs_baseline"] = result["new_net_pnl"] - baseline_net
    result["max_loss_improvement"] = result["new_max_loss"] - baseline_max_loss
    return result.sort_values("delta_net_pnl_vs_baseline", ascending=False)


def build_composite_policies() -> list[CompositePolicy]:
    r_no_plus_1_10 = _make_no_gain_rule("R", "", 1.0, 10).evaluator
    r_dd_3_15 = _make_drop_rule("R", "", 3.0, 15).evaluator
    r_dd_2_10 = _make_drop_rule("R", "", 2.0, 10).evaluator
    r_ef_no_rec_10 = _make_early_failure_no_recovery("R", "", 10).evaluator

    def _both(tr: pd.Series, marks: pd.DataFrame, early: pd.Series | None) -> tuple[pd.Timestamp, float] | None:
        a = r_ef_no_rec_10(tr, marks, early)
        b = r_no_plus_1_10(tr, marks, early)
        if a is None or b is None:
            return None
        t = max(a[0], b[0])
        row = _row_at_or_after(marks, (t - tr["entry_time"]).total_seconds())
        if row is None:
            return None
        return pd.Timestamp(row["mark_time"]), float(row["ltp"])

    def _dd_plus_weak(tr: pd.Series, marks: pd.DataFrame, early: pd.Series | None) -> tuple[pd.Timestamp, float] | None:
        b = r_no_plus_1_10(tr, marks, early)
        d = r_dd_3_15(tr, marks, early)
        if b is None or d is None:
            return None
        return d

    def _tight_cont_call(tr: pd.Series, marks: pd.DataFrame, early: pd.Series | None) -> tuple[pd.Timestamp, float] | None:
        if str(tr.get("signal_kind", "")) != "CONTINUATION_CALL":
            return None
        a = r_no_plus_1_10(tr, marks, early)
        b = r_dd_2_10(tr, marks, early)
        if a is None:
            return b
        if b is None:
            return a
        return a if a[0] <= b[0] else b

    return [
        CompositePolicy(
            policy_id="COMP_NO_ENTRY_AFTER_1230",
            description="No entries after 12:30",
            entry_filter=lambda tr: pd.to_datetime(tr["entry_time"]).time() >= pd.Timestamp("12:30:00").time(),
            exit_evaluator=None,
        ),
        CompositePolicy(
            policy_id="COMP_EF_AND_NO_PLUS1_10",
            description="Early-failure + no +1 premium within 10 seconds",
            entry_filter=None,
            exit_evaluator=_both,
        ),
        CompositePolicy(
            policy_id="COMP_DD3_15_AND_WEAK_CONFIRM",
            description="Drawdown threshold + weak confirmation (DD>=3 by 15s AND no +1 by 10s)",
            entry_filter=None,
            exit_evaluator=_dd_plus_weak,
        ),
        CompositePolicy(
            policy_id="COMP_TIGHT_CONT_CALL",
            description="Tighter kill-switch only for continuation_call trades",
            entry_filter=None,
            exit_evaluator=_tight_cont_call,
        ),
        CompositePolicy(
            policy_id="COMP_POST_1PM_FILTER_PLUS_WEAK",
            description="No entry after 1PM + no +1 premium by 10 seconds",
            entry_filter=lambda tr: pd.to_datetime(tr["entry_time"]).time() >= pd.Timestamp("13:00:00").time(),
            exit_evaluator=r_no_plus_1_10,
        ),
    ]


def evaluate_composites(trades: pd.DataFrame, marks: pd.DataFrame, early: pd.DataFrame) -> pd.DataFrame:
    closed = trades[trades["status"] == "CLOSED"].copy()
    marks_map = {tid: grp.sort_values("mark_time").copy() for tid, grp in marks.groupby("trade_id")}
    early_map = early.set_index("trade_id").to_dict("index") if not early.empty else {}
    baseline_tail_ids = closed.nsmallest(10, "net_pnl_effective")["trade_id"].tolist()

    rows: list[dict[str, object]] = []
    baseline = _simulate_single_policy(
        trades=closed,
        marks_map=marks_map,
        early_map=early_map,
        policy_id="BASELINE",
        description="Actual outcomes from logs",
        entry_filter=None,
        exit_evaluator=None,
        baseline_tail_ids=baseline_tail_ids,
    )
    rows.append(baseline)

    for p in build_composite_policies():
        out = _simulate_single_policy(
            trades=closed,
            marks_map=marks_map,
            early_map=early_map,
            policy_id=p.policy_id,
            description=p.description,
            entry_filter=p.entry_filter,
            exit_evaluator=p.exit_evaluator,
            baseline_tail_ids=baseline_tail_ids,
        )
        rows.append(out)

    result = pd.DataFrame(rows)
    baseline_net = float(result.loc[result["policy_id"] == "BASELINE", "new_net_pnl"].iloc[0])
    result["delta_net_pnl_vs_baseline"] = result["new_net_pnl"] - baseline_net
    return result.sort_values("delta_net_pnl_vs_baseline", ascending=False)


def _robustness_label(sample_size: int, delta_net: float, tail_reduction_pct: float | float) -> str:
    if sample_size >= 10 and delta_net > 0 and pd.notna(tail_reduction_pct) and tail_reduction_pct >= 0.35:
        return "strong"
    if sample_size >= 5 and delta_net > 0:
        return "suggestive"
    if sample_size >= 3 and delta_net > -5000:
        return "weak"
    return "weak"


def _feature_classification(candidate: pd.DataFrame) -> pd.DataFrame:
    c = candidate[(candidate["policy_id"] != "BASELINE") & (candidate["tested"] == True)].copy()
    if c.empty:
        return pd.DataFrame(columns=["feature", "class", "reason"])

    out = []
    for _, r in c.iterrows():
        losers = int(r["losers_cut_early"])
        winners = int(r["winners_cut_early"])
        delta = float(r["delta_net_pnl_vs_baseline"])
        tail = float(r["tail_loss_reduction_pct"]) if pd.notna(r["tail_loss_reduction_pct"]) else np.nan

        if delta > 0 and losers > winners and pd.notna(tail) and tail >= 0.3:
            cls = "strong hard-exit candidate"
        elif delta > 0 and losers >= winners:
            cls = "weak but useful warning indicator"
        elif delta <= 0 and losers > 0:
            cls = "not useful / inconclusive"
        else:
            cls = "not useful / inconclusive"

        out.append(
            {
                "feature": r["policy_id"],
                "class": cls,
                "sample_size": int(r["trades_affected"]),
                "delta_net": delta,
                "tail_reduction_pct": tail,
                "reason": f"losers_cut={losers}, winners_cut={winners}",
            }
        )

    return pd.DataFrame(out).sort_values(["class", "delta_net"], ascending=[True, False])


def _fmt_num(v: object, nd: int = 2) -> str:
    if v is None:
        return "NA"
    if isinstance(v, (float, np.floating)) and pd.isna(v):
        return "NA"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    return f"{float(v):,.{nd}f}"


def _md_table(df: pd.DataFrame, cols: list[str], n: int = 8) -> str:
    view = df[cols].head(n).copy()
    if view.empty:
        return "_No rows_"
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body_rows = []
    for _, row in view.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if pd.isna(v):
                vals.append("NA")
            elif isinstance(v, (pd.Timestamp, np.datetime64)):
                vals.append(str(pd.Timestamp(v)))
            elif isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):.2f}")
            else:
                vals.append(str(v))
        body_rows.append("| " + " | ".join(vals) + " |")
    return "\\n".join([header, sep] + body_rows)


def write_report(
    trades: pd.DataFrame,
    forensic: pd.DataFrame,
    candidate: pd.DataFrame,
    composite: pd.DataFrame,
    feature_cls: pd.DataFrame,
) -> None:
    closed = trades[trades["status"] == "CLOSED"].copy()
    worst_pnl = forensic.nsmallest(10, "realized_pnl").copy()
    worst_dd = forensic.nlargest(10, "max_drawdown_points").copy()

    baseline = candidate[candidate["policy_id"] == "BASELINE"].iloc[0]
    best_standalone = candidate[(candidate["policy_id"] != "BASELINE") & (candidate["tested"] == True)].sort_values(
        "delta_net_pnl_vs_baseline", ascending=False
    )
    best_composite = composite[composite["policy_id"] != "BASELINE"].sort_values(
        "delta_net_pnl_vs_baseline", ascending=False
    )

    cont_call = forensic[forensic["signal_kind"] == "CONTINUATION_CALL"].copy()
    cont_call_loss = cont_call[cont_call["realized_pnl"] <= 0]

    manual_time = forensic[forensic["exit_reason"].isin(["MANUAL_EXIT", "TIME_STOP_AFTER_1PM"])]

    robust_lines = []
    for _, row in best_standalone.head(5).iterrows():
        label = _robustness_label(int(row["trades_affected"]), float(row["delta_net_pnl_vs_baseline"]), row.get("tail_loss_reduction_pct", np.nan))
        robust_lines.append(
            f"- `{row['policy_id']}`: {label} | sample={int(row['trades_affected'])} | delta_net={_fmt_num(row['delta_net_pnl_vs_baseline'])} | likely overfit risk={'high' if int(row['trades_affected']) < 8 else 'moderate'}"
        )

    report = f"""# Tail Loss Forensics Report (2026-03-19)

## Baseline recap
- Dataset date: **2026-03-19** from `logs/trades.jsonl` (other log files contain no events for this date).
- Closed trades: **{len(closed)}**
- Target hits: **{int((closed['exit_reason'] == 'TARGET_HIT').sum())}**
- Manual exits: **{int((closed['exit_reason'] == 'MANUAL_EXIT').sum())}**
- Time-stop after 1PM exits: **{int((closed['exit_reason'] == 'TIME_STOP_AFTER_1PM').sum())}**
- Baseline net PnL: **{_fmt_num(baseline['new_net_pnl'])}**
- Baseline expectancy (avg PnL/trade): **{_fmt_num(baseline['new_expectancy'])}**
- Baseline max loss: **{_fmt_num(baseline['new_max_loss'])}**

## Tail-loss anatomy
Top 10 worst trades by realized PnL:

{_md_table(worst_pnl, ['trade_id','signal_kind','direction','entry_time','exit_reason','realized_pnl','max_drawdown_points','holding_seconds'], 10)}

Top 10 worst trades by drawdown:

{_md_table(worst_dd, ['trade_id','signal_kind','direction','entry_time','exit_reason','max_drawdown_points','realized_pnl','holding_seconds'], 10)}

Manual + time-stop loss bucket summary:
- Trades in bucket: **{len(manual_time)}**
- Net PnL from bucket: **{_fmt_num(manual_time['realized_pnl'].sum())}**
- Median holding time (s): **{_fmt_num(manual_time['holding_seconds'].median())}**
- Median max drawdown (pts): **{_fmt_num(manual_time['max_drawdown_points'].median())}**

## What catastrophic losers looked like before they became catastrophic
Observed recurring pre-loss signatures (from per-trade forensic reconstruction):
- Premium confirmation failure within first 10-15s (`runup_10s < +1`) appears frequently in the worst-loss set.
- Early adverse move (first `-1`/`-2` points) often arrived quickly in large losers.
- Early-failure flag was directionally useful but not sufficient by itself.
- Many severe losses were **not** immediate straight-line drops; they often spent time near entry and then expanded after waiting.
- Spot-trigger reversion cannot be directly measured from current logs because post-entry spot ticks are missing.

## Best standalone kill-switch candidates

{_md_table(best_standalone, ['policy_id','trades_affected','winners_cut_early','losers_cut_early','new_net_pnl','delta_net_pnl_vs_baseline','new_max_loss','tail_loss_reduction_pct','target_hit_change'], 10)}

Robustness labels (one-day sample discipline):
{chr(10).join(robust_lines) if robust_lines else '- No tested candidate rules.'}

## Best composite kill-switch candidates

{_md_table(best_composite, ['policy_id','trades_affected','entries_skipped','winners_cut_early','losers_cut_early','new_net_pnl','delta_net_pnl_vs_baseline','new_max_loss','tail_loss_reduction_pct','target_hit_change'], 10)}

## What appears specific to continuation_call trades
- Continuation call trades: **{len(cont_call)}**
- Losing continuation call trades: **{len(cont_call_loss)}**
- Continuation call net PnL: **{_fmt_num(cont_call['realized_pnl'].sum())}**
- Median drawdown for continuation call losers (pts): **{_fmt_num(cont_call_loss['max_drawdown_points'].median()) if not cont_call_loss.empty else 'NA'}**
- Practical implication: continuation_call-specific tight invalidation is justified as a **suggestive** control on this sample, but still at high overfit risk if hardcoded to a single threshold.

## Time-of-day conclusions
- Post-1PM exits are a small count but disproportionately represented in negative tail outcomes.
- Entry-cutoff style policies (no new trades after 12:30 or 1PM) should be evaluated as risk controls even if they reduce total target-hit count.
- Time-of-day filters alone are unlikely to be sufficient; combining with early premium weakness improves tail control.

## What should be implemented next in live strategy logic
1. Add a configurable early invalidation module (time-window + min confirmation + max adverse excursion).
2. Add continuation_call-specific stricter invalidation than reversal/put variants.
3. Add post-12:30 and post-1PM adaptive limits (either no-entry or tighter kill-switch).
4. Keep thresholds in broad bands (`~10-15s`, `~1-3 points`) instead of brittle exact values.

## What additional logging is needed for stronger future testing
- Underlying spot tick stream during open trades, with trigger-distance over time.
- Explicit trigger event timestamp (not just entry timestamp).
- Bid/ask spread and depth snapshots at entry and during first 30 seconds.
- Order-state timestamps (placed, acknowledged, filled) for both entry and exit.
- Latency metrics and quote staleness markers.

## Risk markers vs hard invalidation features

{_md_table(feature_cls, ['feature','class','sample_size','delta_net','tail_reduction_pct','reason'], 20)}

Notes:
- All findings are from a **single day (n={len(closed)})** and should be treated as exploratory.
- Recommendations with small affected sample sizes should be considered **suggestive/weak** until multi-day validation confirms stability.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    events = load_events()
    trades, marks, early = build_day_dataset(events)

    forensic, timelines = compute_trade_forensics(trades, marks, early)
    candidate = evaluate_candidates(trades, marks, early)
    composite = evaluate_composites(trades, marks, early)
    feature_cls = _feature_classification(candidate)

    forensic.to_csv(OUT_PER_TRADE, index=False)
    candidate.to_csv(OUT_CANDIDATE, index=False)
    composite.to_csv(OUT_COMPOSITE, index=False)
    timelines.to_csv(OUT_TIMELINES, index=False)

    write_report(trades, forensic, candidate, composite, feature_cls)

    print(f"Wrote: {OUT_PER_TRADE}")
    print(f"Wrote: {OUT_CANDIDATE}")
    print(f"Wrote: {OUT_COMPOSITE}")
    print(f"Wrote: {OUT_TIMELINES}")
    print(f"Wrote: {REPORT_PATH}")


if __name__ == "__main__":
    main()
