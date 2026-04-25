# Sensex Noise Paper/Live Trading Engine

Python engine for Sensex option signal execution with layered risk exits, websocket-first market data, structured event telemetry, and enriched ML-ready trade summaries.

## What This Repo Does

- Streams `BSE:SENSEX` and related instruments via Kite WebSocket.
- Builds 5-minute candle state and keeps the existing signal generation logic.
- Uses the candle signal as directional context, then applies a pre-entry microburst gate.
- Enters one options position at a time (paper or live broker mode).
- Applies layered exit policy (edge invalidation + hard stop + target + legacy risk layers + manual controls).
- Emits detailed JSONL event stream + enriched per-trade summaries.

## Strategy Summary

### Signal generation (unchanged core rule)

- Previous green candle:
  - continuation call trigger: `prev_close + ENTRY_BUFFER_POINTS`
  - reversal put trigger: `prev_open - ENTRY_BUFFER_POINTS`
- Previous red candle:
  - continuation put trigger: `prev_close - ENTRY_BUFFER_POINTS`
  - reversal call trigger: `prev_open + ENTRY_BUFFER_POINTS`

### Layered exit policy

Entry gate:

- Candle logic still decides direction/context only.
- A pre-entry microburst score is computed from the recent underlying + option tape.
- Entries require `MICROBURST_MIN_SCORE` or higher.
- score `3/4`: normal target (`NORMAL_TARGET_POINTS`, default `3`)
- score `>=5`: promoted target (`PROMOTED_TARGET_POINTS`, default `7`)

Exit precedence:

1. manual exit commands (`EXIT_NOW`)
2. catastrophic edge safety exits (`EDGE_HARD_STOP`, `STALE_QUOTE_FAILSAFE`)
3. edge invalidation / promoted-policy exits (`EARLY_FAIL_1S`, `EARLY_FAIL_3S`, `PROMOTED_FAIL_3S`, `PROMOTION_PERSISTENCE_FAIL`)
4. hard stop
5. manual limit hit
6. target hit
7. legacy early/path risk exits
8. time-stop after 1 PM

Policy details:

- Edge invalidation (fast edge kill):
  - 1-second soft invalidation: weak runup + non-positive pnl can force exit
  - normal trades keep the existing 3-second invalidation rule
  - promoted trades use stricter 3-second diagnostics:
    - `runup_3s >= 4.0`
    - `pnl_3s > 1.5`
    - `mae_3s > -3.5`
    - `velocity_2_3s >= 0.5 * velocity_0_1s`
  - promoted trades that pass 3s enter Layer 4 persistence:
    - first `+3.0` touch arms a 2-second window
    - they must reach `+4.5` inside that window or exit immediately
  - fail-safe hard stop (`EDGE_INVALIDATION_HARD_STOP_POINTS`) is evaluated continuously
  - optional stale quote fail-safe if `EDGE_INVALIDATION_KILL_ON_STALE_QUOTES=true`
  - legacy early/path-risk can be bypassed via `PREFER_EDGE_INVALIDATION_OVER_LEGACY_EARLY_RISK=true`
- Layer 0 hard stop:
  - arms only after `HARD_STOP_ARM_AFTER_SECONDS` from entry
  - normal trades: `-HARD_STOP_POINTS`
  - continuation call trades: `-CONTINUATION_CALL_HARD_STOP_POINTS`
- Layer 1 early-risk:
  - suspicion checkpoint at `EARLY_RISK_SUSPICION_SECONDS`
  - forced exit checkpoint at `EARLY_RISK_EXIT_SECONDS` with configured runup/drawdown/below-entry criteria
- Layer 2 path-risk:
  - checkpoint at `PATH_RISK_CHECK_SECONDS`
  - exit on configured pnl + runup criteria
- Dynamic risky target:
  - when trade becomes fragile, target can be reduced to `RISKY_TARGET_POINTS`
  - stricter post-1PM risky target supported via `STRICT_AFTER_1PM_RISKY_TARGET_POINTS`
  - live mode repricing prefers modify-order first, with safe cancel-replace fallback

## Logging Outputs

The engine now writes multiple logs in parallel:

