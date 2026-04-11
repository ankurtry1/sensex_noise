# Session Report (2026-04-01)

Analyzed date: **2026-04-01**

## Data Inputs Used
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trades/2026-04-01.trades_enriched.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trades/2026-04-01.trades.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/events/2026-04-01.events.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/ticks/2026-04-01/sensex.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/ticks/2026-04-01/futures.jsonl`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/logs/trade_ticks/2026-04-01`
- `/Users/ankurkumar/Downloads/sensex-noise-papertrade/runtime/control.json`

## 1. Executive Summary
- Trades: **57**
- Wins / Losses / Flat: **41 / 16 / 0**
- Gross PnL: **-21925.00**
- Net PnL: **-21925.00**
- Average Winner: **1463.41**
- Average Loser: **-5120.31**
- Largest Win: **1500.00**
- Largest Loss: **-13400.00**
- Hit Rate: **71.93%**
- Expectancy per Trade: **-384.65**
- Day Pattern: **Many small wins offset by a few tail losses**

## 2. System Health / Runtime Summary
- STREAM_CONNECTED events: **1**
- Stream close events: **0**
- Reconnect-related events: **0**
- Watchdog-related events: **0**
- Stream degraded/recovered events: **0 / 0**
- Entry deferred (quote unavailable): **0**
- Lattice rebases: **569**
- Queue/backpressure explicit events: **0**
- Max runtime tick drops: **0**
- Max critical tick drops: **0**
- Max background tick drops: **0**
- Max journal drops: **0**
- Queue max sizes seen (critical/background/journal): **5 / 22 / 16**
- Inference trustworthiness: **True**
- Data-quality assessment: No drop/backpressure evidence and no degradation incidents in session telemetry; data quality appears reliable for behavioral inference.

