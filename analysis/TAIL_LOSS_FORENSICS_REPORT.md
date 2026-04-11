# Tail Loss Forensics Report (2026-03-19)

## Baseline recap
- Dataset date: **2026-03-19** from `logs/trades.jsonl` (other log files contain no events for this date).
- Closed trades: **49**
- Target hits: **42**
- Manual exits: **3**
- Time-stop after 1PM exits: **4**
- Baseline net PnL: **-428,880.00**
- Baseline expectancy (avg PnL/trade): **-8,752.65**
- Baseline max loss: **-316,414.00**

## Tail-loss anatomy
Top 10 worst trades by realized PnL:

| trade_id | signal_kind | direction | entry_time | exit_reason | realized_pnl | max_drawdown_points | holding_seconds |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| BFO:SENSEX2631974900CE|2026-03-19T12:55:06.308630 | CONTINUATION_CALL | CALL | 2026-03-19 12:55:06.308630 | MANUAL_EXIT | -316414.00 | 170.95 | 1747.48 |\n| BFO:SENSEX2631975100PE|2026-03-19T10:20:02.358870 | CONTINUATION_PUT | PUT | 2026-03-19 10:20:02.358870 | MANUAL_EXIT | -176320.00 | 129.70 | 472.30 |\n| BFO:SENSEX2631975100PE|2026-03-19T10:00:09.117322 | REVERSAL_PUT | PUT | 2026-03-19 10:00:09.117322 | MANUAL_EXIT | -84609.00 | 59.95 | 257.57 |\n| BFO:SENSEX2631974400CE|2026-03-19T14:35:04.267412 | CONTINUATION_CALL | CALL | 2026-03-19 14:35:04.267412 | TIME_STOP_AFTER_1PM | -37492.00 | 24.00 | 60.77 |\n| BFO:SENSEX2631974400CE|2026-03-19T14:45:20.283498 | CONTINUATION_CALL | CALL | 2026-03-19 14:45:20.283498 | TIME_STOP_AFTER_1PM | -22022.00 | 20.80 | 61.14 |\n| BFO:SENSEX2631974700PE|2026-03-19T14:30:05.937477 | CONTINUATION_PUT | PUT | 2026-03-19 14:30:05.937477 | TIME_STOP_AFTER_1PM | -22010.00 | 33.00 | 60.94 |\n| BFO:SENSEX2631975000PE|2026-03-19T13:25:01.152512 | CONTINUATION_PUT | PUT | 2026-03-19 13:25:01.152512 | TIME_STOP_AFTER_1PM | -13673.00 | 20.25 | 60.08 |\n| BFO:SENSEX2631975400PE|2026-03-19T09:30:12.814187 | CONTINUATION_PUT | PUT | 2026-03-19 09:30:12.814187 | TARGET_HIT | 4200.00 | 0.00 | 1.10 |\n| BFO:SENSEX2631974700CE|2026-03-19T09:55:26.427574 | REVERSAL_CALL | CALL | 2026-03-19 09:55:26.427574 | TARGET_HIT | 4200.00 | 5.75 | 15.48 |\n| BFO:SENSEX2631974800CE|2026-03-19T10:30:01.465720 | CONTINUATION_CALL | CALL | 2026-03-19 10:30:01.465720 | TARGET_HIT | 4200.00 | 0.00 | 3.30 |

Top 10 worst trades by drawdown:

