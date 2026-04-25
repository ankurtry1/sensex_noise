# Session Report (2026-04-22)

Analyzed date: **2026-04-22**

## Data Inputs Used
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trades/2026-04-22.trades_enriched.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trades/2026-04-22.trades.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/events/2026-04-22.events.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/ticks/2026-04-22/sensex.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/ticks/2026-04-22/futures.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trade_ticks/2026-04-22`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/runtime/control.json`

## 1. Executive Summary
- Trades: **46**
- Wins / Losses / Flat: **24 / 21 / 1**
- Gross PnL: **11975.00**
- Net PnL: **11975.00**
- Average Winner: **1391.67**
- Average Loser: **-1020.24**
- Largest Win: **4150.00**
- Largest Loss: **-3475.00**
- Hit Rate: **52.17%**
- Expectancy per Trade: **260.33**
- Day Pattern: **Positive expectancy driven by frequent target hits**

## 2. System Health / Runtime Summary
- STREAM_CONNECTED events: **1**
- Stream close events: **0**
- Reconnect-related events: **0**
- Watchdog-related events: **0**
- Stream degraded/recovered events: **0 / 0**
- Entry deferred (quote unavailable): **0**
- Lattice rebases: **133**
- Queue/backpressure explicit events: **0**
- Max runtime tick drops: **0**
- Max critical tick drops: **0**
- Max background tick drops: **0**
- Max journal drops: **0**
- Queue max sizes seen (critical/background/journal): **4 / 16 / 16**
- Inference trustworthiness: **True**
- Data-quality assessment: No drop/backpressure evidence and no degradation incidents in session telemetry; data quality appears reliable for behavioral inference.