## 3. Trade Ledger Table
| trade_id | entry_time | exit_time | holding_seconds | side | symbol | entry_price | exit_price | target_price | mfe | mae | net_pnl | exit_reason | exit_timing_assessment | target_nearly_reached | post_exit_best_delta | post_exit_final_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260401T092011|BFO:SENSEX2640273600CE|REVERSAL_CALL|CALL | 09:20:11 | 09:20:12 | 0.52 | CALL | BFO:SENSEX2640273600CE | 688.20 | 691.20 | 691.20 | 6.95 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 4.85 | -8.10 |
| 20260401T092501|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL | 09:25:01 | 09:25:06 | 4.08 | CALL | BFO:SENSEX2640273600CE | 658.00 | 661.00 | 661.00 | 3.15 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 3.40 | 3.40 |
| 20260401T093005|BFO:SENSEX2640273700CE|CONTINUATION_CALL|CALL | 09:30:05 | 09:30:07 | 1.40 | CALL | BFO:SENSEX2640273700CE | 648.25 | 651.25 | 651.25 | 6.40 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 5.85 | -2.65 |
| 20260401T093501|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT | 09:35:01 | 09:35:02 | 0.84 | PUT | BFO:SENSEX2640273800PE | 607.90 | 610.90 | 610.90 | 4.85 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 28.75 | 28.75 |
| 20260401T094027|BFO:SENSEX2640273400CE|REVERSAL_CALL|CALL | 09:40:27 | 09:40:30 | 2.31 | CALL | BFO:SENSEX2640273400CE | 691.65 | 694.65 | 694.65 | 4.40 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 9.05 | 5.85 |
| 20260401T094516|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL | 09:45:16 | 09:45:23 | 6.83 | CALL | BFO:SENSEX2640273500CE | 655.20 | 658.20 | 658.20 | 4.60 | -2.10 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 4.05 | -1.10 |
| 20260401T095039|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL | 09:50:39 | 09:50:51 | 11.63 | CALL | BFO:SENSEX2640273600CE | 651.85 | 649.20 | 653.85 | 0.15 | -4.45 | -1325.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 13.40 | 13.25 |
| 20260401T095505|BFO:SENSEX2640273700CE|CONTINUATION_CALL|CALL | 09:55:05 | 09:55:07 | 1.64 | CALL | BFO:SENSEX2640273700CE | 617.45 | 620.45 | 620.45 | 3.40 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 1.65 | -6.30 |
| 20260401T100019|BFO:SENSEX2640274000PE|CONTINUATION_PUT|PUT | 10:00:19 | 10:00:31 | 12.09 | PUT | BFO:SENSEX2640274000PE | 593.85 | 569.80 | 595.85 | 0.00 | -24.05 | -12025.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 6.35 | 5.50 |
| 20260401T100511|BFO:SENSEX2640273700CE|CONTINUATION_CALL|CALL | 10:05:11 | 10:05:40 | 28.58 | CALL | BFO:SENSEX2640273700CE | 657.60 | 659.60 | 659.60 | 3.20 | -7.70 | 1000.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 0.45 | -17.45 |
| 20260401T101005|BFO:SENSEX2640274000PE|CONTINUATION_PUT|PUT | 10:10:05 | 10:10:06 | 0.04 | PUT | BFO:SENSEX2640274000PE | 565.25 | 568.25 | 568.25 | 3.60 | -1.50 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 3.15 | -0.25 |
| 20260401T102005|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL | 10:20:06 | 10:20:18 | 12.03 | CALL | BFO:SENSEX2640273500CE | 672.85 | 663.30 | 674.85 | 0.00 | -9.55 | -4775.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 4.25 | 1.50 |
| 20260401T102513|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT | 10:25:13 | 10:25:19 | 5.13 | PUT | BFO:SENSEX2640273800PE | 595.70 | 598.70 | 598.70 | 6.40 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 21.30 | 21.30 |
| 20260401T103022|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT | 10:30:22 | 10:30:23 | 0.56 | PUT | BFO:SENSEX2640273700PE | 620.30 | 623.30 | 623.30 | 4.65 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.85 | 5.70 |
| 20260401T103515|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL | 10:35:15 | 10:35:21 | 5.36 | CALL | BFO:SENSEX2640273300CE | 661.25 | 664.25 | 664.25 | 3.60 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 0.60 | -4.70 |
| 20260401T104512|BFO:SENSEX2640273700PE|REVERSAL_PUT|PUT | 10:45:12 | 10:45:14 | 1.06 | PUT | BFO:SENSEX2640273700PE | 581.50 | 584.50 | 584.50 | 3.05 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | -4.10 | -9.05 |
| 20260401T105015|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT | 10:50:15 | 10:50:17 | 1.30 | PUT | BFO:SENSEX2640273700PE | 596.85 | 599.85 | 599.85 | 4.35 | -0.55 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 3.85 | 0.55 |
| 20260401T105510|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT | 10:55:10 | 10:55:14 | 3.09 | PUT | BFO:SENSEX2640273700PE | 597.40 | 600.40 | 600.40 | 3.05 | -0.85 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 10.15 | 10.15 |
| 20260401T110001|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT | 11:00:01 | 11:00:01 | -0.70 | PUT | BFO:SENSEX2640273600PE | 573.00 | 576.00 | 576.00 | 5.15 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 8.90 | 7.70 |
| 20260401T110503|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT | 11:05:04 | 11:05:09 | 4.94 | PUT | BFO:SENSEX2640273600PE | 602.70 | 605.70 | 605.70 | 3.60 | -0.15 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 8.80 | 8.80 |
| 20260401T111018|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL | 11:10:18 | 11:10:21 | 2.46 | CALL | BFO:SENSEX2640273200CE | 664.10 | 667.10 | 667.10 | 3.35 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 9.70 | 9.70 |
| 20260401T112006|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL | 11:20:06 | 11:20:18 | 11.99 | CALL | BFO:SENSEX2640273200CE | 656.35 | 650.05 | 658.35 | 0.00 | -7.45 | -3150.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 7.25 | 7.25 |
| 20260401T112519|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL | 11:25:19 | 11:25:27 | 7.70 | CALL | BFO:SENSEX2640273300CE | 630.70 | 633.70 | 633.70 | 4.85 | -4.10 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 3.20 | -0.85 |
| 20260401T113030|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL | 11:30:32 | 11:30:38 | 5.99 | CALL | BFO:SENSEX2640273300CE | 642.75 | 645.75 | 645.75 | 6.65 | -3.35 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.65 | 7.65 |
| 20260401T113510|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL | 11:35:10 | 11:35:23 | 13.14 | CALL | BFO:SENSEX2640273300CE | 660.30 | 658.75 | 662.30 | 0.25 | -4.45 | -775.00 | EARLY_RISK_EXIT | Mixed / inconclusive timing | False | 0.00 | -2.50 |
| 20260401T114001|BFO:SENSEX2640273400CE|CONTINUATION_CALL|CALL | 11:40:02 | 11:40:16 | 13.91 | CALL | BFO:SENSEX2640273400CE | 613.05 | 615.05 | 615.05 | 2.45 | -5.35 | 1000.00 | TARGET_HIT | Reasonable target exit | True | 4.95 | -0.50 |
| 20260401T114502|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT | 11:45:02 | 11:45:08 | 5.66 | PUT | BFO:SENSEX2640273700PE | 548.00 | 551.00 | 551.00 | 4.00 | -1.20 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.80 | 2.20 |
| 20260401T115509|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT | 11:55:09 | 11:55:21 | 11.26 | PUT | BFO:SENSEX2640273600PE | 580.00 | 582.00 | 582.00 | 2.35 | -2.25 | 1000.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.80 | -5.30 |
| 20260401T120007|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL | 12:00:07 | 12:00:08 | 0.74 | CALL | BFO:SENSEX2640273300CE | 606.55 | 609.55 | 609.55 | 5.05 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 28.80 | 25.15 |
| 20260401T120526|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL | 12:05:26 | 12:05:27 | 0.18 | CALL | BFO:SENSEX2640273500CE | 622.85 | 625.85 | 625.85 | 4.95 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 1.95 | -5.25 |
| 20260401T121025|BFO:SENSEX2640273900PE|REVERSAL_PUT|PUT | 12:10:25 | 12:10:26 | 0.71 | PUT | BFO:SENSEX2640273900PE | 555.80 | 558.80 | 558.80 | 4.45 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 16.20 | 9.80 |
| 20260401T121509|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL | 12:15:09 | 12:15:42 | 33.17 | CALL | BFO:SENSEX2640273500CE | 656.85 | 634.65 | 658.85 | 1.50 | -10.05 | -11100.00 | PATH_RISK_EXIT | Possibly early; post-exit recovery | True | 6.00 | 6.00 |
| 20260401T122013|BFO:SENSEX2640273900PE|CONTINUATION_PUT|PUT | 12:20:13 | 12:20:16 | 2.65 | PUT | BFO:SENSEX2640273900PE | 562.30 | 565.30 | 565.30 | 5.55 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 4.35 | 4.35 |
| 20260401T122509|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT | 12:25:10 | 12:25:27 | 16.90 | PUT | BFO:SENSEX2640273800PE | 512.70 | 515.70 | 515.70 | 3.30 | -0.60 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 2.05 | -5.25 |
| 20260401T123002|BFO:SENSEX2640273500CE|REVERSAL_CALL|CALL | 12:30:02 | 12:30:03 | 0.43 | CALL | BFO:SENSEX2640273500CE | 608.40 | 611.40 | 611.40 | 5.50 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 8.55 | 8.55 |
| 20260401T123531|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT | 12:35:31 | 12:35:37 | 5.41 | PUT | BFO:SENSEX2640273800PE | 518.00 | 521.00 | 521.00 | 4.25 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 5.25 | 4.75 |
| 20260401T124002|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL | 12:40:02 | 12:40:04 | 1.16 | CALL | BFO:SENSEX2640273500CE | 630.00 | 633.00 | 633.00 | 3.50 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 14.80 | 10.20 |
| 20260401T124521|BFO:SENSEX2640273500CE|REVERSAL_CALL|CALL | 12:45:21 | 12:45:21 | -0.44 | CALL | BFO:SENSEX2640273500CE | 614.85 | 617.85 | 617.85 | 3.00 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 14.90 | 14.90 |
| 20260401T125027|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL | 12:50:28 | 12:50:39 | 11.89 | CALL | BFO:SENSEX2640273600CE | 605.30 | 602.55 | 607.30 | 0.70 | -5.95 | -1375.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 11.05 | 10.80 |
| 20260401T125532|BFO:SENSEX2640273600CE|REVERSAL_CALL|CALL | 12:55:32 | 12:56:07 | 34.61 | CALL | BFO:SENSEX2640273600CE | 612.05 | 606.55 | 614.05 | 1.85 | -8.95 | -2750.00 | PATH_RISK_EXIT | Possibly early; post-exit recovery | True | 5.45 | -7.20 |
| 20260401T130002|BFO:SENSEX2640274000PE|CONTINUATION_PUT|PUT | 13:00:02 | 13:00:34 | 31.36 | PUT | BFO:SENSEX2640274000PE | 553.15 | 545.00 | 555.15 | 1.70 | -8.15 | -4075.00 | HARD_STOP_EXIT | Likely justified; weakness persisted | True | 0.00 | -4.65 |
| 20260401T130506|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL | 13:05:07 | 13:05:19 | 12.42 | CALL | BFO:SENSEX2640273600CE | 606.50 | 606.40 | 609.50 | 1.05 | -3.45 | -50.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 4.35 | 4.35 |
| 20260401T131505|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL | 13:15:06 | 13:15:06 | -0.13 | CALL | BFO:SENSEX2640273600CE | 643.05 | 646.05 | 646.05 | 3.60 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 16.75 | 15.30 |
| 20260401T132002|BFO:SENSEX2640273900PE|CONTINUATION_PUT|PUT | 13:20:02 | 13:20:07 | 4.43 | PUT | BFO:SENSEX2640273900PE | 521.15 | 524.15 | 524.15 | 3.85 | 0.00 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 2.20 | 2.20 |
| 20260401T133009|BFO:SENSEX2640273800PE|REVERSAL_PUT|PUT | 13:30:09 | 13:30:21 | 11.64 | PUT | BFO:SENSEX2640273800PE | 554.95 | 548.20 | 556.95 | 0.00 | -8.80 | -3375.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 5.80 | 5.80 |
| 20260401T133503|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT | 13:35:03 | 13:35:07 | 3.50 | PUT | BFO:SENSEX2640273700PE | 564.50 | 567.50 | 567.50 | 3.85 | -1.10 | 1500.00 | TARGET_HIT | Reasonable target exit | True | 2.40 | -1.65 |
| 20260401T134000|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT | 13:40:00 | 13:40:02 | 1.05 | PUT | BFO:SENSEX2640273600PE | 531.85 | 534.85 | 534.85 | 3.85 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 24.45 | 24.45 |
| 20260401T134504|BFO:SENSEX2640273300PE|CONTINUATION_PUT|PUT | 13:45:04 | 13:45:04 | -0.34 | PUT | BFO:SENSEX2640273300PE | 609.25 | 612.25 | 612.25 | 5.30 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 9.10 | 4.55 |
| 20260401T135506|BFO:SENSEX2640273400PE|CONTINUATION_PUT|PUT | 13:55:06 | 13:55:07 | 0.28 | PUT | BFO:SENSEX2640273400PE | 566.65 | 569.65 | 569.65 | 4.95 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 7.30 | 1.80 |
| 20260401T140003|BFO:SENSEX2640273100CE|CONTINUATION_CALL|CALL | 14:00:04 | 14:00:16 | 12.50 | CALL | BFO:SENSEX2640273100CE | 582.75 | 576.85 | 584.75 | 1.00 | -5.90 | -2950.00 | EARLY_RISK_EXIT | Possibly early; post-exit recovery | False | 4.15 | 4.15 |
| 20260401T141001|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL | 14:10:02 | 14:10:34 | 31.63 | CALL | BFO:SENSEX2640273200CE | 571.80 | 549.90 | 573.80 | 1.70 | -21.90 | -10950.00 | HARD_STOP_EXIT | Possibly early; post-exit recovery | True | 8.85 | 6.55 |
| 20260401T141504|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL | 14:15:04 | 14:15:07 | 2.40 | CALL | BFO:SENSEX2640273200CE | 603.65 | 606.65 | 606.65 | 5.25 | 0.00 | 1500.00 | TARGET_HIT | Timely target exit; post-exit fade | True | 1.70 | -8.25 |
| 20260401T142513|BFO:SENSEX2640273500PE|CONTINUATION_PUT|PUT | 14:25:14 | 14:25:45 | 31.60 | PUT | BFO:SENSEX2640273500PE | 568.20 | 541.40 | 570.20 | 1.50 | -26.80 | -13400.00 | HARD_STOP_EXIT | Likely justified; weakness persisted | True | 1.30 | -5.35 |
| 20260401T143006|BFO:SENSEX2640273100CE|CONTINUATION_CALL|CALL | 14:30:06 | 14:30:39 | 32.46 | CALL | BFO:SENSEX2640273100CE | 625.90 | 607.60 | 627.90 | 1.90 | -20.85 | -9150.00 | HARD_STOP_EXIT | Likely justified; weakness persisted | True | 1.60 | -6.25 |
| 20260401T143511|BFO:SENSEX2640273400PE|CONTINUATION_PUT|PUT | 14:35:11 | 14:35:14 | 2.12 | PUT | BFO:SENSEX2640273400PE | 535.70 | 538.70 | 538.70 | 3.15 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 5.70 | 5.70 |
| 20260401T144006|BFO:SENSEX2640273300PE|CONTINUATION_PUT|PUT | 14:40:06 | 14:40:08 | 1.48 | PUT | BFO:SENSEX2640273300PE | 552.35 | 555.35 | 555.35 | 6.35 | 0.00 | 1500.00 | TARGET_HIT | Captured target; additional upside remained | True | 25.30 | 19.15 |
| 20260401T144505|BFO:SENSEX2640273300PE|CONTINUATION_PUT|PUT | 14:45:06 | 14:45:21 | 15.40 | PUT | BFO:SENSEX2640273300PE | 564.50 | 563.10 | 566.50 | 1.90 | -6.80 | -700.00 | EARLY_RISK_EXIT | Likely justified; weakness persisted | True | -2.30 | -3.10 |

