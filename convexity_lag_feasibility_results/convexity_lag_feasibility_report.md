# Convexity / Lead-Lag Feasibility Report

## Executive Summary
- Full-tape dates analyzed: **2026-04-24, 2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30**.
- Underlying impulse events (all cooldown sets): **8413**.
- Best impulse grid cell: **U_2S_20PTS**, lag **0s**, bucket **ATM**, hold **10s**; harvest-3 rate **59.1%**, net expectancy after 0.5 cost **2.67 pts**.
- Best direct candidate trade variant: **IMPULSE_ENTRY_0S_H10_CD30** on **U_1S_10PTS**, total PnL **109,025**, PF **1.36**, trades **460**.
- Peak lead-lag correlation: bucket **ATM_200**, side **CALL**, lag **-1s**, corr **0.173**.

## Data Coverage
| date | underlying_first | underlying_last | underlying_seconds | day_net_move | total_abs_intraday_move | trend_ratio | avg_realized_vol_1m | usable | option_symbols | option_strikes | option_first_timestamp | option_last_timestamp | option_raw_rows | impulse_count_cd10 | impulse_density_per_hour_cd10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-24 | 2026-04-24 08:40:24 | 2026-04-24 17:30:01 | 31778 | -999.790 | 50039.050 | 0.020 | 2.377 | True | 76 | 38 | 2026-04-24 10:31:17 | 2026-04-24 15:29:59 | 5258 | 816 | 92.441 |
| 2026-04-27 | 2026-04-27 08:48:35 | 2026-04-27 17:30:03 | 31289 | 639.420 | 49428.760 | 0.013 | 2.432 | True | 83 | 42 | 2026-04-27 09:15:00 | 2026-04-27 15:29:59 | 1482295 | 819 | 94.231 |
| 2026-04-28 | 2026-04-28 08:50:23 | 2026-04-28 17:30:02 | 31180 | -416.720 | 51080.520 | 0.008 | 2.908 | True | 80 | 41 | 2026-04-28 09:15:00 | 2026-04-28 15:29:59 | 1486183 | 717 | 82.784 |
| 2026-04-29 | 2026-04-29 09:27:30 | 2026-04-29 15:34:13 | 22004 | 212.300 | 40176.820 | 0.005 | 2.640 | True | 86 | 44 | 2026-04-29 09:25:28 | 2026-04-29 15:29:59 | 1441741 | 607 | 99.309 |
| 2026-04-30 | 2026-04-30 09:06:20 | 2026-04-30 16:43:14 | 27415 | -60.350 | 62234.030 | 0.001 | 3.286 | True | 77 | 40 | 2026-04-30 09:15:00 | 2026-04-30 15:29:59 | 1465096 | 1900 | 249.498 |

