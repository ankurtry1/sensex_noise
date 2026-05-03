# ATM Impulse Synchronization Scalper Research

## Executive Summary
- Full-tape dates tested: **2026-04-24, 2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30**.
- Best underlying-impulse variant: **ATM_U1S10_0S_H5_CD30__NO_MORNING_WEAK**, PnL **25,600**, PF **3.45**, trades **44**, PnL after 0.5 cost **14,600**.
- Best option-lead variant: **OPT_LEAD_1S2PTS_H10_CD30__MIDDAY_ONLY**, PnL **11,475**, PF **1.36**, trades **86**.
- Paper-trade ready under the stated standard: **yes**.
- Best paper-trade-qualified variant: **ATM_U2S20_0S_H5_CD30**, PnL **9,950**, PF **3.07**, trades **22**.

## Underlying-Impulse Variant Summary
| variant_name | total_trades | active_days | total_net_pnl | worst_day_pnl | best_day_pnl | profit_factor | win_rate | avg_pnl_per_trade | max_drawdown_sum | target_hit_rate | avg_mfe | avg_mae | beats_random_controls | live_candidate_flag | pnl_after_0_5_cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM_U1S10_0S_H5_CD30__NO_MORNING_WEAK | 44 | 4 | 25600.000 | -100.000 | 23250.000 | 3.450 | 0.477 | 581.818 | -3850.000 | 0.273 | 1.795 | -0.488 |  | False | 14600.000 |
| ATM_U1S10_0S_H5_CD30__AVOID_OPEN | 46 | 4 | 24900.000 | -100.000 | 22550.000 | 3.233 | 0.457 | 541.304 | -3850.000 | 0.261 | 1.732 | -0.497 |  | False | 13400.000 |
| ATM_U1S10_0S_H5_CD30__ACTIVE_WINDOW | 37 | 3 | 24875.000 | -175.000 | 23225.000 | 3.538 | 0.486 | 672.297 | -3850.000 | 0.324 | 2.032 | -0.545 |  | False | 15625.000 |
| ATM_U1S10_0S_H5_CD30 | 47 | 4 | 24375.000 | -100.000 | 22025.000 | 3.088 | 0.447 | 518.617 | -3850.000 | 0.255 | 1.695 | -0.509 |  | False | 12625.000 |
| ATM_U1S10_0S_H5_CD30__IMPULSE_DENSITY_ACTIVE | 47 | 4 | 24375.000 | -100.000 | 22025.000 | 3.088 | 0.447 | 518.617 | -3850.000 | 0.255 | 1.695 | -0.509 |  | False | 12625.000 |
| ATM_U1S10_0S_H10_CD30__NO_MORNING_WEAK | 44 | 4 | 21250.000 | -100.000 | 18900.000 | 2.499 | 0.455 | 482.955 | -4825.000 | 0.273 | 1.795 | -0.644 |  | False | 10250.000 |
| ATM_U1S10_0S_H5_CD30__HIGH_VOL_ONLY | 45 | 4 | 21100.000 | -100.000 | 18750.000 | 2.807 | 0.422 | 468.889 | -3850.000 | 0.244 | 1.624 | -0.531 |  | False | 9850.000 |
| ATM_U1S10_0S_H10_CD30__AVOID_OPEN | 46 | 4 | 20550.000 | -100.000 | 18200.000 | 2.382 | 0.435 | 446.739 | -4825.000 | 0.261 | 1.732 | -0.647 |  | False | 9050.000 |
| ATM_U1S10_0S_H10_CD30__ACTIVE_WINDOW | 37 | 3 | 20525.000 | -175.000 | 18875.000 | 2.518 | 0.459 | 554.730 | -4825.000 | 0.324 | 2.032 | -0.731 |  | False | 11275.000 |
| ATM_U1S10_0S_H5_CD30__TRENDING_ACTIVE | 26 | 3 | 20250.000 | -375.000 | 18800.000 | 4.951 | 0.500 | 778.846 | -1550.000 | 0.346 | 2.065 | -0.415 |  | False | 13750.000 |
| ATM_U1S10_0S_H10_CD30 | 47 | 4 | 20025.000 | -100.000 | 17675.000 | 2.300 | 0.426 | 426.064 | -4825.000 | 0.255 | 1.695 | -0.655 |  | False | 8275.000 |
| ATM_U1S10_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 47 | 4 | 20025.000 | -100.000 | 17675.000 | 2.300 | 0.426 | 426.064 | -4825.000 | 0.255 | 1.695 | -0.655 |  | False | 8275.000 |
| ATM_U1S10_0S_H5_CD60 | 39 | 4 | 19275.000 | -100.000 | 16925.000 | 3.067 | 0.462 | 494.231 | -2900.000 | 0.282 | 1.656 | -0.492 |  | False | 9525.000 |
| ATM_U1S10_0S_H10_CD30__TRENDING_ACTIVE | 26 | 3 | 17450.000 | -375.000 | 16000.000 | 3.390 | 0.462 | 671.154 | -2225.000 | 0.346 | 2.065 | -0.562 |  | False | 10950.000 |
| ATM_U1S10_0S_H10_CD30__HIGH_VOL_ONLY | 45 | 4 | 16750.000 | -100.000 | 14400.000 | 2.088 | 0.400 | 372.222 | -4875.000 | 0.244 | 1.624 | -0.684 |  | False | 5500.000 |
| ATM_U1S10_0S_H10_CD60 | 39 | 4 | 14925.000 | -100.000 | 12575.000 | 2.144 | 0.436 | 382.692 | -4825.000 | 0.282 | 1.656 | -0.669 |  | False | 5175.000 |
| ATM_U2S20_0S_H5_CD30 | 22 | 4 | 9950.000 | -275.000 | 7850.000 | 3.073 | 0.409 | 452.273 | -2025.000 | 0.273 | 1.477 | -0.436 |  | True | 4450.000 |
| ATM_U2S20_0S_H10_CD30 | 22 | 4 | 8400.000 | -275.000 | 6300.000 | 2.323 | 0.409 | 381.818 | -2175.000 | 0.273 | 1.477 | -0.577 |  | True | 2900.000 |
| ATM_U2S20_0S_H10_CD30__HIGH_VOL_ONLY | 22 | 4 | 8400.000 | -275.000 | 6300.000 | 2.323 | 0.409 | 381.818 | -2175.000 | 0.273 | 1.477 | -0.577 |  | True | 2900.000 |
| ATM_U2S20_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 22 | 4 | 8400.000 | -275.000 | 6300.000 | 2.323 | 0.409 | 381.818 | -2175.000 | 0.273 | 1.477 | -0.577 |  | True | 2900.000 |

