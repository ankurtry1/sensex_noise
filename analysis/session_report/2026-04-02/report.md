# Session Report (2026-04-02)

Analyzed date: **2026-04-02**

## Data Inputs Used
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trades/2026-04-02.trades_enriched.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trades/2026-04-02.trades.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/events/2026-04-02.events.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/ticks/2026-04-02/sensex.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/ticks/2026-04-02/futures.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trade_ticks/2026-04-02`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/runtime/control.json`

## 1. Executive Summary
- Trades: **57**
- Wins / Losses / Flat: **38 / 19 / 0**
- Gross PnL: **-15700.00**
- Net PnL: **-15700.00**
- Average Winner: **1368.42**
- Average Loser: **-3563.16**
- Largest Win: **1500.00**
- Largest Loss: **-9750.00**
- Hit Rate: **66.67%**
- Expectancy per Trade: **-275.44**
- Day Pattern: **Many small wins offset by a few tail losses**

## 2. System Health / Runtime Summary
- STREAM_CONNECTED events: **1**
- Stream close events: **0**
- Reconnect-related events: **0**
- Watchdog-related events: **0**
- Stream degraded/recovered events: **0 / 0**
- Entry deferred (quote unavailable): **0**
- Lattice rebases: **717**
- Queue/backpressure explicit events: **0**
- Max runtime tick drops: **0**
- Max critical tick drops: **0**
- Max background tick drops: **0**
- Max journal drops: **0**
- Queue max sizes seen (critical/background/journal): **5 / 23 / 15**
- Inference trustworthiness: **True**
- Data-quality assessment: No drop/backpressure evidence and no degradation incidents in session telemetry; data quality appears reliable for behavioral inference.

