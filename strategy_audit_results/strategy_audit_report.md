# Strategy Audit Report

## Executive Summary
- Burst/promotion live patch first appears in logs on **2026-04-22**.
- Post-patch live sessions in this repo: **6** | negative sessions: **4** | cumulative net: **-51,550**.
- Pre-burst eras cumulative net in available logs: **-125,975**.
- The immediately prior **edge_1s/3s** era was near flat by comparison: **6 sessions, -2,700 cumulative net**.
- Promoted trades were **not** the main post-patch drag in available live data: **35 promoted trades, 17,150 net**.
- Dominant post-patch failure modes: **{'good entry but 1s killed too early': 57, 'bad entry immediately': 40, 'good entry but 3s killed too early': 18, 'hard stop / tail event': 13, 'stale 5-minute candle signal': 12}**.
- Immediate microstructure confirmation is the cleanest separator in the post-patch set: confirmed trades made **107,800** across **153** trades, while non-confirmed trades lost **-159,350** across **130** trades.
- Tape-based burst-only replay on the last two tape days shows a mixed answer: the current candle-gated live system lost **-35,250** on **83** trades, while a naive pure-burst replay lost **-313,143** on **2450** trades. So removing candles without better burst candidate ranking would overtrade badly.

## Patch Timeline
| date | patch_era | active_features | number_of_trades | notes |
| --- | --- | --- | --- | --- |
| 2026-03-23 | pre_1s3s | post_exit_observation | 55 |  |
| 2026-03-24 | pre_1s3s | post_exit_observation | 57 |  |
| 2026-03-25 | pre_1s3s | post_exit_observation | 51 |  |
| 2026-03-27 | pre_1s3s | post_exit_observation | 48 |  |
| 2026-03-30 | pre_1s3s | post_exit_observation | 54 |  |
| 2026-04-01 | pre_1s3s | post_exit_observation | 57 | dated trades.jsonl matches event log |
| 2026-04-02 | pre_1s3s | post_exit_observation | 57 | dated trades.jsonl matches event log |
| 2026-04-06 | pre_1s3s | post_exit_observation | 53 | dated trades.jsonl matches event log |
| 2026-04-07 | pre_1s3s | post_exit_observation | 18 | dated trades.jsonl matches event log |
| 2026-04-08 | pre_1s3s | post_exit_observation | 35 | dated trades.jsonl matches event log |
| 2026-04-09 | pre_1s3s | post_exit_observation | 25 | dated trades.jsonl matches event log |
| 2026-04-10 | pre_1s3s | post_exit_observation | 47 | dated trades.jsonl matches event log |
| 2026-04-13 | edge_1s3s | post_exit_observation, edge_1s3s | 50 | dated trades.jsonl matches event log |
| 2026-04-15 | edge_1s3s | post_exit_observation, edge_1s3s | 46 | dated trades.jsonl matches event log |
| 2026-04-16 | edge_1s3s | post_exit_observation, edge_1s3s | 56 | dated trades.jsonl matches event log |
| 2026-04-17 | edge_1s3s | post_exit_observation, edge_1s3s | 50 | dated trades.jsonl matches event log |
| 2026-04-20 | edge_1s3s | post_exit_observation, edge_1s3s | 51 | dated trades.jsonl matches event log |
| 2026-04-21 | edge_1s3s | post_exit_observation, edge_1s3s | 42 | dated trades.jsonl matches event log |
| 2026-04-22 | burst_promotion | post_exit_observation, edge_1s3s, microburst_gate, promotion_3s | 46 | dated trades.jsonl matches event log |
| 2026-04-23 | burst_promotion | post_exit_observation, edge_1s3s, microburst_gate, promotion_3s, layer4 | 54 | dated trades.jsonl matches event log; layer4_events=2 |
| 2026-04-24 | burst_promotion_tape | post_exit_observation, edge_1s3s, microburst_gate, promotion_3s, layer4, full_option_tape | 52 | dated trades.jsonl matches event log; layer4_events=2; tape_present |
| 2026-04-27 | burst_promotion_tape | post_exit_observation, edge_1s3s, microburst_gate, promotion_3s, full_option_tape | 48 | dated trades.jsonl matches event log; tape_present |
| 2026-04-28 | burst_promotion_tape | post_exit_observation, edge_1s3s, microburst_gate, promotion_3s, full_option_tape | 44 | dated trades.jsonl matches event log; tape_present |
| 2026-04-29 | burst_promotion_tape | post_exit_observation, edge_1s3s, microburst_gate, promotion_3s, full_option_tape | 39 | dated trades.jsonl matches event log; tape_present |