## Option-Lead Variant Summary
| variant_name | total_trades | active_days | total_net_pnl | worst_day_pnl | best_day_pnl | profit_factor | win_rate | avg_pnl_per_trade | max_drawdown_sum | target_hit_rate | avg_mfe | avg_mae | beats_random_controls | live_candidate_flag | pnl_after_0_5_cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OPT_LEAD_1S2PTS_H10_CD30__MIDDAY_ONLY | 86 | 3 | 11475.000 | -2225.000 | 14200.000 | 1.365 | 0.384 | 133.430 | -11675.000 | 0.221 | 1.142 | -0.795 |  | False | -10025.000 |
| OPT_LEAD_1S2PTS_H10_CD30 | 181 | 4 | 9425.000 | -4775.000 | 19375.000 | 1.124 | 0.315 | 52.072 | -21575.000 | 0.204 | 1.068 | -0.882 |  | False | -35825.000 |
| OPT_LEAD_1S3PTS_H10_CD30__MIDDAY_ONLY | 54 | 3 | 8725.000 | -1675.000 | 7825.000 | 1.332 | 0.389 | 161.574 | -10850.000 | 0.259 | 1.388 | -0.973 |  | False | -4775.000 |
| OPT_LEAD_1S2PTS_H10_CD30__IMPULSE_DENSITY_ACTIVE | 167 | 4 | 7550.000 | -7800.000 | 19375.000 | 1.104 | 0.299 | 45.210 | -18825.000 | 0.210 | 1.068 | -0.912 |  | False | -34200.000 |
| OPT_LEAD_1S3PTS_H10_CD30 | 105 | 4 | 7250.000 | -1950.000 | 9725.000 | 1.134 | 0.324 | 69.048 | -13775.000 | 0.229 | 1.356 | -1.045 |  | False | -19000.000 |
| OPT_LEAD_1S3PTS_H5_CD30 | 105 | 4 | 6900.000 | -1950.000 | 6650.000 | 1.131 | 0.333 | 65.714 | -13775.000 | 0.210 | 1.313 | -1.011 |  | False | -19350.000 |
| OPT_LEAD_1S3PTS_H5_CD30__MIDDAY_ONLY | 54 | 3 | 5550.000 | -1675.000 | 4650.000 | 1.211 | 0.389 | 102.778 | -10850.000 | 0.222 | 1.306 | -0.973 |  | False | -7950.000 |
| OPT_LEAD_1S3PTS_H10_CD30__IMPULSE_DENSITY_ACTIVE | 103 | 4 | 5475.000 | -3225.000 | 9725.000 | 1.101 | 0.311 | 53.155 | -13775.000 | 0.223 | 1.345 | -1.066 |  | False | -20275.000 |
| OPT_LEAD_1S3PTS_H5_CD30__IMPULSE_DENSITY_ACTIVE | 103 | 4 | 5125.000 | -1950.000 | 6650.000 | 1.098 | 0.320 | 49.757 | -13775.000 | 0.204 | 1.302 | -1.031 |  | False | -20625.000 |
| OPT_LEAD_1S2PTS_H5_CD30__MIDDAY_ONLY | 87 | 3 | 2400.000 | -2225.000 | 5075.000 | 1.069 | 0.356 | 27.586 | -12400.000 | 0.184 | 1.071 | -0.798 |  | False | -19350.000 |
| OPT_LEAD_2S4PTS_H5_CD30__IMPULSE_DENSITY_ACTIVE | 99 | 4 | 1550.000 | -9550.000 | 13475.000 | 1.031 | 0.313 | 15.657 | -21425.000 | 0.192 | 1.214 | -1.031 |  | False | -23200.000 |
| OPT_LEAD_2S4PTS_H5_CD30 | 107 | 4 | -550.000 | -9550.000 | 13025.000 | 0.990 | 0.308 | -5.140 | -24100.000 | 0.178 | 1.144 | -1.007 |  | False | -27300.000 |
| OPT_LEAD_1S2PTS_H5_CD30 | 182 | 4 | -1075.000 | -4725.000 | 8825.000 | 0.986 | 0.302 | -5.907 | -21475.000 | 0.181 | 1.020 | -0.882 |  | False | -46575.000 |
| OPT_LEAD_2S4PTS_H10_CD30__IMPULSE_DENSITY_ACTIVE | 99 | 4 | -2400.000 | -10775.000 | 10750.000 | 0.956 | 0.293 | -24.242 | -21675.000 | 0.202 | 1.242 | -1.107 |  | False | -27150.000 |
| OPT_LEAD_1S2PTS_H5_CD30__IMPULSE_DENSITY_ACTIVE | 168 | 4 | -3000.000 | -7800.000 | 8825.000 | 0.960 | 0.286 | -17.857 | -18725.000 | 0.185 | 1.016 | -0.917 |  | False | -45000.000 |
| OPT_LEAD_2S4PTS_H10_CD30 | 107 | 4 | -4500.000 | -10775.000 | 10300.000 | 0.921 | 0.290 | -42.056 | -24350.000 | 0.187 | 1.170 | -1.077 |  | False | -31250.000 |
| OPT_LEAD_ACCEL_H10_CD30__IMPULSE_DENSITY_ACTIVE | 99 | 4 | -4675.000 | -11150.000 | 8850.000 | 0.914 | 0.293 | -47.222 | -21725.000 | 0.192 | 1.201 | -1.115 |  | False | -29425.000 |
| OPT_LEAD_ACCEL_H10_CD30__MIDDAY_ONLY | 54 | 4 | -5700.000 | -11450.000 | 8425.000 | 0.813 | 0.296 | -105.556 | -19950.000 | 0.148 | 1.046 | -1.127 |  | False | -19200.000 |
| OPT_LEAD_2S4PTS_H10_CD30__MIDDAY_ONLY | 54 | 4 | -6375.000 | -11400.000 | 7700.000 | 0.790 | 0.278 | -118.056 | -20725.000 | 0.148 | 1.054 | -1.125 |  | False | -19875.000 |
| OPT_LEAD_ACCEL_H10_CD30 | 107 | 4 | -6775.000 | -11150.000 | 8400.000 | 0.882 | 0.290 | -63.318 | -24400.000 | 0.178 | 1.131 | -1.084 |  | False | -33525.000 |

