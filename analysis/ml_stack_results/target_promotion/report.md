# Target Promotion Shadow Model

## Model Comparison

| model | eval_rows | eval_days | accuracy | macro_f1 | weighted_f1 | fallback_rate | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | positive_day_ratio | over_promotion_losses | runner_capture_gains | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 174.000 | 9.000 | 0.443 | 0.327 | 0.427 | 0.264 | 237850.000 | 296900.000 | 59050.000 | 0.778 | 67025.000 | 119650.000 | -7875.000 |
| logistic | 174.000 | 9.000 | 0.471 | 0.306 | 0.429 | 0.385 | 237850.000 | 287075.000 | 49225.000 | 0.667 | 71725.000 | 120950.000 | -5750.000 |

## Features

- `idx_pre_velocity_aligned`
- `idx_pre_accel_aligned`
- `opt_pre_velocity_5s`
- `opt_pre_depth_imb_mean`
- `opt_pre_spread_mean`
- `burst_score_reconstructed`
- `pre_entry_option_tick_count`
- `pre_entry_index_tick_count`
- `pre_or_post_1pm`
- `continuation_or_reversal`
- `call_or_put`

## Logistic

| model | eval_rows | eval_days | accuracy | macro_f1 | weighted_f1 | fallback_rate |
| --- | --- | --- | --- | --- | --- | --- |
| logistic | 174.000 | 9.000 | 0.471 | 0.306 | 0.429 | 0.385 |

Policy summary:

| model | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | positive_day_ratio | over_promotion_losses | runner_capture_gains | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 237850.000 | 287075.000 | 49225.000 | 0.667 | 71725.000 | 120950.000 | -5750.000 |

Confusion matrix:

| actual | keep_3 | extend_to_5 | extend_to_7 |
| --- | --- | --- | --- |
| keep_3 | 14.000 | 0.000 | 22.000 |
| extend_to_5 | 9.000 | 0.000 | 26.000 |
| extend_to_7 | 35.000 | 0.000 | 68.000 |

## Hgb

| model | eval_rows | eval_days | accuracy | macro_f1 | weighted_f1 | fallback_rate |
| --- | --- | --- | --- | --- | --- | --- |
| hgb | 174.000 | 9.000 | 0.443 | 0.327 | 0.427 | 0.264 |

Policy summary:

| model | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | positive_day_ratio | over_promotion_losses | runner_capture_gains | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 237850.000 | 296900.000 | 59050.000 | 0.778 | 67025.000 | 119650.000 | -7875.000 |

Confusion matrix:

| actual | keep_3 | extend_to_5 | extend_to_7 |
| --- | --- | --- | --- |
| keep_3 | 15.000 | 1.000 | 20.000 |
| extend_to_5 | 10.000 | 2.000 | 23.000 |
| extend_to_7 | 35.000 | 8.000 | 60.000 |
