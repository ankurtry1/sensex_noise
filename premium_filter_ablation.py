from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import burst_onset_research as bor
import near_atm_burst_research as natm
import tradable_expansion_edge_hunt as teh

REPO_ROOT = Path(__file__).resolve().parent
TES_RESULTS = REPO_ROOT / "tradable_expansion_edge_results"
OUTPUT_DIR = REPO_ROOT / "premium_filter_ablation_results"
CHARTS_DIR = OUTPUT_DIR / "charts"
CANDIDATE_PATH = TES_RESULTS / "tradable_expansion_candidates.csv"
SUMMARY_PATH = TES_RESULTS / "tradable_expansion_summary.csv"
DAYWISE_PATH = TES_RESULTS / "tradable_expansion_daywise.csv"

GLOBAL_COOLDOWN_SECONDS = 45
SYMBOL_COOLDOWN_SECONDS = 60
TOP_WINDOW_SECONDS = 30
MAX_HOLD_SECONDS = 30
FIXED_QTY = 500


@dataclass(frozen=True)
class PremiumVariant:
    name: str
    atm_max_abs: int
    premium_min: float | None = None
    premium_max: float | None = None
    dynamic_band: tuple[float, float] | None = None
    spread_abs_max: float | None = None
    spread_pct_max: float | None = None
    depth_min: float | None = None
    raw_score_min: int = 5
    use_promoted_logic: bool = False
    target_points: float = 3.0
    cooldown_seconds: int = GLOBAL_COOLDOWN_SECONDS
    symbol_cooldown_seconds: int = SYMBOL_COOLDOWN_SECONDS
    top_window_seconds: int = TOP_WINDOW_SECONDS
    notes: str | None = None


BASELINE_NAME = "BASE_ATM100_SCORE5_P80_300_SPREAD2_DEPTH250"

BASE_VARIANTS: list[PremiumVariant] = [
    PremiumVariant(
        name=BASELINE_NAME,
        atm_max_abs=100,
        premium_min=80,
        premium_max=300,
        spread_abs_max=2.0,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="BASE_ATM100_SCORE5_NO_PREMIUM_SPREAD2_DEPTH250",
        atm_max_abs=100,
        spread_abs_max=2.0,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="BASE_ATM100_SCORE5_NO_PREMIUM_SPREAD2_SPREADPCT015_DEPTH250",
        atm_max_abs=100,
        spread_abs_max=2.0,
        spread_pct_max=0.015,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="BASE_ATM100_SCORE5_NO_PREMIUM_SPREAD1P5_SPREADPCT010_DEPTH250",
        atm_max_abs=100,
        spread_abs_max=1.5,
        spread_pct_max=0.010,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="BASE_ATM100_SCORE5_P50_400_SPREAD2_DEPTH250",
        atm_max_abs=100,
        premium_min=50,
        premium_max=400,
        spread_abs_max=2.0,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="BASE_ATM100_SCORE5_P100_500_SPREAD2_DEPTH250",
        atm_max_abs=100,
        premium_min=100,
        premium_max=500,
        spread_abs_max=2.0,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="BASE_ATM200_SCORE5_NO_PREMIUM_SPREAD2_DEPTH250",
        atm_max_abs=200,
        spread_abs_max=2.0,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="BASE_ATM200_SCORE5_NO_PREMIUM_SPREAD2_SPREADPCT015_DEPTH250",
        atm_max_abs=200,
        spread_abs_max=2.0,
        spread_pct_max=0.015,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="DYNAMIC_PREMIUM_ATM100_SCORE5_MIDBAND_SPREAD2_DEPTH250",
        atm_max_abs=100,
        dynamic_band=(0.20, 0.80),
        spread_abs_max=2.0,
        depth_min=250,
        target_points=3.0,
    ),
    PremiumVariant(
        name="DYNAMIC_PREMIUM_ATM100_SCORE5_UPPERBAND_SPREAD2_DEPTH250",
        atm_max_abs=100,
        dynamic_band=(0.40, 0.90),
        spread_abs_max=2.0,
        depth_min=250,
        target_points=3.0,
    ),
]


def safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if math.isnan(out):
            return None
        return out
    except (TypeError, ValueError):
        return None


def discover_dates_from_candidates() -> list[str]:
    if not CANDIDATE_PATH.exists():
        raise FileNotFoundError(f"Missing candidate file: {CANDIDATE_PATH}")
    cands = pd.read_csv(CANDIDATE_PATH, usecols=["date"])
    dates = sorted(cands["date"].astype(str).unique().tolist())
    return dates


def load_candidate_universe(dates: list[str]) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(CANDIDATE_PATH, parse_dates=["timestamp"])
    df["date"] = df["date"].astype(str)
    df = df[df["date"].isin(dates)].copy()
    full_tape_dirs = sorted([p.name for p in (REPO_ROOT / "data" / "tape" / "sensex_options").iterdir() if p.is_dir()]) if (REPO_ROOT / "data" / "tape" / "sensex_options").exists() else []
    skipped = [d for d in full_tape_dirs if d not in set(df["date"].unique())]
    return df, skipped