## 3. Trade Ledger Table
| trade_id | entry_time | exit_time | holding_seconds | side | symbol | entry_price | exit_price | target_price | mfe | mae | net_pnl | exit_reason | exit_timing_assessment | target_nearly_reached | post_exit_best_delta | post_exit_final_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260422T092004|BFO:SENSEX2642379100PE|CONTINUATION_PUT|PUT | 09:20:04 | 09:20:05 | 0.52 | PUT | BFO:SENSEX2642379100PE | 546.40 | 549.40 | 549.40 | 3.45 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 3.15 | -5.95 |
| 20260422T092504|BFO:SENSEX2642379000PE|CONTINUATION_PUT|PUT | 09:25:04 | 09:25:04 | -0.15 | PUT | BFO:SENSEX2642379000PE | 503.70 | 506.70 | 506.70 | 5.30 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 9.05 | 9.00 |
| 20260422T093002|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 09:30:02 | 09:30:03 | 0.60 | PUT | BFO:SENSEX2642378900PE | 513.75 | 516.75 | 516.75 | 3.20 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 0.20 | -1.60 |
| 20260422T093501|BFO:SENSEX2642378600CE|CONTINUATION_CALL|CALL | 09:35:01 | 09:35:03 | 1.10 | CALL | BFO:SENSEX2642378600CE | 489.35 | 492.35 | 492.35 | 4.40 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 10.65 | 8.80 |
| 20260422T094000|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 09:40:00 | 09:40:01 | 0.21 | PUT | BFO:SENSEX2642378900PE | 509.35 | 516.35 | 516.35 | 9.35 | 0.00 | 3500.00 | TARGET_HIT | Captured target; additional upside remained | True | 15.35 | 4.85 |
| 20260422T094525|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 09:45:25 | 09:45:25 | -0.23 | PUT | BFO:SENSEX2642378900PE | 541.40 | 544.40 | 544.40 | 4.60 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 3.40 | -6.35 |
| 20260422T095508|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 09:55:08 | 09:55:11 | 2.75 | PUT | BFO:SENSEX2642378800PE | 512.90 | 515.90 | 515.90 | 8.10 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 8.10 | 8.10 |
| 20260422T100001|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT | 10:00:01 | 10:00:06 | 4.16 | PUT | BFO:SENSEX2642378700PE | 515.00 | 523.30 | 522.00 | 6.55 | -0.75 | 4150.00 | PROMOTED_FAIL_3S | Possibly early; post-exit recovery | True | 11.15 | 11.15 |
| 20260422T100516|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT | 10:05:17 | 10:05:22 | 4.94 | PUT | BFO:SENSEX2642378700PE | 526.45 | 525.80 | 529.45 | 2.65 | -0.65 | -325.00 | EARLY_FAIL_3S | Possibly early; post-exit recovery | True | 16.35 | 16.35 |
| 20260422T101015|BFO:SENSEX2642378400CE|REVERSAL_CALL|CALL | 10:10:15 | 10:10:19 | 3.94 | CALL | BFO:SENSEX2642378400CE | 478.00 | 478.85 | 481.00 | 2.85 | 0.00 | 425.00 | EARLY_FAIL_3S | Possibly early; post-exit recovery | True | 6.95 | 4.40 |
| 20260422T101509|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT | 10:15:09 | 10:15:12 | 2.69 | PUT | BFO:SENSEX2642378700PE | 531.75 | 531.65 | 534.75 | 0.00 | -0.25 | -50.00 | EARLY_FAIL_1S | Likely justified; weakness persisted | False | 2.60 | -13.45 |
| 20260422T102022|BFO:SENSEX2642378700PE|REVERSAL_PUT|PUT | 10:20:22 | 10:20:24 | 1.97 | PUT | BFO:SENSEX2642378700PE | 528.60 | 528.40 | 531.60 | 0.00 | -0.60 | -100.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 8.95 | 8.95 |
| 20260422T102514|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT | 10:25:14 | 10:25:19 | 5.36 | PUT | BFO:SENSEX2642378700PE | 548.00 | 548.25 | 555.00 | 4.90 | 0.00 | 125.00 | PROMOTED_FAIL_3S | Likely justified; weakness persisted | False | 1.75 | -3.75 |
| 20260422T103520|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 10:35:20 | 10:35:22 | 2.06 | CALL | BFO:SENSEX2642378400CE | 468.85 | 466.40 | 471.85 | 0.00 | -2.45 | -1225.00 | EARLY_FAIL_1S | Mixed / inconclusive timing | False | 2.00 | -0.80 |
| 20260422T104005|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 10:40:06 | 10:40:09 | 3.58 | CALL | BFO:SENSEX2642378400CE | 501.10 | 498.50 | 504.10 | 0.00 | -2.90 | -1300.00 | EARLY_FAIL_1S | Likely justified; weakness persisted | False | 2.60 | -5.40 |
| 20260422T105006|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL | 10:50:07 | 10:50:09 | 1.72 | CALL | BFO:SENSEX2642378500CE | 483.50 | 486.50 | 486.50 | 4.50 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 16.65 | 15.60 |
| 20260422T110016|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 11:00:16 | 11:00:18 | 2.50 | PUT | BFO:SENSEX2642378900PE | 498.35 | 498.05 | 501.35 | 0.25 | -1.35 | -150.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 3.25 | 3.25 |
| 20260422T110529|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 11:05:29 | 11:05:34 | 4.81 | PUT | BFO:SENSEX2642378900PE | 497.10 | 496.35 | 500.10 | 0.90 | -1.55 | -375.00 | EARLY_FAIL_3S | Possibly early; post-exit recovery | False | 6.75 | 3.85 |
| 20260422T111016|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 11:10:16 | 11:10:19 | 2.66 | PUT | BFO:SENSEX2642378900PE | 527.00 | 530.00 | 530.00 | 3.70 | -0.20 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 8.70 | 8.70 |
| 20260422T113006|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 11:30:06 | 11:30:10 | 4.09 | PUT | BFO:SENSEX2642378900PE | 477.90 | 477.90 | 480.90 | 2.10 | -0.35 | 0.00 | EARLY_FAIL_3S | Mixed / inconclusive timing | False | 0.80 | 0.05 |
| 20260422T114005|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 11:40:05 | 11:40:07 | 1.34 | PUT | BFO:SENSEX2642378900PE | 489.80 | 492.80 | 492.80 | 3.20 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 0.20 | -7.70 |
| 20260422T114501|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 11:45:02 | 11:45:03 | 0.88 | PUT | BFO:SENSEX2642378800PE | 471.10 | 474.10 | 474.10 | 3.15 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 0.15 | -0.25 |
| 20260422T115514|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 11:55:14 | 11:55:17 | 3.43 | CALL | BFO:SENSEX2642378400CE | 507.70 | 501.30 | 510.70 | 0.00 | -6.40 | -3200.00 | EDGE_HARD_STOP | Possibly early; post-exit recovery | False | 5.05 | 4.20 |
| 20260422T120004|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL | 12:00:04 | 12:00:08 | 4.16 | CALL | BFO:SENSEX2642378500CE | 475.50 | 476.70 | 478.50 | 1.20 | -1.45 | 600.00 | EARLY_FAIL_3S | Possibly early; post-exit recovery | False | 6.40 | 1.40 |
| 20260422T121002|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 12:10:03 | 12:10:08 | 4.96 | PUT | BFO:SENSEX2642378800PE | 445.35 | 447.05 | 448.35 | 2.20 | -0.25 | 850.00 | EARLY_FAIL_3S | Possibly early; post-exit recovery | False | 3.90 | 0.30 |
| 20260422T121506|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 12:15:06 | 12:15:09 | 2.26 | PUT | BFO:SENSEX2642378800PE | 451.75 | 454.75 | 454.75 | 3.05 | -0.10 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 1.25 | 0.20 |
| 20260422T122500|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 12:25:00 | 12:25:02 | 1.97 | PUT | BFO:SENSEX2642378800PE | 480.00 | 477.00 | 483.00 | 0.00 | -3.00 | -1500.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 4.05 | 1.60 |
| 20260422T123016|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 12:30:17 | 12:30:18 | 0.92 | CALL | BFO:SENSEX2642378400CE | 494.40 | 497.40 | 497.40 | 3.00 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 4.70 | 4.70 |
| 20260422T124529|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 12:45:29 | 12:46:05 | 35.28 | CALL | BFO:SENSEX2642378400CE | 504.95 | 498.00 | 507.95 | 2.60 | -6.55 | -3475.00 | EDGE_HARD_STOP | Likely justified; weakness persisted | True | 0.00 | -5.90 |
| 20260422T125012|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 12:50:12 | 12:50:15 | 2.90 | PUT | BFO:SENSEX2642378800PE | 473.60 | 471.25 | 476.60 | 0.00 | -3.60 | -1175.00 | EARLY_FAIL_1S | Likely justified; weakness persisted | False | 0.55 | -6.35 |
| 20260422T125511|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 12:55:11 | 12:55:15 | 3.10 | CALL | BFO:SENSEX2642378400CE | 502.00 | 505.00 | 505.00 | 3.00 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.30 | 7.30 |
| 20260422T130514|BFO:SENSEX2642378500CE|REVERSAL_CALL|CALL | 13:05:15 | 13:05:20 | 5.28 | CALL | BFO:SENSEX2642378500CE | 469.20 | 469.30 | 476.20 | 1.35 | -4.70 | 50.00 | PROMOTED_FAIL_3S | Likely justified; weakness persisted | False | 2.65 | -4.90 |
| 20260422T132009|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 13:20:09 | 13:20:12 | 2.32 | PUT | BFO:SENSEX2642378800PE | 459.60 | 457.90 | 462.60 | 0.00 | -1.70 | -850.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 16.95 | 5.90 |
| 20260422T132508|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT | 13:25:09 | 13:25:12 | 2.91 | PUT | BFO:SENSEX2642378700PE | 445.45 | 443.60 | 448.45 | 0.00 | -1.85 | -925.00 | EARLY_FAIL_1S | Likely justified; weakness persisted | False | -0.15 | -16.15 |
| 20260422T133006|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 13:30:06 | 13:30:10 | 3.93 | CALL | BFO:SENSEX2642378400CE | 474.65 | 476.40 | 477.65 | 1.75 | -1.00 | 875.00 | EARLY_FAIL_3S | Likely justified; weakness persisted | False | 0.00 | -3.05 |
| 20260422T133512|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL | 13:35:12 | 13:35:16 | 4.39 | CALL | BFO:SENSEX2642378500CE | 430.75 | 429.35 | 433.75 | 1.25 | -2.60 | -700.00 | EARLY_FAIL_3S | Mixed / inconclusive timing | False | 2.05 | -2.05 |
| 20260422T134001|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 13:40:01 | 13:40:04 | 2.62 | PUT | BFO:SENSEX2642378800PE | 432.75 | 430.00 | 435.75 | 0.00 | -2.75 | -1375.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 3.45 | -3.50 |
| 20260422T134511|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL | 13:45:11 | 13:45:14 | 2.85 | CALL | BFO:SENSEX2642378500CE | 438.40 | 435.75 | 441.40 | 0.05 | -2.65 | -1325.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 4.05 | -0.10 |
| 20260422T135002|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL | 13:50:02 | 13:50:05 | 2.16 | CALL | BFO:SENSEX2642378500CE | 449.20 | 448.00 | 452.20 | 0.00 | -1.20 | -600.00 | EARLY_FAIL_1S | Likely justified; weakness persisted | False | 1.65 | -4.25 |
| 20260422T135521|BFO:SENSEX2642378500CE|REVERSAL_CALL|CALL | 13:55:21 | 13:55:26 | 4.47 | CALL | BFO:SENSEX2642378500CE | 430.85 | 428.90 | 433.85 | 0.50 | -1.95 | -975.00 | EARLY_FAIL_3S | Possibly early; post-exit recovery | False | 3.65 | 3.65 |
| 20260422T140007|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL | 14:00:07 | 14:00:10 | 2.57 | CALL | BFO:SENSEX2642378500CE | 482.90 | 482.15 | 485.90 | 0.00 | -0.75 | -375.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 16.75 | 15.05 |
| 20260422T141004|BFO:SENSEX2642378800PE|REVERSAL_PUT|PUT | 14:10:04 | 14:10:06 | 2.54 | PUT | BFO:SENSEX2642378800PE | 422.55 | 421.65 | 425.55 | 0.00 | -1.15 | -450.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 19.05 | 19.05 |
| 20260422T142507|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 14:25:08 | 14:25:13 | 5.66 | CALL | BFO:SENSEX2642378400CE | 462.45 | 463.10 | 465.45 | 1.65 | 0.00 | 325.00 | EARLY_FAIL_3S | Possibly early; post-exit recovery | False | 5.95 | 5.10 |
| 20260422T144000|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | 14:40:00 | 14:40:00 | -0.51 | CALL | BFO:SENSEX2642378400CE | 474.25 | 477.25 | 477.25 | 5.75 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 2.75 | -2.30 |
| 20260422T144516|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 14:45:16 | 14:45:18 | 1.12 | PUT | BFO:SENSEX2642378800PE | 431.40 | 434.40 | 434.40 | 3.15 | -0.10 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 3.45 | -1.00 |
| 20260422T145002|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 14:50:02 | 14:50:05 | 3.10 | PUT | BFO:SENSEX2642378800PE | 441.00 | 439.05 | 448.00 | 0.00 | -1.95 | -975.00 | EARLY_FAIL_1S | Possibly early; post-exit recovery | False | 4.95 | 0.15 |

