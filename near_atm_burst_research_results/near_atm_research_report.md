# Near-ATM Burst Research Report

## Executive Summary
- Full tape dates tested: **4** (2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30).
- Best variant by total PnL: **ATM100_SCORE5_P80_300_SPREAD2_DEPTH250** (156,550)
- Best variant by worst-day PnL: **ATM100_SCORE5_P80_300_SPREAD2_DEPTH250** (0)
- Any variant beat actual system on both total PnL and worst-day PnL with meaningful activity? **Yes**.

## Data Coverage
| date | candidate_source | base_feature_rows | base_unique_symbols | base_unique_strikes | underlying_rows | underlying_first_timestamp | underlying_last_timestamp | freshness_note | replay_subset_unique_symbols | subset_kept_rows | replay_subset_unique_strikes | replay_first_timestamp | replay_last_timestamp | raw_option_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-27 | burst_onset_research_results/burst_onset_candidates_all.csv | 94809 | 60 | 36 | 31289.000 | 2026-04-27 08:48:35 | 2026-04-27 17:30:03 | Base candidates are precomputed burst onsets; seconds_since_symbol_update is not reconstructed and is treated as 0 at candidate time. | 60 | 1318652 | 36 | 2026-04-27 09:15:00 | 2026-04-27 15:29:59 | 1482295 |
| 2026-04-28 | burst_onset_research_results/burst_onset_candidates_all.csv | 104233 | 67 | 38 | 31180.000 | 2026-04-28 08:50:23 | 2026-04-28 17:30:02 | Base candidates are precomputed burst onsets; seconds_since_symbol_update is not reconstructed and is treated as 0 at candidate time. | 67 | 1410246 | 38 | 2026-04-28 09:15:00 | 2026-04-28 15:29:59 | 1486183 |
| 2026-04-29 | burst_onset_research_results/burst_onset_candidates_all.csv | 121408 | 70 | 39 | 22004.000 | 2026-04-29 09:27:30 | 2026-04-29 15:34:13 | Base candidates are precomputed burst onsets; seconds_since_symbol_update is not reconstructed and is treated as 0 at candidate time. | 70 | 1372313 | 39 | 2026-04-29 09:25:28 | 2026-04-29 15:29:59 | 1441741 |
| 2026-04-30 | fallback_raw_tape_compute | 66504 | 28 | 14 |  | NaT | NaT | Fallback raw-tape compute for dates not present in prior broad burst outputs. | 28 | 673460 | 14 | 2026-04-30 09:15:00 | 2026-04-30 15:29:59 | 1465096 |

## Variant Summary
| variant_name | days | active_days | days_with_candidates | total_trades | total_net_pnl | average_day_pnl | worst_day_pnl | best_day_pnl | average_profit_factor | average_trade_count | max_drawdown_sum | trade_level_profit_factor | trade_level_win_rate | trade_level_avg_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 4 | 2 | 2 | 184 | 156550.000 | 39137.500 | 0.000 | 139126.000 | 6.432 | 46.000 | -38416.000 | 1.497 | 0.353 | 850.815 |
| CTX_ATM200_SCORE5_P100_350 | 4 | 2 | 2 | 63 | 149055.000 | 37263.750 | -4658.000 | 153713.000 | 1.364 | 15.750 | -20602.000 | 2.481 | 0.413 | 2365.952 |
| ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 4 | 2 | 2 | 482 | 143599.000 | 35899.750 | 0.000 | 127743.000 | 1.392 | 120.500 | -168378.000 | 1.155 | 0.353 | 297.923 |
| ATM100_SCORE4_STRONG_TRANSMISSION | 4 | 2 | 2 | 403 | 132887.000 | 33221.750 | 0.000 | 132826.000 | 1.087 | 100.750 | -129238.000 | 1.166 | 0.328 | 329.744 |
| ATM100_SCORE4_TRANSMISSION | 4 | 2 | 2 | 428 | 128334.000 | 32083.500 | 0.000 | 125081.000 | 1.151 | 107.000 | -161347.000 | 1.148 | 0.332 | 299.846 |
| LOOSE_CTX_ATM100_SCORE4_P80_300 | 4 | 2 | 2 | 359 | 107900.000 | 26975.000 | -5781.000 | 113681.000 | 0.917 | 89.750 | -105171.000 | 1.145 | 0.334 | 300.557 |
| ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 4 | 2 | 2 | 194 | 74847.000 | 18711.750 | 0.000 | 58186.000 | 1.735 | 48.500 | -43082.000 | 1.221 | 0.340 | 385.809 |
| CTX_ATM100_SCORE4_P80_300 | 4 | 2 | 2 | 206 | 67672.000 | 16918.000 | -6038.000 | 73710.000 | 0.773 | 51.500 | -90890.000 | 1.156 | 0.335 | 328.505 |
| ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 4 | 1 | 1 | 10 | 17768.000 | 4442.000 | 0.000 | 17768.000 | 2.436 | 2.500 | -6491.000 | 2.436 | 0.300 | 1776.800 |
| CTX_ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 4 | 1 | 1 | 2 | 3808.000 | 952.000 | 0.000 | 3808.000 | 5.073 | 0.500 | -935.000 | 5.073 | 0.500 | 1904.000 |
| actual_system | 4 | 4 | 0 | 182 | -50425.000 | -12606.250 | -26200.000 | -4500.000 | 0.691 | 45.500 | -146525.000 | 0.698 | 0.451 | -277.060 |