## Timewise
| variant_name | time_bucket | trades | net_pnl | win_rate | profit_factor | avg_pnl | target_hit_rate | avg_mfe | avg_mae | worst_day_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM_U1S10_0S_H10_CD30__AVOID_OPEN | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H10_CD30__ACTIVE_WINDOW | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H10_CD30__NO_MORNING_WEAK | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H5_CD30 | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H5_CD30__NO_MORNING_WEAK | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H10_CD30 | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H5_CD30__ACTIVE_WINDOW | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H5_CD30__IMPULSE_DENSITY_ACTIVE | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H5_CD30__AVOID_OPEN | 14:45-15:15 | 10 | 12750.000 | 0.500 | 13.750 | 1275.000 | 0.400 | 2.825 | -0.200 | 12750.000 |
| ATM_U1S10_0S_H10_CD30__TRENDING_ACTIVE | 14:45-15:15 | 8 | 11275.000 | 0.500 | 18.346 | 1409.375 | 0.375 | 3.044 | -0.162 | 11275.000 |
| ATM_U1S10_0S_H5_CD30__TRENDING_ACTIVE | 14:45-15:15 | 8 | 11275.000 | 0.500 | 18.346 | 1409.375 | 0.375 | 3.044 | -0.162 | 11275.000 |
| ATM_U1S10_0S_H5_CD30__HIGH_VOL_ONLY | 14:45-15:15 | 9 | 10375.000 | 0.444 | 11.375 | 1152.778 | 0.333 | 2.611 | -0.222 | 10375.000 |
| ATM_U1S10_0S_H10_CD30__HIGH_VOL_ONLY | 14:45-15:15 | 9 | 10375.000 | 0.444 | 11.375 | 1152.778 | 0.333 | 2.611 | -0.222 | 10375.000 |
| ATM_U1S10_0S_H5_CD60 | 13:30-14:45 | 10 | 7325.000 | 0.500 | 3.442 | 732.500 | 0.400 | 2.220 | -0.600 | -375.000 |
| ATM_U1S10_0S_H10_CD60 | 13:30-14:45 | 10 | 7325.000 | 0.500 | 3.442 | 732.500 | 0.400 | 2.220 | -0.600 | -375.000 |
| ATM_U2S20_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 13:30-14:45 | 4 | 6550.000 | 0.750 | 6.347 | 1637.500 | 0.750 | 3.888 | -0.613 | 6550.000 |
| ATM_U2S20_0S_H5_CD30 | 13:30-14:45 | 4 | 6550.000 | 0.750 | 6.347 | 1637.500 | 0.750 | 3.888 | -0.613 | 6550.000 |
| ATM_U2S20_0S_H10_CD30__ACTIVE_WINDOW | 13:30-14:45 | 4 | 6550.000 | 0.750 | 6.347 | 1637.500 | 0.750 | 3.888 | -0.613 | 6550.000 |
| ATM_U2S20_0S_H10_CD30__MIDDAY_ONLY | 13:30-14:45 | 4 | 6550.000 | 0.750 | 6.347 | 1637.500 | 0.750 | 3.888 | -0.613 | 6550.000 |