## 3. Trade Ledger Table
| trade_id | entry_time | exit_time | holding_seconds | side | symbol | entry_price | exit_price | target_price | mfe | mae | net_pnl | exit_reason | exit_timing_assessment | target_nearly_reached | post_exit_best_delta | post_exit_final_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260402T092003|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT | 09:20:04 | 09:20:07 | 2.71 | PUT | BFO:SENSEX2640271900PE | 427.50 | 430.50 | 430.50 | 4.65 | -1.20 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | -0.65 | -10.75 |
| 20260402T092501|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL | 09:25:01 | 09:25:15 | 13.35 | CALL | BFO:SENSEX2640271600CE | 376.05 | 378.05 | 378.05 | 2.90 | -8.85 | 1000.00 | TARGET_HIT | Captured target; additional upside remained | True | 13.10 | 12.80 |
| 20260402T093500|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL | 09:35:00 | 09:35:11 | 11.04 | CALL | BFO:SENSEX2640271600CE | 365.00 | 355.35 | 367.00 | 0.00 | -11.25 | -4825.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 9.50 | 3.40 |
| 20260402T094003|BFO:SENSEX2640272000PE|CONTINUATION_PUT|PUT | 09:40:03 | 09:40:03 | -0.55 | PUT | BFO:SENSEX2640272000PE | 455.80 | 458.80 | 458.80 | 5.90 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 3.50 | -8.35 |
| 20260402T094503|BFO:SENSEX2640271600CE|REVERSAL_CALL|CALL | 09:45:03 | 09:45:14 | 10.90 | CALL | BFO:SENSEX2640271600CE | 369.35 | 369.00 | 371.35 | 0.40 | -5.45 | -175.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 11.90 | 10.90 |
| 20260402T095006|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT | 09:50:06 | 09:50:10 | 3.43 | PUT | BFO:SENSEX2640271900PE | 405.85 | 408.85 | 408.85 | 3.15 | -1.30 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 0.15 | -4.85 |
| 20260402T095514|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT | 09:55:14 | 09:55:26 | 11.64 | PUT | BFO:SENSEX2640271900PE | 427.70 | 424.85 | 429.70 | 0.55 | -4.00 | -1425.00 | EARLY_RISK_EXIT | Mixed / inconclusive timing | False | 1.45 | -1.70 |
| 20260402T100001|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT | 10:00:01 | 10:00:03 | 1.64 | PUT | BFO:SENSEX2640271800PE | 367.55 | 370.55 | 370.55 | 6.45 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 28.30 | 28.30 |
| 20260402T100508|BFO:SENSEX2640271800PE|REVERSAL_PUT|PUT | 10:05:09 | 10:05:17 | 7.89 | PUT | BFO:SENSEX2640271800PE | 357.70 | 360.70 | 360.70 | 3.80 | -4.25 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 2.05 | -6.70 |
| 20260402T101003|BFO:SENSEX2640271700PE|CONTINUATION_PUT|PUT | 10:10:03 | 10:10:14 | 11.58 | PUT | BFO:SENSEX2640271700PE | 327.45 | 324.90 | 329.45 | 0.00 | -7.60 | -1275.00 | EARLY_RISK_EXIT | Mixed / inconclusive timing | False | 1.75 | -0.50 |
| 20260402T102537|BFO:SENSEX2640271400CE|REVERSAL_CALL|CALL | 10:25:38 | 10:25:48 | 9.69 | CALL | BFO:SENSEX2640271400CE | 346.60 | 348.60 | 348.60 | 6.40 | -4.75 | 1000.00 | TARGET_HIT | Captured target; additional upside remained | True | 10.70 | 9.55 |
| 20260402T103529|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT | 10:35:30 | 10:35:44 | 13.76 | PUT | BFO:SENSEX2640271800PE | 349.25 | 351.25 | 351.25 | 2.15 | -2.60 | 1000.00 | TARGET_HIT | Reasonable target exit | True | 0.15 | -1.40 |
| 20260402T104001|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL | 10:40:01 | 10:40:03 | 1.40 | CALL | BFO:SENSEX2640271500CE | 302.70 | 305.70 | 305.70 | 3.75 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 13.25 | 11.75 |
| 20260402T104503|BFO:SENSEX2640271500CE|REVERSAL_CALL|CALL | 10:45:03 | 10:45:03 | -0.23 | CALL | BFO:SENSEX2640271500CE | 307.55 | 310.55 | 310.55 | 4.45 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 1.45 | -4.15 |
| 20260402T105003|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT | 10:50:03 | 10:50:11 | 7.10 | PUT | BFO:SENSEX2640271800PE | 347.80 | 349.80 | 349.80 | 2.00 | -4.90 | 1000.00 | TARGET_HIT | Reasonable target exit | True | 2.15 | 2.15 |
| 20260402T110002|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL | 11:00:03 | 11:00:14 | 11.88 | CALL | BFO:SENSEX2640271500CE | 355.00 | 353.90 | 357.00 | 0.55 | -6.55 | -550.00 | EARLY_RISK_EXIT | Likely justified; weakness persisted | False | 0.55 | -17.10 |
| 20260402T110512|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT | 11:05:12 | 11:05:57 | 44.64 | PUT | BFO:SENSEX2640271900PE | 356.40 | 348.00 | 358.40 | 1.60 | -13.90 | -4200.00 | HARD_STOP_EXIT | Possibly early; post-exit recovery | True | 10.50 | 6.45 |
| 20260402T111008|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT | 11:10:08 | 11:10:12 | 3.75 | PUT | BFO:SENSEX2640271900PE | 369.85 | 372.85 | 372.85 | 11.85 | -0.95 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 10.80 | 8.75 |
| 20260402T111504|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT | 11:15:04 | 11:15:07 | 2.61 | PUT | BFO:SENSEX2640271900PE | 373.50 | 376.50 | 376.50 | 3.00 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | -0.45 | -0.45 |
| 20260402T112011|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT | 11:20:11 | 11:20:23 | 11.72 | PUT | BFO:SENSEX2640271800PE | 330.35 | 325.75 | 332.35 | 0.00 | -5.45 | -2300.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 9.95 | 3.35 |
| 20260402T112509|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT | 11:25:09 | 11:25:42 | 33.14 | PUT | BFO:SENSEX2640271800PE | 331.65 | 324.05 | 333.65 | 1.35 | -7.60 | -3800.00 | PATH_RISK_EXIT | Possibly early; post-exit recovery | False | 10.05 | 5.20 |
| 20260402T113536|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL | 11:35:36 | 11:35:38 | 1.21 | CALL | BFO:SENSEX2640271500CE | 269.95 | 272.95 | 272.95 | 3.15 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 6.75 | 2.65 |
| 20260402T114006|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL | 11:40:07 | 11:40:10 | 2.82 | CALL | BFO:SENSEX2640271500CE | 284.60 | 287.60 | 287.60 | 3.25 | -2.65 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 1.80 | -3.80 |
| 20260402T114500|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT | 11:45:00 | 11:45:12 | 11.26 | PUT | BFO:SENSEX2640271900PE | 381.65 | 367.90 | 383.65 | 0.00 | -16.60 | -6875.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 5.15 | 2.95 |
| 20260402T115016|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL | 11:50:17 | 11:50:37 | 19.93 | CALL | BFO:SENSEX2640271500CE | 311.00 | 313.00 | 313.00 | 3.85 | -3.95 | 1000.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 3.95 | -3.50 |
| 20260402T115502|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL | 11:55:02 | 11:55:33 | 30.62 | CALL | BFO:SENSEX2640271500CE | 310.00 | 304.10 | 312.00 | 1.20 | -6.55 | -2950.00 | PATH_RISK_EXIT | Likely justified; weakness persisted | False | 0.90 | -3.80 |
| 20260402T120012|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL | 12:00:12 | 12:00:25 | 12.69 | CALL | BFO:SENSEX2640271600CE | 326.05 | 328.05 | 328.05 | 3.95 | -4.75 | 1000.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.95 | 1.90 |
| 20260402T120519|BFO:SENSEX2640272000PE|CONTINUATION_PUT|PUT | 12:05:19 | 12:05:38 | 18.16 | PUT | BFO:SENSEX2640272000PE | 366.00 | 368.00 | 368.00 | 2.80 | -3.05 | 1000.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.15 | 6.35 |
| 20260402T121506|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL | 12:15:07 | 12:15:18 | 11.46 | CALL | BFO:SENSEX2640271600CE | 288.55 | 282.00 | 290.55 | 0.00 | -9.05 | -3275.00 | EARLY_RISK_EXIT | Likely justified; weakness persisted | False | 2.60 | -5.65 |
| 20260402T122513|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL | 12:25:14 | 12:25:15 | 0.72 | CALL | BFO:SENSEX2640271600CE | 262.10 | 265.10 | 265.10 | 4.95 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 2.15 | -12.90 |
| 20260402T123002|BFO:SENSEX2640271700CE|CONTINUATION_CALL|CALL | 12:30:02 | 12:30:14 | 11.59 | CALL | BFO:SENSEX2640271700CE | 285.55 | 283.15 | 287.55 | 0.65 | -7.05 | -1200.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 3.80 | -9.50 |
| 20260402T123501|BFO:SENSEX2640271800CE|CONTINUATION_CALL|CALL | 12:35:02 | 12:35:13 | 10.93 | CALL | BFO:SENSEX2640271800CE | 268.85 | 270.85 | 270.85 | 3.60 | -4.15 | 1000.00 | TARGET_HIT | Timely target exit; post-exit fade | True | -0.30 | -23.80 |
| 20260402T124004|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL | 12:40:04 | 12:40:08 | 3.20 | CALL | BFO:SENSEX2640271900CE | 293.70 | 296.70 | 296.70 | 3.25 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 15.20 | 15.20 |
| 20260402T124504|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL | 12:45:04 | 12:45:04 | -0.32 | CALL | BFO:SENSEX2640271900CE | 314.45 | 317.45 | 317.45 | 3.45 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 0.05 | -16.30 |
| 20260402T130002|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL | 13:00:02 | 13:00:03 | 0.00 | CALL | BFO:SENSEX2640271900CE | 310.80 | 313.80 | 313.80 | 10.95 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 57.20 | 54.45 |
| 20260402T130501|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL | 13:05:01 | 13:05:03 | 1.58 | CALL | BFO:SENSEX2640271900CE | 312.60 | 315.60 | 315.60 | 5.10 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 6.90 | -3.70 |
| 20260402T131028|BFO:SENSEX2640272300PE|REVERSAL_PUT|PUT | 13:10:29 | 13:10:40 | 10.88 | PUT | BFO:SENSEX2640272300PE | 342.70 | 344.70 | 344.70 | 3.35 | -8.55 | 1000.00 | TARGET_HIT | Captured target; additional upside remained | True | 5.95 | 2.75 |
| 20260402T131513|BFO:SENSEX2640272300PE|CONTINUATION_PUT|PUT | 13:15:13 | 13:15:24 | 11.63 | PUT | BFO:SENSEX2640272300PE | 331.30 | 312.20 | 333.30 | 0.30 | -19.10 | -9550.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 4.20 | -4.05 |
| 20260402T132018|BFO:SENSEX2640272000CE|CONTINUATION_CALL|CALL | 13:20:19 | 13:20:51 | 32.42 | CALL | BFO:SENSEX2640272000CE | 285.20 | 279.25 | 287.20 | 2.40 | -16.40 | -2975.00 | PATH_RISK_EXIT | Likely justified; weakness persisted | True | 1.45 | -7.55 |
| 20260402T132503|BFO:SENSEX2640272100CE|CONTINUATION_CALL|CALL | 13:25:03 | 13:25:06 | 2.37 | CALL | BFO:SENSEX2640272100CE | 338.75 | 341.75 | 341.75 | 3.60 | -0.05 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 21.20 | 1.90 |
| 20260402T133000|BFO:SENSEX2640272300CE|CONTINUATION_CALL|CALL | 13:30:01 | 13:30:06 | 4.90 | CALL | BFO:SENSEX2640272300CE | 324.00 | 327.00 | 327.00 | 3.10 | -1.25 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 6.35 | -3.40 |
| 20260402T133518|BFO:SENSEX2640272700PE|CONTINUATION_PUT|PUT | 13:35:18 | 13:35:20 | 1.13 | PUT | BFO:SENSEX2640272700PE | 330.00 | 333.00 | 333.00 | 4.35 | -0.10 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 30.90 | 25.30 |
| 20260402T134001|BFO:SENSEX2640272400CE|CONTINUATION_CALL|CALL | 13:40:02 | 13:40:07 | 4.86 | CALL | BFO:SENSEX2640272400CE | 282.15 | 285.15 | 285.15 | 3.15 | -5.20 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 32.45 | 16.60 |
| 20260402T134511|BFO:SENSEX2640272500CE|CONTINUATION_CALL|CALL | 13:45:12 | 13:45:12 | -0.08 | CALL | BFO:SENSEX2640272500CE | 271.05 | 274.05 | 274.05 | 3.30 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 0.30 | -6.75 |
| 20260402T135005|BFO:SENSEX2640272800PE|CONTINUATION_PUT|PUT | 13:50:05 | 13:50:17 | 11.66 | PUT | BFO:SENSEX2640272800PE | 305.75 | 300.20 | 307.75 | 0.00 | -5.55 | -2775.00 | EARLY_RISK_EXIT | Likely justified; weakness persisted | False | -1.85 | -17.85 |
| 20260402T135503|BFO:SENSEX2640272900PE|REVERSAL_PUT|PUT | 13:55:03 | 13:55:05 | 1.13 | PUT | BFO:SENSEX2640272900PE | 360.95 | 363.95 | 363.95 | 4.30 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 2.55 | -5.10 |
| 20260402T140002|BFO:SENSEX2640272800PE|CONTINUATION_PUT|PUT | 14:00:02 | 14:00:05 | 2.64 | PUT | BFO:SENSEX2640272800PE | 285.75 | 288.75 | 288.75 | 3.75 | -0.75 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 5.90 | 5.90 |
| 20260402T140510|BFO:SENSEX2640272500CE|CONTINUATION_CALL|CALL | 14:05:11 | 14:05:11 | -0.05 | CALL | BFO:SENSEX2640272500CE | 289.55 | 292.55 | 292.55 | 3.40 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 3.90 | 3.90 |
| 20260402T141007|BFO:SENSEX2640272600CE|CONTINUATION_CALL|CALL | 14:10:07 | 14:10:16 | 8.69 | CALL | BFO:SENSEX2640272600CE | 249.45 | 251.45 | 251.45 | 2.55 | -6.40 | 1000.00 | TARGET_HIT | Reasonable target exit | True | 0.55 | -0.95 |
| 20260402T141503|BFO:SENSEX2640272800CE|CONTINUATION_CALL|CALL | 14:15:03 | 14:15:04 | 0.19 | CALL | BFO:SENSEX2640272800CE | 254.05 | 257.05 | 257.05 | 3.20 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 5.85 | 4.05 |
| 20260402T142013|BFO:SENSEX2640272900CE|CONTINUATION_CALL|CALL | 14:20:13 | 14:20:44 | 31.20 | CALL | BFO:SENSEX2640272900CE | 259.20 | 245.60 | 261.20 | 1.70 | -21.70 | -6800.00 | HARD_STOP_EXIT | Possibly early; post-exit recovery | True | 16.40 | 8.35 |
| 20260402T142500|BFO:SENSEX2640272900CE|CONTINUATION_CALL|CALL | 14:25:00 | 14:25:00 | -0.36 | CALL | BFO:SENSEX2640272900CE | 296.45 | 299.45 | 299.45 | 3.60 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 33.20 | 18.35 |
| 20260402T143004|BFO:SENSEX2640273300PE|REVERSAL_PUT|PUT | 14:30:04 | 14:30:07 | 2.57 | PUT | BFO:SENSEX2640273300PE | 256.70 | 259.70 | 259.70 | 7.20 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.95 | 0.70 |
| 20260402T143500|BFO:SENSEX2640273000CE|CONTINUATION_CALL|CALL | 14:35:00 | 14:35:11 | 11.64 | CALL | BFO:SENSEX2640273000CE | 254.65 | 235.15 | 256.65 | 0.00 | -23.20 | -9750.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 3.15 | -7.05 |
| 20260402T144000|BFO:SENSEX2640273200PE|CONTINUATION_PUT|PUT | 14:40:00 | 14:40:11 | 10.93 | PUT | BFO:SENSEX2640273200PE | 269.85 | 268.90 | 271.85 | 0.00 | -15.45 | -475.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 30.10 | 17.75 |
| 20260402T144507|BFO:SENSEX2640273000PE|CONTINUATION_PUT|PUT | 14:45:08 | 14:45:19 | 11.59 | PUT | BFO:SENSEX2640273000PE | 272.40 | 267.35 | 274.40 | 0.00 | -9.40 | -2525.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 27.95 | 17.70 |
| 20260402T145015|BFO:SENSEX2640272800CE|CONTINUATION_CALL|CALL | 14:50:15 | 14:50:16 | 0.37 | CALL | BFO:SENSEX2640272800CE | 195.60 | 198.60 | 198.60 | 8.35 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 48.45 | 16.40 |

