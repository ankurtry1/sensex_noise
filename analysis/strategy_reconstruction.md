# Strategy Reconstruction

## Scope
This reconstruction is derived directly from runtime and strategy source code. It documents observed logic only; ambiguous behavior is explicitly marked.

## Plain-English Strategy
- Build 5-minute SENSEX candles from tick stream.
- Generate continuation/reversal triggers from previous candle color and live underlying LTP.
- Select option instrument via strike offsets around spot (call/put offset settings).
- Entry is market BUY; target SELL LIMIT is placed immediately.
- Open trade is monitored tick-by-tick for hard-stop, early-risk, path-risk, manual, target-hit, and post-1pm time-stop exits.
- Exit reason precedence determines which candidate is executed when multiple signals are true.

## Event-Driven Lifecycle
1. Signal generation: `StrategyEvaluator.evaluate` computes trigger hits from candle state and live underlying.  
   Source: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/strategy.py:26`
2. Entry planning: `EntryPlanner.build` resolves selected option token, in-memory quote availability, quantity, and target points.  
   Source: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/runtime/entry_planner.py:28`
3. Entry attempt commit: runtime marks candle attempted only after plan is ready, then executes market entry order.  
   Source: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/runtime/strategy_runtime.py:303`, `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/runtime/strategy_runtime.py:412`
4. Position tracking: per option tick, path features and checkpoints are updated (MFE/MAE/runup/drawdown/time-to-threshold).  
   Source: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/services/engine.py:606`
5. Exit candidate collection and selection: hard stop, early risk, path risk, manual, manual limit, target, and time-stop.  
   Source: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/services/engine.py:932`, `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/services/engine.py:32`, `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/runtime/exit_runtime.py:13`
6. Final exit execution: market exits for risk/manual/time-stop paths, direct close for target/manual-limit hits.

## Rule Reconstruction (Pseudo-Math)
Let `p_t` = option LTP at time t, `p_0` = entry price, `u_t` = underlying spot, and `τ` = seconds since entry.

Signal logic (from previous candle):
- If previous candle is GREEN:
  - Continuation CALL when `u_t >= prev_close + entry_buffer_points`.
  - Reversal PUT when `u_t <= prev_open - entry_buffer_points`.
- If previous candle is RED:
  - Continuation PUT when `u_t <= prev_close - entry_buffer_points`.
  - Reversal CALL when `u_t >= prev_open + entry_buffer_points`.

Exit candidate semantics:
- Hard stop: after arm-time, exit if `(p_t - p_0) <= -hard_stop_points`.
- Early risk: after early-risk checkpoint, exit when runup is weak and drawdown is sufficiently adverse (plus optional below-entry requirement).
- Path risk: after path-risk checkpoint, exit when current pnl is below threshold and runup remains weak.
- Target hit: exit when `p_t >= target_price`.
- Post-1pm time stop: for entries after 1pm, exit after configured holding duration.

## Default/Configured Knobs (from config parser)
- `TARGET_POINTS` default: `3`
- `ENTRY_BUFFER_POINTS` default: `5`
- `ENTRY_WINDOW_SECONDS` default: `40`
- `EARLY_RISK_EXIT_SECONDS` default: `10`
- `PATH_RISK_CHECK_SECONDS` default: `30`
- `HARD_STOP_POINTS` default: `8`
- `POST_1PM_TIME_STOP_SECONDS` default: `60`
- `CALL_OFFSET_POINTS` default: `-200`
- `PUT_OFFSET_POINTS` default: `200`
- Config source: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/config.py`

## Market Data / Execution Substrate
- Market data interface is `MarketDataService`, which prefers in-memory TickStore and raises explicit quote-unavailable errors when missing.
- Source: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/src/sensex_noise/services/market_data.py:12`
- Runtime is websocket-driven (`StrategyRuntime`) with queue-based tick ingestion.

## Ambiguities / Caveats
- Some behavior (e.g., target reprice edge cases, order-state nuances) depends on broker responses and runtime event timing.
- Legacy and day-wise logs may duplicate events; reconciliation layer must deduplicate by trade_id and latest close summary.