## Regimewise
| variant_name | regime_dimension | regime_value | trades | net_pnl | win_rate | profit_factor | avg_pnl | target_hit_rate | avg_mfe | avg_mae | worst_day_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ATM_U1S10_0S_H5_CD30__NO_MORNING_WEAK | impulse_density_regime | active | 44 | 25600.000 | 0.477 | 3.450 | 581.818 | 0.273 | 1.795 | -0.488 | -100.000 |
| ATM_U1S10_0S_H5_CD30__AVOID_OPEN | impulse_density_regime | active | 46 | 24900.000 | 0.457 | 3.233 | 541.304 | 0.261 | 1.732 | -0.497 | -100.000 |
| ATM_U1S10_0S_H5_CD30__ACTIVE_WINDOW | impulse_density_regime | active | 37 | 24875.000 | 0.486 | 3.538 | 672.297 | 0.324 | 2.032 | -0.545 | -175.000 |
| ATM_U1S10_0S_H5_CD30 | impulse_density_regime | active | 47 | 24375.000 | 0.447 | 3.088 | 518.617 | 0.255 | 1.695 | -0.509 | -100.000 |
| ATM_U1S10_0S_H5_CD30__IMPULSE_DENSITY_ACTIVE | impulse_density_regime | active | 47 | 24375.000 | 0.447 | 3.088 | 518.617 | 0.255 | 1.695 | -0.509 | -100.000 |
| ATM_U1S10_0S_H5_CD30__NO_MORNING_WEAK | vol_regime | high_vol | 42 | 22325.000 | 0.452 | 3.136 | 531.548 | 0.262 | 1.725 | -0.511 | -100.000 |
| ATM_U1S10_0S_H5_CD30__AVOID_OPEN | vol_regime | high_vol | 44 | 21625.000 | 0.432 | 2.939 | 491.477 | 0.250 | 1.661 | -0.519 | -100.000 |
| ATM_U1S10_0S_H5_CD30__ACTIVE_WINDOW | vol_regime | high_vol | 35 | 21600.000 | 0.457 | 3.204 | 617.143 | 0.314 | 1.961 | -0.576 | -175.000 |
| ATM_U1S10_0S_H10_CD30__NO_MORNING_WEAK | impulse_density_regime | active | 44 | 21250.000 | 0.455 | 2.499 | 482.955 | 0.273 | 1.795 | -0.644 | -100.000 |
| ATM_U1S10_0S_H5_CD30__IMPULSE_DENSITY_ACTIVE | vol_regime | high_vol | 45 | 21100.000 | 0.422 | 2.807 | 468.889 | 0.244 | 1.624 | -0.531 | -100.000 |
| ATM_U1S10_0S_H5_CD30 | vol_regime | high_vol | 45 | 21100.000 | 0.422 | 2.807 | 468.889 | 0.244 | 1.624 | -0.531 | -100.000 |
| ATM_U1S10_0S_H5_CD30__HIGH_VOL_ONLY | impulse_density_regime | active | 45 | 21100.000 | 0.422 | 2.807 | 468.889 | 0.244 | 1.624 | -0.531 | -100.000 |
| ATM_U1S10_0S_H5_CD30__HIGH_VOL_ONLY | vol_regime | high_vol | 45 | 21100.000 | 0.422 | 2.807 | 468.889 | 0.244 | 1.624 | -0.531 | -100.000 |
| ATM_U1S10_0S_H5_CD30__NO_MORNING_WEAK | trend_regime | trending | 25 | 20725.000 | 0.520 | 5.457 | 829.000 | 0.360 | 2.122 | -0.394 | -375.000 |
| ATM_U1S10_0S_H5_CD30__ACTIVE_WINDOW | trend_regime | trending | 20 | 20700.000 | 0.550 | 6.049 | 1035.000 | 0.450 | 2.542 | -0.438 | -375.000 |
| ATM_U1S10_0S_H10_CD30__AVOID_OPEN | impulse_density_regime | active | 46 | 20550.000 | 0.435 | 2.382 | 446.739 | 0.261 | 1.732 | -0.647 | -100.000 |
| ATM_U1S10_0S_H10_CD30__ACTIVE_WINDOW | impulse_density_regime | active | 37 | 20525.000 | 0.459 | 2.518 | 554.730 | 0.324 | 2.032 | -0.731 | -175.000 |
| ATM_U1S10_0S_H5_CD30__TRENDING_ACTIVE | impulse_density_regime | active | 26 | 20250.000 | 0.500 | 4.951 | 778.846 | 0.346 | 2.065 | -0.415 | -375.000 |
| ATM_U1S10_0S_H5_CD30__AVOID_OPEN | trend_regime | trending | 26 | 20250.000 | 0.500 | 4.951 | 778.846 | 0.346 | 2.065 | -0.415 | -375.000 |
| ATM_U1S10_0S_H5_CD30__TRENDING_ACTIVE | trend_regime | trending | 26 | 20250.000 | 0.500 | 4.951 | 778.846 | 0.346 | 2.065 | -0.415 | -375.000 |