## 4. Full Trade Lifecycle Analysis (Per Trade)
### 20260422T092004|BFO:SENSEX2642379100PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642379100PE`
- Entry/Exit: `2026-04-22 09:20:04` -> `2026-04-22 09:20:05` | Duration `0.52s` | Exit reason `TARGET_HIT`
- Prices: entry `546.40`, target `549.40`, exit `549.40` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 7.55 points (index -17.41). After entry: first 1s move 3.45, first 3s move 3.45, in-trade range [3.45, 3.45] points vs entry. Post-exit best/worst delta: 3.15 / -12.80, final @15s -5.95. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T092004_BFO_SENSEX2642379100PE_CONTINUATION_PUT_PUT.png`

### 20260422T092504|BFO:SENSEX2642379000PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642379000PE`
- Entry/Exit: `2026-04-22 09:25:04` -> `2026-04-22 09:25:04` | Duration `-0.15s` | Exit reason `TARGET_HIT`
- Prices: entry `503.70`, target `506.70`, exit `506.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.00 points (index -9.72). After entry: first 1s move 5.30, first 3s move 5.30, in-trade range [5.30, 5.30] points vs entry. Post-exit best/worst delta: 9.05 / 4.20, final @15s 9.00. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T092504_BFO_SENSEX2642379000PE_CONTINUATION_PUT_PUT.png`

### 20260422T093002|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 09:30:02` -> `2026-04-22 09:30:03` | Duration `0.60s` | Exit reason `TARGET_HIT`
- Prices: entry `513.75`, target `516.75`, exit `516.75` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 1.25 points (index -13.69). After entry: first 1s move 3.20, first 3s move 3.20, in-trade range [3.20, 3.20] points vs entry. Post-exit best/worst delta: 0.20 / -13.15, final @15s -1.60. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T093002_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T093501|BFO:SENSEX2642378600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378600CE`
- Entry/Exit: `2026-04-22 09:35:01` -> `2026-04-22 09:35:03` | Duration `1.10s` | Exit reason `TARGET_HIT`
- Prices: entry `489.35`, target `492.35`, exit `492.35` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.35 points (index 5.23). After entry: first 1s move 1.60, first 3s move 4.40, in-trade range [1.60, 4.40] points vs entry. Post-exit best/worst delta: 10.65 / 0.10, final @15s 8.80. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T093501_BFO_SENSEX2642378600CE_CONTINUATION_CALL_CALL.png`