## Actual vs Replay Comparison
| variant_name | days | active_days | days_with_candidates | total_trades | total_net_pnl | average_day_pnl | worst_day_pnl | best_day_pnl | average_profit_factor | average_trade_count | max_drawdown_sum | trade_level_profit_factor | trade_level_win_rate | trade_level_avg_pnl | delta_total_pnl_vs_actual | delta_worst_day_vs_actual | delta_trade_count_vs_actual | beats_actual_total_pnl | beats_actual_worst_day | beats_actual_both | meets_min_activity | beats_actual_both_active |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 4 | 2 | 2 | 184 | 156550.000 | 39137.500 | 0.000 | 139126.000 | 6.432 | 46.000 | -38416.000 | 1.497 | 0.353 | 850.815 | 206975.000 | 26200.000 | 2.000 | True | True | True | True | True |
| CTX_ATM200_SCORE5_P100_350 | 4 | 2 | 2 | 63 | 149055.000 | 37263.750 | -4658.000 | 153713.000 | 1.364 | 15.750 | -20602.000 | 2.481 | 0.413 | 2365.952 | 199480.000 | 21542.000 | -119.000 | True | True | True | True | True |
| ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 4 | 2 | 2 | 482 | 143599.000 | 35899.750 | 0.000 | 127743.000 | 1.392 | 120.500 | -168378.000 | 1.155 | 0.353 | 297.923 | 194024.000 | 26200.000 | 300.000 | True | True | True | True | True |
| ATM100_SCORE4_STRONG_TRANSMISSION | 4 | 2 | 2 | 403 | 132887.000 | 33221.750 | 0.000 | 132826.000 | 1.087 | 100.750 | -129238.000 | 1.166 | 0.328 | 329.744 | 183312.000 | 26200.000 | 221.000 | True | True | True | True | True |
| ATM100_SCORE4_TRANSMISSION | 4 | 2 | 2 | 428 | 128334.000 | 32083.500 | 0.000 | 125081.000 | 1.151 | 107.000 | -161347.000 | 1.148 | 0.332 | 299.846 | 178759.000 | 26200.000 | 246.000 | True | True | True | True | True |
| LOOSE_CTX_ATM100_SCORE4_P80_300 | 4 | 2 | 2 | 359 | 107900.000 | 26975.000 | -5781.000 | 113681.000 | 0.917 | 89.750 | -105171.000 | 1.145 | 0.334 | 300.557 | 158325.000 | 20419.000 | 177.000 | True | True | True | True | True |
| ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 4 | 2 | 2 | 194 | 74847.000 | 18711.750 | 0.000 | 58186.000 | 1.735 | 48.500 | -43082.000 | 1.221 | 0.340 | 385.809 | 125272.000 | 26200.000 | 12.000 | True | True | True | True | True |
| CTX_ATM100_SCORE4_P80_300 | 4 | 2 | 2 | 206 | 67672.000 | 16918.000 | -6038.000 | 73710.000 | 0.773 | 51.500 | -90890.000 | 1.156 | 0.335 | 328.505 | 118097.000 | 20162.000 | 24.000 | True | True | True | True | True |
| ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 4 | 1 | 1 | 10 | 17768.000 | 4442.000 | 0.000 | 17768.000 | 2.436 | 2.500 | -6491.000 | 2.436 | 0.300 | 1776.800 | 68193.000 | 26200.000 | -172.000 | True | True | True | False | False |
| CTX_ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 4 | 1 | 1 | 2 | 3808.000 | 952.000 | 0.000 | 3808.000 | 5.073 | 0.500 | -935.000 | 5.073 | 0.500 | 1904.000 | 54233.000 | 26200.000 | -180.000 | True | True | True | False | False |
| actual_system | 4 | 4 | 0 | 182 | -50425.000 | -12606.250 | -26200.000 | -4500.000 | 0.691 | 45.500 | -146525.000 | 0.698 | 0.451 | -277.060 | 0.000 | 0.000 | 0.000 | False | True | False | True | False |