## 4. Full Trade Lifecycle Analysis (Per Trade)
### 20260401T092011|BFO:SENSEX2640273600CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273600CE`
- Entry/Exit: `2026-04-01 09:20:11` -> `2026-04-01 09:20:12` | Duration `0.52s` | Exit reason `TARGET_HIT`
- Prices: entry `688.20`, target `691.20`, exit `691.20` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -6.90 points (index 7.20). After entry: first 1s move 6.95, first 3s move 6.95, in-trade range [6.95, 6.95] points vs entry. Post-exit best/worst delta: 4.85 / -17.40, final @15s -8.10. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T092011_BFO_SENSEX2640273600CE_REVERSAL_CALL_CALL.png`

### 20260401T092501|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273600CE`
- Entry/Exit: `2026-04-01 09:25:01` -> `2026-04-01 09:25:06` | Duration `4.08s` | Exit reason `TARGET_HIT`
- Prices: entry `658.00`, target `661.00`, exit `661.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.80 points (index 6.87). After entry: first 1s move 1.95, first 3s move 1.15, in-trade range [0.55, 3.15] points vs entry. Post-exit best/worst delta: 3.40 / -3.95, final @15s 3.40. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T092501_BFO_SENSEX2640273600CE_CONTINUATION_CALL_CALL.png`

### 20260401T093005|BFO:SENSEX2640273700CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273700CE`
- Entry/Exit: `2026-04-01 09:30:05` -> `2026-04-01 09:30:07` | Duration `1.40s` | Exit reason `TARGET_HIT`
- Prices: entry `648.25`, target `651.25`, exit `651.25` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.85 points (index 19.47). After entry: first 1s move 0.40, first 3s move 6.40, in-trade range [0.40, 6.40] points vs entry. Post-exit best/worst delta: 5.85 / -6.30, final @15s -2.65. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T093005_BFO_SENSEX2640273700CE_CONTINUATION_CALL_CALL.png`

### 20260401T093501|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273800PE`
- Entry/Exit: `2026-04-01 09:35:01` -> `2026-04-01 09:35:02` | Duration `0.84s` | Exit reason `TARGET_HIT`
- Prices: entry `607.90`, target `610.90`, exit `610.90` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.45 points (index -11.25). After entry: first 1s move 4.85, first 3s move 4.85, in-trade range [2.65, 4.85] points vs entry. Post-exit best/worst delta: 28.75 / 1.85, final @15s 28.75. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T093501_BFO_SENSEX2640273800PE_CONTINUATION_PUT_PUT.png`

### 20260401T094027|BFO:SENSEX2640273400CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273400CE`
- Entry/Exit: `2026-04-01 09:40:27` -> `2026-04-01 09:40:30` | Duration `2.31s` | Exit reason `TARGET_HIT`
- Prices: entry `691.65`, target `694.65`, exit `694.65` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 6.85 points (index 14.58). After entry: first 1s move 1.35, first 3s move 4.40, in-trade range [1.35, 4.40] points vs entry. Post-exit best/worst delta: 9.05 / 0.55, final @15s 5.85. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T094027_BFO_SENSEX2640273400CE_REVERSAL_CALL_CALL.png`

### 20260401T094516|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273500CE`
- Entry/Exit: `2026-04-01 09:45:16` -> `2026-04-01 09:45:23` | Duration `6.83s` | Exit reason `TARGET_HIT`
- Prices: entry `655.20`, target `658.20`, exit `658.20` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.15 points (index 3.11). After entry: first 1s move 0.00, first 3s move -2.10, in-trade range [-2.10, 4.60] points vs entry. Post-exit best/worst delta: 4.05 / -1.10, final @15s -1.10. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T094516_BFO_SENSEX2640273500CE_CONTINUATION_CALL_CALL.png`

### 20260401T095039|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273600CE`
- Entry/Exit: `2026-04-01 09:50:39` -> `2026-04-01 09:50:51` | Duration `11.63s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `651.85`, target `653.85`, exit `649.20` | Realized PnL `-1325.00`
- Lifecycle read: Pre-entry option drift -1.70 points (index 5.33). After entry: first 1s move -1.85, first 3s move 0.15, in-trade range [-4.45, 0.15] points vs entry. Post-exit best/worst delta: 13.40 / -0.30, final @15s 13.25. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T095039_BFO_SENSEX2640273600CE_CONTINUATION_CALL_CALL.png`