## Best Grid Cells
| impulse_type | impulse_horizon_seconds | underlying_threshold_points | entry_lag_seconds | strike_bucket | max_hold_seconds | spread_pct_threshold | depth_threshold | event_count | tradable_event_count | harvest_3pt_rate | avg_mfe | avg_mae | net_expectancy_after_0_5_cost | worst_day_expectancy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U_2S_25PTS | 2 | 25.000 | 1 | ATM | 5 | 0.005 | 500 | 1 | 1 | 1.000 | 10.750 | 0.000 | 10.250 | 10.250 |
| U_2S_25PTS | 2 | 25.000 | 1 | ATM | 5 | 0.010 | 500 | 1 | 1 | 1.000 | 10.750 | 0.000 | 10.250 | 10.250 |
| U_2S_25PTS | 2 | 25.000 | 1 | ATM | 5 | 0.015 | 500 | 1 | 1 | 1.000 | 10.750 | 0.000 | 10.250 | 10.250 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 10 | 0.005 | 250 | 6 | 6 | 0.833 | 13.467 | -1.942 | 8.467 | 6.730 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 10 | 0.010 | 250 | 7 | 7 | 0.857 | 12.307 | -1.664 | 7.950 | 6.417 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 10 | 0.015 | 250 | 7 | 7 | 0.857 | 12.307 | -1.664 | 7.950 | 6.417 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 5 | 0.005 | 250 | 6 | 6 | 0.667 | 9.708 | -0.833 | 7.025 | 5.600 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 3 | 0.005 | 250 | 6 | 6 | 0.667 | 7.625 | -0.825 | 6.992 | 5.560 |
| U_2S_25PTS | 2 | 25.000 | 1 | ATM | 5 | 0.005 | 250 | 2 | 2 | 1.000 | 8.275 | 0.000 | 6.550 | 6.550 |
| U_2S_25PTS | 2 | 25.000 | 1 | ATM | 5 | 0.010 | 250 | 2 | 2 | 1.000 | 8.275 | 0.000 | 6.550 | 6.550 |
| U_2S_25PTS | 2 | 25.000 | 1 | ATM | 5 | 0.015 | 250 | 2 | 2 | 1.000 | 8.275 | 0.000 | 6.550 | 6.550 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 5 | 0.005 | 500 | 3 | 3 | 0.667 | 9.733 | -0.817 | 6.550 | 6.550 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 5 | 0.010 | 500 | 3 | 3 | 0.667 | 9.733 | -0.817 | 6.550 | 6.550 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 5 | 0.015 | 500 | 3 | 3 | 0.667 | 9.733 | -0.817 | 6.550 | 6.550 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 3 | 0.010 | 250 | 7 | 7 | 0.714 | 6.964 | -0.707 | 6.350 | 5.050 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 3 | 0.015 | 250 | 7 | 7 | 0.714 | 6.964 | -0.707 | 6.350 | 5.050 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 5 | 0.010 | 250 | 7 | 7 | 0.714 | 8.750 | -0.714 | 6.214 | 4.892 |
| U_3S_30PTS | 3 | 30.000 | 0 | ATM | 5 | 0.015 | 250 | 7 | 7 | 0.714 | 8.750 | -0.714 | 6.214 | 4.892 |
| U_1S_20PTS | 1 | 20.000 | 2 | ATM | 3 | 0.005 | 500 | 2 | 2 | 0.500 | 6.225 | 0.000 | 5.725 | 5.725 |
| U_1S_20PTS | 1 | 20.000 | 2 | ATM | 3 | 0.010 | 500 | 2 | 2 | 0.500 | 6.225 | 0.000 | 5.725 | 5.725 |

