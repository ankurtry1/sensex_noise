# Bad Trade Exit Shadow Model (3s)

## Model Comparison

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | exit_rate | baseline_bad_loss | policy_bad_loss | bad_loss_reduction | winner_giveback_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 205.000 | 9.000 | 0.483 | 0.903 | 0.396 | 0.551 | 0.859 | 0.626 | -75050.000 | -54800.000 | 20250.000 | 0.351 | 164925.000 | 141900.000 | 0.140 | 0.108 | 0.333 | 0.000 |
| logistic | 205.000 | 9.000 | 0.424 | 0.883 | 0.323 | 0.473 | 0.842 | 0.616 | -75050.000 | -57500.000 | 17550.000 | 0.293 | 164925.000 | 143775.000 | 0.128 | 0.108 | 0.333 | -550.000 |

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
- `feat_pnl_3s`
- `feat_runup_3s`
- `feat_drawdown_3s`
- `feat_velocity_decay_ratio`
- `pre_or_post_1pm`
- `continuation_or_reversal`
- `call_or_put`

## Logistic

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | 205.000 | 9.000 | 0.424 | 0.883 | 0.323 | 0.473 | 0.842 | 0.616 |

Policy summary:

| model | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | exit_rate | baseline_bad_loss | policy_bad_loss | bad_loss_reduction | winner_giveback_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| logistic | -75050.000 | -57500.000 | 17550.000 | 0.293 | 164925.000 | 143775.000 | 0.128 | 0.108 | 0.333 | -550.000 |

Confusion matrix:

| actual | pred_not_bad | pred_bad |
| --- | --- | --- |
| actual_not_bad | 34.000 | 7.000 |
| actual_bad | 111.000 | 53.000 |

## Hgb

| model | eval_rows | eval_days | accuracy | precision_bad | recall_bad | f1_bad | pr_auc_bad | mean_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | 205.000 | 9.000 | 0.483 | 0.903 | 0.396 | 0.551 | 0.859 | 0.626 |

Policy summary:

| model | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | exit_rate | baseline_bad_loss | policy_bad_loss | bad_loss_reduction | winner_giveback_ratio | positive_day_ratio | worst_day_delta_pnl |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | -75050.000 | -54800.000 | 20250.000 | 0.351 | 164925.000 | 141900.000 | 0.140 | 0.108 | 0.333 | 0.000 |

Confusion matrix:

| actual | pred_not_bad | pred_bad |
| --- | --- | --- |
| actual_not_bad | 34.000 | 7.000 |
| actual_bad | 99.000 | 65.000 |