### 20260401T095505|BFO:SENSEX2640273700CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273700CE`
- Entry/Exit: `2026-04-01 09:55:05` -> `2026-04-01 09:55:07` | Duration `1.64s` | Exit reason `TARGET_HIT`
- Prices: entry `617.45`, target `620.45`, exit `620.45` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 0.40 points (index 6.76). After entry: first 1s move 1.05, first 3s move 3.40, in-trade range [1.05, 3.40] points vs entry. Post-exit best/worst delta: 1.65 / -13.45, final @15s -6.30. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T095505_BFO_SENSEX2640273700CE_CONTINUATION_CALL_CALL.png`

### 20260401T100019|BFO:SENSEX2640274000PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640274000PE`
- Entry/Exit: `2026-04-01 10:00:19` -> `2026-04-01 10:00:31` | Duration `12.09s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `593.85`, target `595.85`, exit `569.80` | Realized PnL `-12025.00`
- Lifecycle read: Pre-entry option drift -1.45 points (index -11.39). After entry: first 1s move -5.05, first 3s move -5.65, in-trade range [-24.05, -5.05] points vs entry. Post-exit best/worst delta: 6.35 / 0.95, final @15s 5.50. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T100019_BFO_SENSEX2640274000PE_CONTINUATION_PUT_PUT.png`

### 20260401T100511|BFO:SENSEX2640273700CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273700CE`
- Entry/Exit: `2026-04-01 10:05:11` -> `2026-04-01 10:05:40` | Duration `28.58s` | Exit reason `TARGET_HIT`
- Prices: entry `657.60`, target `659.60`, exit `659.60` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 1.15 points (index 11.02). After entry: first 1s move 2.40, first 3s move -4.15, in-trade range [-7.70, 3.20] points vs entry. Post-exit best/worst delta: 0.45 / -18.40, final @15s -17.45. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T100511_BFO_SENSEX2640273700CE_CONTINUATION_CALL_CALL.png`

### 20260401T101005|BFO:SENSEX2640274000PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640274000PE`
- Entry/Exit: `2026-04-01 10:10:05` -> `2026-04-01 10:10:06` | Duration `0.04s` | Exit reason `TARGET_HIT`
- Prices: entry `565.25`, target `568.25`, exit `568.25` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 0.30 points (index -3.06). After entry: first 1s move 3.60, first 3s move 3.60, in-trade range [3.60, 3.60] points vs entry. Post-exit best/worst delta: 3.15 / -1.50, final @15s -0.25. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T101005_BFO_SENSEX2640274000PE_CONTINUATION_PUT_PUT.png`

### 20260401T102005|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273500CE`
- Entry/Exit: `2026-04-01 10:20:06` -> `2026-04-01 10:20:18` | Duration `12.03s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `672.85`, target `674.85`, exit `663.30` | Realized PnL `-4775.00`
- Lifecycle read: Pre-entry option drift 4.60 points (index 6.75). After entry: first 1s move -4.05, first 3s move -0.85, in-trade range [-9.55, -0.60] points vs entry. Post-exit best/worst delta: 4.25 / -2.85, final @15s 1.50. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T102005_BFO_SENSEX2640273500CE_CONTINUATION_CALL_CALL.png`

### 20260401T102513|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273800PE`
- Entry/Exit: `2026-04-01 10:25:13` -> `2026-04-01 10:25:19` | Duration `5.13s` | Exit reason `TARGET_HIT`
- Prices: entry `595.70`, target `598.70`, exit `598.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.85 points (index -12.86). After entry: first 1s move 2.80, first 3s move 1.95, in-trade range [1.95, 6.40] points vs entry. Post-exit best/worst delta: 21.30 / 3.40, final @15s 21.30. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T102513_BFO_SENSEX2640273800PE_CONTINUATION_PUT_PUT.png`

### 20260401T103022|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273700PE`
- Entry/Exit: `2026-04-01 10:30:22` -> `2026-04-01 10:30:23` | Duration `0.56s` | Exit reason `TARGET_HIT`
- Prices: entry `620.30`, target `623.30`, exit `623.30` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 10.20 points (index -28.44). After entry: first 1s move 4.65, first 3s move 4.65, in-trade range [4.65, 4.65] points vs entry. Post-exit best/worst delta: 7.85 / 0.30, final @15s 5.70. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T103022_BFO_SENSEX2640273700PE_CONTINUATION_PUT_PUT.png`

### 20260401T103515|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273300CE`
- Entry/Exit: `2026-04-01 10:35:15` -> `2026-04-01 10:35:21` | Duration `5.36s` | Exit reason `TARGET_HIT`
- Prices: entry `661.25`, target `664.25`, exit `664.25` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.50 points (index 9.57). After entry: first 1s move 1.45, first 3s move 0.40, in-trade range [0.40, 3.60] points vs entry. Post-exit best/worst delta: 0.60 / -4.70, final @15s -4.70. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T103515_BFO_SENSEX2640273300CE_CONTINUATION_CALL_CALL.png`

### 20260401T104512|BFO:SENSEX2640273700PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273700PE`
- Entry/Exit: `2026-04-01 10:45:12` -> `2026-04-01 10:45:14` | Duration `1.06s` | Exit reason `TARGET_HIT`
- Prices: entry `581.50`, target `584.50`, exit `584.50` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 8.30 points (index -6.16). After entry: first 1s move 2.45, first 3s move 3.05, in-trade range [2.45, 3.05] points vs entry. Post-exit best/worst delta: -4.10 / -9.10, final @15s -9.05. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T104512_BFO_SENSEX2640273700PE_REVERSAL_PUT_PUT.png`

### 20260401T105015|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273700PE`
- Entry/Exit: `2026-04-01 10:50:15` -> `2026-04-01 10:50:17` | Duration `1.30s` | Exit reason `TARGET_HIT`
- Prices: entry `596.85`, target `599.85`, exit `599.85` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.55 points (index -9.31). After entry: first 1s move 1.00, first 3s move 4.35, in-trade range [1.00, 4.35] points vs entry. Post-exit best/worst delta: 3.85 / 0.00, final @15s 0.55. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T105015_BFO_SENSEX2640273700PE_CONTINUATION_PUT_PUT.png`

### 20260401T105510|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273700PE`
- Entry/Exit: `2026-04-01 10:55:10` -> `2026-04-01 10:55:14` | Duration `3.09s` | Exit reason `TARGET_HIT`
- Prices: entry `597.40`, target `600.40`, exit `600.40` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 1.30 points (index -2.88). After entry: first 1s move -0.85, first 3s move 2.40, in-trade range [-0.85, 3.05] points vs entry. Post-exit best/worst delta: 10.15 / 0.05, final @15s 10.15. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T105510_BFO_SENSEX2640273700PE_CONTINUATION_PUT_PUT.png`

### 20260401T110001|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273600PE`
- Entry/Exit: `2026-04-01 11:00:01` -> `2026-04-01 11:00:01` | Duration `-0.70s` | Exit reason `TARGET_HIT`
- Prices: entry `573.00`, target `576.00`, exit `576.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.50 points (index -9.89). After entry: first 1s move 5.15, first 3s move 5.15, in-trade range [0.00, 5.15] points vs entry. Post-exit best/worst delta: 8.90 / -0.10, final @15s 7.70. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T110001_BFO_SENSEX2640273600PE_CONTINUATION_PUT_PUT.png`

### 20260401T110503|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273600PE`
- Entry/Exit: `2026-04-01 11:05:04` -> `2026-04-01 11:05:09` | Duration `4.94s` | Exit reason `TARGET_HIT`
- Prices: entry `602.70`, target `605.70`, exit `605.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.40 points (index -5.30). After entry: first 1s move -0.15, first 3s move 2.80, in-trade range [-0.15, 3.60] points vs entry. Post-exit best/worst delta: 8.80 / 1.05, final @15s 8.80. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T110503_BFO_SENSEX2640273600PE_CONTINUATION_PUT_PUT.png`