## Cost Sensitivity
| variant_name | cost_points | adjusted_pnl | adjusted_avg_pnl | adjusted_profit_factor | days_positive | worst_day_pnl |
| --- | --- | --- | --- | --- | --- | --- |
| ATM_ACCEL_0S_H10_CD30 | 0.000 | 2600.000 | 81.250 | 1.191 | 1 | -1925.000 |
| ATM_ACCEL_0S_H10_CD30 | 0.250 | -1400.000 | -43.750 | 0.914 | 1 | -2175.000 |
| ATM_ACCEL_0S_H10_CD30 | 0.500 | -5400.000 | -168.750 | 0.714 | 0 | -2425.000 |
| ATM_ACCEL_0S_H10_CD30 | 0.750 | -9400.000 | -293.750 | 0.564 | 0 | -5400.000 |
| ATM_ACCEL_0S_H10_CD30 | 1.000 | -13400.000 | -418.750 | 0.451 | 0 | -8900.000 |
| ATM_ACCEL_0S_H10_CD30__ACTIVE_WINDOW | 0.000 | 2125.000 | 81.731 | 1.177 | 1 | -1925.000 |
| ATM_ACCEL_0S_H10_CD30__ACTIVE_WINDOW | 0.250 | -1125.000 | -43.269 | 0.920 | 1 | -2175.000 |
| ATM_ACCEL_0S_H10_CD30__ACTIVE_WINDOW | 0.500 | -4375.000 | -168.269 | 0.730 | 0 | -2425.000 |
| ATM_ACCEL_0S_H10_CD30__ACTIVE_WINDOW | 0.750 | -7625.000 | -293.269 | 0.584 | 0 | -4100.000 |
| ATM_ACCEL_0S_H10_CD30__ACTIVE_WINDOW | 1.000 | -10875.000 | -418.269 | 0.471 | 0 | -6975.000 |
| ATM_ACCEL_0S_H10_CD30__AVOID_OPEN | 0.000 | 775.000 | 25.000 | 1.057 | 1 | -1925.000 |
| ATM_ACCEL_0S_H10_CD30__AVOID_OPEN | 0.250 | -3100.000 | -100.000 | 0.809 | 0 | -2175.000 |
| ATM_ACCEL_0S_H10_CD30__AVOID_OPEN | 0.500 | -6975.000 | -225.000 | 0.630 | 0 | -3475.000 |
| ATM_ACCEL_0S_H10_CD30__AVOID_OPEN | 0.750 | -10850.000 | -350.000 | 0.497 | 0 | -6850.000 |
| ATM_ACCEL_0S_H10_CD30__AVOID_OPEN | 1.000 | -14725.000 | -475.000 | 0.397 | 0 | -10225.000 |
| ATM_ACCEL_0S_H10_CD30__CHOPPY_ACTIVE | 0.000 | -1650.000 | -165.000 | 0.740 | 1 | -1925.000 |
| ATM_ACCEL_0S_H10_CD30__CHOPPY_ACTIVE | 0.250 | -2900.000 | -290.000 | 0.599 | 0 | -2175.000 |
| ATM_ACCEL_0S_H10_CD30__CHOPPY_ACTIVE | 0.500 | -4150.000 | -415.000 | 0.488 | 0 | -2425.000 |
| ATM_ACCEL_0S_H10_CD30__CHOPPY_ACTIVE | 0.750 | -5400.000 | -540.000 | 0.398 | 0 | -2675.000 |
| ATM_ACCEL_0S_H10_CD30__CHOPPY_ACTIVE | 1.000 | -6650.000 | -665.000 | 0.325 | 0 | -3125.000 |
| ATM_ACCEL_0S_H10_CD30__HIGH_VOL_ONLY | 0.000 | 2600.000 | 81.250 | 1.191 | 1 | -1925.000 |
| ATM_ACCEL_0S_H10_CD30__HIGH_VOL_ONLY | 0.250 | -1400.000 | -43.750 | 0.914 | 1 | -2175.000 |
| ATM_ACCEL_0S_H10_CD30__HIGH_VOL_ONLY | 0.500 | -5400.000 | -168.750 | 0.714 | 0 | -2425.000 |
| ATM_ACCEL_0S_H10_CD30__HIGH_VOL_ONLY | 0.750 | -9400.000 | -293.750 | 0.564 | 0 | -5400.000 |
| ATM_ACCEL_0S_H10_CD30__HIGH_VOL_ONLY | 1.000 | -13400.000 | -418.750 | 0.451 | 0 | -8900.000 |
| ATM_ACCEL_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 0.000 | 3075.000 | 99.194 | 1.234 | 1 | -1925.000 |
| ATM_ACCEL_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 0.250 | -800.000 | -25.806 | 0.949 | 1 | -2175.000 |
| ATM_ACCEL_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 0.500 | -4675.000 | -150.806 | 0.742 | 0 | -2425.000 |
| ATM_ACCEL_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 0.750 | -8550.000 | -275.806 | 0.587 | 0 | -5400.000 |
| ATM_ACCEL_0S_H10_CD30__IMPULSE_DENSITY_ACTIVE | 1.000 | -12425.000 | -400.806 | 0.470 | 0 | -8900.000 |

