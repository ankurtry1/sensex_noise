# Entry Filter Shadow Model

## Model Comparison

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold | baseline_trade_count | accepted_trade_count | retained_trade_ratio | baseline_bad_trade_rate | accepted_bad_trade_rate | bad_trade_rate_reduction | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | retained_non_bad_gross_pnl_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 447.000 | 9.000 | 0.407 | 0.667 | 0.059 | 0.108 | 0.625 | 0.629 | 447.000 | 423.000 | 0.946 | 0.611 | 0.608 | 0.005 | -8325.000 | -11100.000 | -2775.000 | 0.955 | 0.111 | -4025.000 |
| logistic | 447.000 | 9.000 | 0.389 | 0.000 | 0.000 | 0.000 | 0.626 | 0.623 | 447.000 | 447.000 | 1.000 | 0.611 | 0.611 | 0.000 | -8325.000 | -8325.000 | 0.000 | 1.000 | 0.000 | 0.000 |

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

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 447.000 | 9.000 | 0.389 | 0.000 | 0.000 | 0.000 | 0.626 | 0.623 |

Policy summary:

| model | baseline_trade_count | accepted_trade_count | retained_trade_ratio | baseline_bad_trade_rate | accepted_bad_trade_rate | bad_trade_rate_reduction | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | retained_non_bad_gross_pnl_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 447.000 | 447.000 | 1.000 | 0.611 | 0.611 | 0.000 | -8325.000 | -8325.000 | 0.000 | 1.000 | 0.000 | 0.000 |

Confusion matrix:

| actual | pred_not_bad | pred_bad |
| --- | --- | --- |
| actual_not_bad | 174.000 | 0.000 |
| actual_bad | 273.000 | 0.000 |

## Hgb

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 447.000 | 9.000 | 0.407 | 0.667 | 0.059 | 0.108 | 0.625 | 0.629 |

Policy summary:

| model | baseline_trade_count | accepted_trade_count | retained_trade_ratio | baseline_bad_trade_rate | accepted_bad_trade_rate | bad_trade_rate_reduction | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | retained_non_bad_gross_pnl_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 447.000 | 423.000 | 0.946 | 0.611 | 0.608 | 0.005 | -8325.000 | -11100.000 | -2775.000 | 0.955 | 0.111 | -4025.000 |

Confusion matrix:

| actual | pred_not_bad | pred_bad |
| --- | --- | --- |
| actual_not_bad | 166.000 | 8.000 |
| actual_bad | 257.000 | 16.000 |