### 20260422T094000|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 09:40:00` -> `2026-04-22 09:40:01` | Duration `0.21s` | Exit reason `TARGET_HIT`
- Prices: entry `509.35`, target `516.35`, exit `516.35` | Realized PnL `3500.00`
- Lifecycle read: Pre-entry option drift 3.65 points (index -11.54). After entry: first 1s move 9.35, first 3s move 9.35, in-trade range [9.35, 9.35] points vs entry. Post-exit best/worst delta: 15.35 / 4.85, final @15s 4.85. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T094000_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T094525|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 09:45:25` -> `2026-04-22 09:45:25` | Duration `-0.23s` | Exit reason `TARGET_HIT`
- Prices: entry `541.40`, target `544.40`, exit `544.40` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.05 points (index -11.83). After entry: first 1s move 4.60, first 3s move 4.60, in-trade range [0.00, 4.60] points vs entry. Post-exit best/worst delta: 3.40 / -6.35, final @15s -6.35. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T094525_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T095508|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 09:55:08` -> `2026-04-22 09:55:11` | Duration `2.75s` | Exit reason `TARGET_HIT`
- Prices: entry `512.90`, target `515.90`, exit `515.90` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 1.30 points (index -8.32). After entry: first 1s move 1.50, first 3s move 8.10, in-trade range [1.50, 8.10] points vs entry. Post-exit best/worst delta: 8.10 / 0.20, final @15s 8.10. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T095508_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T100001|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378700PE`
- Entry/Exit: `2026-04-22 10:00:01` -> `2026-04-22 10:00:06` | Duration `4.16s` | Exit reason `PROMOTED_FAIL_3S`
- Prices: entry `515.00`, target `522.00`, exit `523.30` | Realized PnL `4150.00`
- Lifecycle read: Pre-entry option drift 3.45 points (index -4.67). After entry: first 1s move 1.95, first 3s move 1.85, in-trade range [-0.75, 6.55] points vs entry. Post-exit best/worst delta: 11.15 / -5.45, final @15s 11.15. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T100001_BFO_SENSEX2642378700PE_CONTINUATION_PUT_PUT.png`

### 20260422T100516|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378700PE`
- Entry/Exit: `2026-04-22 10:05:17` -> `2026-04-22 10:05:22` | Duration `4.94s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `526.45`, target `529.45`, exit `525.80` | Realized PnL `-325.00`
- Lifecycle read: Pre-entry option drift -1.80 points (index -7.22). After entry: first 1s move 2.65, first 3s move 1.55, in-trade range [-0.65, 2.65] points vs entry. Post-exit best/worst delta: 16.35 / 1.10, final @15s 16.35. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T100516_BFO_SENSEX2642378700PE_CONTINUATION_PUT_PUT.png`

### 20260422T101015|BFO:SENSEX2642378400CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 10:10:15` -> `2026-04-22 10:10:19` | Duration `3.94s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `478.00`, target `481.00`, exit `478.85` | Realized PnL `425.00`
- Lifecycle read: Pre-entry option drift -2.00 points (index 2.01). After entry: first 1s move 2.85, first 3s move 2.45, in-trade range [0.40, 2.85] points vs entry. Post-exit best/worst delta: 6.95 / 2.15, final @15s 4.40. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T101015_BFO_SENSEX2642378400CE_REVERSAL_CALL_CALL.png`

### 20260422T101509|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378700PE`
- Entry/Exit: `2026-04-22 10:15:09` -> `2026-04-22 10:15:12` | Duration `2.69s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `531.75`, target `534.75`, exit `531.65` | Realized PnL `-50.00`
- Lifecycle read: Pre-entry option drift 3.65 points (index -7.97). After entry: first 1s move -0.25, first 3s move -0.10, in-trade range [-0.25, -0.10] points vs entry. Post-exit best/worst delta: 2.60 / -13.45, final @15s -13.45. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T101509_BFO_SENSEX2642378700PE_CONTINUATION_PUT_PUT.png`

### 20260422T102022|BFO:SENSEX2642378700PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378700PE`
- Entry/Exit: `2026-04-22 10:20:22` -> `2026-04-22 10:20:24` | Duration `1.97s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `528.60`, target `531.60`, exit `528.40` | Realized PnL `-100.00`
- Lifecycle read: Pre-entry option drift 1.15 points (index -4.58). After entry: first 1s move NA, first 3s move -0.20, in-trade range [-0.20, -0.20] points vs entry. Post-exit best/worst delta: 8.95 / 0.60, final @15s 8.95. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T102022_BFO_SENSEX2642378700PE_REVERSAL_PUT_PUT.png`