## Option-Lead Predictive Controls
| control_type | variant_name | impulse_type | pnl_or_expectancy | direction_correct_3s | hit_future_10pts_rate | events |
| --- | --- | --- | --- | --- | --- | --- |
| opposite_side | 2026-04-27_option_lead | OPT_1S_2PTS | 1.648 | 0.500 | 0.100 | 10 |
| opposite_side | 2026-04-27_option_lead | OPT_1S_3PTS | 1.160 | 0.500 | 0.167 | 6 |
| opposite_side | 2026-04-27_option_lead | OPT_2S_4PTS | 3.420 | 0.500 | 0.500 | 2 |
| opposite_side | 2026-04-27_option_lead | OPT_ACCEL | 3.420 | 0.500 | 0.500 | 2 |
| random_time | 2026-04-27_option_lead | OPT_1S_2PTS | 0.027 | 0.571 | 0.000 | 7 |
| random_time | 2026-04-27_option_lead | OPT_1S_3PTS | -4.260 | 0.000 | 0.000 | 1 |
| random_time | 2026-04-27_option_lead | OPT_2S_4PTS | 2.715 | 0.500 | 0.500 | 2 |
| random_time | 2026-04-27_option_lead | OPT_ACCEL | 1.495 | 1.000 | 0.000 | 2 |
| real | 2026-04-27_option_lead | OPT_1S_2PTS | 0.993 | 0.584 | 0.156 | 2459 |
| real | 2026-04-27_option_lead | OPT_1S_3PTS | 1.465 | 0.610 | 0.204 | 1532 |
| real | 2026-04-27_option_lead | OPT_2S_4PTS | 1.666 | 0.634 | 0.224 | 1294 |
| real | 2026-04-27_option_lead | OPT_ACCEL | 1.716 | 0.634 | 0.220 | 1271 |
| shuffled_time | 2026-04-27_option_lead | OPT_1S_2PTS | 1.146 | 0.600 | 0.000 | 5 |
| shuffled_time | 2026-04-27_option_lead | OPT_1S_3PTS | 3.450 | 1.000 | 0.000 | 1 |
| shuffled_time | 2026-04-27_option_lead | OPT_2S_4PTS | 8.840 | 1.000 | 0.000 | 1 |
| shuffled_time | 2026-04-27_option_lead | OPT_ACCEL | -0.372 | 0.400 | 0.000 | 5 |
| opposite_side | 2026-04-28_option_lead | OPT_1S_2PTS | 1.470 | 0.375 | 0.250 | 8 |
| opposite_side | 2026-04-28_option_lead | OPT_1S_3PTS | -0.565 | 0.333 | 0.333 | 6 |
| opposite_side | 2026-04-28_option_lead | OPT_2S_4PTS | -0.263 | 0.333 | 0.333 | 3 |
| opposite_side | 2026-04-28_option_lead | OPT_ACCEL | -0.263 | 0.333 | 0.333 | 3 |
| random_time | 2026-04-28_option_lead | OPT_1S_2PTS | -1.613 | 0.500 | 0.000 | 4 |
| random_time | 2026-04-28_option_lead | OPT_1S_3PTS | -7.890 | 0.333 | 0.000 | 3 |
| random_time | 2026-04-28_option_lead | OPT_2S_4PTS | -3.615 | 0.500 | 0.500 | 2 |
| random_time | 2026-04-28_option_lead | OPT_ACCEL | 12.605 | 1.000 | 0.500 | 2 |
| real | 2026-04-28_option_lead | OPT_1S_2PTS | 0.895 | 0.568 | 0.151 | 2258 |
| real | 2026-04-28_option_lead | OPT_1S_3PTS | 1.630 | 0.639 | 0.200 | 1243 |
| real | 2026-04-28_option_lead | OPT_2S_4PTS | 1.840 | 0.640 | 0.233 | 1107 |
| real | 2026-04-28_option_lead | OPT_ACCEL | 1.758 | 0.635 | 0.231 | 1095 |
| shuffled_time | 2026-04-28_option_lead | OPT_1S_2PTS | 6.073 | 0.750 | 0.250 | 4 |
| shuffled_time | 2026-04-28_option_lead | OPT_1S_3PTS | 1.335 | 0.750 | 0.000 | 4 |

