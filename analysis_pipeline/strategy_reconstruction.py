from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _line_no_for_pattern(path: Path, pattern: str) -> int | None:
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            return i
    return None


def _extract_settings_defaults(config_path: Path, keys: list[str]) -> dict[str, str]:
    text = config_path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for key in keys:
        m = re.search(rf"{re.escape(key)}\", \"([^\"]+)\"", text)
        if m:
            out[key] = m.group(1)
    return out


def reconstruct_strategy(repo_root: Path) -> str:
    strategy_path = repo_root / "src/sensex_noise/strategy.py"
    runtime_path = repo_root / "src/sensex_noise/runtime/strategy_runtime.py"
    entry_path = repo_root / "src/sensex_noise/runtime/entry_planner.py"
    exit_runtime_path = repo_root / "src/sensex_noise/runtime/exit_runtime.py"
    engine_path = repo_root / "src/sensex_noise/services/engine.py"
    market_data_path = repo_root / "src/sensex_noise/services/market_data.py"
    config_path = repo_root / "src/sensex_noise/config.py"

    defaults = _extract_settings_defaults(
        config_path,
        [
            "TARGET_POINTS",
            "ENTRY_BUFFER_POINTS",
            "ENTRY_WINDOW_SECONDS",
            "EARLY_RISK_EXIT_SECONDS",
            "PATH_RISK_CHECK_SECONDS",
            "HARD_STOP_POINTS",
            "POST_1PM_TIME_STOP_SECONDS",
            "CALL_OFFSET_POINTS",
            "PUT_OFFSET_POINTS",
        ],
    )

    refs: dict[str, tuple[Path, int | None]] = {
        "signal_eval": (strategy_path, _line_no_for_pattern(strategy_path, "def evaluate")),
        "entry_plan": (entry_path, _line_no_for_pattern(entry_path, "def build")),
        "entry_attempt": (runtime_path, _line_no_for_pattern(runtime_path, "def _maybe_attempt_entry")),
        "entry_execute": (runtime_path, _line_no_for_pattern(runtime_path, "def _execute_entry_plan")),
        "path_features": (engine_path, _line_no_for_pattern(engine_path, "def _update_path_features")),
        "early_exit": (engine_path, _line_no_for_pattern(engine_path, "def _should_early_exit")),
        "path_exit": (engine_path, _line_no_for_pattern(engine_path, "def _should_path_exit")),
        "hard_stop": (engine_path, _line_no_for_pattern(engine_path, "def _should_hard_stop")),
        "exit_candidates": (engine_path, _line_no_for_pattern(engine_path, "def _collect_exit_candidates")),
        "exit_precedence": (engine_path, _line_no_for_pattern(engine_path, "EXIT_REASON_PRECEDENCE")),
        "exit_runtime": (exit_runtime_path, _line_no_for_pattern(exit_runtime_path, "def evaluate_and_execute")),
        "mkt_data": (market_data_path, _line_no_for_pattern(market_data_path, "class MarketDataService")),
    }

    def ref_link(key: str) -> str:
        path, line = refs[key]
        if line is None:
            return f"{path}"
        return f"{path}:{line}"

    md = []
    md.append("# Strategy Reconstruction")
    md.append("")
    md.append("## Scope")
    md.append("This reconstruction is derived directly from runtime and strategy source code. It documents observed logic only; ambiguous behavior is explicitly marked.")
    md.append("")
    md.append("## Plain-English Strategy")
    md.append("- Build 5-minute SENSEX candles from tick stream.")
    md.append("- Generate continuation/reversal triggers from previous candle color and live underlying LTP.")
    md.append("- Select option instrument via strike offsets around spot (call/put offset settings).")
    md.append("- Entry is market BUY; target SELL LIMIT is placed immediately.")
    md.append("- Open trade is monitored tick-by-tick for hard-stop, early-risk, path-risk, manual, target-hit, and post-1pm time-stop exits.")
    md.append("- Exit reason precedence determines which candidate is executed when multiple signals are true.")
    md.append("")

    md.append("## Event-Driven Lifecycle")
    md.append("1. Signal generation: `StrategyEvaluator.evaluate` computes trigger hits from candle state and live underlying.  ")
    md.append(f"   Source: `{ref_link('signal_eval')}`")
    md.append("2. Entry planning: `EntryPlanner.build` resolves selected option token, in-memory quote availability, quantity, and target points.  ")
    md.append(f"   Source: `{ref_link('entry_plan')}`")
    md.append("3. Entry attempt commit: runtime marks candle attempted only after plan is ready, then executes market entry order.  ")
    md.append(f"   Source: `{ref_link('entry_attempt')}`, `{ref_link('entry_execute')}`")
    md.append("4. Position tracking: per option tick, path features and checkpoints are updated (MFE/MAE/runup/drawdown/time-to-threshold).  ")
    md.append(f"   Source: `{ref_link('path_features')}`")
    md.append("5. Exit candidate collection and selection: hard stop, early risk, path risk, manual, manual limit, target, and time-stop.  ")
    md.append(f"   Source: `{ref_link('exit_candidates')}`, `{ref_link('exit_precedence')}`, `{ref_link('exit_runtime')}`")
    md.append("6. Final exit execution: market exits for risk/manual/time-stop paths, direct close for target/manual-limit hits.")
    md.append("")

    md.append("## Rule Reconstruction (Pseudo-Math)")
    md.append("Let `p_t` = option LTP at time t, `p_0` = entry price, `u_t` = underlying spot, and `τ` = seconds since entry.")
    md.append("")
    md.append("Signal logic (from previous candle):")
    md.append("- If previous candle is GREEN:")
    md.append("  - Continuation CALL when `u_t >= prev_close + entry_buffer_points`.")
    md.append("  - Reversal PUT when `u_t <= prev_open - entry_buffer_points`.")
    md.append("- If previous candle is RED:")
    md.append("  - Continuation PUT when `u_t <= prev_close - entry_buffer_points`.")
    md.append("  - Reversal CALL when `u_t >= prev_open + entry_buffer_points`.")
    md.append("")
    md.append("Exit candidate semantics:")
    md.append("- Hard stop: after arm-time, exit if `(p_t - p_0) <= -hard_stop_points`.")
    md.append("- Early risk: after early-risk checkpoint, exit when runup is weak and drawdown is sufficiently adverse (plus optional below-entry requirement).")
    md.append("- Path risk: after path-risk checkpoint, exit when current pnl is below threshold and runup remains weak.")
    md.append("- Target hit: exit when `p_t >= target_price`.")
    md.append("- Post-1pm time stop: for entries after 1pm, exit after configured holding duration.")
    md.append("")

    md.append("## Default/Configured Knobs (from config parser)")
    for k, v in defaults.items():
        md.append(f"- `{k}` default: `{v}`")
    md.append(f"- Config source: `{config_path}`")
    md.append("")

    md.append("## Market Data / Execution Substrate")
    md.append("- Market data interface is `MarketDataService`, which prefers in-memory TickStore and raises explicit quote-unavailable errors when missing.")
    md.append(f"- Source: `{ref_link('mkt_data')}`")
    md.append("- Runtime is websocket-driven (`StrategyRuntime`) with queue-based tick ingestion.")
    md.append("")

    md.append("## Ambiguities / Caveats")
    md.append("- Some behavior (e.g., target reprice edge cases, order-state nuances) depends on broker responses and runtime event timing.")
    md.append("- Legacy and day-wise logs may duplicate events; reconciliation layer must deduplicate by trade_id and latest close summary.")

    return "\n".join(md)


def write_strategy_reconstruction(repo_root: Path, out_path: Path) -> None:
    content = reconstruct_strategy(repo_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