## 4. Full Trade Lifecycle Analysis (Per Trade)
### 20260402T092003|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271900PE`
- Entry/Exit: `2026-04-02 09:20:04` -> `2026-04-02 09:20:07` | Duration `2.71s` | Exit reason `TARGET_HIT`
- Prices: entry `427.50`, target `430.50`, exit `430.50` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 15.40 points (index -5.50). After entry: first 1s move -1.20, first 3s move 4.65, in-trade range [-1.20, 4.65] points vs entry. Post-exit best/worst delta: -0.65 / -17.80, final @15s -10.75. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T092003_BFO_SENSEX2640271900PE_CONTINUATION_PUT_PUT.png`

### 20260402T092501|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271600CE`
- Entry/Exit: `2026-04-02 09:25:01` -> `2026-04-02 09:25:15` | Duration `13.35s` | Exit reason `TARGET_HIT`
- Prices: entry `376.05`, target `378.05`, exit `378.05` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 4.30 points (index 12.01). After entry: first 1s move -7.10, first 3s move 1.35, in-trade range [-8.85, 2.90] points vs entry. Post-exit best/worst delta: 13.10 / -6.50, final @15s 12.80. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T092501_BFO_SENSEX2640271600CE_CONTINUATION_CALL_CALL.png`

### 20260402T093500|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271600CE`
- Entry/Exit: `2026-04-02 09:35:00` -> `2026-04-02 09:35:11` | Duration `11.04s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `365.00`, target `367.00`, exit `355.35` | Realized PnL `-4825.00`
- Lifecycle read: Pre-entry option drift -5.05 points (index 7.45). After entry: first 1s move -4.80, first 3s move -7.55, in-trade range [-11.25, -2.20] points vs entry. Post-exit best/worst delta: 9.50 / -5.65, final @15s 3.40. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T093500_BFO_SENSEX2640271600CE_CONTINUATION_CALL_CALL.png`

### 20260402T094003|BFO:SENSEX2640272000PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272000PE`
- Entry/Exit: `2026-04-02 09:40:03` -> `2026-04-02 09:40:03` | Duration `-0.55s` | Exit reason `TARGET_HIT`
- Prices: entry `455.80`, target `458.80`, exit `458.80` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.50 points (index -13.05). After entry: first 1s move 5.90, first 3s move 5.90, in-trade range [5.90, 5.90] points vs entry. Post-exit best/worst delta: 3.50 / -8.35, final @15s -8.35. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T094003_BFO_SENSEX2640272000PE_CONTINUATION_PUT_PUT.png`

### 20260402T094503|BFO:SENSEX2640271600CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271600CE`
- Entry/Exit: `2026-04-02 09:45:03` -> `2026-04-02 09:45:14` | Duration `10.90s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `369.35`, target `371.35`, exit `369.00` | Realized PnL `-175.00`
- Lifecycle read: Pre-entry option drift 3.05 points (index 11.72). After entry: first 1s move 0.40, first 3s move -5.10, in-trade range [-5.45, 0.40] points vs entry. Post-exit best/worst delta: 11.90 / 1.40, final @15s 10.90. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T094503_BFO_SENSEX2640271600CE_REVERSAL_CALL_CALL.png`