- `TRADE_LOG_PATH`:
  - legacy-compatible JSONL event stream (kept for backward compatibility)
- `EVENT_LOG_PATH`:
  - preferred JSONL event stream for all detailed lifecycle/snapshot/risk events
- `ENRICHED_TRADE_LOG_PATH`:
  - one JSONL enriched summary record per closed trade (ML-friendly)
- `FEATURES_OUTPUT_PATH`:
  - default output path for offline feature export utility

### Hybrid tick logging

- Full-day raw tick logs are always written for:
  - `logs/ticks/YYYY-MM-DD/sensex.jsonl`
  - `logs/ticks/YYYY-MM-DD/futures.jsonl`
- Option raw full-day tape is controlled by `ENABLE_FULL_OPTION_TAPE_LOGGING`:
  - `false` (default): no full-day options tape
  - `true`: writes `logs/ticks/YYYY-MM-DD/options.jsonl`
- Trade-scoped option paths are always captured in:
  - `logs/trade_ticks/YYYY-MM-DD/<trade_id>.jsonl`
  - includes pre-entry (5s), in-trade, post-exit (15s)

### Important emitted events

Includes (non-exhaustive):

- `SIGNAL_GENERATED`
- `ENTRY_CONTEXT`
- `MICROBURST_FEATURES_COMPUTED`
- `ENTRY_BLOCKED_MICROBURST_GATE`, `ENTRY_ALLOWED_MICROBURST_GATE`
- `ENTRY_ORDER_SENT`, `ENTRY_ORDER_ACKED`, `ENTRY_FILLED`
- `TRADE_SNAPSHOT`
- `EDGE_INVALIDATION_STATE_UPDATE`
- `EDGE_INVALIDATION_CHECK_1S_PASS`, `EDGE_INVALIDATION_CHECK_1S_FAIL`
- `EDGE_INVALIDATION_CHECK_3S_PASS`, `EDGE_INVALIDATION_CHECK_3S_FAIL`
- `PROMOTED_3S_PASS`, `PROMOTED_3S_FAIL`
- `PROMOTION_ARMED_AT_3PTS`, `PROMOTION_PERSISTENCE_PASS`, `PROMOTION_PERSISTENCE_FAIL`
- `EDGE_INVALIDATION_HARD_STOP`
- `EDGE_INVALIDATION_STALE_QUOTE`
- `EDGE_INVALIDATION_EXIT_REQUESTED`
- `EARLY_RISK_SUSPECTED`, `EARLY_RISK_EXIT`
- `PATH_RISK_EXIT`
- `HARD_STOP_EXIT`
- `TARGET_PLACED`, `TARGET_REPRICED`, `TARGET_HIT`
- `TARGET_REPRICE_ATTEMPT`, `TARGET_REPRICE_MODIFY_SUCCESS`, `TARGET_REPRICE_MODIFY_FAILED`
- `TARGET_REPRICE_CANCEL_REPLACE_SUCCESS`, `TARGET_REPRICE_CANCEL_REPLACE_FAILED`
- `MANUAL_EXIT`, `MANUAL_LIMIT_HIT`
- `TIME_STOP_AFTER_1PM`
- `EXIT_ORDER_SENT`, `EXIT_ORDER_ACKED`, `EXIT_FILLED`
- `EXIT_DECISION_SELECTED`, `EXIT_EXECUTION_FAILED`
- `POST_EXIT_OBSERVATION`, `POST_EXIT_OBSERVATION_ERROR`, `POST_EXIT_OBSERVATION_COMPLETED`
- optional `POST_EXIT_COUNTERFACTUAL`
- `TRADE_CLOSED_SUMMARY`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Fill Kite credentials in `.env`.

## Core Environment Variables

See `.env.example` for the full list. Key groups:

- runtime:
  - `TRADING_MODE=paper|live`
  - `POLL_INTERVAL_SECONDS`, `TRADE_QTY`, `ORDER_PRODUCT`
- baseline strategy:
  - `TARGET_POINTS`, `ENTRY_BUFFER_POINTS`
  - `SESSION_SQUARE_OFF_ENABLED`, `SESSION_SQUARE_OFF_TIME` (absolute close, e.g. `15:15`)