| trade_id | signal_kind | direction | entry_time | exit_reason | max_drawdown_points | realized_pnl | holding_seconds |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n| BFO:SENSEX2631974900CE|2026-03-19T12:55:06.308630 | CONTINUATION_CALL | CALL | 2026-03-19 12:55:06.308630 | MANUAL_EXIT | 170.95 | -316414.00 | 1747.48 |\n| BFO:SENSEX2631975100PE|2026-03-19T10:20:02.358870 | CONTINUATION_PUT | PUT | 2026-03-19 10:20:02.358870 | MANUAL_EXIT | 129.70 | -176320.00 | 472.30 |\n| BFO:SENSEX2631975100PE|2026-03-19T10:00:09.117322 | REVERSAL_PUT | PUT | 2026-03-19 10:00:09.117322 | MANUAL_EXIT | 59.95 | -84609.00 | 257.57 |\n| BFO:SENSEX2631975000CE|2026-03-19T10:40:10.409532 | CONTINUATION_CALL | CALL | 2026-03-19 10:40:10.409532 | TARGET_HIT | 50.90 | 5280.00 | 280.83 |\n| BFO:SENSEX2631975200PE|2026-03-19T12:35:04.789148 | CONTINUATION_PUT | PUT | 2026-03-19 12:35:04.789148 | TARGET_HIT | 33.85 | 6300.00 | 363.67 |\n| BFO:SENSEX2631974700PE|2026-03-19T14:30:05.937477 | CONTINUATION_PUT | PUT | 2026-03-19 14:30:05.937477 | TIME_STOP_AFTER_1PM | 33.00 | -22010.00 | 60.94 |\n| BFO:SENSEX2631974500PE|2026-03-19T14:55:00.444246 | CONTINUATION_PUT | PUT | 2026-03-19 14:55:00.444246 | TARGET_HIT | 25.55 | 8880.00 | 45.23 |\n| BFO:SENSEX2631974400CE|2026-03-19T14:35:04.267412 | CONTINUATION_CALL | CALL | 2026-03-19 14:35:04.267412 | TIME_STOP_AFTER_1PM | 24.00 | -37492.00 | 60.77 |\n| BFO:SENSEX2631974800CE|2026-03-19T11:55:18.019630 | CONTINUATION_CALL | CALL | 2026-03-19 11:55:18.019630 | TARGET_HIT | 21.30 | 5580.00 | 52.68 |\n| BFO:SENSEX2631974400CE|2026-03-19T14:45:20.283498 | CONTINUATION_CALL | CALL | 2026-03-19 14:45:20.283498 | TIME_STOP_AFTER_1PM | 20.80 | -22022.00 | 61.14 |

Manual + time-stop loss bucket summary:
- Trades in bucket: **7**
- Net PnL from bucket: **-672,540.00**
- Median holding time (s): **61.14**
- Median max drawdown (pts): **33.00**

## What catastrophic losers looked like before they became catastrophic
Observed recurring pre-loss signatures (from per-trade forensic reconstruction):
- Premium confirmation failure within first 10-15s (`runup_10s < +1`) appears frequently in the worst-loss set.
- Early adverse move (first `-1`/`-2` points) often arrived quickly in large losers.
- Early-failure flag was directionally useful but not sufficient by itself.
- Many severe losses were **not** immediate straight-line drops; they often spent time near entry and then expanded after waiting.
- Spot-trigger reversion cannot be directly measured from current logs because post-entry spot ticks are missing.

## Best standalone kill-switch candidates

| policy_id | trades_affected | winners_cut_early | losers_cut_early | new_net_pnl | delta_net_pnl_vs_baseline | new_max_loss | tail_loss_reduction_pct | target_hit_change |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| DROP_1_WITHIN_10S | 30 | 23 | 7 | -30654.00 | 398226.00 | -14641.00 | 0.95 | -23 |\n| DROP_1_WITHIN_15S | 30 | 23 | 7 | -30654.00 | 398226.00 | -14641.00 | 0.95 | -23 |\n| DD_5_WITHIN_20S | 18 | 11 | 7 | -58471.00 | 370409.00 | -21204.00 | 0.86 | -11 |\n| DD_3_WITHIN_15S | 24 | 17 | 7 | -64464.00 | 364416.00 | -15759.00 | 0.89 | -17 |\n| DD_2_WITHIN_10S | 27 | 20 | 7 | -72159.00 | 356721.00 | -15759.00 | 0.90 | -20 |\n| MFE_LT_0_5_BY_10S | 8 | 2 | 6 | -205415.00 | 223465.00 | -316414.00 | 0.35 | -2 |\n| NO_PLUS_0_5_BY_5S | 17 | 11 | 6 | -222123.00 | 206757.00 | -316414.00 | 0.44 | -11 |\n| NO_PLUS_1_BY_10S | 9 | 3 | 6 | -238767.00 | 190113.00 | -316414.00 | 0.35 | -3 |\n| CONT_PUT_NO_PLUS_1_BY_10S | 4 | 1 | 3 | -296183.00 | 132697.00 | -316414.00 | 0.21 | -1 |\n| NO_PLUS_1_BY_15S | 7 | 1 | 6 | -305991.00 | 122889.00 | -316414.00 | 0.23 | -1 |