### 20260401T111018|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273200CE`
- Entry/Exit: `2026-04-01 11:10:18` -> `2026-04-01 11:10:21` | Duration `2.46s` | Exit reason `TARGET_HIT`
- Prices: entry `664.10`, target `667.10`, exit `667.10` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -1.70 points (index 3.77). After entry: first 1s move NA, first 3s move 3.35, in-trade range [0.65, 3.35] points vs entry. Post-exit best/worst delta: 9.70 / -1.95, final @15s 9.70. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T111018_BFO_SENSEX2640273200CE_CONTINUATION_CALL_CALL.png`

### 20260401T112006|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273200CE`
- Entry/Exit: `2026-04-01 11:20:06` -> `2026-04-01 11:20:18` | Duration `11.99s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `656.35`, target `658.35`, exit `650.05` | Realized PnL `-3150.00`
- Lifecycle read: Pre-entry option drift 2.80 points (index 4.26). After entry: first 1s move NA, first 3s move -3.85, in-trade range [-7.45, -1.45] points vs entry. Post-exit best/worst delta: 7.25 / 0.05, final @15s 7.25. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T112006_BFO_SENSEX2640273200CE_CONTINUATION_CALL_CALL.png`

### 20260401T112519|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273300CE`
- Entry/Exit: `2026-04-01 11:25:19` -> `2026-04-01 11:25:27` | Duration `7.70s` | Exit reason `TARGET_HIT`
- Prices: entry `630.70`, target `633.70`, exit `633.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -2.15 points (index 4.04). After entry: first 1s move -1.85, first 3s move 1.00, in-trade range [-1.85, 4.85] points vs entry. Post-exit best/worst delta: 3.20 / -2.00, final @15s -0.85. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T112519_BFO_SENSEX2640273300CE_CONTINUATION_CALL_CALL.png`

### 20260401T113030|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273300CE`
- Entry/Exit: `2026-04-01 11:30:32` -> `2026-04-01 11:30:38` | Duration `5.99s` | Exit reason `TARGET_HIT`
- Prices: entry `642.75`, target `645.75`, exit `645.75` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 0.45 points (index -3.40). After entry: first 1s move -0.50, first 3s move -3.35, in-trade range [-3.35, 6.65] points vs entry. Post-exit best/worst delta: 7.65 / -2.10, final @15s 7.65. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T113030_BFO_SENSEX2640273300CE_CONTINUATION_CALL_CALL.png`

### 20260401T113510|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273300CE`
- Entry/Exit: `2026-04-01 11:35:10` -> `2026-04-01 11:35:23` | Duration `13.14s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `660.30`, target `662.30`, exit `658.75` | Realized PnL `-775.00`
- Lifecycle read: Pre-entry option drift 1.70 points (index 5.27). After entry: first 1s move -0.70, first 3s move -3.30, in-trade range [-4.45, 0.25] points vs entry. Post-exit best/worst delta: 0.00 / -5.60, final @15s -2.50. Exit quality mixed; post-exit path inconclusive.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T113510_BFO_SENSEX2640273300CE_CONTINUATION_CALL_CALL.png`

### 20260401T114001|BFO:SENSEX2640273400CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273400CE`
- Entry/Exit: `2026-04-01 11:40:02` -> `2026-04-01 11:40:16` | Duration `13.91s` | Exit reason `TARGET_HIT`
- Prices: entry `613.05`, target `615.05`, exit `615.05` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 4.00 points (index 10.79). After entry: first 1s move -1.35, first 3s move -4.45, in-trade range [-5.35, 2.45] points vs entry. Post-exit best/worst delta: 4.95 / -1.15, final @15s -0.50. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T114001_BFO_SENSEX2640273400CE_CONTINUATION_CALL_CALL.png`

### 20260401T114502|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273700PE`
- Entry/Exit: `2026-04-01 11:45:02` -> `2026-04-01 11:45:08` | Duration `5.66s` | Exit reason `TARGET_HIT`
- Prices: entry `548.00`, target `551.00`, exit `551.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.40 points (index -3.04). After entry: first 1s move -0.65, first 3s move 2.00, in-trade range [-1.20, 4.00] points vs entry. Post-exit best/worst delta: 7.80 / 1.95, final @15s 2.20. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T114502_BFO_SENSEX2640273700PE_CONTINUATION_PUT_PUT.png`

### 20260401T115509|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273600PE`
- Entry/Exit: `2026-04-01 11:55:09` -> `2026-04-01 11:55:21` | Duration `11.26s` | Exit reason `TARGET_HIT`
- Prices: entry `580.00`, target `582.00`, exit `582.00` | Realized PnL `1000.00`
- Lifecycle read: Pre-entry option drift 3.05 points (index -11.55). After entry: first 1s move 1.30, first 3s move 2.20, in-trade range [-2.25, 2.35] points vs entry. Post-exit best/worst delta: 7.80 / -6.50, final @15s -5.30. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T115509_BFO_SENSEX2640273600PE_CONTINUATION_PUT_PUT.png`

### 20260401T120007|BFO:SENSEX2640273300CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273300CE`
- Entry/Exit: `2026-04-01 12:00:07` -> `2026-04-01 12:00:08` | Duration `0.74s` | Exit reason `TARGET_HIT`
- Prices: entry `606.55`, target `609.55`, exit `609.55` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.95 points (index 5.35). After entry: first 1s move 5.05, first 3s move 5.05, in-trade range [5.05, 5.05] points vs entry. Post-exit best/worst delta: 28.80 / 2.05, final @15s 25.15. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T120007_BFO_SENSEX2640273300CE_CONTINUATION_CALL_CALL.png`

### 20260401T120526|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273500CE`
- Entry/Exit: `2026-04-01 12:05:26` -> `2026-04-01 12:05:27` | Duration `0.18s` | Exit reason `TARGET_HIT`
- Prices: entry `622.85`, target `625.85`, exit `625.85` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 7.85 points (index 6.84). After entry: first 1s move 4.95, first 3s move 4.95, in-trade range [4.95, 4.95] points vs entry. Post-exit best/worst delta: 1.95 / -10.30, final @15s -5.25. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T120526_BFO_SENSEX2640273500CE_CONTINUATION_CALL_CALL.png`

### 20260401T121025|BFO:SENSEX2640273900PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273900PE`
- Entry/Exit: `2026-04-01 12:10:25` -> `2026-04-01 12:10:26` | Duration `0.71s` | Exit reason `TARGET_HIT`
- Prices: entry `555.80`, target `558.80`, exit `558.80` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.30 points (index -7.92). After entry: first 1s move 4.45, first 3s move 4.45, in-trade range [2.10, 4.45] points vs entry. Post-exit best/worst delta: 16.20 / -2.40, final @15s 9.80. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T121025_BFO_SENSEX2640273900PE_REVERSAL_PUT_PUT.png`

### 20260401T121509|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273500CE`
- Entry/Exit: `2026-04-01 12:15:09` -> `2026-04-01 12:15:42` | Duration `33.17s` | Exit reason `PATH_RISK_EXIT`
- Prices: entry `656.85`, target `658.85`, exit `634.65` | Realized PnL `-11100.00`
- Lifecycle read: Pre-entry option drift 1.20 points (index 3.24). After entry: first 1s move 0.40, first 3s move -4.00, in-trade range [-10.05, 1.50] points vs entry. Post-exit best/worst delta: 6.00 / -4.65, final @15s 6.00. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T121509_BFO_SENSEX2640273500CE_CONTINUATION_CALL_CALL.png`

### 20260401T122013|BFO:SENSEX2640273900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273900PE`
- Entry/Exit: `2026-04-01 12:20:13` -> `2026-04-01 12:20:16` | Duration `2.65s` | Exit reason `TARGET_HIT`
- Prices: entry `562.30`, target `565.30`, exit `565.30` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -4.50 points (index -6.29). After entry: first 1s move 0.45, first 3s move 5.55, in-trade range [0.45, 5.55] points vs entry. Post-exit best/worst delta: 4.35 / -3.95, final @15s 4.35. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T122013_BFO_SENSEX2640273900PE_CONTINUATION_PUT_PUT.png`

### 20260401T122509|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273800PE`
- Entry/Exit: `2026-04-01 12:25:10` -> `2026-04-01 12:25:27` | Duration `16.90s` | Exit reason `TARGET_HIT`
- Prices: entry `512.70`, target `515.70`, exit `515.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 0.45 points (index -0.42). After entry: first 1s move -0.40, first 3s move 1.35, in-trade range [-0.60, 3.30] points vs entry. Post-exit best/worst delta: 2.05 / -7.65, final @15s -5.25. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T122509_BFO_SENSEX2640273800PE_CONTINUATION_PUT_PUT.png`