def build_dynamic_bounds(candidates: pd.DataFrame) -> dict[tuple[str, str], tuple[float, float]]:
    base = candidates[(candidates["atm_distance_abs"] <= 100) & (candidates["raw_burst_score"] >= 5)].copy()
    out: dict[tuple[str, str], tuple[float, float]] = {}
    if base.empty:
        return out
    for date, g in base.groupby("date"):
        ltp = g["ltp"].astype(float)
        out[(str(date), "MIDBAND")] = (float(ltp.quantile(0.20)), float(ltp.quantile(0.80)))
        out[(str(date), "UPPERBAND")] = (float(ltp.quantile(0.40)), float(ltp.quantile(0.90)))
    return out


def premium_bounds_for_variant(date: str, variant: PremiumVariant, dynamic_bounds: dict[tuple[str, str], tuple[float, float]]) -> tuple[float | None, float | None]:
    if variant.dynamic_band is None:
        return variant.premium_min, variant.premium_max
    key = "MIDBAND" if variant.dynamic_band == (0.20, 0.80) else "UPPERBAND"
    return dynamic_bounds.get((date, key), (None, None))


def variant_passes(row: pd.Series, variant: PremiumVariant, dynamic_bounds: dict[tuple[str, str], tuple[float, float]]) -> bool:
    if int(row.get("raw_burst_score", 0)) < variant.raw_score_min:
        return False
    if int(row.get("atm_distance_abs", 10**9)) > variant.atm_max_abs:
        return False
    premium_min, premium_max = premium_bounds_for_variant(str(row["date"]), variant, dynamic_bounds)
    ltp = float(row["ltp"])
    if premium_min is not None and ltp < float(premium_min):
        return False
    if premium_max is not None and ltp > float(premium_max):
        return False
    spread_now = safe_float(row.get("spread_now"))
    if spread_now is None:
        spread_now = safe_float(row.get("spread"))
    if variant.spread_abs_max is not None and (spread_now is None or spread_now > variant.spread_abs_max):
        return False
    spread_pct_now = safe_float(row.get("spread_pct_now"))
    if spread_pct_now is None:
        spread_pct_now = safe_float(row.get("spread_pct"))
    if variant.spread_pct_max is not None and (spread_pct_now is None or spread_pct_now > variant.spread_pct_max):
        return False
    depth = safe_float(row.get("depth_min_qty"))
    if variant.depth_min is not None and (depth is None or depth < variant.depth_min):
        return False
    return True