### 20260402T095006|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271900PE`
- Entry/Exit: `2026-04-02 09:50:06` -> `2026-04-02 09:50:10` | Duration `3.43s` | Exit reason `TARGET_HIT`
- Prices: entry `405.85`, target `408.85`, exit `408.85` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.75 points (index -17.71). After entry: first 1s move 2.20, first 3s move 2.25, in-trade range [-1.30, 3.15] points vs entry. Post-exit best/worst delta: 0.15 / -8.55, final @15s -4.85. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T095006_BFO_SENSEX2640271900PE_CONTINUATION_PUT_PUT.png`

### 20260402T095514|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271900PE`
- Entry/Exit: `2026-04-02 09:55:14` -> `2026-04-02 09:55:26` | Duration `11.64s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `427.70`, target `429.70`, exit `424.85` | Realized PnL `-1425.00`
- Lifecycle read: Pre-entry option drift 10.00 points (index -17.66). After entry: first 1s move -1.20, first 3s move -3.45, in-trade range [-4.00, 0.55] points vs entry. Post-exit best/worst delta: 1.45 / -4.00, final @15s -1.70. Exit quality mixed; post-exit path inconclusive.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T095514_BFO_SENSEX2640271900PE_CONTINUATION_PUT_PUT.png`

### 20260402T100001|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271800PE`
- Entry/Exit: `2026-04-02 10:00:01` -> `2026-04-02 10:00:03` | Duration `1.64s` | Exit reason `TARGET_HIT`
- Prices: entry `367.55`, target `370.55`, exit `370.55` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.80 points (index -6.53). After entry: first 1s move NA, first 3s move 6.45, in-trade range [6.45, 6.45] points vs entry. Post-exit best/worst delta: 28.30 / 1.35, final @15s 28.30. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T100001_BFO_SENSEX2640271800PE_CONTINUATION_PUT_PUT.png`

### 20260402T100508|BFO:SENSEX2640271800PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271800PE`
- Entry/Exit: `2026-04-02 10:05:09` -> `2026-04-02 10:05:17` | Duration `7.89s` | Exit reason `TARGET_HIT`
- Prices: entry `357.70`, target `360.70`, exit `360.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.60 points (index -8.52). After entry: first 1s move -2.10, first 3s move -4.25, in-trade range [-4.25, 3.80] points vs entry. Post-exit best/worst delta: 2.05 / -6.70, final @15s -6.70. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T100508_BFO_SENSEX2640271800PE_REVERSAL_PUT_PUT.png`

### 20260402T101003|BFO:SENSEX2640271700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271700PE`
- Entry/Exit: `2026-04-02 10:10:03` -> `2026-04-02 10:10:14` | Duration `11.58s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `327.45`, target `329.45`, exit `324.90` | Realized PnL `-1275.00`
- Lifecycle read: Pre-entry option drift 4.85 points (index -7.50). After entry: first 1s move -6.20, first 3s move -4.80, in-trade range [-7.60, -2.55] points vs entry. Post-exit best/worst delta: 1.75 / -3.25, final @15s -0.50. Exit quality mixed; post-exit path inconclusive.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T101003_BFO_SENSEX2640271700PE_CONTINUATION_PUT_PUT.png`

### 20260402T102537|BFO:SENSEX2640271400CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271400CE`
- Entry/Exit: `2026-04-02 10:25:38` -> `2026-04-02 10:25:48` | Duration `9.69s` | Exit reason `TARGET_HIT`
- Prices: entry `346.60`, target `348.60`, exit `348.60` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 2.15 points (index 32.95). After entry: first 1s move -3.65, first 3s move -0.30, in-trade range [-4.75, 6.40] points vs entry. Post-exit best/worst delta: 10.70 / -0.15, final @15s 9.55. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T102537_BFO_SENSEX2640271400CE_REVERSAL_CALL_CALL.png`

### 20260402T103529|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271800PE`
- Entry/Exit: `2026-04-02 10:35:30` -> `2026-04-02 10:35:44` | Duration `13.76s` | Exit reason `TARGET_HIT`
- Prices: entry `349.25`, target `351.25`, exit `351.25` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 4.75 points (index -4.05). After entry: first 1s move -1.70, first 3s move -1.65, in-trade range [-2.60, 2.15] points vs entry. Post-exit best/worst delta: 0.15 / -4.25, final @15s -1.40. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T103529_BFO_SENSEX2640271800PE_CONTINUATION_PUT_PUT.png`

### 20260402T104001|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271500CE`
- Entry/Exit: `2026-04-02 10:40:01` -> `2026-04-02 10:40:03` | Duration `1.40s` | Exit reason `TARGET_HIT`
- Prices: entry `302.70`, target `305.70`, exit `305.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.40 points (index 5.41). After entry: first 1s move NA, first 3s move 3.75, in-trade range [3.75, 3.75] points vs entry. Post-exit best/worst delta: 13.25 / -5.00, final @15s 11.75. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T104001_BFO_SENSEX2640271500CE_CONTINUATION_CALL_CALL.png`

### 20260402T104503|BFO:SENSEX2640271500CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271500CE`
- Entry/Exit: `2026-04-02 10:45:03` -> `2026-04-02 10:45:03` | Duration `-0.23s` | Exit reason `TARGET_HIT`
- Prices: entry `307.55`, target `310.55`, exit `310.55` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.30 points (index 1.29). After entry: first 1s move 4.45, first 3s move 4.45, in-trade range [4.45, 4.45] points vs entry. Post-exit best/worst delta: 1.45 / -5.45, final @15s -4.15. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T104503_BFO_SENSEX2640271500CE_REVERSAL_CALL_CALL.png`

### 20260402T105003|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271800PE`
- Entry/Exit: `2026-04-02 10:50:03` -> `2026-04-02 10:50:11` | Duration `7.10s` | Exit reason `TARGET_HIT`
- Prices: entry `347.80`, target `349.80`, exit `349.80` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift -1.35 points (index -8.66). After entry: first 1s move 1.35, first 3s move -2.45, in-trade range [-4.90, 2.00] points vs entry. Post-exit best/worst delta: 2.15 / -3.50, final @15s 2.15. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T105003_BFO_SENSEX2640271800PE_CONTINUATION_PUT_PUT.png`

### 20260402T110002|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271500CE`
- Entry/Exit: `2026-04-02 11:00:03` -> `2026-04-02 11:00:14` | Duration `11.88s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `355.00`, target `357.00`, exit `353.90` | Realized PnL `-550.00`
- Lifecycle read: Pre-entry option drift 9.90 points (index 8.24). After entry: first 1s move -5.35, first 3s move -3.70, in-trade range [-6.55, 0.55] points vs entry. Post-exit best/worst delta: 0.55 / -17.10, final @15s -17.10. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T110002_BFO_SENSEX2640271500CE_CONTINUATION_CALL_CALL.png`

### 20260402T110512|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271900PE`
- Entry/Exit: `2026-04-02 11:05:12` -> `2026-04-02 11:05:57` | Duration `44.64s` | Exit reason `HARD_STOP_EXIT`
- Prices: entry `356.40`, target `358.40`, exit `348.00` | Realized PnL `-4200.00`
- Lifecycle read: Pre-entry option drift -0.05 points (index -8.92). After entry: first 1s move -0.30, first 3s move 1.30, in-trade range [-13.90, 1.55] points vs entry. Post-exit best/worst delta: 10.50 / 0.00, final @15s 6.45. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T110512_BFO_SENSEX2640271900PE_CONTINUATION_PUT_PUT.png`

### 20260402T111008|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271900PE`
- Entry/Exit: `2026-04-02 11:10:08` -> `2026-04-02 11:10:12` | Duration `3.75s` | Exit reason `TARGET_HIT`
- Prices: entry `369.85`, target `372.85`, exit `372.85` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 7.80 points (index -7.57). After entry: first 1s move -0.95, first 3s move 0.65, in-trade range [-0.95, 11.85] points vs entry. Post-exit best/worst delta: 10.80 / 6.15, final @15s 8.75. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T111008_BFO_SENSEX2640271900PE_CONTINUATION_PUT_PUT.png`

### 20260402T111504|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271900PE`
- Entry/Exit: `2026-04-02 11:15:04` -> `2026-04-02 11:15:07` | Duration `2.61s` | Exit reason `TARGET_HIT`
- Prices: entry `373.50`, target `376.50`, exit `376.50` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.20 points (index -6.74). After entry: first 1s move 1.75, first 3s move 3.00, in-trade range [1.65, 3.00] points vs entry. Post-exit best/worst delta: -0.45 / -8.75, final @15s -0.45. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T111504_BFO_SENSEX2640271900PE_CONTINUATION_PUT_PUT.png`

### 20260402T112011|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271800PE`
- Entry/Exit: `2026-04-02 11:20:11` -> `2026-04-02 11:20:23` | Duration `11.72s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `330.35`, target `332.35`, exit `325.75` | Realized PnL `-2300.00`
- Lifecycle read: Pre-entry option drift 4.65 points (index -8.31). After entry: first 1s move -1.75, first 3s move -2.15, in-trade range [-5.45, -1.75] points vs entry. Post-exit best/worst delta: 9.95 / -4.15, final @15s 3.35. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T112011_BFO_SENSEX2640271800PE_CONTINUATION_PUT_PUT.png`