## Day-wise Performance By Patch Era
| date | patch_era | total_trades | net_pnl | win_rate | avg_win | avg_loss | profit_factor | max_intraday_drawdown | num_1s_kills | num_3s_kills | num_hard_stops | num_target_hits | num_promoted_trades |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-23 | pre_1s3s | 55 | -12000.000 | 0.709 | 1435.897 | -4250.000 | 0.824 | -28000.000 | 0 | 0 | 14 | 39 | 0 |
| 2026-03-24 | pre_1s3s | 57 | -21800.000 | 0.702 | 1362.500 | -4488.235 | 0.714 | -30275.000 | 0 | 0 | 2 | 40 | 0 |
| 2026-03-25 | pre_1s3s | 51 | -7900.000 | 0.706 | 1347.222 | -3760.000 | 0.860 | -20575.000 | 0 | 0 | 1 | 36 | 0 |
| 2026-03-27 | pre_1s3s | 48 | -13700.000 | 0.667 | 1375.000 | -3606.250 | 0.763 | -28275.000 | 0 | 0 | 3 | 32 | 0 |
| 2026-03-30 | pre_1s3s | 54 | -23950.000 | 0.630 | 1441.176 | -3647.500 | 0.672 | -26700.000 | 0 | 0 | 3 | 34 | 0 |
| 2026-04-01 | pre_1s3s | 57 | -21925.000 | 0.719 | 1463.415 | -5120.313 | 0.732 | -80600.000 | 0 | 0 | 4 | 41 | 0 |
| 2026-04-02 | pre_1s3s | 57 | -15700.000 | 0.667 | 1368.421 | -3563.158 | 0.768 | -62875.000 | 0 | 0 | 2 | 38 | 0 |
| 2026-04-06 | pre_1s3s | 53 | -41400.000 | 0.736 | 1410.256 | -6885.714 | 0.571 | -89475.000 | 0 | 0 | 3 | 39 | 0 |
| 2026-04-07 | pre_1s3s | 18 | 7625.000 | 0.833 | 1500.000 | -4958.333 | 1.513 | -7250.000 | 0 | 0 | 0 | 15 | 0 |
| 2026-04-08 | pre_1s3s | 35 | 20250.000 | 0.857 | 1433.333 | -4550.000 | 1.890 | -18000.000 | 0 | 0 | 0 | 30 | 0 |
| 2026-04-09 | pre_1s3s | 25 | 20800.000 | 0.880 | 1454.545 | -3733.333 | 2.857 | -10500.000 | 0 | 0 | 0 | 22 | 0 |
| 2026-04-10 | pre_1s3s | 47 | -13575.000 | 0.638 | 1411.667 | -3289.706 | 0.757 | -52125.000 | 0 | 0 | 4 | 29 | 0 |
| 2026-04-13 | edge_1s3s | 50 | 6100.000 | 0.620 | 1292.742 | -1788.158 | 1.180 | -28350.000 | 8 | 12 | 5 | 25 | 0 |
| 2026-04-15 | edge_1s3s | 46 | -2825.000 | 0.435 | 1263.750 | -1124.000 | 0.899 | -26775.000 | 18 | 10 | 2 | 16 | 0 |
| 2026-04-16 | edge_1s3s | 56 | 13225.000 | 0.625 | 1372.857 | -1741.250 | 1.380 | -33875.000 | 11 | 6 | 7 | 32 | 0 |
| 2026-04-17 | edge_1s3s | 50 | -3500.000 | 0.440 | 1165.909 | -1121.154 | 0.880 | -26825.000 | 23 | 9 | 2 | 16 | 0 |
| 2026-04-20 | edge_1s3s | 51 | -5800.000 | 0.451 | 1357.609 | -1424.038 | 0.843 | -30400.000 | 17 | 11 | 4 | 19 | 0 |
| 2026-04-21 | edge_1s3s | 42 | -9900.000 | 0.429 | 1112.500 | -1301.087 | 0.669 | -23225.000 | 17 | 10 | 3 | 12 | 0 |
| 2026-04-22 | burst_promotion | 46 | 11975.000 | 0.522 | 1391.667 | -1020.238 | 1.559 | -18275.000 | 15 | 13 | 2 | 16 | 5 |
| 2026-04-23 | burst_promotion | 54 | -21975.000 | 0.389 | 1545.238 | -1700.781 | 0.596 | -47700.000 | 18 | 10 | 8 | 18 | 8 |
| 2026-04-24 | burst_promotion_tape | 52 | 4375.000 | 0.481 | 1569.000 | -1394.000 | 1.126 | -32825.000 | 19 | 10 | 3 | 20 | 11 |
| 2026-04-27 | burst_promotion_tape | 48 | -10675.000 | 0.375 | 1243.056 | -1180.357 | 0.677 | -30350.000 | 18 | 14 | 3 | 13 | 6 |
| 2026-04-28 | burst_promotion_tape | 44 | -9050.000 | 0.477 | 1282.143 | -1564.130 | 0.748 | -33625.000 | 14 | 10 | 4 | 16 | 2 |
| 2026-04-29 | burst_promotion_tape | 39 | -26200.000 | 0.359 | 1389.286 | -1902.083 | 0.426 | -42125.000 | 13 | 8 | 7 | 11 | 3 |