### 20260422T102514|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378700PE`
- Entry/Exit: `2026-04-22 10:25:14` -> `2026-04-22 10:25:19` | Duration `5.36s` | Exit reason `PROMOTED_FAIL_3S`
- Prices: entry `548.00`, target `555.00`, exit `548.25` | Realized PnL `125.00`
- Lifecycle read: Pre-entry option drift -2.05 points (index -5.40). After entry: first 1s move 4.90, first 3s move 1.70, in-trade range [0.25, 4.90] points vs entry. Post-exit best/worst delta: 1.75 / -11.25, final @15s -3.75. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T102514_BFO_SENSEX2642378700PE_CONTINUATION_PUT_PUT.png`

### 20260422T103520|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 10:35:20` -> `2026-04-22 10:35:22` | Duration `2.06s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `468.85`, target `471.85`, exit `466.40` | Realized PnL `-1225.00`
- Lifecycle read: Pre-entry option drift -1.00 points (index 8.55). After entry: first 1s move -1.50, first 3s move -2.45, in-trade range [-2.45, -1.50] points vs entry. Post-exit best/worst delta: 2.00 / -1.60, final @15s -0.80. Exit quality mixed; post-exit path inconclusive.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T103520_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T104005|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 10:40:06` -> `2026-04-22 10:40:09` | Duration `3.58s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `501.10`, target `504.10`, exit `498.50` | Realized PnL `-1300.00`
- Lifecycle read: Pre-entry option drift 0.25 points (index 6.42). After entry: first 1s move -2.90, first 3s move -2.60, in-trade range [-2.90, -1.10] points vs entry. Post-exit best/worst delta: 2.60 / -7.10, final @15s -5.40. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T104005_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T105006|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 10:50:07` -> `2026-04-22 10:50:09` | Duration `1.72s` | Exit reason `TARGET_HIT`
- Prices: entry `483.50`, target `486.50`, exit `486.50` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -3.70 points (index 1.93). After entry: first 1s move 1.50, first 3s move 4.50, in-trade range [1.50, 4.50] points vs entry. Post-exit best/worst delta: 16.65 / 1.15, final @15s 15.60. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T105006_BFO_SENSEX2642378500CE_CONTINUATION_CALL_CALL.png`

### 20260422T110016|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 11:00:16` -> `2026-04-22 11:00:18` | Duration `2.50s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `498.35`, target `501.35`, exit `498.05` | Realized PnL `-150.00`
- Lifecycle read: Pre-entry option drift 3.55 points (index -10.10). After entry: first 1s move 0.25, first 3s move -0.30, in-trade range [-0.30, 0.25] points vs entry. Post-exit best/worst delta: 3.25 / -3.05, final @15s 3.25. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T110016_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T110529|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 11:05:29` -> `2026-04-22 11:05:34` | Duration `4.81s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `497.10`, target `500.10`, exit `496.35` | Realized PnL `-375.00`
- Lifecycle read: Pre-entry option drift 0.30 points (index -2.25). After entry: first 1s move -1.55, first 3s move -0.15, in-trade range [-1.55, 0.90] points vs entry. Post-exit best/worst delta: 6.75 / -0.75, final @15s 3.85. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T110529_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T111016|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 11:10:16` -> `2026-04-22 11:10:19` | Duration `2.66s` | Exit reason `TARGET_HIT`
- Prices: entry `527.00`, target `530.00`, exit `530.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.70 points (index -7.06). After entry: first 1s move 1.45, first 3s move 3.70, in-trade range [1.45, 3.70] points vs entry. Post-exit best/worst delta: 8.70 / -0.30, final @15s 8.70. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T111016_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T113006|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 11:30:06` -> `2026-04-22 11:30:10` | Duration `4.09s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `477.90`, target `480.90`, exit `477.90` | Realized PnL `0.00`
- Lifecycle read: Pre-entry option drift 3.00 points (index -2.76). After entry: first 1s move 0.85, first 3s move 2.10, in-trade range [0.00, 2.10] points vs entry. Post-exit best/worst delta: 0.80 / -2.45, final @15s 0.05. Exit quality mixed; post-exit path inconclusive.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T113006_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T114005|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378900PE`
- Entry/Exit: `2026-04-22 11:40:05` -> `2026-04-22 11:40:07` | Duration `1.34s` | Exit reason `TARGET_HIT`
- Prices: entry `489.80`, target `492.80`, exit `492.80` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.10 points (index -8.23). After entry: first 1s move 1.60, first 3s move 3.20, in-trade range [1.60, 3.20] points vs entry. Post-exit best/worst delta: 0.20 / -7.70, final @15s -7.70. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T114005_BFO_SENSEX2642378900PE_CONTINUATION_PUT_PUT.png`

### 20260422T114501|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 11:45:02` -> `2026-04-22 11:45:03` | Duration `0.88s` | Exit reason `TARGET_HIT`
- Prices: entry `471.10`, target `474.10`, exit `474.10` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.10 points (index -7.58). After entry: first 1s move 3.15, first 3s move 3.15, in-trade range [2.15, 3.15] points vs entry. Post-exit best/worst delta: 0.15 / -7.80, final @15s -0.25. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T114501_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T115514|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 11:55:14` -> `2026-04-22 11:55:17` | Duration `3.43s` | Exit reason `EDGE_HARD_STOP`
- Prices: entry `507.70`, target `510.70`, exit `501.30` | Realized PnL `-3200.00`
- Lifecycle read: Pre-entry option drift -2.30 points (index 1.75). After entry: first 1s move -3.25, first 3s move -6.40, in-trade range [-6.40, -3.25] points vs entry. Post-exit best/worst delta: 5.05 / 0.00, final @15s 4.20. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T115514_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T120004|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 12:00:04` -> `2026-04-22 12:00:08` | Duration `4.16s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `475.50`, target `478.50`, exit `476.70` | Realized PnL `600.00`
- Lifecycle read: Pre-entry option drift 7.05 points (index 2.22). After entry: first 1s move -1.45, first 3s move -0.60, in-trade range [-1.45, 1.20] points vs entry. Post-exit best/worst delta: 6.40 / 0.25, final @15s 1.40. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T120004_BFO_SENSEX2642378500CE_CONTINUATION_CALL_CALL.png`