## Candidate Trade Summary
| impulse_type | variant_name | trades | active_days | total_net_pnl | avg_pnl | win_rate | profit_factor | worst_day_pnl | target_hit_rate | avg_mfe | avg_mae | best_time_bucket | best_strike_bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 460 | 5 | 109025.000 | 269.198 | 0.485 | 1.357 | 0.000 | 0.407 | 2.132 | -1.625 | 12:00-13:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_0S_H5_CD30 | 472 | 5 | 102850.000 | 249.636 | 0.494 | 1.405 | 0.000 | 0.280 | 1.775 | -1.342 | 12:00-13:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD60 | 355 | 5 | 89400.000 | 289.320 | 0.493 | 1.402 | 0.000 | 0.411 | 2.102 | -1.551 | 13:30-14:45 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_0S_H5_CD60 | 354 | 5 | 86400.000 | 280.519 | 0.500 | 1.490 | 0.000 | 0.282 | 1.771 | -1.247 | 13:30-14:45 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_LIGHT_CONFIRM_H10_CD30 | 242 | 5 | 60300.000 | 320.745 | 0.413 | 1.477 | -700.000 | 0.326 | 1.859 | -1.332 | 09:30-10:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_LIGHT_CONFIRM_H5_CD30 | 247 | 5 | 52800.000 | 276.440 | 0.409 | 1.501 | 0.000 | 0.227 | 1.566 | -1.121 | 13:30-14:45 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_2S_NOT_EXHAUSTED_H10_CD30 | 410 | 5 | 49275.000 | 138.025 | 0.451 | 1.176 | -18725.000 | 0.366 | 1.937 | -1.732 | 09:30-10:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_H5_CD30 | 464 | 5 | 48775.000 | 119.547 | 0.463 | 1.174 | -8150.000 | 0.272 | 1.748 | -1.459 | 09:15-09:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_LIGHT_CONFIRM_H10_CD60 | 209 | 5 | 46350.000 | 286.111 | 0.421 | 1.426 | -1750.000 | 0.325 | 1.843 | -1.364 | 13:30-14:45 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_H10_CD30 | 461 | 5 | 42950.000 | 105.528 | 0.453 | 1.126 | -6250.000 | 0.371 | 2.037 | -1.770 | 09:15-09:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_NOT_EXHAUSTED_H5_CD30 | 446 | 5 | 39625.000 | 101.603 | 0.455 | 1.150 | -9750.000 | 0.260 | 1.678 | -1.439 | 13:30-14:45 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_LIGHT_CONFIRM_H5_CD60 | 205 | 5 | 39500.000 | 245.342 | 0.429 | 1.451 | 0.000 | 0.220 | 1.570 | -1.135 | 09:30-10:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_1S_NOT_EXHAUSTED_H10_CD30 | 442 | 5 | 38125.000 | 98.260 | 0.448 | 1.120 | -7850.000 | 0.362 | 1.979 | -1.745 | 13:30-14:45 | ATM |
| U_1S_15PTS | IMPULSE_ENTRY_0S_H5_CD60 | 12 | 5 | 36725.000 | 4080.556 | 0.583 | 105.929 | -350.000 | 0.333 | 6.300 | -0.217 | outside | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_2S_NOT_EXHAUSTED_H5_CD60 | 326 | 5 | 32700.000 | 115.957 | 0.451 | 1.186 | -15825.000 | 0.252 | 1.572 | -1.422 | 09:30-10:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_2S_NOT_EXHAUSTED_H10_CD60 | 332 | 5 | 32075.000 | 112.150 | 0.452 | 1.139 | -9250.000 | 0.364 | 1.926 | -1.776 | 09:15-09:30 | ATM |
| U_1S_10PTS | IMPULSE_ENTRY_2S_NOT_EXHAUSTED_H5_CD30 | 413 | 5 | 31525.000 | 88.059 | 0.443 | 1.138 | -22075.000 | 0.259 | 1.531 | -1.415 | 09:30-10:30 | ATM |
| ACCEL_SPIKE | IMPULSE_ENTRY_1S_H5_CD30 | 62 | 5 | 27250.000 | 534.314 | 0.435 | 1.811 | -875.000 | 0.371 | 2.254 | -1.212 | 09:15-09:30 | ATM |
| ACCEL_SPIKE | IMPULSE_ENTRY_1S_H10_CD30 | 63 | 5 | 25125.000 | 502.500 | 0.476 | 1.664 | -5300.000 | 0.397 | 2.290 | -1.383 | 09:15-09:30 | ATM |
| U_3S_20PTS | IMPULSE_ENTRY_2S_NOT_EXHAUSTED_H10_CD30 | 29 | 5 | 22075.000 | 919.792 | 0.517 | 2.967 | -4000.000 | 0.448 | 2.338 | -1.267 | 09:15-09:30 | ATM |

## Time Bucket
| time_bucket | impulse_count | tradable_event_count | harvest_3pt_rate | avg_mfe | avg_mae | candidate_trade_count | candidate_trade_net_pnl | candidate_trade_profit_factor | candidate_trade_worst_day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12:00-13:30 | 6 | 6 | 0.286 | 2.350 | -3.414 | 76 | 30450.000 | 1.644 | 0.000 |
| 13:30-14:45 | 33 | 33 | 0.265 | 2.981 | -1.581 | 129 | 26200.000 | 1.258 | -725.000 |
| 10:30-12:00 | 18 | 18 | 0.364 | 2.541 | -1.925 | 128 | 21925.000 | 1.249 | -9125.000 |
| 14:45-15:15 | 7 | 7 | 0.600 | 4.210 | -1.255 | 57 | 21575.000 | 1.600 | -5975.000 |
| outside | 5 | 5 | 0.167 | 1.800 | -0.617 | 71 | 6675.000 | 1.663 | 0.000 |
| 09:15-09:30 | 2 | 1 | 1.000 | 16.000 | -6.275 | 69 | 625.000 | 1.007 | -13225.000 |
| 09:30-10:30 | 6 | 6 | 0.167 | 0.708 | -4.667 | 116 | -725.000 | 0.993 | -7475.000 |