## Post-patch Failure Modes
| date | failure_mode | trades | net_pnl |
| --- | --- | --- | --- |
| 2026-04-22 | good entry but 1s killed too early | 11 | -7750.000 |
| 2026-04-22 | bad entry immediately | 4 | -6600.000 |
| 2026-04-22 | hard stop / tail event | 1 | -3475.000 |
| 2026-04-22 | good entry but 3s killed too early | 4 | -2375.000 |
| 2026-04-22 | stale 5-minute candle signal | 1 | -1225.000 |
| 2026-04-23 | bad entry immediately | 11 | -20350.000 |
| 2026-04-23 | hard stop / tail event | 3 | -12500.000 |
| 2026-04-23 | good entry but 1s killed too early | 11 | -10750.000 |
| 2026-04-23 | good entry but 3s killed too early | 3 | -3750.000 |
| 2026-04-23 | fake burst / exhaustion | 2 | -3725.000 |
| 2026-04-23 | stale 5-minute candle signal | 2 | -3350.000 |
| 2026-04-24 | good entry but 1s killed too early | 12 | -12975.000 |
| 2026-04-24 | bad entry immediately | 6 | -11125.000 |
| 2026-04-24 | hard stop / tail event | 2 | -6800.000 |
| 2026-04-24 | fake burst / exhaustion | 4 | -2175.000 |
| 2026-04-24 | good entry but 3s killed too early | 1 | -1775.000 |
| 2026-04-27 | bad entry immediately | 7 | -15675.000 |
| 2026-04-27 | good entry but 1s killed too early | 10 | -6600.000 |
| 2026-04-27 | hard stop / tail event | 1 | -3975.000 |
| 2026-04-27 | stale 5-minute candle signal | 1 | -2775.000 |
| 2026-04-27 | fake burst / exhaustion | 3 | -2275.000 |
| 2026-04-27 | good entry but 3s killed too early | 5 | -1650.000 |
| 2026-04-27 | good entry but bad promotion | 1 | -100.000 |
| 2026-04-28 | bad entry immediately | 6 | -13725.000 |
| 2026-04-28 | good entry but 1s killed too early | 9 | -11150.000 |
| 2026-04-28 | hard stop / tail event | 2 | -7225.000 |
| 2026-04-28 | good entry but 3s killed too early | 4 | -2075.000 |
| 2026-04-28 | stale 5-minute candle signal | 2 | -1800.000 |
| 2026-04-29 | bad entry immediately | 6 | -16175.000 |
| 2026-04-29 | hard stop / tail event | 4 | -13450.000 |
| 2026-04-29 | stale 5-minute candle signal | 6 | -6975.000 |
| 2026-04-29 | fake burst / exhaustion | 3 | -6475.000 |
| 2026-04-29 | good entry but 1s killed too early | 4 | -2300.000 |
| 2026-04-29 | good entry but 3s killed too early | 1 | -275.000 |