### 20260422T121002|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 12:10:03` -> `2026-04-22 12:10:08` | Duration `4.96s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `445.35`, target `448.35`, exit `447.05` | Realized PnL `850.00`
- Lifecycle read: Pre-entry option drift 2.90 points (index -3.69). After entry: first 1s move -0.10, first 3s move 2.20, in-trade range [-0.25, 2.20] points vs entry. Post-exit best/worst delta: 3.90 / -1.10, final @15s 0.30. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T121002_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T121506|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 12:15:06` -> `2026-04-22 12:15:09` | Duration `2.26s` | Exit reason `TARGET_HIT`
- Prices: entry `451.75`, target `454.75`, exit `454.75` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.05 points (index -1.92). After entry: first 1s move -0.10, first 3s move 3.05, in-trade range [-0.10, 3.05] points vs entry. Post-exit best/worst delta: 1.25 / -3.40, final @15s 0.20. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T121506_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T122500|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 12:25:00` -> `2026-04-22 12:25:02` | Duration `1.97s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `480.00`, target `483.00`, exit `477.00` | Realized PnL `-1500.00`
- Lifecycle read: Pre-entry option drift 1.55 points (index -15.71). After entry: first 1s move -1.55, first 3s move -3.00, in-trade range [-3.00, -1.55] points vs entry. Post-exit best/worst delta: 4.05 / 0.60, final @15s 1.60. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T122500_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T123016|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 12:30:17` -> `2026-04-22 12:30:18` | Duration `0.92s` | Exit reason `TARGET_HIT`
- Prices: entry `494.40`, target `497.40`, exit `497.40` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 0.65 points (index 6.00). After entry: first 1s move 3.00, first 3s move 3.00, in-trade range [3.00, 3.00] points vs entry. Post-exit best/worst delta: 4.70 / -0.95, final @15s 4.70. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T123016_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T124529|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 12:45:29` -> `2026-04-22 12:46:05` | Duration `35.28s` | Exit reason `EDGE_HARD_STOP`
- Prices: entry `504.95`, target `507.95`, exit `498.00` | Realized PnL `-3475.00`
- Lifecycle read: Pre-entry option drift 0.15 points (index 5.96). After entry: first 1s move 1.05, first 3s move 1.85, in-trade range [-6.55, 2.60] points vs entry. Post-exit best/worst delta: 0.00 / -6.30, final @15s -5.90. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T124529_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T125012|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 12:50:12` -> `2026-04-22 12:50:15` | Duration `2.90s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `473.60`, target `476.60`, exit `471.25` | Realized PnL `-1175.00`
- Lifecycle read: Pre-entry option drift -1.80 points (index -7.84). After entry: first 1s move -3.60, first 3s move -2.35, in-trade range [-3.60, -2.35] points vs entry. Post-exit best/worst delta: 0.55 / -6.35, final @15s -6.35. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T125012_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T125511|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 12:55:11` -> `2026-04-22 12:55:15` | Duration `3.10s` | Exit reason `TARGET_HIT`
- Prices: entry `502.00`, target `505.00`, exit `505.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.40 points (index 1.49). After entry: first 1s move 1.20, first 3s move 2.00, in-trade range [1.20, 3.00] points vs entry. Post-exit best/worst delta: 7.30 / -0.35, final @15s 7.30. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T125511_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T130514|BFO:SENSEX2642378500CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 13:05:15` -> `2026-04-22 13:05:20` | Duration `5.28s` | Exit reason `PROMOTED_FAIL_3S`
- Prices: entry `469.20`, target `476.20`, exit `469.30` | Realized PnL `50.00`
- Lifecycle read: Pre-entry option drift -1.10 points (index 8.27). After entry: first 1s move -4.70, first 3s move -2.30, in-trade range [-4.70, 0.10] points vs entry. Post-exit best/worst delta: 2.65 / -4.90, final @15s -4.90. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T130514_BFO_SENSEX2642378500CE_REVERSAL_CALL_CALL.png`

### 20260422T132009|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 13:20:09` -> `2026-04-22 13:20:12` | Duration `2.32s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `459.60`, target `462.60`, exit `457.90` | Realized PnL `-850.00`
- Lifecycle read: Pre-entry option drift -0.60 points (index -1.39). After entry: first 1s move -1.55, first 3s move -1.70, in-trade range [-1.70, -1.55] points vs entry. Post-exit best/worst delta: 16.95 / -3.40, final @15s 5.90. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T132009_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T132508|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378700PE`
- Entry/Exit: `2026-04-22 13:25:09` -> `2026-04-22 13:25:12` | Duration `2.91s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `445.45`, target `448.45`, exit `443.60` | Realized PnL `-925.00`
- Lifecycle read: Pre-entry option drift 7.40 points (index -7.34). After entry: first 1s move -0.90, first 3s move -1.85, in-trade range [-1.85, -0.55] points vs entry. Post-exit best/worst delta: -0.15 / -19.90, final @15s -16.15. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T132508_BFO_SENSEX2642378700PE_CONTINUATION_PUT_PUT.png`

### 20260422T133006|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 13:30:06` -> `2026-04-22 13:30:10` | Duration `3.93s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `474.65`, target `477.65`, exit `476.40` | Realized PnL `875.00`
- Lifecycle read: Pre-entry option drift 1.30 points (index 5.16). After entry: first 1s move -1.00, first 3s move 1.65, in-trade range [-1.00, 1.75] points vs entry. Post-exit best/worst delta: 0.00 / -5.55, final @15s -3.05. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T133006_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T133512|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 13:35:12` -> `2026-04-22 13:35:16` | Duration `4.39s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `430.75`, target `433.75`, exit `429.35` | Realized PnL `-700.00`
- Lifecycle read: Pre-entry option drift 3.75 points (index 6.58). After entry: first 1s move 1.25, first 3s move -2.60, in-trade range [-2.60, 1.25] points vs entry. Post-exit best/worst delta: 2.05 / -6.25, final @15s -2.05. Exit quality mixed; post-exit path inconclusive.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T133512_BFO_SENSEX2642378500CE_CONTINUATION_CALL_CALL.png`

### 20260422T134001|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 13:40:01` -> `2026-04-22 13:40:04` | Duration `2.62s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `432.75`, target `435.75`, exit `430.00` | Realized PnL `-1375.00`
- Lifecycle read: Pre-entry option drift 0.00 points (index -11.06). After entry: first 1s move -2.75, first 3s move -2.75, in-trade range [-2.75, -2.75] points vs entry. Post-exit best/worst delta: 3.45 / -6.55, final @15s -3.50. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T134001_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T134511|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 13:45:11` -> `2026-04-22 13:45:14` | Duration `2.85s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `438.40`, target `441.40`, exit `435.75` | Realized PnL `-1325.00`
- Lifecycle read: Pre-entry option drift -1.25 points (index 6.78). After entry: first 1s move -1.15, first 3s move -2.65, in-trade range [-2.65, -1.15] points vs entry. Post-exit best/worst delta: 4.05 / -2.20, final @15s -0.10. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T134511_BFO_SENSEX2642378500CE_CONTINUATION_CALL_CALL.png`