## Strike Distance
| atm_bucket | event_count | tradable_event_count | avg_mfe | median_mfe | harvest_3pt_rate | harvest_5pt_rate | avg_mae | net_edge_after_0_5_cost | candidate_trade_expectancy | candidate_trade_count | candidate_trade_net_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM | 22 | 21 | 5.925 | 3.875 | 0.591 | 0.409 | -2.055 | 5.425 | 185.983 | 573 | 101175.000 |
| ATM_100 | 31 | 31 | 3.031 | 2.100 | 0.323 | 0.194 | -2.435 | 2.531 | 1115.000 | 35 | 5575.000 |
| ATM_200 | 49 | 49 | 1.699 | 0.950 | 0.204 | 0.102 | -1.629 | 1.199 | -25.000 | 38 | -25.000 |

## Regime
| regime_dimension | regime_value | impulse_events | tradable_event_count | harvest_3pt_rate | avg_mfe | avg_mae | candidate_trade_expectancy | candidate_trade_net_pnl | candidate_trade_profit_factor | best_entry_lag | best_strike_bucket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| impulse_density_regime | high_density | 75 | 74 | 0.320 | 3.002 | -1.992 | 229.865 | 111025.000 | 1.284 | 0 | ATM |
| impulse_density_regime | low_density | 2 | 2 | 0.500 | 3.675 | -0.675 | -65.152 | -4300.000 | 0.944 | 0 | ATM |
| event_vol_regime | high_vol | 36 | 35 | 0.308 | 3.309 | -2.222 | 148.624 | 62125.000 | 1.162 | 0 | ATM |
| event_vol_regime | low_vol | 41 | 41 | 0.340 | 2.710 | -1.699 | 229.865 | 111025.000 | 1.284 | 0 | ATM_100 |
| trend_regime | choppy | 72 | 72 | 0.312 | 2.767 | -1.923 | 244.717 | 99600.000 | 1.321 | 0 | ATM |
| trend_regime | trending | 5 | 4 | 0.500 | 6.983 | -2.650 | 50.176 | 7125.000 | 1.045 | 0 | ATM |
| spread_regime | tight_spread | 43 | 43 | 0.314 | 2.946 | -2.200 | 194.399 | 106725.000 | 1.228 | 0 | ATM |
| spread_regime | wide_spread | 42 | 41 | 0.333 | 3.084 | -1.731 | 188.707 | 66425.000 | 1.217 | 0 | ATM |
| depth_regime | high_depth | 43 | 43 | 0.275 | 2.422 | -1.350 | 244.717 | 99600.000 | 1.321 | 0 | ATM |
| depth_regime | low_depth | 47 | 46 | 0.373 | 3.609 | -2.581 | 194.399 | 106725.000 | 1.228 | 0 | ATM |

## Null Controls
| control_type | sample_id | impulse_type | variant_name | trades | total_net_pnl | win_rate | profit_factor | avg_mfe | avg_mae | harvest_3pt_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| real | real | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 460 | 109025.000 | 0.485 | 1.357 | 2.132 | -1.625 | 0.407 |
| opposite_side | deterministic | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 622 | -131825.000 | 0.381 | 0.766 | 1.667 | -2.135 | 0.296 |
| wrong_lag_pre_event | deterministic | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 618 | 292375.000 | 0.515 | 1.789 | 2.440 | -1.420 | 0.451 |
| random_event_times | 11 | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 769 | -68050.000 | 0.345 | 0.861 | 1.396 | -1.541 | 0.231 |
| random_event_times | 23 | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 770 | -2750.000 | 0.335 | 0.994 | 1.568 | -1.553 | 0.252 |
| random_event_times | 37 | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 761 | -84850.000 | 0.334 | 0.839 | 1.413 | -1.626 | 0.254 |
| random_event_times | 47 | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 762 | -72175.000 | 0.323 | 0.856 | 1.400 | -1.563 | 0.247 |
| random_event_times | 59 | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 774 | -13575.000 | 0.364 | 0.972 | 1.509 | -1.540 | 0.264 |
| shuffled_day | cyclic_next_day | U_1S_10PTS | IMPULSE_ENTRY_0S_H10_CD30 | 578 | 138200.000 | 0.260 | 1.581 | 1.396 | -0.923 | 0.166 |

