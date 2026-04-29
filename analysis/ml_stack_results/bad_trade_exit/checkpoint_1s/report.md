# Bad Trade Exit Shadow Model (1s)

## Model Comparison

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | exit_rate | baseline_bad_loss | policy_bad_loss | bad_loss_reduction | winner_giveback_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 376.000 | 9.000 | 0.279 | 0.000 | 0.000 | 0.000 | 0.770 | 0.765 | -109200.000 | -109200.000 | 0.000 | 0.000 | 297075.000 | 297075.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| logistic | 376.000 | 9.000 | 0.330 | 0.913 | 0.077 | 0.143 | 0.787 | 0.775 | -109200.000 | -105325.000 | 3875.000 | 0.061 | 297075.000 | 289225.000 | 0.026 | 0.025 | 0.111 | 0.000 |

## Features

- `idx_pre_velocity_aligned`
- `idx_pre_accel_aligned`
- `opt_pre_velocity_5s`
- `opt_pre_depth_imb_mean`
- `opt_pre_spread_mean`
- `burst_score_reconstructed`
- `pre_entry_option_tick_count`
- `pre_entry_index_tick_count`
- `pnl_0p25s`
- `pnl_0p5s`
- `feat_pnl_1s`
- `feat_runup_1s`
- `feat_drawdown_1s`
- `pre_or_post_1pm`
- `continuation_or_reversal`
- `call_or_put`

## Logistic

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 376.000 | 9.000 | 0.330 | 0.913 | 0.077 | 0.143 | 0.787 | 0.775 |

Policy summary:

| model | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | exit_rate | baseline_bad_loss | policy_bad_loss | bad_loss_reduction | winner_giveback_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | -109200.000 | -105325.000 | 3875.000 | 0.061 | 297075.000 | 289225.000 | 0.026 | 0.025 | 0.111 | 0.000 |

Confusion matrix:

| actual | pred_not_bad | pred_bad |
| --- | --- | --- |
| actual_not_bad | 103.000 | 2.000 |
| actual_bad | 250.000 | 21.000 |

## Hgb

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 376.000 | 9.000 | 0.279 | 0.000 | 0.000 | 0.000 | 0.770 | 0.765 |

Policy summary:

| model | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | exit_rate | baseline_bad_loss | policy_bad_loss | bad_loss_reduction | winner_giveback_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | -109200.000 | -109200.000 | 0.000 | 0.000 | 297075.000 | 297075.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Confusion matrix:

| actual | pred_not_bad | pred_bad |
| --- | --- | --- |
| actual_not_bad | 105.000 | 0.000 |
| actual_bad | 271.000 | 0.000 |