## Worst Trades
| date | trade_id | signal_kind | exit_reason | net_pnl | failure_mode | burst_score_effective | candle_age_seconds | mfe | mae | post_exit_points_best_recovery | post_exit_hit_target_15s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-23 | 20260423T114505|BFO:SENSEX2642377900PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -4750.000 | hard stop / tail event | 3.000 | 5.543 | 2.750 | -9.500 | -0.700 | False |
| 2026-04-27 | 20260427T114501|BFO:SENSEX26APR76800CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -4275.000 | bad entry immediately | 3.000 | 1.425 | 0.000 | -8.550 | 6.700 | False |
| 2026-04-28 | 20260428T122006|BFO:SENSEX26APR77200PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -4175.000 | bad entry immediately | 4.000 | 6.246 | 0.450 | -8.350 | -3.000 | False |
| 2026-04-23 | 20260423T123002|BFO:SENSEX2642377900PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -4000.000 | hard stop / tail event | 3.000 | 2.731 | 2.050 | -8.000 | 6.300 | False |
| 2026-04-27 | 20260427T112000|BFO:SENSEX26APR77000CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3975.000 | hard stop / tail event | 4.000 | 0.831 | 1.600 | -7.950 | 1.550 | False |
| 2026-04-27 | 20260427T105508|BFO:SENSEX26APR77100CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3750.000 | bad entry immediately | 3.000 | 8.399 | 0.000 | -7.500 | 4.550 | False |
| 2026-04-23 | 20260423T143014|BFO:SENSEX2642377900PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -3750.000 | hard stop / tail event | 4.000 | 14.330 | 1.000 | -7.500 | 7.300 | False |
| 2026-04-28 | 20260428T113005|BFO:SENSEX26APR77300PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -3750.000 | hard stop / tail event | 4.000 | 5.353 | 0.000 | -7.500 | 11.150 | True |
| 2026-04-29 | 20260429T100504|BFO:SENSEX26APR77400CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3650.000 | hard stop / tail event | 3.000 | 5.045 | 0.000 | -7.300 | 13.800 | True |
| 2026-04-24 | 20260424T120518|BFO:SENSEX26APR76500CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3650.000 | hard stop / tail event | 4.000 | 19.050 | 2.850 | -7.300 | 0.500 | False |
| 2026-04-29 | 20260429T115502|BFO:SENSEX26APR77600CE|REVERSAL_CALL|CALL | REVERSAL_CALL | EDGE_HARD_STOP | -3600.000 | hard stop / tail event | 4.000 | 2.420 | 2.000 | -7.200 | 5.500 | False |
| 2026-04-28 | 20260428T125515|BFO:SENSEX26APR77200PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -3475.000 | hard stop / tail event | 3.000 | 16.109 | 2.450 | -6.950 | -2.850 | False |
| 2026-04-22 | 20260422T124529|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3475.000 | hard stop / tail event | 3.000 | 29.998 | 2.600 | -6.550 | -1.600 | False |
| 2026-04-29 | 20260429T101008|BFO:SENSEX26APR77400CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3475.000 | bad entry immediately | 4.000 | 8.344 | 0.000 | -6.950 | 9.100 | False |
| 2026-04-23 | 20260423T132002|BFO:SENSEX2642377700CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3350.000 | bad entry immediately | 4.000 | 3.078 | 0.000 | -6.700 | 6.900 | False |
| 2026-04-23 | 20260423T093501|BFO:SENSEX2642378100PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -3350.000 | bad entry immediately | 4.000 | 1.748 | 0.000 | -6.700 | 0.950 | False |
| 2026-04-23 | 20260423T141512|BFO:SENSEX2642378000PE|CONTINUATION_PUT|PUT | CONTINUATION_PUT | EDGE_HARD_STOP | -3325.000 | bad entry immediately | 3.000 | 12.786 | 0.000 | -6.650 | 1.750 | False |
| 2026-04-23 | 20260423T093001|BFO:SENSEX2642377800CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3275.000 | bad entry immediately | 4.000 | 1.219 | 0.000 | -6.550 | -2.550 | False |
| 2026-04-22 | 20260422T115514|BFO:SENSEX2642378400CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3200.000 | bad entry immediately | 3.000 | 14.399 | 0.000 | -6.400 | 5.050 | False |
| 2026-04-29 | 20260429T095004|BFO:SENSEX26APR77300CE|CONTINUATION_CALL|CALL | CONTINUATION_CALL | EDGE_HARD_STOP | -3175.000 | bad entry immediately | 3.000 | 4.291 | 0.000 | -6.350 | 4.600 | False |

## Entry Freshness And Burst Context
| analysis_axis | bucket | trades | net_pnl | avg_pnl | win_rate | target_hit_rate | hard_stop_rate | avg_burst_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| candle_age | 0-10s | 144 | -28225.000 | -196.007 | 0.451 | 0.361 | 0.118 | 3.688 |
| candle_age | 10-20s | 76 | -13625.000 | -179.276 | 0.447 | 0.329 | 0.092 | 3.671 |
| candle_age | 20-30s | 41 | -10150.000 | -247.561 | 0.390 | 0.268 | 0.073 | 3.659 |
| candle_age | 30-40s | 22 | 450.000 | 20.455 | 0.364 | 0.273 | 0.000 | 3.773 |
| candle_age | 40s+ | 0 | 0.000 |  |  |  |  |  |
| signal_to_entry | 0-250ms | 244 | -45600.000 | -186.885 | 0.426 | 0.332 | 0.098 | 3.693 |
| signal_to_entry | 250-500ms | 38 | -4000.000 | -105.263 | 0.500 | 0.342 | 0.079 | 3.658 |
| signal_to_entry | 0.5-1s | 0 | 0.000 |  |  |  |  |  |
| signal_to_entry | 1-2s | 1 | -1950.000 | -1950.000 | 0.000 | 0.000 | 0.000 | 3.000 |
| signal_to_entry | 2s+ | 0 | 0.000 |  |  |  |  |  |
| underlying_accel | neg | 4 | -1350.000 | -337.500 | 0.500 | 0.250 | 0.000 | 3.000 |
| underlying_accel | 0-1.5 | 1 | -1075.000 | -1075.000 | 0.000 | 0.000 | 0.000 | 3.000 |
| underlying_accel | 1.5-3 | 62 | -16325.000 | -263.306 | 0.435 | 0.355 | 0.065 | 3.274 |
| underlying_accel | 3-5 | 79 | -7225.000 | -91.456 | 0.468 | 0.354 | 0.127 | 3.646 |
| underlying_accel | 5+ | 137 | -25575.000 | -186.679 | 0.416 | 0.314 | 0.095 | 3.920 |
| option_velocity | neg | 71 | -37875.000 | -533.451 | 0.366 | 0.268 | 0.155 | 3.296 |
| option_velocity | 0-1 | 22 | -14300.000 | -650.000 | 0.318 | 0.227 | 0.136 | 3.364 |
| option_velocity | 1-2 | 18 | -1250.000 | -69.444 | 0.444 | 0.333 | 0.000 | 3.333 |
| option_velocity | 2-4 | 65 | -1775.000 | -27.308 | 0.462 | 0.308 | 0.062 | 3.985 |
| option_velocity | 4+ | 107 | 3650.000 | 34.112 | 0.486 | 0.411 | 0.084 | 3.888 |
| stale_candle_flag | False | 220 | -41850.000 | -190.227 | 0.450 | 0.350 | 0.109 | 3.682 |
| stale_candle_flag | True | 63 | -9700.000 | -153.968 | 0.381 | 0.270 | 0.048 | 3.698 |
| immediate_confirmation | False | 130 | -159350.000 | -1225.769 | 0.069 | 0.008 | 0.123 | 3.677 |
| immediate_confirmation | True | 153 | 107800.000 | 704.575 | 0.745 | 0.608 | 0.072 | 3.693 |