## False Burst / Noise
| group_dimension | group_value | class_label | count | tradable_rate | opposite_side_moving_rate | underlying_led_rate | noise_led_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| overall | all | impulse_present_harvestable | 162 | 0.019 | 0.000 | 1.000 | 0.000 |
| overall | all | impulse_present_not_harvestable | 351 | 0.063 | 0.000 | 1.000 | 0.000 |
| overall | all | no_impulse_harvestable | 2293 | 0.026 | 0.000 | 0.000 | 0.972 |
| overall | all | no_impulse_not_harvestable | 6311 | 0.029 | 0.000 | 0.000 | 0.977 |
| atm_bucket | ATM | impulse_present_harvestable | 33 | 0.000 | 0.000 | 1.000 | 0.000 |
| atm_bucket | ATM | impulse_present_not_harvestable | 80 | 0.000 | 0.000 | 1.000 | 0.000 |
| atm_bucket | ATM | no_impulse_harvestable | 463 | 0.041 | 0.000 | 0.000 | 0.981 |
| atm_bucket | ATM | no_impulse_not_harvestable | 1297 | 0.020 | 0.000 | 0.000 | 0.980 |
| atm_bucket | ATM_100 | impulse_present_harvestable | 63 | 0.016 | 0.000 | 1.000 | 0.000 |
| atm_bucket | ATM_100 | impulse_present_not_harvestable | 161 | 0.050 | 0.000 | 1.000 | 0.000 |
| atm_bucket | ATM_100 | no_impulse_harvestable | 962 | 0.023 | 0.000 | 0.000 | 0.973 |
| atm_bucket | ATM_100 | no_impulse_not_harvestable | 2563 | 0.030 | 0.000 | 0.000 | 0.980 |
| atm_bucket | ATM_200 | impulse_present_harvestable | 66 | 0.030 | 0.000 | 1.000 | 0.000 |
| atm_bucket | ATM_200 | impulse_present_not_harvestable | 110 | 0.127 | 0.000 | 1.000 | 0.000 |
| atm_bucket | ATM_200 | no_impulse_harvestable | 868 | 0.021 | 0.000 | 0.000 | 0.965 |
| atm_bucket | ATM_200 | no_impulse_not_harvestable | 2451 | 0.033 | 0.000 | 0.000 | 0.973 |
| premium_bucket | 150-300 | impulse_present_harvestable | 46 | 0.000 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 150-300 | impulse_present_not_harvestable | 116 | 0.034 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 150-300 | no_impulse_harvestable | 535 | 0.022 | 0.000 | 0.000 | 0.959 |
| premium_bucket | 150-300 | no_impulse_not_harvestable | 1283 | 0.025 | 0.000 | 0.000 | 0.965 |
| premium_bucket | 300-500 | impulse_present_harvestable | 39 | 0.000 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 300-500 | impulse_present_not_harvestable | 87 | 0.000 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 300-500 | no_impulse_harvestable | 821 | 0.002 | 0.000 | 0.000 | 0.983 |
| premium_bucket | 300-500 | no_impulse_not_harvestable | 2509 | 0.004 | 0.000 | 0.000 | 0.986 |
| premium_bucket | 50-80 | impulse_present_harvestable | 7 | 0.286 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 50-80 | impulse_present_not_harvestable | 18 | 0.333 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 50-80 | no_impulse_harvestable | 48 | 0.271 | 0.000 | 0.000 | 0.896 |
| premium_bucket | 50-80 | no_impulse_not_harvestable | 180 | 0.222 | 0.000 | 0.000 | 0.967 |
| premium_bucket | 80-150 | impulse_present_harvestable | 27 | 0.000 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 80-150 | impulse_present_not_harvestable | 64 | 0.078 | 0.000 | 1.000 | 0.000 |
| premium_bucket | 80-150 | no_impulse_harvestable | 184 | 0.109 | 0.000 | 0.000 | 0.951 |
| premium_bucket | 80-150 | no_impulse_not_harvestable | 567 | 0.101 | 0.000 | 0.000 | 0.951 |
| premium_bucket | <50 | impulse_present_not_harvestable | 16 | 0.438 | 0.000 | 1.000 | 0.000 |
| premium_bucket | <50 | no_impulse_harvestable | 38 | 0.289 | 0.000 | 0.000 | 0.974 |
| premium_bucket | <50 | no_impulse_not_harvestable | 136 | 0.338 | 0.000 | 0.000 | 0.934 |
| premium_bucket | >500 | impulse_present_harvestable | 43 | 0.023 | 0.000 | 1.000 | 0.000 |
| premium_bucket | >500 | impulse_present_not_harvestable | 50 | 0.000 | 0.000 | 1.000 | 0.000 |
| premium_bucket | >500 | no_impulse_harvestable | 667 | 0.001 | 0.000 | 0.000 | 0.979 |
| premium_bucket | >500 | no_impulse_not_harvestable | 1636 | 0.001 | 0.000 | 0.000 | 0.987 |
| spread_bucket | 0.5-1.0% | impulse_present_harvestable | 3 | 0.000 | 0.000 | 1.000 | 0.000 |