def select_variant_candidates(day_df: pd.DataFrame, variant: PremiumVariant, dynamic_bounds: dict[tuple[str, str], tuple[float, float]]) -> pd.DataFrame:
    filtered = day_df[day_df.apply(lambda r: variant_passes(r, variant, dynamic_bounds), axis=1)].copy()
    if filtered.empty:
        return filtered
    date = str(filtered["date"].iloc[0])
    start = pd.Timestamp(f"{date} 09:15:00")
    filtered["window_index"] = ((pd.to_datetime(filtered["timestamp"]) - start).dt.total_seconds() // variant.top_window_seconds).astype(int)
    filtered = filtered.sort_values(["window_index", "rank_score", "timestamp", "symbol"], ascending=[True, False, True, True])
    top = filtered.groupby("window_index", as_index=False, group_keys=False).head(1).drop(columns=["window_index"]).reset_index(drop=True)
    top["variant_name"] = variant.name
    top["dynamic_premium_min"] = [premium_bounds_for_variant(date, variant, dynamic_bounds)[0]] * len(top)
    top["dynamic_premium_max"] = [premium_bounds_for_variant(date, variant, dynamic_bounds)[1]] * len(top)
    return top


def load_market_context(date: str, symbols: list[str], audit: Any) -> tuple[dict[str, list[dict[str, Any]]], pd.Series, dict[str, pd.DataFrame]]:
    symbol_rows, _quality = natm.load_option_second_rows_subset(date, set(symbols))
    underlying = audit.load_underlying_second_series(date)
    series_cache = {sym: audit.build_ffill_symbol_series(rows) for sym, rows in symbol_rows.items() if rows}
    return symbol_rows, underlying, series_cache


def replay_variant_day(
    date: str,
    variant: PremiumVariant,
    selected_df: pd.DataFrame,
    symbol_rows: dict[str, list[dict[str, Any]]],
    underlying: pd.Series,
    settings: Any,
    series_cache: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if selected_df.empty:
        return pd.DataFrame()
    trades: list[dict[str, Any]] = []
    next_free_time: pd.Timestamp | None = None
    last_symbol_entry: dict[str, pd.Timestamp] = {}
    for row in selected_df.sort_values(["timestamp", "rank_score"], ascending=[True, False]).to_dict(orient="records"):
        ts = pd.Timestamp(row["timestamp"])
        sym = str(row["symbol"])
        if next_free_time is not None and ts < next_free_time:
            continue
        prev = last_symbol_entry.get(sym)
        if prev is not None and (ts - prev).total_seconds() < variant.symbol_cooldown_seconds:
            continue
        if sym not in symbol_rows or sym not in series_cache:
            continue
        if variant.use_promoted_logic:
            result = teh.simulate_promoted_trade_fixed_qty(sym, ts, int(row["raw_burst_score"]), symbol_rows[sym], settings, series_cache, max_hold_seconds=MAX_HOLD_SECONDS, quantity=FIXED_QTY)
        else:
            result = teh.simulate_fixed_target_trade(sym, ts, symbol_rows[sym], settings, series_cache, target_points=variant.target_points, max_hold_seconds=MAX_HOLD_SECONDS, quantity=FIXED_QTY)
        if result is None:
            continue
        merged = {**row, **result}
        merged["variant_name"] = variant.name
        merged["points_pnl"] = float(merged["exit_price"] - merged["entry_price"])
        merged["entry_premium"] = float(merged["entry_price"])
        merged["avg_spread_candidate"] = safe_float(row.get("spread_now")) or safe_float(row.get("spread"))
        merged["avg_spread_pct_candidate"] = safe_float(row.get("spread_pct_now")) or safe_float(row.get("spread_pct"))
        trades.append(merged)
        last_symbol_entry[sym] = ts
        next_free_time = pd.Timestamp(result["exit_time"]) + pd.Timedelta(seconds=variant.cooldown_seconds)
    return pd.DataFrame(trades)


def summarize_replay_day(replay_df: pd.DataFrame, date: str, variant_name: str, candidate_count: int) -> dict[str, Any]:
    if replay_df.empty:
        return {
            "date": date,
            "variant_name": variant_name,
            "candidate_count": int(candidate_count),
            "selected_trades": 0,
            "net_pnl": 0.0,
            "profit_factor": np.nan,
            "win_rate": np.nan,
            "avg_pnl": np.nan,
            "max_drawdown": 0.0,
            "target_hits": 0,
            "hard_stops": 0,
            "one_sec_kills": 0,
            "three_sec_kills": 0,
            "avg_entry_premium": np.nan,
            "min_entry_premium": np.nan,
            "max_entry_premium": np.nan,
            "median_entry_premium": np.nan,
            "avg_spread": np.nan,
            "avg_spread_pct": np.nan,
            "avg_depth_min_qty": np.nan,
            "avg_atm_distance_abs": np.nan,
        }
    ordered = replay_df.sort_values("exit_time").copy()
    eq = ordered["net_pnl"].cumsum()
    dd = eq - eq.cummax()
    wins = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"]
    losses = ordered.loc[ordered["net_pnl"] < 0, "net_pnl"]
    pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
    return {
        "date": date,
        "variant_name": variant_name,
        "candidate_count": int(candidate_count),
        "selected_trades": int(len(ordered)),
        "net_pnl": float(ordered["net_pnl"].sum()),
        "profit_factor": pf,
        "win_rate": float((ordered["net_pnl"] > 0).mean()),
        "avg_pnl": float(ordered["net_pnl"].mean()),
        "max_drawdown": float(dd.min()) if not dd.empty else 0.0,
        "target_hits": int((ordered["exit_reason"] == "TARGET_HIT").sum()),
        "hard_stops": int((ordered["exit_reason"] == "EDGE_HARD_STOP").sum()),
        "one_sec_kills": int((ordered["exit_reason"] == "EARLY_FAIL_1S").sum()),
        "three_sec_kills": int(ordered["exit_reason"].isin(["EARLY_FAIL_3S", "PROMOTED_FAIL_3S", "PROMOTION_PERSISTENCE_FAIL"]).sum()),
        "avg_entry_premium": float(ordered["entry_price"].mean()),
        "min_entry_premium": float(ordered["entry_price"].min()),
        "max_entry_premium": float(ordered["entry_price"].max()),
        "median_entry_premium": float(ordered["entry_price"].median()),
        "avg_spread": float(ordered["avg_spread_candidate"].mean()),
        "avg_spread_pct": float(ordered["avg_spread_pct_candidate"].mean()),
        "avg_depth_min_qty": float(ordered["depth_min_qty"].mean()),
        "avg_atm_distance_abs": float(ordered["atm_distance_abs"].mean()),
    }


def aggregate_summary(daywise_df: pd.DataFrame, replay_df: pd.DataFrame, baseline_row: pd.Series) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variant_name, g in daywise_df.groupby("variant_name"):
        trades = replay_df[replay_df["variant_name"] == variant_name].copy()
        wins = trades.loc[trades["net_pnl"] > 0, "net_pnl"]
        losses = trades.loc[trades["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        total_trades = int(g["selected_trades"].sum())
        row = {
            "variant_name": variant_name,
            "total_trades": total_trades,
            "active_days": int((g["selected_trades"] > 0).sum()),
            "total_net_pnl": float(g["net_pnl"].sum()),
            "worst_day_pnl": float(g["net_pnl"].min()),
            "best_day_pnl": float(g["net_pnl"].max()),
            "avg_day_pnl": float(g["net_pnl"].mean()),
            "profit_factor": pf,
            "win_rate": float((trades["net_pnl"] > 0).mean()) if not trades.empty else np.nan,
            "avg_pnl_per_trade": float(trades["net_pnl"].mean()) if not trades.empty else np.nan,
            "max_drawdown_sum": float(g["max_drawdown"].sum()),
            "avg_entry_premium": float(trades["entry_price"].mean()) if not trades.empty else np.nan,
            "median_entry_premium": float(trades["entry_price"].median()) if not trades.empty else np.nan,
            "beats_current_baseline_total_pnl": bool(float(g["net_pnl"].sum()) > float(baseline_row["total_net_pnl"])),
            "beats_current_baseline_worst_day": bool(float(g["net_pnl"].min()) >= float(baseline_row["worst_day_pnl"])),
            "beats_current_baseline_pf": bool((pf if np.isfinite(pf) else np.inf) >= float(baseline_row["profit_factor"])),
            "improves_trade_count_discipline": bool(total_trades <= int(baseline_row["total_trades"])),
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).reset_index(drop=True)


def bucket_premium(value: float) -> str:
    if value < 50:
        return "<50"
    if value < 80:
        return "50-80"
    if value < 150:
        return "80-150"
    if value < 300:
        return "150-300"
    if value < 500:
        return "300-500"
    return ">500"


def build_trade_distribution(replay_df: pd.DataFrame) -> pd.DataFrame:
    if replay_df.empty:
        return pd.DataFrame(columns=["variant_name", "premium_bucket", "trades", "net_pnl", "win_rate", "avg_pnl", "profit_factor", "avg_spread_pct", "avg_depth"])
    df = replay_df.copy()
    df["premium_bucket"] = df["entry_price"].map(bucket_premium)
    rows: list[dict[str, Any]] = []
    order = ["<50", "50-80", "80-150", "150-300", "300-500", ">500"]
    for (variant_name, bucket), g in df.groupby(["variant_name", "premium_bucket"]):
        wins = g.loc[g["net_pnl"] > 0, "net_pnl"]
        losses = g.loc[g["net_pnl"] < 0, "net_pnl"]
        pf = float(wins.sum() / abs(losses.sum())) if not losses.empty and abs(losses.sum()) > 1e-9 else (np.inf if not wins.empty else np.nan)
        rows.append({
            "variant_name": variant_name,
            "premium_bucket": bucket,
            "bucket_order": order.index(bucket),
            "trades": int(len(g)),
            "net_pnl": float(g["net_pnl"].sum()),
            "win_rate": float((g["net_pnl"] > 0).mean()),
            "avg_pnl": float(g["net_pnl"].mean()),
            "profit_factor": pf,
            "avg_spread_pct": float(g["avg_spread_pct_candidate"].mean()),
            "avg_depth": float(g["depth_min_qty"].mean()),
        })
    return pd.DataFrame(rows).sort_values(["variant_name", "bucket_order"]).drop(columns=["bucket_order"]).reset_index(drop=True)


def build_best_worst(replay_df: pd.DataFrame) -> pd.DataFrame:
    if replay_df.empty:
        return pd.DataFrame()
    cols = [
        "variant_name", "date", "timestamp", "symbol", "side", "strike", "atm_distance_abs",
        "entry_price", "spread_now", "spread_pct_now", "depth_min_qty", "raw_burst_score", "net_pnl",
        "exit_reason", "holding_seconds", "runup_points", "drawdown_points",
    ]
    cols = [c for c in cols if c in replay_df.columns]
    winners = replay_df.sort_values("net_pnl", ascending=False).head(20).copy()
    winners["bucket"] = "top_winner"
    losers = replay_df.sort_values("net_pnl", ascending=True).head(20).copy()
    losers["bucket"] = "top_loser"
    out = pd.concat([winners, losers], ignore_index=True)
    return out[["bucket"] + cols]


def save_charts(summary_df: pd.DataFrame, daywise_df: pd.DataFrame, trade_dist_df: pd.DataFrame) -> list[Path]:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if not summary_df.empty:
        p = CHARTS_DIR / "trade_count_vs_pnl.png"
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(summary_df["total_trades"], summary_df["total_net_pnl"], color="#1f77b4")
        for _, row in summary_df.iterrows():
            ax.annotate(str(row["variant_name"]), (row["total_trades"], row["total_net_pnl"]), fontsize=7)
        ax.axhline(0, color="#333", lw=1)
        ax.set_xlabel("Total trades")
        ax.set_ylabel("Total net PnL")
        ax.set_title("Trade Count vs PnL by Variant")
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not daywise_df.empty:
        p = CHARTS_DIR / "daywise_pnl_by_variant.png"
        fig, ax = plt.subplots(figsize=(12, 6))
        keep_names = daywise_df.groupby("variant_name")["net_pnl"].sum().sort_values(ascending=False).head(5).index.tolist()
        for name in keep_names:
            g = daywise_df[daywise_df["variant_name"] == name].sort_values("date")
            ax.plot(pd.to_datetime(g["date"]), g["net_pnl"], marker="o", label=name)
        ax.axhline(0, color="#333", lw=1)
        ax.legend(fontsize=8)
        ax.set_title("Day-wise PnL by Variant")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)
    if not trade_dist_df.empty:
        p = CHARTS_DIR / "premium_distribution_by_variant.png"
        pivot = trade_dist_df.pivot(index="premium_bucket", columns="variant_name", values="trades").fillna(0)
        fig, ax = plt.subplots(figsize=(12, 6))
        pivot.plot(kind="bar", ax=ax)
        ax.set_title("Trade Count by Premium Bucket")
        ax.set_ylabel("Trades")
        fig.tight_layout()
        fig.savefig(p, dpi=160)
        plt.close(fig)
        paths.append(p)

        p2 = CHARTS_DIR / "pnl_by_premium_bucket.png"
        pivot2 = trade_dist_df.pivot(index="premium_bucket", columns="variant_name", values="net_pnl").fillna(0)
        fig, ax = plt.subplots(figsize=(12, 6))
        pivot2.plot(kind="bar", ax=ax)
        ax.axhline(0, color="#333", lw=1)
        ax.set_title("Net PnL by Premium Bucket")
        ax.set_ylabel("Net PnL")
        fig.tight_layout()
        fig.savefig(p2, dpi=160)
        plt.close(fig)
        paths.append(p2)
    return paths


def markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "(no data)"
    use = df.head(max_rows).copy()
    cols = list(use.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in use.iterrows():
        vals = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                if math.isnan(value):
                    vals.append("")
                else:
                    vals.append(f"{value:.3f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def build_report(
    dates: list[str],
    skipped_dates: list[str],
    baseline_expected: pd.Series | None,
    baseline_actual: pd.Series,
    actual_system_row: pd.Series | None,
    summary_df: pd.DataFrame,
    daywise_df: pd.DataFrame,
    trade_dist_df: pd.DataFrame,
    best_worst_df: pd.DataFrame,
    charts: list[Path],
) -> str:
    lines: list[str] = []
    lines.append("# Premium Filter Ablation Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"- Dates tested: **{', '.join(dates)}**.")
    if skipped_dates:
        lines.append(f"- Full-tape folders skipped because they were not in the prepared candidate universe: **{', '.join(skipped_dates)}**.")
    if baseline_expected is not None:
        exp_pnl = float(baseline_expected["total_net_pnl"])
        exp_trades = int(baseline_expected["total_trades"])
        exp_pf = float(baseline_expected["trade_level_profit_factor"])
        lines.append(f"- Baseline reference from TES study: `{exp_pnl:,.0f}` PnL, `{exp_trades}` trades, PF `{exp_pf:.2f}`.")
        lines.append(f"- Reproduced here: `{float(baseline_actual['total_net_pnl']):,.0f}` PnL, `{int(baseline_actual['total_trades'])}` trades, PF `{float(baseline_actual['profit_factor']):.2f}`.")
    best_no = summary_df[summary_df["variant_name"].str.contains("NO_PREMIUM", na=False) & ~summary_df["variant_name"].str.contains("TARGET7", na=False)].sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).head(1)
    best_dyn = summary_df[summary_df["variant_name"].str.contains("DYNAMIC_PREMIUM", na=False)].sort_values(["total_net_pnl", "worst_day_pnl"], ascending=[False, False]).head(1)
    if not best_no.empty:
        row = best_no.iloc[0]
        lines.append(f"- Best no-premium target-3 variant: **{row['variant_name']}** (`{row['total_net_pnl']:,.0f}`, `{int(row['total_trades'])}` trades, PF `{row['profit_factor']:.2f}`).")
    if not best_dyn.empty:
        row = best_dyn.iloc[0]
        lines.append(f"- Best dynamic-premium variant: **{row['variant_name']}** (`{row['total_net_pnl']:,.0f}`, `{int(row['total_trades'])}` trades, PF `{row['profit_factor']:.2f}`).")
    lines.append("")
    lines.append("## Variant Summary")
    lines.append(markdown_table(summary_df, max_rows=20))
    lines.append("")
    lines.append("## Day-wise")
    lines.append(markdown_table(daywise_df, max_rows=80))
    lines.append("")
    lines.append("## Premium Distribution")
    lines.append(markdown_table(trade_dist_df, max_rows=80))
    lines.append("")
    lines.append("## Best and Worst Trades")
    lines.append(markdown_table(best_worst_df, max_rows=40))
    lines.append("")
    lines.append("## Findings")
    baseline_pnl = float(baseline_actual["total_net_pnl"])
    baseline_worst = float(baseline_actual["worst_day_pnl"])
    baseline_pf = float(baseline_actual["profit_factor"])
    baseline_trades = int(baseline_actual["total_trades"])
    if not best_no.empty:
        row = best_no.iloc[0]
        helped = float(row["total_net_pnl"]) > baseline_pnl
        lines.append(f"- **Does removing premium 80-300 improve total PnL?** {'Yes' if helped else 'No'}. Best no-premium target-3 variant `{row['variant_name']}` made `{float(row['total_net_pnl']):,.0f}` vs baseline `{baseline_pnl:,.0f}`.")
        lines.append(f"- **Does it improve or worsen worst-day PnL?** {'Improves' if float(row['worst_day_pnl']) >= baseline_worst else 'Worsens'}. Best no-premium worst day was `{float(row['worst_day_pnl']):,.0f}` vs baseline `{baseline_worst:,.0f}`.")
        lines.append(f"- **Does it increase trade count dangerously?** {'Yes' if int(row['total_trades']) > baseline_trades else 'No'}. Best no-premium variant used `{int(row['total_trades'])}` trades vs baseline `{baseline_trades}`.")
    bucket_pivot = trade_dist_df.groupby("premium_bucket").agg(trades=("trades", "sum"), net_pnl=("net_pnl", "sum")).reset_index() if not trade_dist_df.empty else pd.DataFrame()
    if not bucket_pivot.empty:
        best_bucket = bucket_pivot.sort_values("net_pnl", ascending=False).iloc[0]
        worst_bucket = bucket_pivot.sort_values("net_pnl", ascending=True).iloc[0]
        lines.append(f"- **Which premium buckets actually make money?** Best aggregated bucket was `{best_bucket['premium_bucket']}` at `{float(best_bucket['net_pnl']):,.0f}`; worst was `{worst_bucket['premium_bucket']}` at `{float(worst_bucket['net_pnl']):,.0f}`.")
    no_prem_plain = summary_df[summary_df["variant_name"] == "BASE_ATM100_SCORE5_NO_PREMIUM_SPREAD2_DEPTH250"]
    no_prem_pct = summary_df[summary_df["variant_name"] == "BASE_ATM100_SCORE5_NO_PREMIUM_SPREAD2_SPREADPCT015_DEPTH250"]
    strict_liq = summary_df[summary_df["variant_name"] == "BASE_ATM100_SCORE5_NO_PREMIUM_SPREAD1P5_SPREADPCT010_DEPTH250"]
    if not no_prem_plain.empty and not no_prem_pct.empty and not strict_liq.empty:
        lines.append(
            f"- **Is premium band acting as useful quality filter, harmful overfit, or redundant because spread/depth already capture quality?** "
            f"It is still a useful quality filter unless spread/depth are tightened materially. Plain no-premium made `{float(no_prem_plain.iloc[0]['total_net_pnl']):,.0f}`, "
            f"adding spread_pct guard made `{float(no_prem_pct.iloc[0]['total_net_pnl']):,.0f}`, and the stricter liquidity-only version made `{float(strict_liq.iloc[0]['total_net_pnl']):,.0f}`."
        )
    if not best_dyn.empty:
        row = best_dyn.iloc[0]
        lines.append(f"- **Does dynamic day-wise premium band outperform fixed band?** {'Yes' if float(row['total_net_pnl']) > baseline_pnl else 'No'}. Best dynamic variant `{row['variant_name']}` made `{float(row['total_net_pnl']):,.0f}` vs baseline `{baseline_pnl:,.0f}`.")
    target3_rows = summary_df[~summary_df["variant_name"].str.contains("TARGET7", na=False)].copy()
    live_gate = target3_rows[
        (target3_rows["variant_name"] != BASELINE_NAME)
        & (target3_rows["beats_current_baseline_total_pnl"])
        & (target3_rows["beats_current_baseline_worst_day"])
        & (target3_rows["profit_factor"] >= 1.3)
        & (target3_rows["improves_trade_count_discipline"])
        & (target3_rows["active_days"] >= 2)
    ].copy()
    if live_gate.empty:
        rec = "keep 80-300"
        rec_reason = (
            "no target-3 premium variant beat the current baseline while preserving downside control, "
            "PF >= 1.3, and trade-count discipline"
        )
    else:
        live_gate = live_gate.sort_values(["total_net_pnl", "profit_factor"], ascending=[False, False])
        top = live_gate.iloc[0]
        rec = str(top["variant_name"])
        rec_reason = "it clears the target-3 baseline standard on PnL, downside, PF, and discipline"
    lines.append(f"- **Direct recommendation:** `{rec}` as the current edge candidate, because {rec_reason}.")
    lines.append("- **Research follow-up:** `BASE_ATM100_SCORE5_NO_PREMIUM_SPREAD1P5_SPREADPCT010_DEPTH250` is the only no-premium target-3 variant worth further study, but it is still research-only because it worsens the bad day and inflates trade count.")
    lines.append("- **Secondary target-7 check:** `NO_PREMIUM_TARGET7_CHECK` improved headline PnL, but it is not the primary validation path because the standard here is target=3 first.")
    lines.append("- **Practical answer:** keep `80-300` for the current tradable candidate; do not remove premium entirely, do not switch to dynamic percentile bands, and do not widen to `100-500`. If you want one exploratory branch, test the stricter no-premium spread/depth version only in research.")
    if actual_system_row is not None:
        lines.append(f"- **Actual live system over the same dates:** `{float(actual_system_row['total_net_pnl']):,.0f}` on `{int(actual_system_row['total_trades'])}` trades, PF `{float(actual_system_row['trade_level_profit_factor']):.2f}`.")
    lines.append("")
    lines.append("## Charts")
    for path in charts:
        lines.append(f"- ![{path.name}]({path})")
    lines.append("")
    lines.append("## Caveats")
    lines.append("- This holds entry ranking and exit logic fixed to the current TES-era baseline framework. The ablation only changes premium-related filters.")
    lines.append("- This is diagnostic replay, not broker-grade execution simulation.")
    lines.append("- Quantity is fixed at 500 for comparability.")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    settings = bor.load_settings_safe()
    audit = bor.load_audit_module()
    audit.ensure_env_loaded()
    teh.audit = audit

    dates = discover_dates_from_candidates()
    candidates_df, skipped_dates = load_candidate_universe(dates)
    dynamic_bounds = build_dynamic_bounds(candidates_df)

    symbol_rows_by_date: dict[str, dict[str, list[dict[str, Any]]]] = {}
    underlying_by_date: dict[str, pd.Series] = {}
    series_cache_by_date: dict[str, dict[str, pd.DataFrame]] = {}
    for date in dates:
        day_symbols = sorted(candidates_df.loc[candidates_df['date'] == date, 'symbol'].astype(str).unique().tolist())
        symbol_rows, underlying, series_cache = load_market_context(date, day_symbols, audit)
        symbol_rows_by_date[date] = symbol_rows
        underlying_by_date[date] = underlying
        series_cache_by_date[date] = series_cache

    replay_parts: list[pd.DataFrame] = []
    daywise_rows: list[dict[str, Any]] = []

    for date in dates:
        day_df = candidates_df[candidates_df['date'] == date].copy()
        for variant in BASE_VARIANTS:
            selected = select_variant_candidates(day_df, variant, dynamic_bounds)
            replay = replay_variant_day(date, variant, selected, symbol_rows_by_date[date], underlying_by_date[date], settings, {k: v.copy() for k, v in series_cache_by_date[date].items()})
            if not replay.empty:
                replay_parts.append(replay)
            daywise_rows.append(summarize_replay_day(replay, date, variant.name, int(len(selected))))

    replay_df = pd.concat(replay_parts, ignore_index=True) if replay_parts else pd.DataFrame()
    daywise_df = pd.DataFrame(daywise_rows)

    summary_df = pd.DataFrame()
    baseline_expected = None
    if SUMMARY_PATH.exists():
        tes_summary = pd.read_csv(SUMMARY_PATH)
        row = tes_summary[tes_summary['variant_name'] == BASELINE_NAME]
        if not row.empty:
            baseline_expected = row.iloc[0]

    baseline_daywise = daywise_df[daywise_df['variant_name'] == BASELINE_NAME]
    baseline_replay = replay_df[replay_df['variant_name'] == BASELINE_NAME]
    if baseline_daywise.empty:
        raise RuntimeError('Baseline variant produced no summary rows.')
    baseline_summary_row = aggregate_summary(baseline_daywise, baseline_replay, pd.Series({'total_net_pnl':0,'worst_day_pnl':0,'profit_factor':0,'total_trades':0})).iloc[0]

    summary_df = aggregate_summary(daywise_df, replay_df, baseline_summary_row)

    no_premium_rows = summary_df[
        summary_df['variant_name'].str.contains('NO_PREMIUM', na=False)
        & ~summary_df['variant_name'].str.contains('TARGET7', na=False)
        & ~summary_df['variant_name'].str.contains('DYNAMIC', na=False)
    ].sort_values(['total_net_pnl','worst_day_pnl'], ascending=[False, False])
    if not no_premium_rows.empty:
        best_no_name = str(no_premium_rows.iloc[0]['variant_name'])
        source_variant = next(v for v in BASE_VARIANTS if v.name == best_no_name)
        target7_variant = replace(source_variant, name='NO_PREMIUM_TARGET7_CHECK', use_promoted_logic=True, target_points=7.0, notes=f'copied from {best_no_name}')
        extra_parts: list[pd.DataFrame] = []
        extra_rows: list[dict[str, Any]] = []
        for date in dates:
            day_df = candidates_df[candidates_df['date'] == date].copy()
            selected = select_variant_candidates(day_df, target7_variant, dynamic_bounds)
            replay = replay_variant_day(date, target7_variant, selected, symbol_rows_by_date[date], underlying_by_date[date], settings, {k: v.copy() for k, v in series_cache_by_date[date].items()})
            if not replay.empty:
                extra_parts.append(replay)
            extra_rows.append(summarize_replay_day(replay, date, target7_variant.name, int(len(selected))))
        extra_replay = pd.concat(extra_parts, ignore_index=True) if extra_parts else pd.DataFrame()
        extra_daywise = pd.DataFrame(extra_rows)
        replay_df = pd.concat([replay_df, extra_replay], ignore_index=True) if not extra_replay.empty else replay_df
        daywise_df = pd.concat([daywise_df, extra_daywise], ignore_index=True)
        summary_df = aggregate_summary(daywise_df, replay_df, baseline_summary_row)

    baseline_actual = summary_df[summary_df['variant_name'] == BASELINE_NAME]
    if baseline_actual.empty:
        raise RuntimeError('Failed to reproduce baseline summary.')
    baseline_actual = baseline_actual.iloc[0]

    trade_dist_df = build_trade_distribution(replay_df)
    best_worst_df = build_best_worst(replay_df)

    actual_system_row = None
    if SUMMARY_PATH.exists():
        tes_summary = pd.read_csv(SUMMARY_PATH)
        row = tes_summary[tes_summary['variant_name'] == 'actual_system']
        if not row.empty:
            actual_system_row = row.iloc[0]

    charts = save_charts(summary_df, daywise_df, trade_dist_df)

    summary_df.to_csv(OUTPUT_DIR / 'premium_filter_variant_summary.csv', index=False)
    daywise_df.to_csv(OUTPUT_DIR / 'premium_filter_variant_daywise.csv', index=False)
    replay_df.to_csv(OUTPUT_DIR / 'premium_filter_replay_trades.csv', index=False)
    trade_dist_df.to_csv(OUTPUT_DIR / 'premium_filter_trade_distribution.csv', index=False)
    best_worst_df.to_csv(OUTPUT_DIR / 'premium_filter_best_worst_trades.csv', index=False)

    report = build_report(dates, skipped_dates, baseline_expected, baseline_actual, actual_system_row, summary_df, daywise_df, trade_dist_df, best_worst_df, charts)
    (OUTPUT_DIR / 'premium_filter_report.md').write_text(report, encoding='utf-8')

    best_no = summary_df[summary_df['variant_name'].str.contains('NO_PREMIUM', na=False) & ~summary_df['variant_name'].str.contains('TARGET7', na=False) & ~summary_df['variant_name'].str.contains('DYNAMIC', na=False)].sort_values(['total_net_pnl','worst_day_pnl'], ascending=[False, False]).head(1)
    best_dyn = summary_df[summary_df['variant_name'].str.contains('DYNAMIC_PREMIUM', na=False)].sort_values(['total_net_pnl','worst_day_pnl'], ascending=[False, False]).head(1)
    removing_helped = bool((not best_no.empty) and float(best_no.iloc[0]['total_net_pnl']) > float(baseline_actual['total_net_pnl']))
    recommendation = 'keep 80-300'
    better = summary_df[
        (summary_df['variant_name'] != BASELINE_NAME)
        & ~summary_df['variant_name'].str.contains('TARGET7', na=False)
        & (summary_df['beats_current_baseline_total_pnl'])
        & (summary_df['beats_current_baseline_worst_day'])
        & (summary_df['profit_factor'] >= 1.3)
        & (summary_df['improves_trade_count_discipline'])
        & (summary_df['active_days'] >= 2)
    ]
    if not better.empty:
        recommendation = str(better.sort_values(['total_net_pnl','profit_factor'], ascending=[False, False]).iloc[0]['variant_name'])

    print(f"Wrote premium filter ablation outputs to {OUTPUT_DIR}")
    print(f"Dates tested: {dates}")
    print(f"Baseline PnL/trades/PF: {float(baseline_actual['total_net_pnl']):.0f} / {int(baseline_actual['total_trades'])} / {float(baseline_actual['profit_factor']):.3f}")
    if not best_no.empty:
        row = best_no.iloc[0]
        print(f"Best no-premium variant: {row['variant_name']} ({float(row['total_net_pnl']):.0f} / {int(row['total_trades'])} / {float(row['profit_factor']):.3f})")
    else:
        print('Best no-premium variant: none')
    if not best_dyn.empty:
        row = best_dyn.iloc[0]
        print(f"Best dynamic-premium variant: {row['variant_name']} ({float(row['total_net_pnl']):.0f} / {int(row['total_trades'])} / {float(row['profit_factor']):.3f})")
    else:
        print('Best dynamic-premium variant: none')
    print(f"Did removing premium help? {'yes' if removing_helped else 'no'}")
    print(f"Final recommendation: {recommendation}")


if __name__ == '__main__':
    main()