| burst_score | trades | net_pnl | avg_pnl | win_rate | target_hit_rate | hard_stop_rate | avg_mfe | avg_mae | avg_candle_age_seconds | promoted_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.000 | 125.000 | -43800.000 | -350.400 | 0.424 | 0.344 | 0.112 | 2.029 | -2.170 | 12.855 | 0.000 |
| 4.000 | 123.000 | -24900.000 | -202.439 | 0.439 | 0.366 | 0.106 | 2.000 | -1.943 | 12.034 | 0.000 |
| 5.000 | 34.000 | 16000.000 | 470.588 | 0.441 | 0.176 | 0.000 | 3.099 | -1.393 | 12.828 | 1.000 |
| 6.000 | 1.000 | 1150.000 | 1150.000 | 1.000 | 0.000 | 0.000 | 3.650 | 0.000 | 12.789 | 1.000 |

| candle_age_bucket | burst_bucket | trades | net_pnl | avg_pnl | win_rate | target_hit_rate | hard_stop_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0-10s | 3 | 62 | -21200.000 | -341.935 | 0.468 | 0.371 | 0.129 |
| 0-10s | 4 | 65 | -17925.000 | -275.769 | 0.446 | 0.385 | 0.138 |
| 0-10s | 5+ | 17 | 10900.000 | 641.176 | 0.412 | 0.235 | 0.000 |
| 10-20s | 3 | 36 | -8175.000 | -227.083 | 0.444 | 0.389 | 0.111 |
| 10-20s | 4 | 30 | -9025.000 | -300.833 | 0.433 | 0.333 | 0.100 |
| 10-20s | 5+ | 10 | 3575.000 | 357.500 | 0.500 | 0.100 | 0.000 |
| 20-30s | 3 | 18 | -12500.000 | -694.444 | 0.333 | 0.222 | 0.111 |
| 20-30s | 4 | 19 | -2250.000 | -118.421 | 0.368 | 0.316 | 0.053 |
| 20-30s | 5+ | 4 | 4600.000 | 1150.000 | 0.750 | 0.250 | 0.000 |
| 30-40s | 3 | 9 | -1925.000 | -213.889 | 0.222 | 0.222 | 0.000 |
| 30-40s | 4 | 9 | 4300.000 | 477.778 | 0.556 | 0.444 | 0.000 |
| 30-40s | 5+ | 4 | -1925.000 | -481.250 | 0.250 | 0.000 | 0.000 |

