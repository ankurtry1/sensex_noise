# Burst Onset Research Report

## Executive Summary
- Full-tape dates analyzed: **4** (2026-04-24, 2026-04-27, 2026-04-28, 2026-04-29).
- Prior audit baseline: current burst/promotion live phase is still negative (**-51,550 over 6 sessions**).
- Best actual lag bucket by average PnL: **5_to_10s** (239/trade). Worst: **2_to_5s** (-1,030/trade).
- Best replay variant by total net PnL in this preliminary sample: **ranked_score5_only** (-301,343 net across 2299 trades).

## Data Coverage
| date | path | exists | raw_rows | parse_errors | unique_symbols | unique_strikes | first_timestamp | last_timestamp | missing_spread_rows | missing_best_bid_rows | missing_best_ask_rows | missing_bid_depth_rows | missing_ask_depth_rows | missing_oi_rows | missing_volume_rows | missing_spread_pct | missing_best_bid_pct | missing_best_ask_pct | missing_bid_depth_pct | missing_ask_depth_pct | missing_oi_pct | missing_volume_pct | candidate_count_score3_onset | underlying_rows | underlying_first_timestamp | underlying_last_timestamp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-24 | /Users/ankurkumar/Downloads/sensex-noise-papertrade/data/tape/sensex_options/2026-04-24/options.jsonl | True | 5258 | 0 | 76 | 38 | 2026-04-24 10:31:17 | 2026-04-24 15:29:59 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 31778 | 2026-04-24 08:40:24 | 2026-04-24 17:30:01 |
| 2026-04-27 | /Users/ankurkumar/Downloads/sensex-noise-papertrade/data/tape/sensex_options/2026-04-27/options.jsonl | True | 1480630 | 0 | 83 | 42 | 2026-04-27 09:15:00 | 2026-04-27 15:29:59 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 94809 | 31289 | 2026-04-27 08:48:35 | 2026-04-27 17:30:03 |
| 2026-04-28 | /Users/ankurkumar/Downloads/sensex-noise-papertrade/data/tape/sensex_options/2026-04-28/options.jsonl | True | 1482281 | 0 | 79 | 40 | 2026-04-28 09:15:00 | 2026-04-28 15:29:59 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 104233 | 31180 | 2026-04-28 08:50:23 | 2026-04-28 17:30:02 |
| 2026-04-29 | /Users/ankurkumar/Downloads/sensex-noise-papertrade/data/tape/sensex_options/2026-04-29/options.jsonl | True | 1426610 | 0 | 78 | 39 | 2026-04-29 09:25:28 | 2026-04-29 15:29:59 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 121408 | 22004 | 2026-04-29 09:27:30 | 2026-04-29 15:34:13 |

## Actual Entry vs Burst Onset Lag Study
| lag_bucket | trades | net_pnl | avg_pnl | win_rate | target_hit_rate | hard_stop_rate | avg_mfe | avg_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exact_same_second | 45 | -7925.000 | -176.111 | 0.489 | 0.378 | 0.089 | 1.997 | -1.896 |
| 0_to_2s | 46 | -9025.000 | -196.196 | 0.413 | 0.348 | 0.109 | 2.316 | -2.002 |
| 2_to_5s | 29 | -29875.000 | -1030.172 | 0.207 | 0.138 | 0.172 | 0.952 | -2.991 |
| 5_to_10s | 9 | 2150.000 | 238.889 | 0.556 | 0.333 | 0.000 | 1.717 | -1.367 |
| 10s_plus | 2 | -1250.000 | -625.000 | 0.500 | 0.000 | 0.000 | 0.300 | -1.550 |
| no_match | 52 | 4375.000 | 84.135 | 0.481 | 0.385 | 0.058 | 2.741 | -1.598 |