### 20260402T112509|BFO:SENSEX2640271800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271800PE`
- Entry/Exit: `2026-04-02 11:25:09` -> `2026-04-02 11:25:42` | Duration `33.14s` | Exit reason `PATH_RISK_EXIT`
- Prices: entry `331.65`, target `333.65`, exit `324.05` | Realized PnL `-3800.00`
- Lifecycle read: Pre-entry option drift 0.50 points (index -13.24). After entry: first 1s move -2.90, first 3s move -0.60, in-trade range [-7.60, 1.20] points vs entry. Post-exit best/worst delta: 10.05 / 4.15, final @15s 5.20. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T112509_BFO_SENSEX2640271800PE_CONTINUATION_PUT_PUT.png`

### 20260402T113536|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271500CE`
- Entry/Exit: `2026-04-02 11:35:36` -> `2026-04-02 11:35:38` | Duration `1.21s` | Exit reason `TARGET_HIT`
- Prices: entry `269.95`, target `272.95`, exit `272.95` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -1.25 points (index 2.44). After entry: first 1s move 0.70, first 3s move 3.15, in-trade range [0.70, 3.15] points vs entry. Post-exit best/worst delta: 6.75 / -0.40, final @15s 2.65. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T113536_BFO_SENSEX2640271500CE_CONTINUATION_CALL_CALL.png`

### 20260402T114006|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271500CE`
- Entry/Exit: `2026-04-02 11:40:07` -> `2026-04-02 11:40:10` | Duration `2.82s` | Exit reason `TARGET_HIT`
- Prices: entry `284.60`, target `287.60`, exit `287.60` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.75 points (index 4.41). After entry: first 1s move -2.65, first 3s move 3.25, in-trade range [-2.65, 3.25] points vs entry. Post-exit best/worst delta: 1.80 / -4.95, final @15s -3.80. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T114006_BFO_SENSEX2640271500CE_CONTINUATION_CALL_CALL.png`

### 20260402T114500|BFO:SENSEX2640271900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640271900PE`
- Entry/Exit: `2026-04-02 11:45:00` -> `2026-04-02 11:45:12` | Duration `11.26s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `381.65`, target `383.65`, exit `367.90` | Realized PnL `-6875.00`
- Lifecycle read: Pre-entry option drift 5.05 points (index -15.56). After entry: first 1s move -1.30, first 3s move -2.10, in-trade range [-16.60, -1.30] points vs entry. Post-exit best/worst delta: 5.15 / -0.85, final @15s 2.95. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T114500_BFO_SENSEX2640271900PE_CONTINUATION_PUT_PUT.png`

### 20260402T115016|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271500CE`
- Entry/Exit: `2026-04-02 11:50:17` -> `2026-04-02 11:50:37` | Duration `19.93s` | Exit reason `TARGET_HIT`
- Prices: entry `311.00`, target `313.00`, exit `313.00` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 1.40 points (index 5.70). After entry: first 1s move 1.05, first 3s move 1.20, in-trade range [-3.95, 3.85] points vs entry. Post-exit best/worst delta: 3.95 / -4.55, final @15s -3.50. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T115016_BFO_SENSEX2640271500CE_CONTINUATION_CALL_CALL.png`

### 20260402T115502|BFO:SENSEX2640271500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271500CE`
- Entry/Exit: `2026-04-02 11:55:02` -> `2026-04-02 11:55:33` | Duration `30.62s` | Exit reason `PATH_RISK_EXIT`
- Prices: entry `310.00`, target `312.00`, exit `304.10` | Realized PnL `-2950.00`
- Lifecycle read: Pre-entry option drift 5.25 points (index 6.47). After entry: first 1s move 1.20, first 3s move -2.55, in-trade range [-6.55, 1.20] points vs entry. Post-exit best/worst delta: 0.90 / -3.80, final @15s -3.80. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T115502_BFO_SENSEX2640271500CE_CONTINUATION_CALL_CALL.png`

### 20260402T120012|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271600CE`
- Entry/Exit: `2026-04-02 12:00:12` -> `2026-04-02 12:00:25` | Duration `12.69s` | Exit reason `TARGET_HIT`
- Prices: entry `326.05`, target `328.05`, exit `328.05` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 4.75 points (index 6.51). After entry: first 1s move -0.10, first 3s move -0.85, in-trade range [-4.75, 3.95] points vs entry. Post-exit best/worst delta: 7.95 / -6.00, final @15s 1.90. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T120012_BFO_SENSEX2640271600CE_CONTINUATION_CALL_CALL.png`

### 20260402T120519|BFO:SENSEX2640272000PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272000PE`
- Entry/Exit: `2026-04-02 12:05:19` -> `2026-04-02 12:05:38` | Duration `18.16s` | Exit reason `TARGET_HIT`
- Prices: entry `366.00`, target `368.00`, exit `368.00` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 12.15 points (index -5.77). After entry: first 1s move -3.05, first 3s move -1.90, in-trade range [-3.05, 2.80] points vs entry. Post-exit best/worst delta: 7.15 / -1.40, final @15s 6.35. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T120519_BFO_SENSEX2640272000PE_CONTINUATION_PUT_PUT.png`

### 20260402T121506|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271600CE`
- Entry/Exit: `2026-04-02 12:15:07` -> `2026-04-02 12:15:18` | Duration `11.46s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `288.55`, target `290.55`, exit `282.00` | Realized PnL `-3275.00`
- Lifecycle read: Pre-entry option drift 4.40 points (index 2.60). After entry: first 1s move -2.30, first 3s move -5.40, in-trade range [-9.05, -2.30] points vs entry. Post-exit best/worst delta: 2.60 / -11.55, final @15s -5.65. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T121506_BFO_SENSEX2640271600CE_CONTINUATION_CALL_CALL.png`

### 20260402T122513|BFO:SENSEX2640271600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271600CE`
- Entry/Exit: `2026-04-02 12:25:14` -> `2026-04-02 12:25:15` | Duration `0.72s` | Exit reason `TARGET_HIT`
- Prices: entry `262.10`, target `265.10`, exit `265.10` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.05 points (index 0.81). After entry: first 1s move 4.95, first 3s move 4.95, in-trade range [4.95, 4.95] points vs entry. Post-exit best/worst delta: 2.15 / -14.45, final @15s -12.90. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T122513_BFO_SENSEX2640271600CE_CONTINUATION_CALL_CALL.png`

### 20260402T123002|BFO:SENSEX2640271700CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271700CE`
- Entry/Exit: `2026-04-02 12:30:02` -> `2026-04-02 12:30:14` | Duration `11.59s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `285.55`, target `287.55`, exit `283.15` | Realized PnL `-1200.00`
- Lifecycle read: Pre-entry option drift 8.70 points (index 8.57). After entry: first 1s move -0.65, first 3s move -3.50, in-trade range [-7.05, 0.65] points vs entry. Post-exit best/worst delta: 3.80 / -9.90, final @15s -9.50. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T123002_BFO_SENSEX2640271700CE_CONTINUATION_CALL_CALL.png`