## Promotion Audit
| date | trade_id | burst_score | exit_reason | net_pnl | mfe | hit_plus3_during_trade | hit_plus5_during_trade | hit_plus7_during_trade | stalled_after_plus3 | promoted_3s_passed | promotion_persistence_passed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-22 | 20260422T094000|BFO:SENSEX2642378900PE|CONTINUATION_PUT|PUT | 5.000 | TARGET_HIT | 3500.000 | 9.350 | True | True | True | False | False | False |
| 2026-04-22 | 20260422T100001|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT | 5.000 | PROMOTED_FAIL_3S | 4150.000 | 6.550 | True | True | False | False | False | False |
| 2026-04-22 | 20260422T102514|BFO:SENSEX2642378700PE|CONTINUATION_PUT|PUT | 5.000 | PROMOTED_FAIL_3S | 125.000 | 4.900 | True | False | False | False | False | False |
| 2026-04-22 | 20260422T130514|BFO:SENSEX2642378500CE|REVERSAL_CALL|CALL | 5.000 | PROMOTED_FAIL_3S | 50.000 | 1.350 | False | False | False | False | False | False |
| 2026-04-22 | 20260422T145002|BFO:SENSEX2642378800PE|CONTINUATION_PUT|PUT | 5.000 | EARLY_FAIL_1S | -975.000 | 0.000 | False | False | False | False | False | False |
| 2026-04-23 | 20260423T095504|BFO:SENSEX2642377900CE|CONTINUATION_CALL|CALL | 5.000 | EARLY_FAIL_1S | -1375.000 | 0.000 | False | False | False | False | False | False |
| 2026-04-23 | 20260423T105510|BFO:SENSEX2642378000PE|REVERSAL_PUT|PUT | 5.000 | EARLY_FAIL_1S | -525.000 | 0.000 | False | False | False | False | False | False |
| 2026-04-23 | 20260423T113522|BFO:SENSEX2642378000PE|CONTINUATION_PUT|PUT | 5.000 | PROMOTED_FAIL_3S | 1800.000 | 3.600 | True | False | False | False | False | False |
| 2026-04-23 | 20260423T120512|BFO:SENSEX2642378000PE|CONTINUATION_PUT|PUT | 6.000 | PROMOTED_FAIL_3S | 1150.000 | 3.650 | True | False | False | False | False | False |
| 2026-04-23 | 20260423T121519|BFO:SENSEX2642377700CE|CONTINUATION_CALL|CALL | 5.000 | EARLY_FAIL_1S | -175.000 | 0.000 | False | False | False | False | False | False |
| 2026-04-23 | 20260423T133011|BFO:SENSEX2642378200PE|REVERSAL_PUT|PUT | 5.000 | TARGET_HIT | 3500.000 | 7.400 | True | True | True | False | True | True |
| 2026-04-23 | 20260423T135501|BFO:SENSEX2642377700CE|CONTINUATION_CALL|CALL | 5.000 | EARLY_FAIL_1S | -1125.000 | 0.200 | False | False | False | False | False | False |
| 2026-04-23 | 20260423T144018|BFO:SENSEX2642377900PE|REVERSAL_PUT|PUT | 5.000 | PROMOTED_FAIL_3S | -800.000 | 1.800 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T092502|BFO:SENSEX26APR77500PE|CONTINUATION_PUT|PUT | 5.000 | PROMOTED_FAIL_3S | 1200.000 | 2.400 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T093001|BFO:SENSEX26APR77400PE|CONTINUATION_PUT|PUT | 5.000 | TARGET_HIT | 3500.000 | 11.100 | True | True | True | False | False | False |
| 2026-04-24 | 20260424T095502|BFO:SENSEX26APR77100PE|CONTINUATION_PUT|PUT | 5.000 | TARGET_HIT | 3500.000 | 9.950 | True | True | True | False | True | True |
| 2026-04-24 | 20260424T103037|BFO:SENSEX26APR76700CE|CONTINUATION_CALL|CALL | 5.000 | EARLY_FAIL_1S | -2450.000 | 0.000 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T105515|BFO:SENSEX26APR76700CE|CONTINUATION_CALL|CALL | 5.000 | PROMOTED_FAIL_3S | 900.000 | 1.800 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T112020|BFO:SENSEX26APR76600CE|CONTINUATION_CALL|CALL | 5.000 | EARLY_FAIL_1S | -950.000 | 0.150 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T114506|BFO:SENSEX26APR77000PE|CONTINUATION_PUT|PUT | 5.000 | EARLY_FAIL_1S | 0.000 | 0.000 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T124025|BFO:SENSEX26APR76900PE|CONTINUATION_PUT|PUT | 5.000 | PROMOTED_FAIL_3S | 250.000 | 1.900 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T124500|BFO:SENSEX26APR76800PE|CONTINUATION_PUT|PUT | 5.000 | PROMOTED_FAIL_3S | -75.000 | 1.750 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T125511|BFO:SENSEX26APR76500CE|CONTINUATION_CALL|CALL | 5.000 | PROMOTED_FAIL_3S | -650.000 | 2.850 | False | False | False | False | False | False |
| 2026-04-24 | 20260424T143026|BFO:SENSEX26APR76400CE|CONTINUATION_CALL|CALL | 5.000 | TARGET_HIT | 3500.000 | 15.850 | True | True | True | False | False | False |
| 2026-04-27 | 20260427T095506|BFO:SENSEX26APR77100CE|CONTINUATION_CALL|CALL | 5.000 | PROMOTED_FAIL_3S | -1725.000 | 0.950 | False | False | False | False | False | False |

## 1s And 3s Exit Audit
### 1s checkpoint
| audit_bucket | trades | net_pnl |
| --- | --- | --- |
| bad_kept | 58 | -109450.000 |
| bad_killed | 70 | -82850.000 |
| good_kept | 91 | 121825.000 |
| good_killed | 27 | -17125.000 |
| not_eligible | 37 | 36050.000 |
### 3s checkpoint
| audit_bucket | trades | net_pnl |
| --- | --- | --- |
| bad_kept | 46 | -80150.000 |
| bad_killed | 36 | -18775.000 |
| good_kept | 28 | 46000.000 |
| good_killed | 29 | 9175.000 |
| not_eligible | 144 | -7800.000 |