Robustness labels (one-day sample discipline):
- `DROP_1_WITHIN_10S`: strong | sample=30 | delta_net=398,226.00 | likely overfit risk=moderate
- `DROP_1_WITHIN_15S`: strong | sample=30 | delta_net=398,226.00 | likely overfit risk=moderate
- `DD_5_WITHIN_20S`: strong | sample=18 | delta_net=370,409.00 | likely overfit risk=moderate
- `DD_3_WITHIN_15S`: strong | sample=24 | delta_net=364,416.00 | likely overfit risk=moderate
- `DD_2_WITHIN_10S`: strong | sample=27 | delta_net=356,721.00 | likely overfit risk=moderate

## Best composite kill-switch candidates

| policy_id | trades_affected | entries_skipped | winners_cut_early | losers_cut_early | new_net_pnl | delta_net_pnl_vs_baseline | new_max_loss | tail_loss_reduction_pct | target_hit_change |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| COMP_NO_ENTRY_AFTER_1230 | 19 | 19 | 0 | 0 | -116809.00 | 312071.00 | -176320.00 | 0.62 | -14 |\n| COMP_DD3_15_AND_WEAK_CONFIRM | 9 | 0 | 3 | 6 | -184072.00 | 244808.00 | -316414.00 | 0.42 | -3 |\n| COMP_TIGHT_CONT_CALL | 12 | 0 | 9 | 3 | -194277.00 | 234603.00 | -176320.00 | 0.52 | -9 |\n| COMP_POST_1PM_FILTER_PLUS_WEAK | 20 | 15 | 3 | 2 | -231989.00 | 196891.00 | -316414.00 | 0.48 | -14 |\n| COMP_EF_AND_NO_PLUS1_10 | 7 | 0 | 2 | 5 | -417365.00 | 11515.00 | -316414.00 | 0.03 | -2 |

## What appears specific to continuation_call trades
- Continuation call trades: **16**
- Losing continuation call trades: **3**
- Continuation call net PnL: **-302,368.00**
- Median drawdown for continuation call losers (pts): **24.00**
- Practical implication: continuation_call-specific tight invalidation is justified as a **suggestive** control on this sample, but still at high overfit risk if hardcoded to a single threshold.

## Time-of-day conclusions
- Post-1PM exits are a small count but disproportionately represented in negative tail outcomes.
- Entry-cutoff style policies (no new trades after 12:30 or 1PM) should be evaluated as risk controls even if they reduce total target-hit count.
- Time-of-day filters alone are unlikely to be sufficient; combining with early premium weakness improves tail control.

## What should be implemented next in live strategy logic
1. Add a configurable early invalidation module (time-window + min confirmation + max adverse excursion).
2. Add continuation_call-specific stricter invalidation than reversal/put variants.
3. Add post-12:30 and post-1PM adaptive limits (either no-entry or tighter kill-switch).
4. Keep thresholds in broad bands (`~10-15s`, `~1-3 points`) instead of brittle exact values.