### 20260401T123002|BFO:SENSEX2640273500CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273500CE`
- Entry/Exit: `2026-04-01 12:30:02` -> `2026-04-01 12:30:03` | Duration `0.43s` | Exit reason `TARGET_HIT`
- Prices: entry `608.40`, target `611.40`, exit `611.40` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.40 points (index 11.11). After entry: first 1s move 5.50, first 3s move 5.50, in-trade range [5.50, 5.50] points vs entry. Post-exit best/worst delta: 8.55 / 0.60, final @15s 8.55. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T123002_BFO_SENSEX2640273500CE_REVERSAL_CALL_CALL.png`

### 20260401T123531|BFO:SENSEX2640273800PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273800PE`
- Entry/Exit: `2026-04-01 12:35:31` -> `2026-04-01 12:35:37` | Duration `5.41s` | Exit reason `TARGET_HIT`
- Prices: entry `518.00`, target `521.00`, exit `521.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 2.80 points (index -3.64). After entry: first 1s move 0.55, first 3s move 0.65, in-trade range [0.05, 4.25] points vs entry. Post-exit best/worst delta: 5.25 / -0.95, final @15s 4.75. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T123531_BFO_SENSEX2640273800PE_CONTINUATION_PUT_PUT.png`

### 20260401T124002|BFO:SENSEX2640273500CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273500CE`
- Entry/Exit: `2026-04-01 12:40:02` -> `2026-04-01 12:40:04` | Duration `1.16s` | Exit reason `TARGET_HIT`
- Prices: entry `630.00`, target `633.00`, exit `633.00` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -0.45 points (index 3.39). After entry: first 1s move 1.15, first 3s move 3.50, in-trade range [1.15, 3.50] points vs entry. Post-exit best/worst delta: 14.80 / -0.20, final @15s 10.20. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T124002_BFO_SENSEX2640273500CE_CONTINUATION_CALL_CALL.png`

### 20260401T124521|BFO:SENSEX2640273500CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273500CE`
- Entry/Exit: `2026-04-01 12:45:21` -> `2026-04-01 12:45:21` | Duration `-0.44s` | Exit reason `TARGET_HIT`
- Prices: entry `614.85`, target `617.85`, exit `617.85` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -3.20 points (index 9.31). After entry: first 1s move 3.00, first 3s move 3.00, in-trade range [0.00, 3.00] points vs entry. Post-exit best/worst delta: 14.90 / -1.95, final @15s 14.90. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T124521_BFO_SENSEX2640273500CE_REVERSAL_CALL_CALL.png`

### 20260401T125027|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273600CE`
- Entry/Exit: `2026-04-01 12:50:28` -> `2026-04-01 12:50:39` | Duration `11.89s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `605.30`, target `607.30`, exit `602.55` | Realized PnL `-1375.00`
- Lifecycle read: Pre-entry option drift -4.45 points (index 4.63). After entry: first 1s move -1.55, first 3s move -2.35, in-trade range [-5.95, 0.70] points vs entry. Post-exit best/worst delta: 11.05 / 2.35, final @15s 10.80. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T125027_BFO_SENSEX2640273600CE_CONTINUATION_CALL_CALL.png`

### 20260401T125532|BFO:SENSEX2640273600CE|REVERSAL_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273600CE`
- Entry/Exit: `2026-04-01 12:55:32` -> `2026-04-01 12:56:07` | Duration `34.61s` | Exit reason `PATH_RISK_EXIT`
- Prices: entry `612.05`, target `614.05`, exit `606.55` | Realized PnL `-2750.00`
- Lifecycle read: Pre-entry option drift -0.40 points (index 11.88). After entry: first 1s move NA, first 3s move 1.15, in-trade range [-8.95, 1.85] points vs entry. Post-exit best/worst delta: 5.45 / -7.55, final @15s -7.20. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T125532_BFO_SENSEX2640273600CE_REVERSAL_CALL_CALL.png`

### 20260401T130002|BFO:SENSEX2640274000PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640274000PE`
- Entry/Exit: `2026-04-01 13:00:02` -> `2026-04-01 13:00:34` | Duration `31.36s` | Exit reason `HARD_STOP_EXIT`
- Prices: entry `553.15`, target `555.15`, exit `545.00` | Realized PnL `-4075.00`
- Lifecycle read: Pre-entry option drift 0.50 points (index -1.85). After entry: first 1s move 1.65, first 3s move 1.70, in-trade range [-8.15, 1.70] points vs entry. Post-exit best/worst delta: 0.00 / -6.00, final @15s -4.65. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T130002_BFO_SENSEX2640274000PE_CONTINUATION_PUT_PUT.png`

### 20260401T130506|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273600CE`
- Entry/Exit: `2026-04-01 13:05:07` -> `2026-04-01 13:05:19` | Duration `12.42s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `606.50`, target `609.50`, exit `606.40` | Realized PnL `-50.00`
- Lifecycle read: Pre-entry option drift 1.35 points (index 5.19). After entry: first 1s move -2.10, first 3s move -3.45, in-trade range [-3.45, 1.05] points vs entry. Post-exit best/worst delta: 4.35 / -3.15, final @15s 4.35. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T130506_BFO_SENSEX2640273600CE_CONTINUATION_CALL_CALL.png`

### 20260401T131505|BFO:SENSEX2640273600CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273600CE`
- Entry/Exit: `2026-04-01 13:15:06` -> `2026-04-01 13:15:06` | Duration `-0.13s` | Exit reason `TARGET_HIT`
- Prices: entry `643.05`, target `646.05`, exit `646.05` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.70 points (index 12.85). After entry: first 1s move 3.60, first 3s move 3.60, in-trade range [3.60, 3.60] points vs entry. Post-exit best/worst delta: 16.75 / 0.60, final @15s 15.30. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T131505_BFO_SENSEX2640273600CE_CONTINUATION_CALL_CALL.png`

### 20260401T132002|BFO:SENSEX2640273900PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273900PE`
- Entry/Exit: `2026-04-01 13:20:02` -> `2026-04-01 13:20:07` | Duration `4.43s` | Exit reason `TARGET_HIT`
- Prices: entry `521.15`, target `524.15`, exit `524.15` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.90 points (index -4.99). After entry: first 1s move 1.30, first 3s move 0.40, in-trade range [0.35, 3.85] points vs entry. Post-exit best/worst delta: 2.20 / -2.25, final @15s 2.20. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T132002_BFO_SENSEX2640273900PE_CONTINUATION_PUT_PUT.png`

### 20260401T133009|BFO:SENSEX2640273800PE|REVERSAL_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273800PE`
- Entry/Exit: `2026-04-01 13:30:09` -> `2026-04-01 13:30:21` | Duration `11.64s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `554.95`, target `556.95`, exit `548.20` | Realized PnL `-3375.00`
- Lifecycle read: Pre-entry option drift 6.55 points (index -15.55). After entry: first 1s move -0.80, first 3s move -6.15, in-trade range [-8.80, -0.80] points vs entry. Post-exit best/worst delta: 5.80 / -1.35, final @15s 5.80. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T133009_BFO_SENSEX2640273800PE_REVERSAL_PUT_PUT.png`