## Replay Variant Day-wise Summary
| date | variant | selected_trades | net_pnl | win_rate | profit_factor | max_drawdown | delta_net_pnl_vs_actual | delta_trade_count_vs_actual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-24 | actual_system | 52 | 4375.000 | 0.481 | 1.126 | -32825.000 | 0.000 | 0.000 |
| 2026-04-24 | naive_score3 | 0 | 0.000 |  |  | 0.000 | -4375.000 | -52.000 |
| 2026-04-24 | ranked_top1_per_15s | 0 | 0.000 |  |  | 0.000 | -4375.000 | -52.000 |
| 2026-04-24 | ranked_score4_top1_per_15s | 0 | 0.000 |  |  | 0.000 | -4375.000 | -52.000 |
| 2026-04-24 | ranked_score5_only | 0 | 0.000 |  |  | 0.000 | -4375.000 | -52.000 |
| 2026-04-24 | candle_context_score3 | 0 | 0.000 |  |  | 0.000 | -4375.000 | -52.000 |
| 2026-04-24 | candle_context_score4 | 0 | 0.000 |  |  | 0.000 | -4375.000 | -52.000 |
| 2026-04-24 | candle_context_plus_immediate_confirmation | 0 | 0.000 |  |  | 0.000 | -4375.000 | -52.000 |
| 2026-04-27 | actual_system | 48 | -10675.000 | 0.375 | 0.677 | -30350.000 | 0.000 | 0.000 |
| 2026-04-27 | naive_score3 | 1311 | -266656.000 | 0.141 | 0.508 | -268245.000 | -255981.000 | 1263.000 |
| 2026-04-27 | ranked_top1_per_15s | 812 | -183867.000 | 0.150 | 0.501 | -195967.000 | -173192.000 | 764.000 |
| 2026-04-27 | ranked_score4_top1_per_15s | 838 | -235197.000 | 0.141 | 0.396 | -235255.000 | -224522.000 | 790.000 |
| 2026-04-27 | ranked_score5_only | 776 | -74312.000 | 0.188 | 0.710 | -78854.000 | -63637.000 | 728.000 |
| 2026-04-27 | candle_context_score3 | 505 | -109852.000 | 0.174 | 0.540 | -115042.000 | -99177.000 | 457.000 |
| 2026-04-27 | candle_context_score4 | 500 | -93707.000 | 0.174 | 0.571 | -100530.000 | -83032.000 | 452.000 |
| 2026-04-27 | candle_context_plus_immediate_confirmation | 496 | -88455.000 | 0.177 | 0.581 | -104006.000 | -77780.000 | 448.000 |
| 2026-04-28 | actual_system | 44 | -9050.000 | 0.477 | 0.748 | -33625.000 | 0.000 | 0.000 |
| 2026-04-28 | naive_score3 | 1309 | -243270.000 | 0.167 | 0.628 | -206271.000 | -234220.000 | 1265.000 |
| 2026-04-28 | ranked_top1_per_15s | 823 | -96895.000 | 0.193 | 0.760 | -96125.000 | -87845.000 | 779.000 |
| 2026-04-28 | ranked_score4_top1_per_15s | 849 | -192451.000 | 0.176 | 0.581 | -174266.000 | -183401.000 | 805.000 |
| 2026-04-28 | ranked_score5_only | 786 | -124144.000 | 0.182 | 0.630 | -134153.000 | -115094.000 | 742.000 |
| 2026-04-28 | candle_context_score3 | 566 | -147700.000 | 0.171 | 0.532 | -144760.000 | -138650.000 | 522.000 |
| 2026-04-28 | candle_context_score4 | 576 | -141406.000 | 0.186 | 0.546 | -138328.000 | -132356.000 | 532.000 |
| 2026-04-28 | candle_context_plus_immediate_confirmation | 557 | -119986.000 | 0.174 | 0.596 | -125980.000 | -110936.000 | 513.000 |
| 2026-04-29 | actual_system | 39 | -26200.000 | 0.359 | 0.426 | -42125.000 | 0.000 | 0.000 |
| 2026-04-29 | naive_score3 | 1252 | -244383.000 | 0.191 | 0.701 | -295765.000 | -218183.000 | 1213.000 |
| 2026-04-29 | ranked_top1_per_15s | 790 | -134501.000 | 0.222 | 0.728 | -171626.000 | -108301.000 | 751.000 |
| 2026-04-29 | ranked_score4_top1_per_15s | 814 | -129807.000 | 0.221 | 0.746 | -146810.000 | -103607.000 | 775.000 |
| 2026-04-29 | ranked_score5_only | 737 | -102887.000 | 0.193 | 0.731 | -109432.000 | -76687.000 | 698.000 |
| 2026-04-29 | candle_context_score3 | 491 | -201822.000 | 0.206 | 0.503 | -208585.000 | -175622.000 | 452.000 |
| 2026-04-29 | candle_context_score4 | 498 | -145727.000 | 0.201 | 0.597 | -148815.000 | -119527.000 | 459.000 |
| 2026-04-29 | candle_context_plus_immediate_confirmation | 497 | -195591.000 | 0.193 | 0.474 | -202788.000 | -169391.000 | 458.000 |