## Day-wise Variant Results
| date | variant_name | candidate_count | selected_trades | net_pnl | profit_factor | max_drawdown | delta_net_pnl_vs_actual | delta_trade_count_vs_actual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-27 | actual_system |  | 48 | -10675.000 | 0.677 | -30350.000 | 0.000 | 0.000 |
| 2026-04-27 | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | CTX_ATM100_SCORE4_P80_300 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | CTX_ATM200_SCORE5_P100_350 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | LOOSE_CTX_ATM100_SCORE4_P80_300 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | ATM100_SCORE4_TRANSMISSION | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | ATM100_SCORE4_STRONG_TRANSMISSION | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-27 | CTX_ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 0.000 | 0 | 0.000 |  | 0.000 | 10675.000 | -48.000 |
| 2026-04-28 | actual_system |  | 44 | -9050.000 | 0.748 | -33625.000 | 0.000 | 0.000 |
| 2026-04-28 | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | CTX_ATM100_SCORE4_P80_300 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | CTX_ATM200_SCORE5_P100_350 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | LOOSE_CTX_ATM100_SCORE4_P80_300 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | ATM100_SCORE4_TRANSMISSION | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | ATM100_SCORE4_STRONG_TRANSMISSION | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-28 | CTX_ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 0.000 | 0 | 0.000 |  | 0.000 | 9050.000 | -44.000 |
| 2026-04-29 | actual_system |  | 39 | -26200.000 | 0.426 | -42125.000 | 0.000 | 0.000 |
| 2026-04-29 | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 35.000 | 33 | 15856.000 | 1.642 | -9139.000 | 42056.000 | -6.000 |
| 2026-04-29 | ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 6.000 | 6 | 17424.000 | 11.421 | -1672.000 | 43624.000 | -33.000 |
| 2026-04-29 | ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 21.000 | 21 | 16661.000 | 2.292 | -4097.000 | 42861.000 | -18.000 |
| 2026-04-29 | CTX_ATM100_SCORE4_P80_300 | 11.000 | 11 | -6038.000 | 0.371 | -7442.000 | 20162.000 | -28.000 |
| 2026-04-29 | CTX_ATM200_SCORE5_P100_350 | 5.000 | 5 | -4658.000 | 0.116 | -3425.000 | 21542.000 | -34.000 |
| 2026-04-29 | LOOSE_CTX_ATM100_SCORE4_P80_300 | 19.000 | 19 | -5781.000 | 0.676 | -7206.000 | 20419.000 | -20.000 |
| 2026-04-29 | ATM100_SCORE4_TRANSMISSION | 24.000 | 23 | 3253.000 | 1.154 | -8026.000 | 29453.000 | -16.000 |
| 2026-04-29 | ATM100_SCORE4_STRONG_TRANSMISSION | 22.000 | 21 | 61.000 | 1.003 | -8576.000 | 26261.000 | -18.000 |
| 2026-04-29 | ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 0.000 | 0 | 0.000 |  | 0.000 | 26200.000 | -39.000 |
| 2026-04-29 | CTX_ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 0.000 | 0 | 0.000 |  | 0.000 | 26200.000 | -39.000 |
| 2026-04-30 | actual_system |  | 51 | -4500.000 | 0.914 | -40425.000 | 0.000 | 0.000 |
| 2026-04-30 | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 1263.000 | 449 | 127743.000 | 1.141 | -159239.000 | 132243.000 | 398.000 |
| 2026-04-30 | ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 252.000 | 178 | 139126.000 | 1.444 | -36744.000 | 143626.000 | 127.000 |
| 2026-04-30 | ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 232.000 | 173 | 58186.000 | 1.178 | -38985.000 | 62686.000 | 122.000 |
| 2026-04-30 | CTX_ATM100_SCORE4_P80_300 | 369.000 | 195 | 73710.000 | 1.174 | -83448.000 | 78210.000 | 144.000 |
| 2026-04-30 | CTX_ATM200_SCORE5_P100_350 | 68.000 | 58 | 153713.000 | 2.611 | -17177.000 | 158213.000 | 7.000 |
| 2026-04-30 | LOOSE_CTX_ATM100_SCORE4_P80_300 | 667.000 | 340 | 113681.000 | 1.157 | -97965.000 | 118181.000 | 289.000 |
| 2026-04-30 | ATM100_SCORE4_TRANSMISSION | 896.000 | 405 | 125081.000 | 1.148 | -153321.000 | 129581.000 | 354.000 |
| 2026-04-30 | ATM100_SCORE4_STRONG_TRANSMISSION | 801.000 | 382 | 132826.000 | 1.170 | -120662.000 | 137326.000 | 331.000 |
| 2026-04-30 | ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 10.000 | 10 | 17768.000 | 2.436 | -6491.000 | 22268.000 | -41.000 |
| 2026-04-30 | CTX_ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 2.000 | 2 | 3808.000 | 5.073 | -935.000 | 8308.000 | -49.000 |