### 20260401T133503|BFO:SENSEX2640273700PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273700PE`
- Entry/Exit: `2026-04-01 13:35:03` -> `2026-04-01 13:35:07` | Duration `3.50s` | Exit reason `TARGET_HIT`
- Prices: entry `564.50`, target `567.50`, exit `567.50` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 4.45 points (index -9.21). After entry: first 1s move -1.10, first 3s move 1.50, in-trade range [-1.10, 3.85] points vs entry. Post-exit best/worst delta: 2.40 / -8.55, final @15s -1.65. Exit looks reasonable around target completion.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T133503_BFO_SENSEX2640273700PE_CONTINUATION_PUT_PUT.png`

### 20260401T134000|BFO:SENSEX2640273600PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273600PE`
- Entry/Exit: `2026-04-01 13:40:00` -> `2026-04-01 13:40:02` | Duration `1.05s` | Exit reason `TARGET_HIT`
- Prices: entry `531.85`, target `534.85`, exit `534.85` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 9.40 points (index -12.65). After entry: first 1s move 2.15, first 3s move 3.85, in-trade range [2.15, 3.85] points vs entry. Post-exit best/worst delta: 24.45 / 0.85, final @15s 24.45. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T134000_BFO_SENSEX2640273600PE_CONTINUATION_PUT_PUT.png`

### 20260401T134504|BFO:SENSEX2640273300PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273300PE`
- Entry/Exit: `2026-04-01 13:45:04` -> `2026-04-01 13:45:04` | Duration `-0.34s` | Exit reason `TARGET_HIT`
- Prices: entry `609.25`, target `612.25`, exit `612.25` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 14.50 points (index -9.50). After entry: first 1s move 5.30, first 3s move 5.30, in-trade range [0.00, 5.30] points vs entry. Post-exit best/worst delta: 9.10 / 1.20, final @15s 4.55. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T134504_BFO_SENSEX2640273300PE_CONTINUATION_PUT_PUT.png`

### 20260401T135506|BFO:SENSEX2640273400PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273400PE`
- Entry/Exit: `2026-04-01 13:55:06` -> `2026-04-01 13:55:07` | Duration `0.28s` | Exit reason `TARGET_HIT`
- Prices: entry `566.65`, target `569.65`, exit `569.65` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 3.75 points (index -7.94). After entry: first 1s move 4.95, first 3s move 4.95, in-trade range [4.95, 4.95] points vs entry. Post-exit best/worst delta: 7.30 / -0.40, final @15s 1.80. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T135506_BFO_SENSEX2640273400PE_CONTINUATION_PUT_PUT.png`

### 20260401T140003|BFO:SENSEX2640273100CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273100CE`
- Entry/Exit: `2026-04-01 14:00:04` -> `2026-04-01 14:00:16` | Duration `12.50s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `582.75`, target `584.75`, exit `576.85` | Realized PnL `-2950.00`
- Lifecycle read: Pre-entry option drift 1.40 points (index 6.51). After entry: first 1s move -2.65, first 3s move -1.60, in-trade range [-5.90, 1.00] points vs entry. Post-exit best/worst delta: 4.15 / -8.10, final @15s 4.15. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T140003_BFO_SENSEX2640273100CE_CONTINUATION_CALL_CALL.png`

### 20260401T141001|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273200CE`
- Entry/Exit: `2026-04-01 14:10:02` -> `2026-04-01 14:10:34` | Duration `31.63s` | Exit reason `HARD_STOP_EXIT`
- Prices: entry `571.80`, target `573.80`, exit `549.90` | Realized PnL `-10950.00`
- Lifecycle read: Pre-entry option drift -1.40 points (index 1.62). After entry: first 1s move 0.15, first 3s move -2.50, in-trade range [-21.90, 1.70] points vs entry. Post-exit best/worst delta: 8.85 / -1.90, final @15s 6.55. Exit may be early; meaningful recovery appeared after close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T141001_BFO_SENSEX2640273200CE_CONTINUATION_CALL_CALL.png`

### 20260401T141504|BFO:SENSEX2640273200CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273200CE`
- Entry/Exit: `2026-04-01 14:15:04` -> `2026-04-01 14:15:07` | Duration `2.40s` | Exit reason `TARGET_HIT`
- Prices: entry `603.65`, target `606.65`, exit `606.65` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift -1.05 points (index 4.25). After entry: first 1s move 2.35, first 3s move 5.25, in-trade range [2.35, 5.25] points vs entry. Post-exit best/worst delta: 1.70 / -8.25, final @15s -8.25. Exit looks timely; post-exit path faded materially.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T141504_BFO_SENSEX2640273200CE_CONTINUATION_CALL_CALL.png`

### 20260401T142513|BFO:SENSEX2640273500PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273500PE`
- Entry/Exit: `2026-04-01 14:25:14` -> `2026-04-01 14:25:45` | Duration `31.60s` | Exit reason `HARD_STOP_EXIT`
- Prices: entry `568.20`, target `570.20`, exit `541.40` | Realized PnL `-13400.00`
- Lifecycle read: Pre-entry option drift 17.45 points (index -3.26). After entry: first 1s move -1.65, first 3s move -3.55, in-trade range [-26.80, 1.50] points vs entry. Post-exit best/worst delta: 1.30 / -7.60, final @15s -5.35. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T142513_BFO_SENSEX2640273500PE_CONTINUATION_PUT_PUT.png`

### 20260401T143006|BFO:SENSEX2640273100CE|CONTINUATION_CALL|CALL
- Side/Contract: `CALL` `BFO:SENSEX2640273100CE`
- Entry/Exit: `2026-04-01 14:30:06` -> `2026-04-01 14:30:39` | Duration `32.46s` | Exit reason `HARD_STOP_EXIT`
- Prices: entry `625.90`, target `627.90`, exit `607.60` | Realized PnL `-9150.00`
- Lifecycle read: Pre-entry option drift 0.75 points (index 6.51). After entry: first 1s move -1.40, first 3s move -1.15, in-trade range [-20.85, 1.90] points vs entry. Post-exit best/worst delta: 1.60 / -10.05, final @15s -6.25. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T143006_BFO_SENSEX2640273100CE_CONTINUATION_CALL_CALL.png`