## Top Missed Ranked Burst Opportunities
| date | variant | timestamp | symbol | score | target_class | net_pnl | exit_reason | opportunity_class | nearest_actual_trade_lag_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-28 | ranked_top1_per_15s | 2026-04-28 09:16:00 | BFO:SENSEX26APR77800CE | 3 | normal | 21489.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | candle_context_plus_immediate_confirmation | 2026-04-29 10:32:22 | BFO:SENSEX26APR79000CE | 3 | normal | 19680.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | ranked_score4_top1_per_15s | 2026-04-29 14:04:17 | BFO:SENSEX26APR76500PE | 4 | normal | 19470.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | naive_score3 | 2026-04-29 15:29:21 | BFO:SENSEX26APR76000PE | 4 | normal | 14544.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-29 | ranked_score5_only | 2026-04-29 09:28:47 | BFO:SENSEX26APR76900PE | 5 | promoted | 12126.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | ranked_score4_top1_per_15s | 2026-04-29 09:28:47 | BFO:SENSEX26APR76900PE | 5 | promoted | 12126.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | ranked_score4_top1_per_15s | 2026-04-29 10:17:19 | BFO:SENSEX26APR79000CE | 4 | normal | 11752.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-29 | candle_context_score4 | 2026-04-29 10:17:19 | BFO:SENSEX26APR79000CE | 4 | normal | 11752.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-29 | ranked_top1_per_15s | 2026-04-29 15:26:19 | BFO:SENSEX26APR76000PE | 4 | normal | 11505.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-29 | naive_score3 | 2026-04-29 15:26:19 | BFO:SENSEX26APR76000PE | 4 | normal | 11505.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-29 | naive_score3 | 2026-04-29 14:59:25 | BFO:SENSEX26APR77300PE | 4 | normal | 10804.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-28 | naive_score3 | 2026-04-28 15:00:16 | BFO:SENSEX26APR76200PE | 4 | normal | 10458.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | naive_score3 | 2026-04-29 13:47:38 | BFO:SENSEX26APR77200PE | 3 | normal | 10374.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-27 | ranked_top1_per_15s | 2026-04-27 09:18:00 | BFO:SENSEX26APR78400CE | 3 | normal | 10010.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | naive_score3 | 2026-04-29 10:16:47 | BFO:SENSEX26APR79000CE | 4 | normal | 9072.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-29 | naive_score3 | 2026-04-29 10:40:44 | BFO:SENSEX26APR79300CE | 4 | normal | 9045.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-29 | candle_context_plus_immediate_confirmation | 2026-04-29 09:41:12 | BFO:SENSEX26APR78200CE | 3 | normal | 8848.000 | EARLY_FAIL_3S | good_missed_opportunity |  |
| 2026-04-28 | ranked_score4_top1_per_15s | 2026-04-28 14:05:00 | BFO:SENSEX26APR76000PE | 4 | normal | 8760.000 | TARGET_HIT | good_missed_opportunity |  |
| 2026-04-29 | ranked_score4_top1_per_15s | 2026-04-29 15:03:32 | BFO:SENSEX26APR77700PE | 5 | promoted | 8405.000 | TARGET_HIT | good_missed_opportunity | 2007.000 |
| 2026-04-29 | ranked_top1_per_15s | 2026-04-29 15:03:32 | BFO:SENSEX26APR77700PE | 5 | promoted | 8405.000 | TARGET_HIT | good_missed_opportunity | 2007.000 |
| 2026-04-29 | ranked_score5_only | 2026-04-29 15:03:32 | BFO:SENSEX26APR77700PE | 5 | promoted | 8405.000 | TARGET_HIT | good_missed_opportunity | 2007.000 |
| 2026-04-27 | naive_score3 | 2026-04-27 15:29:58 | BFO:SENSEX26APR77400PE | 3 | normal | 8400.000 | TARGET_HIT | good_missed_opportunity | 9875.000 |
| 2026-04-28 | ranked_score5_only | 2026-04-28 09:15:21 | BFO:SENSEX26APR77100CE | 5 | promoted | 8365.000 | TARGET_HIT | good_missed_opportunity | 897.000 |
| 2026-04-28 | naive_score3 | 2026-04-28 13:35:24 | BFO:SENSEX26APR75700PE | 5 | promoted | 8342.000 | PROMOTED_FAIL_3S | good_missed_opportunity |  |
| 2026-04-28 | naive_score3 | 2026-04-28 09:15:17 | BFO:SENSEX26APR75800PE | 3 | normal | 8127.000 | TARGET_HIT | good_missed_opportunity |  |