### 20260422T135002|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 13:50:02` -> `2026-04-22 13:50:05` | Duration `2.16s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `449.20`, target `452.20`, exit `448.00` | Realized PnL `-600.00`
- Lifecycle read: Pre-entry option drift 0.90 points (index 5.98). After entry: first 1s move -1.05, first 3s move -1.20, in-trade range [-1.20, -1.05] points vs entry. Post-exit best/worst delta: 1.65 / -4.25, final @15s -4.25. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T135002_BFO_SENSEX2642378500CE_CONTINUATION_CALL_CALL.png`

### 20260422T135521|BFO:SENSEX2642378500CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 13:55:21` -> `2026-04-22 13:55:26` | Duration `4.47s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `430.85`, target `433.85`, exit `428.90` | Realized PnL `-975.00`
- Lifecycle read: Pre-entry option drift 2.55 points (index 6.43). After entry: first 1s move NA, first 3s move -1.35, in-trade range [-1.95, 0.50] points vs entry. Post-exit best/worst delta: 3.65 / -3.25, final @15s 3.65. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T135521_BFO_SENSEX2642378500CE_REVERSAL_CALL_CALL.png`

### 20260422T140007|BFO:SENSEX2642378500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378500CE`
- Entry/Exit: `2026-04-22 14:00:07` -> `2026-04-22 14:00:10` | Duration `2.57s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `482.90`, target `485.90`, exit `482.15` | Realized PnL `-375.00`
- Lifecycle read: Pre-entry option drift -0.70 points (index 12.40). After entry: first 1s move -0.05, first 3s move -0.75, in-trade range [-0.75, -0.05] points vs entry. Post-exit best/worst delta: 16.75 / -2.25, final @15s 15.05. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T140007_BFO_SENSEX2642378500CE_CONTINUATION_CALL_CALL.png`

### 20260422T141004|BFO:SENSEX2642378800PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 14:10:04` -> `2026-04-22 14:10:06` | Duration `2.54s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `422.55`, target `425.55`, exit `421.65` | Realized PnL `-450.00`
- Lifecycle read: Pre-entry option drift -0.70 points (index -6.83). After entry: first 1s move NA, first 3s move -0.90, in-trade range [-0.90, -0.90] points vs entry. Post-exit best/worst delta: 19.05 / 3.85, final @15s 19.05. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T141004_BFO_SENSEX2642378800PE_REVERSAL_PUT_PUT.png`

### 20260422T142507|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 14:25:08` -> `2026-04-22 14:25:13` | Duration `5.66s` | Exit reason `EARLY_FAIL_3S`
- Prices: entry `462.45`, target `465.45`, exit `463.10` | Realized PnL `325.00`
- Lifecycle read: Pre-entry option drift -0.55 points (index 0.03). After entry: first 1s move 1.65, first 3s move 0.50, in-trade range [0.50, 1.65] points vs entry. Post-exit best/worst delta: 5.95 / -0.60, final @15s 5.10. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T142507_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T144000|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2642378400CE`
- Entry/Exit: `2026-04-22 14:40:00` -> `2026-04-22 14:40:00` | Duration `-0.51s` | Exit reason `TARGET_HIT`
- Prices: entry `474.25`, target `477.25`, exit `477.25` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.50 points (index 7.21). After entry: first 1s move 5.75, first 3s move 5.75, in-trade range [0.00, 5.75] points vs entry. Post-exit best/worst delta: 2.75 / -5.35, final @15s -2.30. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T144000_BFO_SENSEX2642378400CE_CONTINUATION_CALL_CALL.png`

### 20260422T144516|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 14:45:16` -> `2026-04-22 14:45:18` | Duration `1.12s` | Exit reason `TARGET_HIT`
- Prices: entry `431.40`, target `434.40`, exit `434.40` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.85 points (index -10.27). After entry: first 1s move NA, first 3s move 3.15, in-trade range [1.15, 3.15] points vs entry. Post-exit best/worst delta: 3.45 / -3.75, final @15s -1.00. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T144516_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

### 20260422T145002|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2642378800PE`
- Entry/Exit: `2026-04-22 14:50:02` -> `2026-04-22 14:50:05` | Duration `3.10s` | Exit reason `EARLY_FAIL_1S`
- Prices: entry `441.00`, target `448.00`, exit `439.05` | Realized PnL `-975.00`
- Lifecycle read: Pre-entry option drift 8.25 points (index -9.18). After entry: first 1s move -0.65, first 3s move -1.95, in-trade range [-1.95, -0.65] points vs entry. Post-exit best/worst delta: 4.95 / -1.15, final @15s 0.15. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts/20260422T145002_BFO_SENSEX2642378800PE_CONTINUATION_PUT_PUT.png`

## 5. Visualizations
- Session-level charts:
  - session_trade_timeline: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/session_trade_timeline.png`
  - pnl_distribution: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/pnl_distribution.png`
  - duration_distribution: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/duration_distribution.png`
  - mfe_vs_mae: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/mfe_vs_mae_scatter.png`
  - pnl_vs_mfe: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/pnl_vs_mfe_scatter.png`
  - entry_first_5s_path_behavior: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/entry_first_5s_path_behavior.png`
  - runtime_health_timeseries_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/runtime_health_timeseries.csv`
  - runtime_stability: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/runtime_stability.png`
  - counterfactual_summary_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/counterfactual_summary.csv`
  - time_of_day_summary_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/time_of_day_summary.csv`
  - runtime_stress_by_time_bucket_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/runtime_stress_by_time_bucket.csv`