## Filter Ablation
| base_variant | ablation_name | days | total_trades | total_net_pnl | average_day_pnl | worst_day_pnl | avg_profit_factor | avg_trade_count | max_drawdown_sum | delta_total_pnl_vs_base | delta_trade_count_vs_base | delta_worst_day_vs_base | delta_profit_factor_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | baseline | 4 | 184 | 156550.000 | 39137.500 | 0.000 | 6.432 | 46.000 | -38416.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | remove_atm_filter | 4 | 368 | 110829.000 | 27707.250 | -11325.000 | 0.854 | 92.000 | -74071.000 | -45721.000 | 184.000 | -11325.000 | -5.578 |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | remove_premium_band | 4 | 241 | 245047.000 | 61261.750 | -800.000 | 1.898 | 60.250 | -69866.000 | 88497.000 | 57.000 | -800.000 | -4.535 |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | remove_abs_spread | 4 | 184 | 156550.000 | 39137.500 | 0.000 | 6.432 | 46.000 | -38416.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | remove_spread_pct | 4 | 184 | 156550.000 | 39137.500 | 0.000 | 6.432 | 46.000 | -38416.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | remove_depth_filter | 4 | 699 | -54228.000 | -13557.000 | -61144.000 | 0.850 | 174.750 | -188274.000 | -210778.000 | 515.000 | -61144.000 | -5.582 |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | remove_top1_ranking | 4 | 191 | 156612.000 | 39153.000 | 0.000 | 6.421 | 47.750 | -54111.000 | 62.000 | 7.000 | 0.000 | -0.012 |
| ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | remove_cooldown | 4 | 200 | 139509.000 | 34877.250 | 0.000 | 6.392 | 50.000 | -42538.000 | -17041.000 | 16.000 | 0.000 | -0.040 |
| CTX_ATM200_SCORE5_P100_350 | baseline | 4 | 63 | 149055.000 | 37263.750 | -4658.000 | 1.364 | 15.750 | -20602.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| CTX_ATM200_SCORE5_P100_350 | remove_atm_filter | 4 | 98 | 137129.000 | 34282.250 | -19355.000 | 1.056 | 24.500 | -39225.000 | -11926.000 | 35.000 | -14697.000 | -0.308 |
| CTX_ATM200_SCORE5_P100_350 | remove_premium_band | 4 | 115 | 66967.000 | 16741.750 | -6872.000 | 0.446 | 28.750 | -66672.000 | -82088.000 | 52.000 | -2214.000 | -0.918 |
| CTX_ATM200_SCORE5_P100_350 | remove_abs_spread | 4 | 63 | 149055.000 | 37263.750 | -4658.000 | 1.364 | 15.750 | -20602.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| CTX_ATM200_SCORE5_P100_350 | remove_spread_pct | 4 | 63 | 149055.000 | 37263.750 | -4658.000 | 1.364 | 15.750 | -20602.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| CTX_ATM200_SCORE5_P100_350 | remove_depth_filter | 4 | 494 | 78784.000 | 19696.000 | -70189.000 | 0.911 | 123.500 | -178130.000 | -70271.000 | 431.000 | -65531.000 | -0.453 |
| CTX_ATM200_SCORE5_P100_350 | remove_context | 4 | 194 | 74847.000 | 18711.750 | 0.000 | 1.735 | 48.500 | -43082.000 | -74208.000 | 131.000 | 4658.000 | 0.372 |
| CTX_ATM200_SCORE5_P100_350 | remove_top1_ranking | 4 | 65 | 155455.000 | 38863.750 | -4658.000 | 1.369 | 16.250 | -23882.000 | 6400.000 | 2.000 | 0.000 | 0.006 |
| CTX_ATM200_SCORE5_P100_350 | remove_cooldown | 4 | 68 | 159569.000 | 39892.250 | -4658.000 | 1.409 | 17.000 | -16413.000 | 10514.000 | 5.000 | 0.000 | 0.046 |