## Variant Verdicts
| variant | days | trades | net_pnl | avg_day | avg_pf | worst_day |
| --- | --- | --- | --- | --- | --- | --- |
| actual_system | 4 | 183 | -41550.000 | -10387.500 | 0.744 | -26200.000 |
| ranked_score5_only | 4 | 2299 | -301343.000 | -75335.750 | 0.690 | -124144.000 |
| candle_context_score4 | 4 | 1574 | -380840.000 | -95210.000 | 0.571 | -145727.000 |
| candle_context_plus_immediate_confirmation | 4 | 1550 | -404032.000 | -101008.000 | 0.550 | -195591.000 |
| ranked_top1_per_15s | 4 | 2425 | -415263.000 | -103815.750 | 0.663 | -183867.000 |
| candle_context_score3 | 4 | 1562 | -459374.000 | -114843.500 | 0.525 | -201822.000 |
| ranked_score4_top1_per_15s | 4 | 2501 | -557455.000 | -139363.750 | 0.574 | -235197.000 |
| naive_score3 | 4 | 3872 | -754309.000 | -188577.250 | 0.612 | -266656.000 |

## Final Recommendation
- **Are we circling or progressing?** Still circling. The current live system remains negative, and this research pipeline does not show a clean burst-onset replay that is robust enough to replace it live on only 4 tape days.
- **Is candle trigger the bottleneck?** Yes, likely as a trigger. Actual trades often lag burst onset, and the lag study penalizes larger lags. But the replay also shows that simply deleting the candle trigger overtrades badly, so candle removal alone is not the answer.
- **Did fresh burst entry outperform candle-triggered entry?** No. None of the tested burst-onset replay variants beat the current live system on total PnL, worst-day PnL, or trade discipline in this 4-day tape sample.
- **What lag from burst onset is acceptable?** The data only rules out some lag zones cleanly: the `2_to_5s` bucket was particularly bad, while `exact_same_second` and `0_to_2s` were merely less bad. The small positive `5_to_10s` bucket is too small to trust.
- **Is the 5-minute candle useful as context?** Possibly, but not enough by itself. Context-aware variants still overtraded and underperformed, although they generally did less damage than the looser score-3 variants.
- **What exact next strategy candidate should be tested?** No live candidate is ready. The next **research** candidate should be **candle_context_score4**, but only after adding stronger throttling / contract-selection filters (for example ATM-distance, premium band, and tighter liquidity ranking).

## Caveats
- This is research-only replay using second-level full-tape snapshots, not broker-grade execution simulation.
- Full tape is only available for a small number of sessions, so results are preliminary.
- Quantity and fills are approximate and should be used for variant ranking, not exact PnL promises.
- Raw logs were not modified.

## Charts
- ![actual_vs_burst_daywise_pnl.png](burst_onset_research_results/charts/actual_vs_burst_daywise_pnl.png)
- ![burst_score_distribution.png](burst_onset_research_results/charts/burst_score_distribution.png)
- ![lag_bucket_pnl.png](burst_onset_research_results/charts/lag_bucket_pnl.png)