- layered risk:
  - `ENABLE_MICROBURST_GATE`, `MICROBURST_*`
  - `NORMAL_TARGET_POINTS`, `PROMOTED_*`
  - `LAYER4_*`
  - `ENABLE_EDGE_INVALIDATION`
  - `EDGE_INVALIDATION_1S_*`, `EDGE_INVALIDATION_3S_*`
  - `EDGE_INVALIDATION_HARD_STOP_*`
  - `EDGE_INVALIDATION_STALE_QUOTE_*`
  - `PREFER_EDGE_INVALIDATION_OVER_LEGACY_EARLY_RISK`
  - `ENABLE_HARD_STOP`, `HARD_STOP_ARM_AFTER_SECONDS`, `HARD_STOP_POINTS`, `CONTINUATION_CALL_HARD_STOP_POINTS`
  - `ENABLE_EARLY_RISK`, `EARLY_RISK_*`
  - `ENABLE_PATH_RISK`, `PATH_RISK_*`
  - `ENABLE_DYNAMIC_RISKY_TARGET`, `RISKY_TARGET_POINTS`, `STRICT_AFTER_1PM_RISKY_TARGET_POINTS`
- telemetry:
  - `ENABLE_SIGNAL_LOGGING`, `ENABLE_ENTRY_CONTEXT_LOGGING`, `ENABLE_SNAPSHOT_LOGGING`
  - `SNAPSHOT_SECONDS` (comma-separated; parsed and sorted)
  - `ENABLE_POST_EXIT_OBSERVATION`, `POST_EXIT_OBSERVATION_SECONDS`, `POST_EXIT_OBSERVATION_INTERVAL_SECONDS`
  - `ENABLE_EXIT_DECISION_LOGGING`, `ENABLE_SLIPPAGE_LOGGING`
- target repricing execution controls:
  - `ENABLE_TARGET_REPRICE_MODIFY`
  - `ENABLE_TARGET_REPRICE_FALLBACK_CANCEL_REPLACE`
  - `TARGET_REPRICE_DEBOUNCE_SECONDS`
- websocket/runtime hardening:
  - `ENABLE_FULL_OPTION_TAPE_LOGGING`
  - `STREAM_WATCHDOG_MAX_IDLE_SECONDS`
  - `WATCHDOG_HARD_RECONNECT_SECONDS`
  - `STREAM_RECONNECT_COOLDOWN_SECONDS`
  - `STREAM_CONNECT_TIMEOUT_SECONDS`
  - `STREAM_FIRST_TICK_TIMEOUT_SECONDS`
  - `HEARTBEAT_LOG_INTERVAL_SECONDS`
  - `REBASE_PERSIST_TICKS`
  - `REBASE_COOLDOWN_SECONDS`
  - `REBASE_MIN_MOVE_POINTS`
  - `CRITICAL_TICK_QUEUE_MAXSIZE`
  - `BACKGROUND_TICK_QUEUE_MAXSIZE`
  - `JOURNAL_QUEUE_MAXSIZE`
  - `JOURNAL_FLUSH_INTERVAL_SECONDS`

## Run

```bash
python3 run.py
```

## Runtime Manual Control

Control file path is `CONTROL_PATH` (default `runtime/control.json`).

Supported actions:

- immediate market exit:

```json
{"action": "EXIT_NOW"}
```

- replace manual limit exit:

```json
{"action": "EXIT_LIMIT", "price": 123.45}
```

## Build Flat Feature CSV From Enriched Trades

Utility script:

```bash
python3 analysis/feature_builder.py --input logs/trades_enriched.jsonl --output logs/features_daily.csv
```

## Notes on Quote Depth

- Paper mode uses Kite `ltp()` fallback and logs `bid/ask/spread` as `None`.
- Live mode attempts `quote()` depth; when unavailable, it safely falls back to `ltp()` and still logs a consistent quote object with nullable depth fields.
- Live target-order repricing relies on Kite order status visibility (`orders()` / `order_history`) to confirm modifiability and reconciliation before trusting modify success.