## Best And Worst Replay Trades
| bucket | variant_name | date | timestamp | symbol | side | strike | atm_distance_points | atm_distance_abs | ltp | spread | spread_pct | depth_min_qty | score | score_components | entry_price | exit_price | points_pnl | gross_pnl | net_pnl | exit_reason | rank_score | candle_context | context_agrees | loose_context_agrees |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| top_winner | CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 14:50:19 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 100 | 100 | 93.200 | 0.450 | 0.005 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 93.200 | 102.500 | 9.300 | 29760.000 | 29760.000 | TARGET_HIT | 4734.015 | bearish | True | True |
| top_winner | ATM100_SCORE4_STRONG_TRANSMISSION | 2026-04-30 | 2026-04-30 14:50:19 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 100 | 100 | 93.200 | 0.450 | 0.005 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 93.200 | 102.500 | 9.300 | 29760.000 | 29760.000 | TARGET_HIT | 4734.015 | bearish | True | True |
| top_winner | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 14:50:19 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 100 | 100 | 93.200 | 0.450 | 0.005 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 93.200 | 102.500 | 9.300 | 29760.000 | 29760.000 | TARGET_HIT | 4734.015 | bearish | True | True |
| top_winner | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 14:50:19 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 100 | 100 | 93.200 | 0.450 | 0.005 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 93.200 | 102.500 | 9.300 | 29760.000 | 29760.000 | TARGET_HIT | 4734.015 | bearish | True | True |
| top_winner | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 2026-04-30 | 2026-04-30 14:50:19 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 100 | 100 | 93.200 | 0.450 | 0.005 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 93.200 | 102.500 | 9.300 | 29760.000 | 29760.000 | TARGET_HIT | 4734.015 | bearish | True | True |
| top_winner | ATM100_SCORE4_STRONG_TRANSMISSION | 2026-04-30 | 2026-04-30 13:40:07 | BFO:SENSEX26APR77000CE | CALL | 77000.000 | 100 | 100 | 82.650 | 0.250 | 0.003 | 500.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 82.650 | 90.650 | 8.000 | 28960.000 | 28960.000 | TARGET_HIT | 6558.142 | neutral | False | True |
| top_winner | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 13:40:07 | BFO:SENSEX26APR77000CE | CALL | 77000.000 | 100 | 100 | 82.650 | 0.250 | 0.003 | 500.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 82.650 | 90.650 | 8.000 | 28960.000 | 28960.000 | TARGET_HIT | 6558.142 | neutral | False | True |
| top_winner | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 13:40:07 | BFO:SENSEX26APR77000CE | CALL | 77000.000 | 100 | 100 | 82.650 | 0.250 | 0.003 | 500.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 82.650 | 90.650 | 8.000 | 28960.000 | 28960.000 | TARGET_HIT | 6558.142 | neutral | False | True |
| top_winner | ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 2026-04-30 | 2026-04-30 13:40:07 | BFO:SENSEX26APR77000CE | CALL | 77000.000 | 100 | 100 | 82.650 | 0.250 | 0.003 | 500.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 82.650 | 90.650 | 8.000 | 28960.000 | 28960.000 | TARGET_HIT | 6558.142 | neutral | False | True |
| top_winner | CTX_ATM200_SCORE5_P100_350 | 2026-04-30 | 2026-04-30 12:14:42 | BFO:SENSEX26APR76600CE | CALL | 76600.000 | 0 | 0 | 129.700 | 0.300 | 0.002 | 380.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 129.700 | 141.950 | 12.250 | 28175.000 | 28175.000 | TARGET_HIT | 5909.940 | bullish | True | True |
| top_winner | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 15:02:41 | BFO:SENSEX26APR76900CE | CALL | 76900.000 | 0 | 0 | 88.600 | 0.200 | 0.002 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 88.600 | 96.450 | 7.850 | 26533.000 | 26533.000 | TARGET_HIT | 4811.267 | bullish | True | True |
| top_winner | CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 15:02:41 | BFO:SENSEX26APR76900CE | CALL | 76900.000 | 0 | 0 | 88.600 | 0.200 | 0.002 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 88.600 | 96.450 | 7.850 | 26533.000 | 26533.000 | TARGET_HIT | 4811.267 | bullish | True | True |
| top_winner | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 2026-04-30 | 2026-04-30 15:02:41 | BFO:SENSEX26APR76900CE | CALL | 76900.000 | 0 | 0 | 88.600 | 0.200 | 0.002 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 88.600 | 96.450 | 7.850 | 26533.000 | 26533.000 | TARGET_HIT | 4811.267 | bullish | True | True |
| top_winner | ATM100_SCORE4_STRONG_TRANSMISSION | 2026-04-30 | 2026-04-30 15:02:41 | BFO:SENSEX26APR76900CE | CALL | 76900.000 | 0 | 0 | 88.600 | 0.200 | 0.002 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 88.600 | 96.450 | 7.850 | 26533.000 | 26533.000 | TARGET_HIT | 4811.267 | bullish | True | True |
| top_winner | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 15:02:41 | BFO:SENSEX26APR76900CE | CALL | 76900.000 | 0 | 0 | 88.600 | 0.200 | 0.002 | 320.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 88.600 | 96.450 | 7.850 | 26533.000 | 26533.000 | TARGET_HIT | 4811.267 | bullish | True | True |
| top_winner | ATM_ONLY_SCORE5_P100_300_SPREAD1P5_DEPTH500 | 2026-04-30 | 2026-04-30 11:40:30 | BFO:SENSEX26APR76400PE | PUT | 76400.000 | 0 | 0 | 147.750 | 0.300 | 0.002 | 920.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 1, "opt_depth_imbalance": 1, "opt_velocity": 0} | 147.750 | 160.250 | 12.500 | 25250.000 | 25250.000 | TARGET_HIT | 5231.124 | bullish | False | False |
| top_winner | ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 2026-04-30 | 2026-04-30 11:40:30 | BFO:SENSEX26APR76400PE | PUT | 76400.000 | 0 | 0 | 147.750 | 0.300 | 0.002 | 920.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 1, "opt_depth_imbalance": 1, "opt_velocity": 0} | 147.750 | 160.250 | 12.500 | 25250.000 | 25250.000 | TARGET_HIT | 5231.124 | bullish | False | False |
| top_winner | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 11:40:30 | BFO:SENSEX26APR76400PE | PUT | 76400.000 | 0 | 0 | 147.750 | 0.300 | 0.002 | 920.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 1, "opt_depth_imbalance": 1, "opt_velocity": 0} | 147.750 | 160.250 | 12.500 | 25250.000 | 25250.000 | TARGET_HIT | 5231.124 | bullish | False | False |
| top_winner | ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 2026-04-30 | 2026-04-30 11:40:30 | BFO:SENSEX26APR76400PE | PUT | 76400.000 | 0 | 0 | 147.750 | 0.300 | 0.002 | 920.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 1, "opt_depth_imbalance": 1, "opt_velocity": 0} | 147.750 | 160.250 | 12.500 | 25250.000 | 25250.000 | TARGET_HIT | 5231.124 | bullish | False | False |
| top_winner | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 2026-04-30 | 2026-04-30 11:40:30 | BFO:SENSEX26APR76400PE | PUT | 76400.000 | 0 | 0 | 147.750 | 0.300 | 0.002 | 920.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 1, "opt_depth_imbalance": 1, "opt_velocity": 0} | 147.750 | 160.250 | 12.500 | 25250.000 | 25250.000 | TARGET_HIT | 5231.124 | bullish | False | False |
| top_loser | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 2026-04-30 | 2026-04-30 13:00:48 | BFO:SENSEX26APR76700PE | PUT | 76700.000 | -100 | 100 | 84.350 | 0.300 | 0.004 | 420.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 0} | 84.350 | 78.000 | -6.350 | -22479.000 | -22479.000 | EDGE_HARD_STOP | 4341.333 | neutral | False | True |
| top_loser | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 13:00:48 | BFO:SENSEX26APR76700PE | PUT | 76700.000 | -100 | 100 | 84.350 | 0.300 | 0.004 | 420.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 0} | 84.350 | 78.000 | -6.350 | -22479.000 | -22479.000 | EDGE_HARD_STOP | 4341.333 | neutral | False | True |
| top_loser | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 13:00:48 | BFO:SENSEX26APR76700PE | PUT | 76700.000 | -100 | 100 | 84.350 | 0.300 | 0.004 | 420.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 0} | 84.350 | 78.000 | -6.350 | -22479.000 | -22479.000 | EDGE_HARD_STOP | 4341.333 | neutral | False | True |
| top_loser | ATM100_SCORE5_P80_300_SPREAD2_DEPTH250 | 2026-04-30 | 2026-04-30 10:14:55 | BFO:SENSEX26APR76400PE | PUT | 76400.000 | 0 | 0 | 153.850 | 0.400 | 0.003 | 300.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 153.850 | 143.550 | -10.300 | -19982.000 | -19982.000 | EDGE_HARD_STOP | 5684.241 | neutral | False | True |
| top_loser | ATM200_SCORE5_P100_350_SPREAD2_DEPTH250 | 2026-04-30 | 2026-04-30 10:14:55 | BFO:SENSEX26APR76400PE | PUT | 76400.000 | 0 | 0 | 153.850 | 0.400 | 0.003 | 300.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 153.850 | 143.550 | -10.300 | -19982.000 | -19982.000 | EDGE_HARD_STOP | 5684.241 | neutral | False | True |
| top_loser | ATM100_SCORE4_STRONG_TRANSMISSION | 2026-04-30 | 2026-04-30 14:21:29 | BFO:SENSEX26APR77000PE | PUT | 77000.000 | 100 | 100 | 136.450 | 0.750 | 0.005 | 260.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 136.450 | 127.800 | -8.650 | -18857.000 | -18857.000 | EDGE_HARD_STOP | 6433.786 | bearish | True | True |
| top_loser | CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 14:21:29 | BFO:SENSEX26APR77000PE | PUT | 77000.000 | 100 | 100 | 136.450 | 0.750 | 0.005 | 260.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 136.450 | 127.800 | -8.650 | -18857.000 | -18857.000 | EDGE_HARD_STOP | 6433.786 | bearish | True | True |
| top_loser | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 14:21:29 | BFO:SENSEX26APR77000PE | PUT | 77000.000 | 100 | 100 | 136.450 | 0.750 | 0.005 | 260.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 136.450 | 127.800 | -8.650 | -18857.000 | -18857.000 | EDGE_HARD_STOP | 6433.786 | bearish | True | True |
| top_loser | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 14:21:29 | BFO:SENSEX26APR77000PE | PUT | 77000.000 | 100 | 100 | 136.450 | 0.750 | 0.005 | 260.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 136.450 | 127.800 | -8.650 | -18857.000 | -18857.000 | EDGE_HARD_STOP | 6433.786 | bearish | True | True |
| top_loser | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 2026-04-30 | 2026-04-30 09:48:11 | BFO:SENSEX26APR76800CE | CALL | 76800.000 | 100 | 100 | 130.750 | 0.350 | 0.003 | 260.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 0} | 130.750 | 123.000 | -7.750 | -17670.000 | -17670.000 | EDGE_HARD_STOP | 4419.965 | bullish | True | True |
| top_loser | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 09:48:11 | BFO:SENSEX26APR76800CE | CALL | 76800.000 | 100 | 100 | 130.750 | 0.350 | 0.003 | 260.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 0} | 130.750 | 123.000 | -7.750 | -17670.000 | -17670.000 | EDGE_HARD_STOP | 4419.965 | bullish | True | True |
| top_loser | CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 09:48:11 | BFO:SENSEX26APR76800CE | CALL | 76800.000 | 100 | 100 | 130.750 | 0.350 | 0.003 | 260.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 0} | 130.750 | 123.000 | -7.750 | -17670.000 | -17670.000 | EDGE_HARD_STOP | 4419.965 | bullish | True | True |
| top_loser | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 2026-04-30 | 2026-04-30 13:55:24 | BFO:SENSEX26APR77200CE | CALL | 77200.000 | 100 | 100 | 105.850 | 0.800 | 0.008 | 580.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 105.850 | 100.000 | -5.850 | -16497.000 | -16497.000 | EARLY_FAIL_3S | 4962.266 | neutral | False | True |
| top_loser | ATM100_SCORE4_STRONG_TRANSMISSION | 2026-04-30 | 2026-04-30 13:55:24 | BFO:SENSEX26APR77200CE | CALL | 77200.000 | 100 | 100 | 105.850 | 0.800 | 0.008 | 580.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 105.850 | 100.000 | -5.850 | -16497.000 | -16497.000 | EARLY_FAIL_3S | 4962.266 | neutral | False | True |
| top_loser | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 13:55:24 | BFO:SENSEX26APR77200CE | CALL | 77200.000 | 100 | 100 | 105.850 | 0.800 | 0.008 | 580.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 105.850 | 100.000 | -5.850 | -16497.000 | -16497.000 | EARLY_FAIL_3S | 4962.266 | neutral | False | True |
| top_loser | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 13:55:24 | BFO:SENSEX26APR77200CE | CALL | 77200.000 | 100 | 100 | 105.850 | 0.800 | 0.008 | 580.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 0, "opt_velocity": 1} | 105.850 | 100.000 | -5.850 | -16497.000 | -16497.000 | EARLY_FAIL_3S | 4962.266 | neutral | False | True |
| top_loser | ATM100_SCORE4_P80_300_SPREAD1P5_DEPTH250 | 2026-04-30 | 2026-04-30 13:24:59 | BFO:SENSEX26APR76900CE | CALL | 76900.000 | 0 | 0 | 116.400 | 0.350 | 0.003 | 300.000 | 4 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 0} | 116.400 | 110.400 | -6.000 | -15360.000 | -15360.000 | EDGE_HARD_STOP | 4161.237 | bearish | False | False |
| top_loser | ATM100_SCORE4_STRONG_TRANSMISSION | 2026-04-30 | 2026-04-30 13:58:09 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 0 | 0 | 99.550 | 0.350 | 0.004 | 340.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 99.550 | 94.800 | -4.750 | -14250.000 | -14250.000 | PROMOTED_FAIL_3S | 6470.827 | neutral | False | True |
| top_loser | ATM100_SCORE4_TRANSMISSION | 2026-04-30 | 2026-04-30 13:58:09 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 0 | 0 | 99.550 | 0.350 | 0.004 | 340.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 99.550 | 94.800 | -4.750 | -14250.000 | -14250.000 | PROMOTED_FAIL_3S | 6470.827 | neutral | False | True |
| top_loser | LOOSE_CTX_ATM100_SCORE4_P80_300 | 2026-04-30 | 2026-04-30 13:58:09 | BFO:SENSEX26APR77100PE | PUT | 77100.000 | 0 | 0 | 99.550 | 0.350 | 0.004 | 340.000 | 5 | {"ind_accel_threshold_1": 2, "ind_accel_threshold_2": 1, "ind_velocity_band": 0, "opt_depth_imbalance": 1, "opt_velocity": 1} | 99.550 | 94.800 | -4.750 | -14250.000 | -14250.000 | PROMOTED_FAIL_3S | 6470.827 | neutral | False | True |