## Full Option Tape Comparison
| date | policy | trades | gross_pnl | net_pnl | target_hits | hard_stops | early_fail_1s | early_fail_3s | raw_burst_opportunities | matched_actual_entries | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-28 | actual_system | 44 | -9050.000 | -9050.000 | 16 | 4 | 14 | 10 | 27128 | 4 | actual candle-gated live trades |
| 2026-04-28 | pure_burst_only_sim | 1252 | -214355.000 | -214355.000 | 64 | 12 | 931 | 243 | 27128 | 0 | 1-position-at-a-time second-level replay |
| 2026-04-29 | actual_system | 39 | -26200.000 | -26200.000 | 11 | 7 | 13 | 8 | 29283 | 4 | actual candle-gated live trades |
| 2026-04-29 | pure_burst_only_sim | 1198 | -98788.000 | -98788.000 | 76 | 5 | 825 | 289 | 29283 | 0 | 1-position-at-a-time second-level replay |
| OVERALL | actual_system | 83 | -35250.000 | -35250.000 | 27 | 11 | 27 | 18 | 56411 | 8 | aggregate over last 2 tape days |
| OVERALL | pure_burst_only_sim | 2450 | -313143.000 | -313143.000 | 140 | 17 | 1756 | 532 | 56411 | 0 | aggregate over last 2 tape days |
### Top missed burst-only opportunities
| date | entry_time | symbol | score | target_class | exit_reason | net_pnl | runup_points | drawdown_points |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-28 | 2026-04-28 12:22:13 | BFO:SENSEX26APR77100PE | 5 | promoted | TARGET_HIT | 14190.000 | 23.650 | 0.000 |
| 2026-04-28 | 2026-04-28 13:35:30 | BFO:SENSEX26APR77800CE | 3 | normal | TARGET_HIT | 7680.000 | 3.000 | 0.000 |
| 2026-04-28 | 2026-04-28 11:45:47 | BFO:SENSEX26APR76500PE | 3 | normal | TARGET_HIT | 6142.000 | 3.700 | 0.000 |
| 2026-04-28 | 2026-04-28 13:40:43 | BFO:SENSEX26APR76300PE | 3 | normal | TARGET_HIT | 6142.000 | 3.700 | 0.000 |
| 2026-04-28 | 2026-04-28 15:18:59 | BFO:SENSEX26APR75300PE | 4 | normal | EARLY_FAIL_3S | 5904.000 | 0.600 | 0.000 |
| 2026-04-28 | 2026-04-28 14:01:54 | BFO:SENSEX26APR76900CE | 5 | promoted | TARGET_HIT | 5780.000 | 8.500 | 0.000 |
| 2026-04-28 | 2026-04-28 09:24:33 | BFO:SENSEX26APR76400PE | 3 | normal | TARGET_HIT | 5590.000 | 3.250 | 0.000 |
| 2026-04-28 | 2026-04-28 12:21:56 | BFO:SENSEX26APR77600PE | 5 | promoted | TARGET_HIT | 4940.000 | 13.000 | 0.000 |
| 2026-04-28 | 2026-04-28 09:54:47 | BFO:SENSEX26APR77200CE | 5 | promoted | TARGET_HIT | 4640.000 | 8.000 | 0.000 |
| 2026-04-28 | 2026-04-28 12:25:01 | BFO:SENSEX26APR76500PE | 3 | normal | TARGET_HIT | 4536.000 | 3.600 | 0.000 |
| 2026-04-28 | 2026-04-28 10:01:40 | BFO:SENSEX26APR78700CE | 3 | normal | EARLY_FAIL_3S | 4439.000 | 1.150 | 0.000 |
| 2026-04-28 | 2026-04-28 09:25:51 | BFO:SENSEX26APR78800CE | 3 | normal | EARLY_FAIL_3S | 4428.000 | 0.900 | 0.000 |
| 2026-04-28 | 2026-04-28 11:08:29 | BFO:SENSEX26APR76300PE | 3 | normal | EARLY_FAIL_3S | 4410.000 | 1.750 | 0.000 |
| 2026-04-28 | 2026-04-28 14:30:50 | BFO:SENSEX26APR76500CE | 3 | normal | TARGET_HIT | 4340.000 | 10.850 | 0.000 |
| 2026-04-28 | 2026-04-28 09:23:36 | BFO:SENSEX26APR76600PE | 3 | normal | TARGET_HIT | 4200.000 | 3.000 | 0.000 |
| 2026-04-28 | 2026-04-28 15:12:17 | BFO:SENSEX26APR77200CE | 4 | normal | TARGET_HIT | 4200.000 | 3.750 | 0.000 |
| 2026-04-28 | 2026-04-28 11:54:30 | BFO:SENSEX26APR76600PE | 3 | normal | TARGET_HIT | 4080.000 | 3.000 | 0.000 |
| 2026-04-28 | 2026-04-28 11:29:40 | BFO:SENSEX26APR76900PE | 5 | promoted | PROMOTED_FAIL_3S | 4059.000 | 5.650 | 0.000 |
| 2026-04-28 | 2026-04-28 10:47:54 | BFO:SENSEX26APR77200CE | 5 | promoted | TARGET_HIT | 4050.000 | 7.500 | 0.000 |
| 2026-04-28 | 2026-04-28 15:18:02 | BFO:SENSEX26APR75800PE | 4 | normal | EARLY_FAIL_3S | 3864.000 | 1.500 | 0.000 |

