# Combined Shadow ML Policy

## Summary

| entry_model | exit_model | target_model | baseline_total_pnl | policy_total_pnl | delta_vs_baseline_pnl | accepted_trade_ratio | positive_day_ratio | worst_day_delta_pnl | last_5_day_delta_pnl | last_5_non_negative_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hgb | hgb | hgb | -8325.000 | 59475.000 | 67800.000 | 0.946 | 0.667 | -7700.000 | 49525.000 | 4.000 |

## Day-wise PnL

| date | trade_count | baseline_pnl | policy_pnl | delta_pnl |
| --- | --- | --- | --- | --- |
| 2026-04-13 | 50.000 | 6100.000 | -1600.000 | -7700.000 |
| 2026-04-15 | 46.000 | -2825.000 | 5150.000 | 7975.000 |
| 2026-04-16 | 56.000 | 13225.000 | 31450.000 | 18225.000 |
| 2026-04-17 | 50.000 | -3500.000 | -3725.000 | -225.000 |
| 2026-04-20 | 51.000 | -5800.000 | 9700.000 | 15500.000 |
| 2026-04-21 | 42.000 | -9900.000 | -2350.000 | 7550.000 |
| 2026-04-22 | 46.000 | 11975.000 | 11125.000 | -850.000 |
| 2026-04-23 | 54.000 | -21975.000 | 925.000 | 22900.000 |
| 2026-04-24 | 52.000 | 4375.000 | 8800.000 | 4425.000 |

## Live Readiness

| gate | actual | threshold | passed | notes |
| --- | --- | --- | --- | --- |
| data_post_patch_days | 9.000 | >= 20 | 0.000 | Minimum post-patch trading days for live sign-off. |
| data_entry_ready_rows | 447.000 | >= 1200 | 0.000 | Entry filter sample size gate. |
| data_target_rows | 174.000 | >= 500 | 0.000 | Non-bad target-promotion sample size gate. |
| entry_bad_rate_reduction | 0.005 | >= 0.20 | 0.000 | Accepted trades should materially reduce bad-trade incidence. |
| entry_trade_retention | 0.946 | >= 0.60 | 1.000 | Avoid shrinking the strategy too much. |
| entry_non_bad_pnl_retention | 0.955 | >= 0.85 | 1.000 | Good trade gross should mostly survive the filter. |
| entry_total_pnl_delta | -2775.000 | > 0 | 0.000 | Shadow entry filter must add net PnL. |
| exit_bad_loss_reduction | 0.076 | >= 0.25 | 0.000 | Bad-trade loss should reduce materially. |
| exit_winner_giveback | 0.026 | <= 0.10 | 1.000 | Do not kill too much winner gross. |
| exit_total_pnl_delta | 20250.000 | > 0 | 1.000 | Exit layer must add net PnL. |
| exit_worst_day | 0.000 | >= -10000 | 1.000 | Single-day underperformance guardrail. |
| target_total_pnl_delta | 59050.000 | > 0 | 1.000 | Promotion layer must improve total counterfactual PnL. |
| target_positive_day_ratio | 0.778 | >= 0.60 | 1.000 | Promotion gains should be broad, not one-day only. |
| target_over_promotion_ratio | 0.560 | <= 0.40 | 0.000 | Over-promotion losses should stay well below runner gains. |
| combined_total_pnl_delta | 67800.000 | > 0 | 1.000 | End-to-end stack must beat realized baseline. |
| combined_positive_day_ratio | 0.667 | >= 0.60 | 1.000 | Combined stack should improve most days. |
| combined_worst_day | -7700.000 | >= -10000 | 1.000 | Single-day underperformance guardrail. |
| combined_last_5_days_stable | 4.000 | >= 4 of last 5 and total delta >= 0 | 1.000 | Simple recent-stability heuristic for shadow sign-off. |