### 20260402T123501|BFO:SENSEX2640271800CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271800CE`
- Entry/Exit: `2026-04-02 12:35:02` -> `2026-04-02 12:35:13` | Duration `10.93s` | Exit reason `TARGET_HIT`
- Prices: entry `268.85`, target `270.85`, exit `270.85` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift -0.40 points (index 7.18). After entry: first 1s move -2.60, first 3s move -4.15, in-trade range [-4.15, 3.60] points vs entry. Post-exit best/worst delta: -0.30 / -27.25, final @15s -23.80. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T123501_BFO_SENSEX2640271800CE_CONTINUATION_CALL_CALL.png`

### 20260402T124004|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271900CE`
- Entry/Exit: `2026-04-02 12:40:04` -> `2026-04-02 12:40:08` | Duration `3.20s` | Exit reason `TARGET_HIT`
- Prices: entry `293.70`, target `296.70`, exit `296.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.40 points (index 1.62). After entry: first 1s move 2.15, first 3s move 1.80, in-trade range [1.80, 3.25] points vs entry. Post-exit best/worst delta: 15.20 / 0.40, final @15s 15.20. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T124004_BFO_SENSEX2640271900CE_CONTINUATION_CALL_CALL.png`

### 20260402T124504|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271900CE`
- Entry/Exit: `2026-04-02 12:45:04` -> `2026-04-02 12:45:04` | Duration `-0.32s` | Exit reason `TARGET_HIT`
- Prices: entry `314.45`, target `317.45`, exit `317.45` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.15 points (index 6.00). After entry: first 1s move 3.45, first 3s move 3.45, in-trade range [3.45, 3.45] points vs entry. Post-exit best/worst delta: 0.05 / -16.30, final @15s -16.30. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T124504_BFO_SENSEX2640271900CE_CONTINUATION_CALL_CALL.png`

### 20260402T130002|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271900CE`
- Entry/Exit: `2026-04-02 13:00:02` -> `2026-04-02 13:00:03` | Duration `0.00s` | Exit reason `TARGET_HIT`
- Prices: entry `310.80`, target `313.80`, exit `313.80` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 10.60 points (index 7.50). After entry: first 1s move 10.95, first 3s move 10.95, in-trade range [10.95, 10.95] points vs entry. Post-exit best/worst delta: 57.20 / -2.30, final @15s 54.45. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T130002_BFO_SENSEX2640271900CE_CONTINUATION_CALL_CALL.png`

### 20260402T130501|BFO:SENSEX2640271900CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640271900CE`
- Entry/Exit: `2026-04-02 13:05:01` -> `2026-04-02 13:05:03` | Duration `1.58s` | Exit reason `TARGET_HIT`
- Prices: entry `312.60`, target `315.60`, exit `315.60` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 0.65 points (index 8.97). After entry: first 1s move 2.25, first 3s move 0.90, in-trade range [0.90, 5.10] points vs entry. Post-exit best/worst delta: 6.90 / -8.05, final @15s -3.70. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T130501_BFO_SENSEX2640271900CE_CONTINUATION_CALL_CALL.png`

### 20260402T131028|BFO:SENSEX2640272300PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272300PE`
- Entry/Exit: `2026-04-02 13:10:29` -> `2026-04-02 13:10:40` | Duration `10.88s` | Exit reason `TARGET_HIT`
- Prices: entry `342.70`, target `344.70`, exit `344.70` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift -4.00 points (index -8.06). After entry: first 1s move -4.25, first 3s move -8.55, in-trade range [-8.55, 3.35] points vs entry. Post-exit best/worst delta: 5.95 / -1.80, final @15s 2.75. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T131028_BFO_SENSEX2640272300PE_REVERSAL_PUT_PUT.png`

### 20260402T131513|BFO:SENSEX2640272300PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272300PE`
- Entry/Exit: `2026-04-02 13:15:13` -> `2026-04-02 13:15:24` | Duration `11.63s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `331.30`, target `333.30`, exit `312.20` | Realized PnL `-9550.00`
- Lifecycle read: Pre-entry option drift 3.20 points (index -4.77). After entry: first 1s move -2.95, first 3s move -2.70, in-trade range [-19.10, 0.30] points vs entry. Post-exit best/worst delta: 4.20 / -6.80, final @15s -4.05. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T131513_BFO_SENSEX2640272300PE_CONTINUATION_PUT_PUT.png`

### 20260402T132018|BFO:SENSEX2640272000CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272000CE`
- Entry/Exit: `2026-04-02 13:20:19` -> `2026-04-02 13:20:51` | Duration `32.42s` | Exit reason `PATH_RISK_EXIT`
- Prices: entry `285.20`, target `287.20`, exit `279.25` | Realized PnL `-2975.00`
- Lifecycle read: Pre-entry option drift -4.45 points (index 7.70). After entry: first 1s move -0.95, first 3s move -2.65, in-trade range [-16.40, 2.40] points vs entry. Post-exit best/worst delta: 1.45 / -7.55, final @15s -7.55. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T132018_BFO_SENSEX2640272000CE_CONTINUATION_CALL_CALL.png`

### 20260402T132503|BFO:SENSEX2640272100CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272100CE`
- Entry/Exit: `2026-04-02 13:25:03` -> `2026-04-02 13:25:06` | Duration `2.37s` | Exit reason `TARGET_HIT`
- Prices: entry `338.75`, target `341.75`, exit `341.75` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.75 points (index 8.50). After entry: first 1s move -0.05, first 3s move 3.60, in-trade range [-0.05, 3.60] points vs entry. Post-exit best/worst delta: 21.20 / -4.35, final @15s 1.90. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T132503_BFO_SENSEX2640272100CE_CONTINUATION_CALL_CALL.png`

### 20260402T133000|BFO:SENSEX2640272300CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272300CE`
- Entry/Exit: `2026-04-02 13:30:01` -> `2026-04-02 13:30:06` | Duration `4.90s` | Exit reason `TARGET_HIT`
- Prices: entry `324.00`, target `327.00`, exit `327.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 13.45 points (index 16.37). After entry: first 1s move 2.45, first 3s move -1.25, in-trade range [-1.25, 3.10] points vs entry. Post-exit best/worst delta: 6.35 / -29.10, final @15s -3.40. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T133000_BFO_SENSEX2640272300CE_CONTINUATION_CALL_CALL.png`

### 20260402T133518|BFO:SENSEX2640272700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272700PE`
- Entry/Exit: `2026-04-02 13:35:18` -> `2026-04-02 13:35:20` | Duration `1.13s` | Exit reason `TARGET_HIT`
- Prices: entry `330.00`, target `333.00`, exit `333.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -5.30 points (index -9.38). After entry: first 1s move -0.10, first 3s move 4.35, in-trade range [-0.10, 4.35] points vs entry. Post-exit best/worst delta: 30.90 / 1.35, final @15s 25.30. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T133518_BFO_SENSEX2640272700PE_CONTINUATION_PUT_PUT.png`