## ML / Dataset Artifact Review
- Canonical dataset metadata: {"canonical_dataset_exists": true, "canonical_dataset_path": "/Users/ankurkumar/Downloads/sensex-noise-papertrade/analysis/canonical_trades_ml_dataset.csv", "canonical_date_max": "2026-04-24", "canonical_date_min": "2026-03-23", "canonical_rows": 1004}
- Promotion dataset metadata: {"shadow_bad_trade_rate": 0.5273390036452005, "tape_meta": {"per_day": {"2026-04-28": {"date": "2026-04-28", "exists": true, "parse_errors": 0, "path": "/Users/ankurkumar/Downloads/sensex-noise-papertrade/data/tape/sensex_options/2026-04-28/options.jsonl", "raw_candidate_count": 27128, "raw_rows": 1482281, "selected_trade_count": 1252, "status": "ok", "unique_strikes": 40, "unique_symbols": 79}, "2026-04-29": {"date": "2026-04-29", "exists": true, "parse_errors": 0, "path": "/Users/ankurkumar/Downloads/sensex-noise-papertrade/data/tape/sensex_options/2026-04-29/options.jsonl", "raw_candidate_count": 29283, "raw_rows": 1426610, "selected_trade_count": 1198, "status": "ok", "unique_strikes": 39, "unique_symbols": 78}}, "selected_tape_days": ["2026-04-28", "2026-04-29"]}, "target_bucket_counts": {"bad_trade": 350, "extend_to_5": 73, "extend_to_7": 236, "keep_3": 80}, "target_live_trainable_rate": 0.5263870094722598, "target_model_results_present": false, "target_promotion_live_rows": 739, "target_promotion_shadow_rows": 823}
- No persisted `target_model_results` artifact was found, so there is no stored model confusion matrix or live-vs-model PnL backtest to reconcile directly.

## Final Verdict
- **Progressing or circling?** Circling. The strategy improved from the deeply negative pre-1s/3s era into a near-flat **edge_1s/3s** phase (-2,700 over 6 sessions), but the subsequent burst/promotion live phase regressed to **-51,550 over 6 sessions** with **4** negative days.
- **Patch that clearly added value:** the 1s/3s edge-invalidations plus richer journaling improved robustness relative to the original strategy. They did not create a durable edge, but they removed some of the older tail behavior.
- **Patch adding complexity without stable value yet:** the burst gate, promotion logic, and Layer-4 persistence did not translate into stable out-of-sample improvement after deployment. Promotion itself was net positive in this sample, so the deeper issue is candidate quality, not promotion alone.
- **Is the 5-minute candle trigger the main structural weakness?** Likely yes as a trigger, though not necessarily as context. The tape comparison shows many missed burst opportunities, while only a small fraction of live candle-gated entries align exactly with tape-detected burst onsets. The candle framework appears to be defining the candidate universe too coarsely for a seconds-scale convexity strategy.
- **Are we harvesting convexity or reacting to stale candle signals?** Both, but mostly the latter on bad days. When immediate post-entry confirmation exists, the post-patch trade set is strongly positive; without it, the system is catastrophically negative. That is consistent with a real convexity thesis buried inside a weak entry-selection process.
- **Recommended next step:** stop tuning exits in isolation. Keep candle state only as context if useful, but move the next research cycle to burst-onset entry logic with stricter candidate ranking and tape-based replay. Do not abandon the strategy family yet, but pause confidence in the current live trigger design.

## Limitations
- The repo has schema drift across March/April. Some early days rely on root journals rather than per-day files.
- Some dated `trades.jsonl` files appear to mirror event logs, so enriched trade journals are treated as the source of truth.
- Tape replay is a second-level approximation of current microburst logic; it is useful for bottleneck diagnosis, not a broker-grade execution simulation.
- One or two tape days are enough to test the candle bottleneck hypothesis, not enough to declare a stable new strategy.

## Charts
- ![equity_curve_by_patch_era.png](/Users/ankurkumar/Downloads/sensex-noise-papertrade/strategy_audit_results/equity_curve_by_patch_era.png)
- ![daywise_net_pnl.png](/Users/ankurkumar/Downloads/sensex-noise-papertrade/strategy_audit_results/daywise_net_pnl.png)