## Direct Answers
- **Does option premium lag underlying movement in a measurable way?** Peak observed correlation was at `-1s`, which implies negative lag, so option appears to lead or timestamps are not cleanly lagged.
- **Is the lag stable enough to trade?** Best grid cell used lag `0s` and hold `10s`, with net expectancy after 0.5 cost `2.67` points.
- **How often does option premium move +3 after a sudden underlying impulse?** Best observed harvest-3 rate was `59.1%` in `ATM` for `U_2S_20PTS`.
- **What entry lag is best?** `0s` in the best-performing grid cell.
- **Which strike distance is best?** `ATM` in the best-performing grid cell.
- **Which time bucket is best?** `12:00-13:30` by candidate-trade PnL.
- **Which regime is best?** `impulse_density_regime=high_density` had the strongest candidate-trade PnL.
- **Is raw burst score capturing the phenomenon or just movement/noise?** See the false-burst table: if the `no_impulse_not_harvestable` class dominates, raw burst is mostly movement/noise; if `impulse_present_harvestable` dominates, it is capturing underlying-led convexity.
- **Do direct impulse-based candidate trades have positive expectancy?** Best candidate variant `IMPULSE_ENTRY_0S_H10_CD30` on `U_1S_10PTS` produced `269.20` average PnL per trade and PF `1.36`.
- **Does the phenomenon outperform random/opposite-side controls?** It beats random-time controls (`-48,280` avg PnL) and opposite-side control (`-131,825`), but it does not beat wrong-lag pre-event (`292,375`) or shuffled-day (`138,200`) controls cleanly.
- **Is this strategy family feasible?** **WEAK**.

## Charts
- ![avg_option_response_after_underlying_impulse.png](convexity_lag_feasibility_results/charts/avg_option_response_after_underlying_impulse.png)
- ![harvestability_heatmap.png](convexity_lag_feasibility_results/charts/harvestability_heatmap.png)
- ![lead_lag_cross_correlation.png](convexity_lag_feasibility_results/charts/lead_lag_cross_correlation.png)
- ![median_option_response_after_underlying_impulse.png](convexity_lag_feasibility_results/charts/median_option_response_after_underlying_impulse.png)
- ![response_distribution_by_lag.png](convexity_lag_feasibility_results/charts/response_distribution_by_lag.png)
- ![strike_distance_edge.png](convexity_lag_feasibility_results/charts/strike_distance_edge.png)
- ![time_bucket_edge.png](convexity_lag_feasibility_results/charts/time_bucket_edge.png)

## Caveats
- This is a market-phenomenon study, not a broker-grade execution simulation.
- Option response is measured on 1-second snapshots; sub-second lead/lag is not resolved.
- `2026-04-24` and `2026-04-29/30` have different session coverage lengths, so the daywise tables matter more than pooled averages.
- Direct candidate trades use fixed quantity 500 and simple target/stop logic to test feasibility, not production sizing.