### 20260402T134001|BFO:SENSEX2640272400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272400CE`
- Entry/Exit: `2026-04-02 13:40:02` -> `2026-04-02 13:40:07` | Duration `4.86s` | Exit reason `TARGET_HIT`
- Prices: entry `282.15`, target `285.15`, exit `285.15` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 1.15 points (index 4.22). After entry: first 1s move -2.40, first 3s move -5.20, in-trade range [-5.20, 3.15] points vs entry. Post-exit best/worst delta: 32.45 / 0.15, final @15s 16.60. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T134001_BFO_SENSEX2640272400CE_CONTINUATION_CALL_CALL.png`

### 20260402T134511|BFO:SENSEX2640272500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272500CE`
- Entry/Exit: `2026-04-02 13:45:12` -> `2026-04-02 13:45:12` | Duration `-0.08s` | Exit reason `TARGET_HIT`
- Prices: entry `271.05`, target `274.05`, exit `274.05` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.45 points (index 4.08). After entry: first 1s move 3.30, first 3s move 3.30, in-trade range [3.30, 3.30] points vs entry. Post-exit best/worst delta: 0.30 / -17.35, final @15s -6.75. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T134511_BFO_SENSEX2640272500CE_CONTINUATION_CALL_CALL.png`

### 20260402T135005|BFO:SENSEX2640272800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272800PE`
- Entry/Exit: `2026-04-02 13:50:05` -> `2026-04-02 13:50:17` | Duration `11.66s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `305.75`, target `307.75`, exit `300.20` | Realized PnL `-2775.00`
- Lifecycle read: Pre-entry option drift 15.50 points (index -14.48). After entry: first 1s move -2.35, first 3s move -2.75, in-trade range [-5.55, -2.05] points vs entry. Post-exit best/worst delta: -1.85 / -17.85, final @15s -17.85. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T135005_BFO_SENSEX2640272800PE_CONTINUATION_PUT_PUT.png`

### 20260402T135503|BFO:SENSEX2640272900PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272900PE`
- Entry/Exit: `2026-04-02 13:55:03` -> `2026-04-02 13:55:05` | Duration `1.13s` | Exit reason `TARGET_HIT`
- Prices: entry `360.95`, target `363.95`, exit `363.95` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.85 points (index -7.21). After entry: first 1s move 2.75, first 3s move 4.30, in-trade range [2.75, 4.30] points vs entry. Post-exit best/worst delta: 2.55 / -12.95, final @15s -5.10. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T135503_BFO_SENSEX2640272900PE_REVERSAL_PUT_PUT.png`

### 20260402T140002|BFO:SENSEX2640272800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640272800PE`
- Entry/Exit: `2026-04-02 14:00:02` -> `2026-04-02 14:00:05` | Duration `2.64s` | Exit reason `TARGET_HIT`
- Prices: entry `285.75`, target `288.75`, exit `288.75` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.15 points (index -20.29). After entry: first 1s move 0.95, first 3s move 3.75, in-trade range [0.95, 3.75] points vs entry. Post-exit best/worst delta: 5.90 / -8.50, final @15s 5.90. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T140002_BFO_SENSEX2640272800PE_CONTINUATION_PUT_PUT.png`

### 20260402T140510|BFO:SENSEX2640272500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272500CE`
- Entry/Exit: `2026-04-02 14:05:11` -> `2026-04-02 14:05:11` | Duration `-0.05s` | Exit reason `TARGET_HIT`
- Prices: entry `289.55`, target `292.55`, exit `292.55` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.05 points (index 12.92). After entry: first 1s move 3.40, first 3s move 3.40, in-trade range [3.40, 3.40] points vs entry. Post-exit best/worst delta: 3.90 / -1.25, final @15s 3.90. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T140510_BFO_SENSEX2640272500CE_CONTINUATION_CALL_CALL.png`

### 20260402T141007|BFO:SENSEX2640272600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272600CE`
- Entry/Exit: `2026-04-02 14:10:07` -> `2026-04-02 14:10:16` | Duration `8.69s` | Exit reason `TARGET_HIT`
- Prices: entry `249.45`, target `251.45`, exit `251.45` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift -3.45 points (index 10.07). After entry: first 1s move -4.80, first 3s move -3.80, in-trade range [-6.40, 2.55] points vs entry. Post-exit best/worst delta: 0.55 / -16.65, final @15s -0.95. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T141007_BFO_SENSEX2640272600CE_CONTINUATION_CALL_CALL.png`

### 20260402T141503|BFO:SENSEX2640272800CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272800CE`
- Entry/Exit: `2026-04-02 14:15:03` -> `2026-04-02 14:15:04` | Duration `0.19s` | Exit reason `TARGET_HIT`
- Prices: entry `254.05`, target `257.05`, exit `257.05` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.40 points (index 5.07). After entry: first 1s move 3.20, first 3s move 3.20, in-trade range [3.20, 3.20] points vs entry. Post-exit best/worst delta: 5.85 / -3.35, final @15s 4.05. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T141503_BFO_SENSEX2640272800CE_CONTINUATION_CALL_CALL.png`

### 20260402T142013|BFO:SENSEX2640272900CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272900CE`
- Entry/Exit: `2026-04-02 14:20:13` -> `2026-04-02 14:20:44` | Duration `31.20s` | Exit reason `HARD_STOP_EXIT`
- Prices: entry `259.20`, target `261.20`, exit `245.60` | Realized PnL `-6800.00`
- Lifecycle read: Pre-entry option drift 18.30 points (index 26.70). After entry: first 1s move 0.65, first 3s move 1.70, in-trade range [-21.70, 1.70] points vs entry. Post-exit best/worst delta: 16.40 / 2.30, final @15s 8.35. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T142013_BFO_SENSEX2640272900CE_CONTINUATION_CALL_CALL.png`

### 20260402T142500|BFO:SENSEX2640272900CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272900CE`
- Entry/Exit: `2026-04-02 14:25:00` -> `2026-04-02 14:25:00` | Duration `-0.36s` | Exit reason `TARGET_HIT`
- Prices: entry `296.45`, target `299.45`, exit `299.45` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 6.70 points (index 14.72). After entry: first 1s move 3.60, first 3s move 3.60, in-trade range [0.00, 3.60] points vs entry. Post-exit best/worst delta: 33.20 / -5.95, final @15s 18.35. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T142500_BFO_SENSEX2640272900CE_CONTINUATION_CALL_CALL.png`

### 20260402T143004|BFO:SENSEX2640273300PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273300PE`
- Entry/Exit: `2026-04-02 14:30:04` -> `2026-04-02 14:30:07` | Duration `2.57s` | Exit reason `TARGET_HIT`
- Prices: entry `256.70`, target `259.70`, exit `259.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.10 points (index -9.35). After entry: first 1s move 1.45, first 3s move 7.20, in-trade range [1.45, 7.20] points vs entry. Post-exit best/worst delta: 7.95 / -8.40, final @15s 0.70. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T143004_BFO_SENSEX2640273300PE_REVERSAL_PUT_PUT.png`

### 20260402T143500|BFO:SENSEX2640273000CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273000CE`
- Entry/Exit: `2026-04-02 14:35:00` -> `2026-04-02 14:35:11` | Duration `11.64s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `254.65`, target `256.65`, exit `235.15` | Realized PnL `-9750.00`
- Lifecycle read: Pre-entry option drift 28.05 points (index 26.88). After entry: first 1s move -9.25, first 3s move -16.65, in-trade range [-23.20, -4.00] points vs entry. Post-exit best/worst delta: 3.15 / -9.60, final @15s -7.05. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T143500_BFO_SENSEX2640273000CE_CONTINUATION_CALL_CALL.png`