- Per-trade charts:
  - Count generated: **46**
  - Folder: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-22/trade_charts`

## 6. Microstructure Feature Analysis
### Winners vs Losers
| feature | winner_mean | loser_mean | winner_median | loser_median |
| --- | --- | --- | --- | --- |
| entry_spread | 1.03 | 1.05 | 1.05 | 1.05 |
| spread_median_first_2s | 1.17 | 1.10 | 1.23 | 1.15 |
| imbalance_entry | -0.11 | -0.01 | -0.16 | 0.00 |
| imbalance_drift_first_2s | 0.02 | -0.02 | -0.03 | 0.04 |
| pre_entry_velocity | 0.90 | 0.44 | 0.86 | 0.10 |
| first_1s_move | 2.20 | -0.97 | 1.65 | -1.10 |
| first_3s_move | 3.22 | -1.52 | 3.15 | -1.70 |
| in_trade_max_points | 3.84 | -0.50 | 3.20 | -0.65 |
| in_trade_min_points | 1.22 | -2.20 | 1.18 | -1.95 |
| post_exit_best_delta | 5.58 | 5.93 | 4.30 | 3.65 |
| post_exit_final_delta | 2.20 | 1.15 | 0.85 | 0.15 |
| holding_seconds | 2.32 | 4.57 | 1.99 | 2.85 |

### Small Losers vs Tail Losers
- Loser count: **21**, tail-loss threshold (median loser pnl): **-925.00**
- Tail losers average first_3s_move: **-2.32**, average post_exit_best_delta: **2.75**
- Smaller losers average first_3s_move: **-0.64**, average post_exit_best_delta: **9.44**

### Continuation/Reversal and Fragility Views
- Continuation trades: **41**, avg pnl `317.68`
- Reversal trades: **5**, avg pnl `-210.00`
- Fragile trades: **1**, avg pnl `-3475.00`
- Non-fragile trades: **45**, avg pnl `343.33`

### Early-Day vs Late-Day
- Early (before 11:30): **19** trades, hit rate `63.16%` avg pnl `877.63`
- Late (after 13:00): **15** trades, hit rate `33.33%` avg pnl `-286.67`

## 7. Exit Quality Analysis
- Target exits: **16**, share of target exits with post-exit fade (< -3 points final delta): **18.75%**
- Non-target exits: **30**, share with post-exit rebound >= +3 points: **60.00%**
- Exit reason mix: TARGET_HIT: 16, EARLY_FAIL_1S: 15, EARLY_FAIL_3S: 10, PROMOTED_FAIL_3S: 3, EDGE_HARD_STOP: 2
- Share of trades that nearly reached target without in-trade touch: **8.70%**

## 8. Counterfactual / What-if Analysis
| target_points | touch_rate_all | touch_rate_winners | touch_rate_losers |
| --- | --- | --- | --- |
| 2.00 | 0.50 | 0.83 | 0.10 |
| 3.00 | 0.39 | 0.75 | 0.00 |
| 4.00 | 0.20 | 0.38 | 0.00 |
| 5.00 | 0.11 | 0.21 | 0.00 |
| weak_follow_through_warning | 0.41 | 0.08 | 0.81 |
| non_target_exits_post_exit_target_touch | 0.37 | NA | NA |
- Interpretation: target-touch counterfactuals are descriptive only; they do not model fill quality, queueing, or order-state interactions.

## 9. Time-of-Day Analysis
| bucket_type | bucket | trades | wins | losses | hit_rate | avg_pnl | median_pnl | tail_loss_count | tail_loss_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bucket_pre_post_1pm | POST_1PM | 15 | 5 | 10 | 0.33 | -286.67 | -600.00 | 2 | 0.13 |
| bucket_pre_post_1pm | PRE_1PM | 31 | 19 | 11 | 0.61 | 525.00 | 850.00 | 4 | 0.13 |
| bucket_3way | EARLY_SESSION | 16 | 11 | 5 | 0.69 | 981.25 | 1500.00 | 2 | 0.12 |
| bucket_3way | LATE_SESSION | 15 | 5 | 10 | 0.33 | -286.67 | -600.00 | 2 | 0.13 |
| bucket_3way | MID_SESSION | 15 | 8 | 6 | 0.53 | 38.33 | 600.00 | 2 | 0.13 |

### Runtime Stress Concentration by Time Bucket
| bucket_type | bucket | stress_event_count | distinct_stress_types |
| --- | --- | --- | --- |
| bucket_pre_post_1pm | PRE_1PM | 0 |  |
| bucket_pre_post_1pm | POST_1PM | 0 |  |
| bucket_3way | EARLY_SESSION | 0 |  |
| bucket_3way | MID_SESSION | 0 |  |
| bucket_3way | LATE_SESSION | 0 |  |

## 10. Actionable Insights
- [runtime insight] Drop counters stayed at zero across runtime telemetry, indicating no observable tick/journal loss in this session.
- [strategy behavior insight] 81% of losing trades showed weak immediate follow-through (first 1s <= 0 and <1 point max gain in first 3s).
- [execution insight] 62% of losing trades had >=3 points of post-exit rebound, suggesting some exits were defensive but potentially early.
- [strategy behavior insight] 88% of winning trades closed within 5 seconds, consistent with a fast-follow-through payoff profile.
- [candidate microstructure filter idea] In-trade option spread difference (loss-win) was -0.08 points; spread alone appears weak as a discriminator in this sample.
- [candidate microstructure filter idea] First-3-second move was -4.74 points lower in losers vs winners, making early path momentum a stronger candidate signal than spread/imbalance.
- [execution insight] 37% of non-target exits later touched target in the next 15 seconds.
- [logging/data-quality insight] Trade-path capture (pre-entry/in-trade/post-exit) was available trade-by-trade, enabling high-confidence path diagnostics without needing full-day options tape.

## 11. Final Recommendation
- Healthy aspects: runtime telemetry showed stable ingest/write behavior with no visible drop counters; trade-path logging quality is high.
- Fragile aspects: tail losses remain concentrated in a minority of trades and are associated with weak immediate follow-through in early seconds.
- Next investigation: validate early path-momentum diagnostics over multiple sessions before changing live risk logic.
- Tomorrow run posture: proceed with strategy unchanged, with observational focus on early in-trade trajectory and post-exit recovery diagnostics.

## Method Notes
- Session date auto-detected from the latest dated log folders/files unless explicitly supplied.
- Trade rows were de-duplicated by `trade_id`, preferring `post_exit_observation_done=true` and `summary_version=post_exit_enriched`.
- Feature formulas are transparent and based on direct tick-path arithmetic (spread medians, imbalance, first-1s/3s move, pre-velocity, post-exit deltas).
- Missing-file handling: optional files (`features_daily.csv`, full-day `options.jsonl`) are used if present; analysis continues when absent.