### 20260401T143511|BFO:SENSEX2640273400PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273400PE`
- Entry/Exit: `2026-04-01 14:35:11` -> `2026-04-01 14:35:14` | Duration `2.12s` | Exit reason `TARGET_HIT`
- Prices: entry `535.70`, target `538.70`, exit `538.70` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 5.95 points (index -4.54). After entry: first 1s move 2.00, first 3s move 3.15, in-trade range [2.00, 3.15] points vs entry. Post-exit best/worst delta: 5.70 / -5.20, final @15s 5.70. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T143511_BFO_SENSEX2640273400PE_CONTINUATION_PUT_PUT.png`

### 20260401T144006|BFO:SENSEX2640273300PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273300PE`
- Entry/Exit: `2026-04-01 14:40:06` -> `2026-04-01 14:40:08` | Duration `1.48s` | Exit reason `TARGET_HIT`
- Prices: entry `552.35`, target `555.35`, exit `555.35` | Realized PnL `1500.00`
- Lifecycle read: Pre-entry option drift 7.35 points (index -8.41). After entry: first 1s move 2.00, first 3s move 6.35, in-trade range [2.00, 6.35] points vs entry. Post-exit best/worst delta: 25.30 / 3.35, final @15s 19.15. Target exit worked but left additional upside afterwards.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T144006_BFO_SENSEX2640273300PE_CONTINUATION_PUT_PUT.png`

### 20260401T144505|BFO:SENSEX2640273300PE|CONTINUATION_PUT|PUT
- Side/Contract: `PUT` `BFO:SENSEX2640273300PE`
- Entry/Exit: `2026-04-01 14:45:06` -> `2026-04-01 14:45:21` | Duration `15.40s` | Exit reason `EARLY_RISK_EXIT`
- Prices: entry `564.50`, target `566.50`, exit `563.10` | Realized PnL `-700.00`
- Lifecycle read: Pre-entry option drift 2.35 points (index -3.00). After entry: first 1s move -6.80, first 3s move -3.10, in-trade range [-6.80, 1.90] points vs entry. Post-exit best/worst delta: -2.30 / -11.35, final @15s -3.10. Exit appears justified; weakness persisted post-close.
- Chart: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts/20260401T144505_BFO_SENSEX2640273300PE_CONTINUATION_PUT_PUT.png`

## 5. Visualizations
- Session-level charts:
  - session_trade_timeline: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/session_trade_timeline.png`
  - pnl_distribution: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/pnl_distribution.png`
  - duration_distribution: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/duration_distribution.png`
  - mfe_vs_mae: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/mfe_vs_mae_scatter.png`
  - pnl_vs_mfe: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/pnl_vs_mfe_scatter.png`
  - entry_first_5s_path_behavior: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/entry_first_5s_path_behavior.png`
  - runtime_health_timeseries_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/runtime_health_timeseries.csv`
  - runtime_stability: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/runtime_stability.png`
  - counterfactual_summary_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/counterfactual_summary.csv`
  - time_of_day_summary_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/time_of_day_summary.csv`
  - runtime_stress_by_time_bucket_csv: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/runtime_stress_by_time_bucket.csv`
- Per-trade charts:
  - Count generated: **57**
  - Folder: `/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/session_report/2026-04-01/trade_charts`

## 6. Microstructure Feature Analysis
### Winners vs Losers
| feature | winner_mean | loser_mean | winner_median | loser_median |
| --- | --- | --- | --- | --- |
| entry_spread | 1.34 | 1.31 | 1.40 | 1.38 |
| spread_median_first_2s | 1.33 | 1.33 | 1.40 | 1.41 |
| imbalance_entry | -0.06 | -0.12 | -0.09 | -0.14 |
| imbalance_drift_first_2s | -0.06 | 0.13 | -0.08 | 0.30 |
| pre_entry_velocity | 1.05 | 0.78 | 1.30 | 0.43 |
| first_1s_move | 2.08 | -1.89 | 1.98 | -1.60 |
| first_3s_move | 2.89 | -2.41 | 3.40 | -2.80 |
| in_trade_max_points | 4.34 | 0.46 | 4.25 | 1.02 |
| in_trade_min_points | 0.92 | -11.10 | 0.65 | -8.48 |
| post_exit_best_delta | 8.57 | 4.84 | 7.30 | 4.90 |
| post_exit_final_delta | 4.54 | 2.26 | 4.35 | 4.25 |
| holding_seconds | 3.82 | 19.97 | 2.12 | 12.82 |

### Small Losers vs Tail Losers
- Loser count: **16**, tail-loss threshold (median loser pnl): **-3262.50**
- Tail losers average first_3s_move: **-2.77**, average post_exit_best_delta: **4.27**
- Smaller losers average first_3s_move: **-2.04**, average post_exit_best_delta: **5.42**

### Continuation/Reversal and Fragility Views
- Continuation trades: **49**, avg pnl `-506.12`
- Reversal trades: **8**, avg pnl `359.38`
- Fragile trades: **18**, avg pnl `-4381.94`
- Non-fragile trades: **39**, avg pnl `1460.26`

### Early-Day vs Late-Day
- Early (before 11:30): **23** trades, hit rate `82.61%` avg pnl `292.39`
- Late (after 13:00): **17** trades, hit rate `52.94%` avg pnl `-1832.35`

## 7. Exit Quality Analysis
- Target exits: **41**, share of target exits with post-exit fade (< -3 points final delta): **21.95%**
- Non-target exits: **16**, share with post-exit rebound >= +3 points: **68.75%**
- Exit reason mix: TARGET_HIT: 41, EARLY_RISK_EXIT: 10, HARD_STOP_EXIT: 4, PATH_RISK_EXIT: 2
- Share of trades that nearly reached target without in-trade touch: **12.28%**

## 8. Counterfactual / What-if Analysis
| target_points | touch_rate_all | touch_rate_winners | touch_rate_losers |
| --- | --- | --- | --- |
| 2.00 | 0.72 | 1.00 | 0.00 |
| 3.00 | 0.68 | 0.95 | 0.00 |
| 4.00 | 0.39 | 0.54 | 0.00 |
| 5.00 | 0.19 | 0.27 | 0.00 |
| weak_follow_through_warning | 0.23 | 0.05 | 0.69 |
| non_target_exits_post_exit_target_touch | 0.19 | NA | NA |
- Interpretation: target-touch counterfactuals are descriptive only; they do not model fill quality, queueing, or order-state interactions.

## 9. Time-of-Day Analysis
| bucket_type | bucket | trades | wins | losses | hit_rate | avg_pnl | median_pnl | tail_loss_count | tail_loss_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bucket_pre_post_1pm | POST_1PM | 17 | 9 | 8 | 0.53 | -1832.35 | 1500.00 | 2 | 0.12 |
| bucket_pre_post_1pm | PRE_1PM | 40 | 32 | 8 | 0.80 | 230.62 | 1500.00 | 4 | 0.10 |
| bucket_3way | EARLY_SESSION | 18 | 15 | 3 | 0.83 | 215.28 | 1500.00 | 2 | 0.11 |
| bucket_3way | LATE_SESSION | 17 | 9 | 8 | 0.53 | -1832.35 | 1500.00 | 2 | 0.12 |
| bucket_3way | MID_SESSION | 22 | 17 | 5 | 0.77 | 243.18 | 1500.00 | 3 | 0.14 |

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
- [strategy behavior insight] 69% of losing trades showed weak immediate follow-through (first 1s <= 0 and <1 point max gain in first 3s).
- [execution insight] 69% of losing trades had >=3 points of post-exit rebound, suggesting some exits were defensive but potentially early.
- [strategy behavior insight] 73% of winning trades closed within 5 seconds, consistent with a fast-follow-through payoff profile.
- [candidate microstructure filter idea] In-trade option spread difference (loss-win) was 0.04 points; spread alone appears weak as a discriminator in this sample.
- [candidate microstructure filter idea] First-3-second move was -5.29 points lower in losers vs winners, making early path momentum a stronger candidate signal than spread/imbalance.
- [execution insight] 19% of non-target exits later touched target in the next 15 seconds.
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