### 20260402T144000|BFO:SENSEX2640273200PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273200PE`
- Entry/Exit: `2026-04-02 14:40:00` -> `2026-04-02 14:40:11` | Duration `10.93s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `269.85`, target `271.85`, exit `268.90` | Realized PnL `-475.00`
- Lifecycle read: Pre-entry option drift -6.60 points (index -4.35). After entry: first 1s move NA, first 3s move -6.05, in-trade range [-15.45, -0.95] points vs entry. Post-exit best/worst delta: 30.10 / -3.75, final @15s 17.75. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T144000_BFO_SENSEX2640273200PE_CONTINUATION_PUT_PUT.png`

### 20260402T144507|BFO:SENSEX2640273000PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273000PE`
- Entry/Exit: `2026-04-02 14:45:08` -> `2026-04-02 14:45:19` | Duration `11.59s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `272.40`, target `274.40`, exit `267.35` | Realized PnL `-2525.00`
- Lifecycle read: Pre-entry option drift -0.60 points (index -6.26). After entry: first 1s move -5.85, first 3s move -5.50, in-trade range [-9.40, -3.50] points vs entry. Post-exit best/worst delta: 27.95 / 2.60, final @15s 17.70. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T144507_BFO_SENSEX2640273000PE_CONTINUATION_PUT_PUT.png`

### 20260402T145015|BFO:SENSEX2640272800CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640272800CE`
- Entry/Exit: `2026-04-02 14:50:15` -> `2026-04-02 14:50:16` | Duration `0.37s` | Exit reason `TARGET_HIT`
- Prices: entry `195.60`, target `198.60`, exit `198.60` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 0.00 points (index 35.26). After entry: first 1s move 8.35, first 3s move 8.35, in-trade range [8.35, 8.35] points vs entry. Post-exit best/worst delta: 48.45 / 2.70, final @15s 16.40. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts/20260402T145015_BFO_SENSEX2640272800CE_CONTINUATION_CALL_CALL.png`

## 5. Visualizations
- Session-level charts:
  - session_trade_timeline: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/session_trade_timeline.png`
  - pnl_distribution: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/pnl_distribution.png`
  - duration_distribution: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/duration_distribution.png`
  - mfe_vs_mae: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/mfe_vs_mae_scatter.png`
  - pnl_vs_mfe: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/pnl_vs_mfe_scatter.png`
  - entry_first_5s_path_behavior: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/entry_first_5s_path_behavior.png`
  - runtime_health_timeseries_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/runtime_health_timeseries.csv`
  - runtime_stability: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/runtime_stability.png`
  - counterfactual_summary_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/counterfactual_summary.csv`
  - time_of_day_summary_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/time_of_day_summary.csv`
  - runtime_stress_by_time_bucket_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/runtime_stress_by_time_bucket.csv`
- Per-trade charts:
  - Count generated: **57**
  - Folder: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-02/trade_charts`

## 6. Microstructure Feature Analysis
### Winners vs Losers
| feature | winner_mean | loser_mean | winner_median | loser_median |
| --- | --- | --- | --- | --- |
| entry_spread | 0.84 | 0.85 | 0.80 | 0.90 |
| spread_median_first_2s | 0.86 | 0.86 | 0.85 | 0.88 |
| imbalance_entry | -0.01 | -0.06 | -0.05 | -0.03 |
| imbalance_drift_first_2s | 0.03 | 0.11 | 0.02 | 0.17 |
| pre_entry_velocity | 1.11 | 1.85 | 1.06 | 1.60 |
| first_1s_move | 0.94 | -2.55 | 1.20 | -2.03 |
| first_3s_move | 1.92 | -3.91 | 3.18 | -3.45 |
| in_trade_max_points | 4.37 | -0.53 | 3.60 | 0.30 |
| in_trade_min_points | -0.01 | -11.15 | -0.03 | -9.05 |
| post_exit_best_delta | 10.49 | 7.87 | 5.92 | 4.20 |
| post_exit_final_delta | 3.50 | 0.07 | 1.90 | -0.50 |
| holding_seconds | 4.65 | 17.50 | 2.62 | 11.64 |

### Small Losers vs Tail Losers
- Loser count: **19**, tail-loss threshold (median loser pnl): **-2950.00**
- Tail losers average first_3s_move: **-3.72**, average post_exit_best_delta: **6.39**
- Smaller losers average first_3s_move: **-4.11**, average post_exit_best_delta: **9.51**

### Continuation/Reversal and Fragility Views
- Continuation trades: **50**, avg pnl `-470.50`
- Reversal trades: **7**, avg pnl `1117.86`
- Fragile trades: **29**, avg pnl `-1989.66`
- Non-fragile trades: **28**, avg pnl `1500.00`

### Early-Day vs Late-Day
- Early (before 11:30): **21** trades, hit rate `61.90%` avg pnl `-50.00`
- Late (after 13:00): **23** trades, hit rate `69.57%` avg pnl `-515.22`

## 7. Exit Quality Analysis
- Target exits: **38**, share of target exits with post-exit fade (< -3 points final delta): **36.84%**
- Non-target exits: **19**, share with post-exit rebound >= +3 points: **63.16%**
- Exit reason mix: TARGET_HIT: 38, EARLY_RISK_EXIT: 14, PATH_RISK_EXIT: 3, HARD_STOP_EXIT: 2
- Share of trades that nearly reached target without in-trade touch: **3.51%**

## 8. Counterfactual / What-if Analysis
| target_points | touch_rate_all | touch_rate_winners | touch_rate_losers |
| --- | --- | --- | --- |
| 2.00 | 0.68 | 1.00 | 0.05 |
| 3.00 | 0.58 | 0.87 | 0.00 |
| 4.00 | 0.23 | 0.34 | 0.00 |
| 5.00 | 0.14 | 0.21 | 0.00 |
| weak_follow_through_warning | 0.37 | 0.16 | 0.79 |
| non_target_exits_post_exit_target_touch | 0.37 | NA | NA |
- Interpretation: target-touch counterfactuals are descriptive only; they do not model fill quality, queueing, or order-state interactions.

## 9. Time-of-Day Analysis
| bucket_type | bucket | trades | wins | losses | hit_rate | avg_pnl | median_pnl | tail_loss_count | tail_loss_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bucket_pre_post_1pm | POST_1PM | 23 | 16 | 7 | 0.70 | -515.22 | 1500.00 | 3 | 0.13 |
| bucket_pre_post_1pm | PRE_1PM | 34 | 22 | 12 | 0.65 | -113.24 | 1000.00 | 4 | 0.12 |
| bucket_3way | EARLY_SESSION | 15 | 11 | 4 | 0.73 | 453.33 | 1000.00 | 2 | 0.13 |
| bucket_3way | LATE_SESSION | 23 | 16 | 7 | 0.70 | -515.22 | 1500.00 | 3 | 0.13 |
| bucket_3way | MID_SESSION | 19 | 11 | 8 | 0.58 | -560.53 | 1000.00 | 2 | 0.11 |

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
- [strategy behavior insight] 79% of losing trades showed weak immediate follow-through (first 1s <= 0 and <1 point max gain in first 3s).
- [execution insight] 63% of losing trades had >=3 points of post-exit rebound, suggesting some exits were defensive but potentially early.
- [strategy behavior insight] 71% of winning trades closed within 5 seconds, consistent with a fast-follow-through payoff profile.
- [candidate microstructure filter idea] In-trade option spread difference (loss-win) was 0.00 points; spread alone appears weak as a discriminator in this sample.
- [candidate microstructure filter idea] First-3-second move was -5.82 points lower in losers vs winners, making early path momentum a stronger candidate signal than spread/imbalance.
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