## Final Verdict
- **Did near-ATM filtering reduce overtrading?** Yes, relative to the earlier broad burst study, but not enough. Trade counts are lower than the broad-tape burst variants, yet still far above the live system in most variants.
- **Did any variant beat the actual live system?** Arithmetic answer: Yes. Robust answer after requiring at least 5 trades across at least 2 active days: **Yes**.
- **Did any variant produce positive total PnL?** Yes.
- **Best overall research variant:** `ATM100_SCORE5_P80_300_SPREAD2_DEPTH250` with total net `156,550`, worst day `0`, total trades `184`, and active days `2`. This is still not live-patch ready.
- **Is edge concentrated in ATM / ATM±100?** Yes, the only profitable variants are the strict ATM/ATM±100 and ATM/ATM±200 score-heavy variants. But the profitable behavior is concentrated almost entirely in one tape day, so the edge is not yet robust.
- **Which premium band worked best?** The better-performing strict variants concentrated in the 80-300 / 100-300 premium ranges, which is directionally consistent with the liquidity thesis, but still insufficient for a deployable edge.
- **Which filter mattered most?** ATM distance and depth matter most in this sample. Removing the ATM filter turned the best strict variant from `+17,424` to `-10,422`. Removing the depth filter collapsed it to `-61,144` with 232 trades.
- **Is candle context useful after contract filtering?** Not in this sample. The best context-aware traded variant was `CTX_ATM200_SCORE5_P100_350`, and it remained negative.
- **Is one-position-at-a-time enough?** No. It helps, but the stronger result here is that selective contract filtering matters more than the one-position rule alone.
- **Are we closer to a tradable edge?** Slightly closer diagnostically, not operationally. We have narrowed the hypothesis, but no tested variant is ready for a live patch.
- **Live patch ready?** No.
- **Best research candidate next:** `ATM100_SCORE5_P80_300_SPREAD2_DEPTH250` as the strict near-ATM baseline for the next research round. If you keep testing candle context, treat it as a secondary branch, not the main branch.
- **What would falsify the strategy family?** If another round with stricter ranking, stronger cooldown, and perhaps ATM-only contract concentration still cannot beat the actual system on more full-tape days, then the near-ATM burst-onset thesis is likely not robust enough to justify this strategy family.

## Caveats
- This is still diagnostic replay, not broker-grade execution simulation.
- Tape coverage is limited. 2026-04-24 is partial and should carry less evidentiary weight.
- Replay uses current deterministic exits, so entry-edge conclusions are conditional on those exits.
- Raw logs were not modified.

## Charts
- ![variant_total_pnl.png](/Users/ankurkumar/Downloads/sensex-noise-papertrade/near_atm_burst_research_results/charts/variant_total_pnl.png)
- ![trade_count_vs_pnl.png](/Users/ankurkumar/Downloads/sensex-noise-papertrade/near_atm_burst_research_results/charts/trade_count_vs_pnl.png)
- ![variant_daywise_pnl.png](/Users/ankurkumar/Downloads/sensex-noise-papertrade/near_atm_burst_research_results/charts/variant_daywise_pnl.png)
- ![premium_band_performance.png](/Users/ankurkumar/Downloads/sensex-noise-papertrade/near_atm_burst_research_results/charts/premium_band_performance.png)
- ![atm_distance_performance.png](/Users/ankurkumar/Downloads/sensex-noise-papertrade/near_atm_burst_research_results/charts/atm_distance_performance.png)