## What additional logging is needed for stronger future testing
- Underlying spot tick stream during open trades, with trigger-distance over time.
- Explicit trigger event timestamp (not just entry timestamp).
- Bid/ask spread and depth snapshots at entry and during first 30 seconds.
- Order-state timestamps (placed, acknowledged, filled) for both entry and exit.
- Latency metrics and quote staleness markers.

## Risk markers vs hard invalidation features

| feature | class | sample_size | delta_net | tail_reduction_pct | reason |\n| --- | --- | --- | --- | --- | --- |\n| DROP_1_WITHIN_10S | not useful / inconclusive | 30 | 398226.00 | 0.95 | losers_cut=7, winners_cut=23 |\n| DROP_1_WITHIN_15S | not useful / inconclusive | 30 | 398226.00 | 0.95 | losers_cut=7, winners_cut=23 |\n| DD_5_WITHIN_20S | not useful / inconclusive | 18 | 370409.00 | 0.86 | losers_cut=7, winners_cut=11 |\n| DD_3_WITHIN_15S | not useful / inconclusive | 24 | 364416.00 | 0.89 | losers_cut=7, winners_cut=17 |\n| DD_2_WITHIN_10S | not useful / inconclusive | 27 | 356721.00 | 0.90 | losers_cut=7, winners_cut=20 |\n| NO_PLUS_0_5_BY_5S | not useful / inconclusive | 17 | 206757.00 | 0.44 | losers_cut=6, winners_cut=11 |\n| DROP_1_WITHIN_5S | not useful / inconclusive | 28 | 95843.00 | 0.47 | losers_cut=6, winners_cut=22 |\n| REV_CALL_NO_PLUS_1_BY_10S | not useful / inconclusive | 1 | -7490.00 | -0.01 | losers_cut=0, winners_cut=1 |\n| EARLY_FAIL_NO_RECOVERY_10S | not useful / inconclusive | 8 | -26894.00 | 0.03 | losers_cut=5, winners_cut=3 |\n| POST_1PM_DD_2_WITHIN_10S | not useful / inconclusive | 9 | -30571.00 | 0.06 | losers_cut=4, winners_cut=5 |\n| EARLY_FAIL_NO_RECOVERY_15S | not useful / inconclusive | 6 | -31932.00 | 0.01 | losers_cut=5, winners_cut=1 |\n| MFE_LT_0_5_BY_10S | strong hard-exit candidate | 8 | 223465.00 | 0.35 | losers_cut=6, winners_cut=2 |\n| NO_PLUS_1_BY_10S | strong hard-exit candidate | 9 | 190113.00 | 0.35 | losers_cut=6, winners_cut=3 |\n| CONT_PUT_NO_PLUS_1_BY_10S | weak but useful warning indicator | 4 | 132697.00 | 0.21 | losers_cut=3, winners_cut=1 |\n| MFE_LT_1_BY_15S | weak but useful warning indicator | 7 | 122889.00 | 0.23 | losers_cut=6, winners_cut=1 |\n| NO_PLUS_1_BY_15S | weak but useful warning indicator | 7 | 122889.00 | 0.23 | losers_cut=6, winners_cut=1 |\n| REV_PUT_NO_PLUS_1_BY_10S | weak but useful warning indicator | 1 | 62252.00 | 0.09 | losers_cut=1, winners_cut=0 |\n| DD_8_WITHIN_20S | weak but useful warning indicator | 11 | 49546.00 | 0.28 | losers_cut=6, winners_cut=5 |\n| POST_1230_NO_PLUS_1_BY_10S | weak but useful warning indicator | 4 | 7959.00 | 0.01 | losers_cut=4, winners_cut=0 |\n| CONT_CALL_NO_PLUS_1_BY_10S | weak but useful warning indicator | 3 | 2654.00 | 0.05 | losers_cut=2, winners_cut=1 |

Notes:
- All findings are from a **single day (n=49)** and should be treated as exploratory.
- Recommendations with small affected sample sizes should be considered **suggestive/weak** until multi-day validation confirms stability.