## Direct Answers
- **Does ATM impulse synchronization produce positive expectancy?** Yes for the best underlying variant in this sample: `ATM_U1S10_0S_H5_CD30__NO_MORNING_WEAK` produced `25,600` with PF `3.45`.
- **Which impulse definition works best?** `U1S10` is the strongest top-line winner in this run.
- **Is 0s entry better than 1s entry?** Yes in this sample: `ATM_U1S10_0S_H10_CD30` = `20,025` vs `ATM_U1S10_1S_H10_CD30` = `3,325`.
- **Does 1s not-exhausted rescue delayed entry?** `ATM_U1S10_1S_NOT_EXHAUSTED_H10_CD30` = `-325` vs immediate `20,025`.
- **Is 5s or 10s hold better?** For U1S10 with CD30, H10 = `20,025` vs H5 = `24,375`.
- **Is cooldown 30s or 60s better?** For U1S10 H10, CD30 = `20,025` vs CD60 = `14,925`.
- **Does time filtering improve robustness?** The strongest entry bucket is `14:45-15:15`; see the timewise table for the filter variants that improved daywise robustness.
- **Does regime filtering improve robustness?** Best regime slice was `impulse_density_regime=active` with net PnL `25,600`.
- **Does the strategy survive 0.5 point cost?** Best underlying variant after 0.5 point cost = `14,600`.
- **Does ATM-only outperform wider strike selection?** This study is ATM-only by design because prior feasibility already showed ATM strongest and ATM±200 diluted the edge.
- **Is option-led signal better than underlying-led signal?** Best option-led variant `OPT_LEAD_1S2PTS_H10_CD30__MIDDAY_ONLY` scored `11,475` vs best underlying-led `25,600`.
- **Does option impulse predict future SENSEX movement?** Real option-impulse 3s signed move expectancy averages `1.56` vs random `-0.20`.
- **Can option-lead information improve option trading?** Only if the option-led trade variants also beat the underlying-led variants with controlled trade counts; the summary table is the deciding evidence.
- **Is any variant paper-trade ready?** **Yes** under the stated standard.
- **What exact next candidate should be tested?** `ATM_U2S20_0S_H5_CD30` in paper trading only.

## Charts
- ![cost_sensitivity.png](atm_impulse_sync_results/charts/cost_sensitivity.png)
- ![daywise_pnl_by_variant.png](atm_impulse_sync_results/charts/daywise_pnl_by_variant.png)
- ![option_lead_accuracy.png](atm_impulse_sync_results/charts/option_lead_accuracy.png)
- ![regime_pnl.png](atm_impulse_sync_results/charts/regime_pnl.png)
- ![time_bucket_pnl.png](atm_impulse_sync_results/charts/time_bucket_pnl.png)

## Caveats
- This is diagnostic replay on 1-second tape, not broker-grade execution.
- The strategy logic here is research-only and separate from live code.
- Paper-trade readiness requires multi-day robustness, not one strong variant headline.